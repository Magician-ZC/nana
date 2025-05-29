from llm import LLMService
from typing import List, Dict, Tuple
import os
from datetime import datetime
from conversation import ConversationHistory
from user_info_processor import UserInfoProcessor
from intent_extractor import IntentExtractor
import asyncio
import json
import logging

class MainAgent:
    def __init__(self, llm_service: LLMService, conversation_history: ConversationHistory, user_id="default_user"):
        self.conversation_history = conversation_history
        self.llm_service = llm_service
        self.current_agent = "nanaA"  # 默认使用娜娜A
        self.prompt_template = ""  # 用于存储自定义提示词
        self._load_prompt_template()
        self.user_id = user_id
            
        # 确保日志和个人信息目录存在
        self.log_dir = 'save/log'
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 为当前用户创建专属目录
        self.user_dir = os.path.join('save', user_id)
        os.makedirs(self.user_dir, exist_ok=True)
        
        # 初始化用户信息处理器和意图提取器
        self.user_info_file = os.path.join(self.user_dir, 'me.txt')
        self.user_info_processor = UserInfoProcessor(self.user_info_file)
        self.intent_extractor = IntentExtractor()
        
        # 获取用户信息
        self.user_info = self.user_info_processor.user_info
    
    def change_user(self, user_id):
        """切换当前用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否成功切换
        """
        if not user_id:
            return False
            
        # 更新用户ID
        self.user_id = user_id
        
        # 为新用户创建专属目录
        self.user_dir = os.path.join('save', user_id)
        os.makedirs(self.user_dir, exist_ok=True)
        
        # 更新用户信息文件路径
        self.user_info_file = os.path.join(self.user_dir, 'me.txt')
        
        # 重新初始化用户信息处理器
        self.user_info_processor = UserInfoProcessor(self.user_info_file)
        
        # 更新用户信息
        self.user_info = self.user_info_processor.user_info
        
        return True
    
    def _load_prompt_template(self):
        """根据当前选择的智能体加载对应的提示词模板"""
        prompt_file = f'prompts/{self.current_agent}.txt'
        if not os.path.exists(prompt_file):
            prompt_file = 'prompts/nanaA.txt'  # 回退到默认模板
            
        with open(prompt_file, 'r', encoding='utf-8') as file:
            self.prompt_template = file.read()
    
    def set_agent(self, agent_name: str) -> bool:
        """设置当前使用的智能体
        
        Args:
            agent_name: 智能体名称（nanaA, nanaB, nanaC）
            
        Returns:
            bool: 是否成功切换
        """
        if agent_name not in ["nanaA", "nanaB", "nanaC"]:
            return False
            
        self.current_agent = agent_name
        self._load_prompt_template()
        return True

    def set_custom_agent(self, prompt: str, config: dict) -> bool:
        """设置自定义智能体
        
        Args:
            prompt: 自定义提示词
            config: 配置信息
            
        Returns:
            bool: 是否成功设置
        """
        try:
            # 设置当前智能体名称
            self.current_agent = config.get("id", "custom_agent")
            print(f"设置自定义智能体: {self.current_agent}")
            
            # 读取提示词模板
            template_path = os.path.join("backend", "prompts", "prompt_template.txt")
            if not os.path.exists(template_path):
                template_path = os.path.join("prompts", "prompt_template.txt")
            
            # 确保模板文件存在
            if os.path.exists(template_path):
                with open(template_path, "r", encoding="utf-8") as f:
                    template = f.read()
                    
                # 检查自定义提示词是否只包含特殊标记或为空
                if prompt.strip() == "/no_think" or not prompt.strip():
                    # 如果只有特殊标记或为空，则使用基本角色设定 + 模板
                    name = config.get("name", "心理咨询师")
                    desc = config.get("description", "一名专业的心理咨询师")
                    
                    # 构建基本角色设定
                    basic_prompt = f"你是{name}，{desc}。"
                    self.prompt = basic_prompt + "\n\n" + template
                    print(f"使用基本角色设定 + 模板: {basic_prompt}")
                else:
                    # 使用远端提示词 + 模板，保留远端提示词的角色设定
                    print(f"使用远端提示词 + 模板")
                    
                    # 添加连接语，确保远端提示词与模板之间有明确分隔
                    connector = "\n\n----- 以下是回复格式要求 -----\n\n"
                    
                    # 远端提示词 + 连接语 + 模板
                    self.prompt = prompt + connector + template
            else:
                # 如果找不到模板，则直接使用远端提示词
                self.prompt = prompt
                print("未找到提示词模板，使用原始远端提示词")
            
            # 设置智能体配置
            self.agent_config = config
            
            print(f"自定义智能体配置: {json.dumps(config, ensure_ascii=False)}")
            print(f"提示词长度: {len(self.prompt)}")
            return True
        except Exception as e:
            print(f"设置自定义智能体失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _is_meaningless_input(self, message: str) -> bool:
        """检测输入是否为无意义内容
        
        检测标准:
        1. 纯数字或主要由数字组成的消息
        2. 太短的消息(1-2个字符)
        3. 重复的字符或词组
        4. 明显的随机字符串
        5. 无意义的随机中文字符串
        
        Args:
            message: 用户输入消息
            
        Returns:
            bool: 是否为无意义内容
        """
        # 去除空白字符
        message = message.strip()
        
        # 检查是否为空消息
        if not message:
            return True
            
        # 检查是否过短(少于3个字符)
        if len(message) < 3:
            return True
            
        # 检查是否纯数字或主要由数字组成
        digit_count = sum(c.isdigit() for c in message)
        if digit_count / len(message) > 0.5:  # 数字占比超过50%
            return True
            
        # 检查是否有过多重复字符
        if len(set(message)) < len(message) * 0.3:  # 不同字符占比低于30%
            return True
            
        # 检查是否缺少有意义的中文或英文单词
        has_chinese = any('\u4e00' <= c <= '\u9fff' for c in message)
        has_meaningful_text = False
        
        # 常见的中文虚词和连词，这些词通常会出现在有意义的中文句子中
        chinese_common_words = ["的", "是", "了", "在", "我", "有", "和", "就", "不", "人", "都", 
                               "一", "一个", "上", "也", "很", "到", "说", "要", "这", "你", "会", 
                               "着", "没有", "看", "好", "自己", "那", "么", "她", "他", "们"]
        
        if has_chinese:
            # 检查是否包含常见中文虚词
            if any(word in message for word in chinese_common_words):
                has_meaningful_text = True
            else:
                # 中文消息中至少要有2个连续的中文字符
                for i in range(len(message) - 1):
                    if '\u4e00' <= message[i] <= '\u9fff' and '\u4e00' <= message[i+1] <= '\u9fff':
                        has_meaningful_text = True
                        break
                
                # 对于短句（3-6个字符）的随机中文，尝试增加额外的检查
                if has_meaningful_text and 3 <= len(message) <= 6 and all('\u4e00' <= c <= '\u9fff' for c in message):
                    # 对于全中文短句，如果没有常见词，可能是随机字符
                    if not any(word in message for word in chinese_common_words):
                        # 额外检查：字符的组合是否看起来随机
                        # 计算字符熵
                        from collections import Counter
                        import math
                        
                        char_counts = Counter(message)
                        entropy = -sum((count / len(message)) * math.log(count / len(message), 2) 
                                    for count in char_counts.values())
                        
                        # 熵值高意味着字符组合更随机
                        if entropy > 2.0:  # 熵阈值设为2.0，可根据需要调整
                            has_meaningful_text = False
        
        # 如果没有有意义的文本，认为是无意义输入
        if not has_meaningful_text:
            return True
            
        return False

    def _log_conversation(self, role: str, content: str) -> None:
        """记录对话到日志文件"""
        current_date = datetime.now().strftime('%Y%m%d')
        current_time = datetime.now().strftime('%H:%M:%S')
        log_file = os.path.join(self.log_dir, f'{current_date}.txt')
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f'[{current_time}] {role.capitalize()}: {content}\n')
        
    async def reply(self, message: str, personality: str = None, is_category: bool = False) -> Tuple[str, str]:
        """根据用户消息生成回复
        
        Args:
            message: 用户消息
            personality: 智能体的性格描述
            is_category: 是否是快捷提问类别
            
        Returns:
            Tuple[str, str]: (回复文本, 表情)
        """
        try:
            # 检查是否是无意义输入
            if self._is_meaningless_input(message):
                print(f"检测到无意义输入: {message}")
                return "请说点有意义的内容吧", "生气"
            
            # 获取相关记忆
            if is_category:
                memory_text = self._get_relevant_category_memories(message)
            else:
                memory_text = self._get_relevant_memories(message)
            print(f"相关记忆: {memory_text}")
            
            # 获取上下文
            context = self.conversation_history.get_context()
            
            # 生成回复（带有上下文）
            reply_content, expression = await self._generate_reply_with_context(
                message=message,
                context=context,
                memory_text=memory_text,
                personality=personality,
                is_category=is_category
            )
            
            # 添加对话到历史记录
            await self._handle_successful_reply(message, reply_content, is_category)
            
            # 触发后台处理对话摘要（不阻塞主流程）
            if len(self.conversation_history.turns) >= 10:
                asyncio.create_task(self._process_dialog_summary_with_timeout())
            
            return reply_content, expression
            
        except Exception as e:
            print(f"生成回复时出错: {e}")
            import traceback
            traceback.print_exc()
            
            # 返回一个简单的错误回复
            return "抱歉，我遇到了一些问题，能再说一遍吗？", "眼泪"

    async def _process_dialog_summary(self, turns_count):
        """异步处理对话总结任务，避免阻塞主回复流程
        
        Args:
            turns_count: 当前对话轮数
        """
        # 创建一个超时控制，避免此任务无限期阻塞
        try:
            # 使用asyncio.shield保护任务不被外部取消
            await asyncio.shield(self._process_dialog_summary_with_timeout())
        except asyncio.TimeoutError:
            print("对话总结任务超时，已在后台继续处理")
        except Exception as e:
            print(f"处理对话总结时发生未处理的错误: {e}")
            # 错误已记录，但不会影响主对话流程

    async def _process_dialog_summary_with_timeout(self):
        """带超时控制的对话总结处理"""
        try:
            # 创建一个有超时的任务
            async with asyncio.timeout(30):  # 30秒超时，避免长时间阻塞
                try:
                    # 触发归档并获取总结
                    summary_profile = await self.conversation_history._auto_archive(self.user_info_processor)
                    
                    if summary_profile:
                        # 确保更新用户信息
                        print("从归档总结更新用户信息")
                        updated_info = self.user_info_processor._load_user_info()  # 使用_load_user_info代替get_user_info
                        if updated_info != self.user_info:
                            print("用户信息已更新")
                            self.user_info = updated_info
                        
                        # 在用户下一次提问后，将总结作为系统消息添加到对话历史
                        await self.conversation_history.add_dialog("SYSTEM_GUIDANCE", 
                            f"【系统消息】根据我们的对话，我整理了一些要点：\n\n{summary_profile}", 
                            None)
                        
                        print("对话总结已添加到对话历史，将在用户下一次提问后显示")
                    else:
                        print("对话归档未返回总结，可能是处理失败或无需总结")
                except Exception as e:
                    print(f"处理对话总结时发生错误: {e}")
                    # 捕获所有异常但不抛出，防止影响主对话流程
        except asyncio.CancelledError:
            # 如果任务被取消，记录但不抛出异常
            print("对话总结任务被取消")
        except Exception as e:
            # 捕获所有其他类型的异常
            print(f"对话总结处理中发生异常: {e}")
            # 不再继续传播异常

    async def _generate_reply(self, message: str, memory_text: str = "无补充信息", personality: str = None, is_category: bool = False) -> Tuple[str, str]:
        """生成回复的核心方法
        
        Args:
            message: 用户消息
            memory_text: 相关记忆文本
            personality: 可选的性格描述，用于调整回复风格
            is_category: 是否是快捷提问类别
            
        Returns:
            Tuple[str, str]: (回复内容, 表情)
        """
        # 准备prompt
        context = self.conversation_history.get_context()
        
        # 调用带上下文的方法
        return await self._generate_reply_with_context(message, context, memory_text, personality, is_category)

    async def _generate_reply_with_context(self, message: str, context: str, memory_text: str = "无补充信息", personality: str = None, is_category: bool = False) -> Tuple[str, str]:
        """生成带上下文的回复
        
        Args:
            message: 用户消息
            context: 对话上下文
            memory_text: 相关记忆文本
            personality: 智能体的性格描述
            is_category: 是否是快捷提问类别
            
        Returns:
            Tuple[str, str]: (回复文本, 表情)
        """
        try:
            # 准备给LLM的提示词
            prompt = self.prompt.format(
                user_info=self.user_info_processor.user_info if self.user_info_processor else "",
                chat_history=context,
                user_message=message,
                memory=memory_text
            )
            
            # 记录提示词长度
            print(f"提示词长度: {len(prompt)}")
            
            # 根据是否快捷提问类别和人格描述，调整调用LLM的参数
            if is_category:
                # 如果是快捷提问类别，调用LLM生成回复
                raw_response = await self.llm_service.async_chat(prompt, max_tokens=2048, temperature=0.7)
            else:
                # 否则，生成更简短的回复
                raw_response = await self.llm_service.async_chat(prompt, max_tokens=100, temperature=0.9)
            
            # 记录LLM原始回复
            print(f"LLM原始回复: {raw_response}")
            
            # 尝试解析回复的JSON格式
            parsed_response = self._parse_response(raw_response)
            
            # 如果解析失败，尝试修复格式
            if not parsed_response:
                # 尝试修复JSON格式
                fixed_response = self._fix_response_format(raw_response)
                parsed_response = self._parse_response(fixed_response)
                
                # 如果仍然解析失败，构造一个默认回复
                if not parsed_response:
                    # 提供默认回复
                    parsed_response = {
                        "reply": raw_response.strip() if raw_response else "我理解了，请继续。",
                        "expression": "nn眼"
                    }
            
            # 提取回复和表情
            reply_content = parsed_response.get("reply", "")
            expression = parsed_response.get("expression", "nn眼")
            
            # 记录处理后的回复
            print(f"处理后的纯文本回复: {reply_content}")
            
            return reply_content, expression
            
        except Exception as e:
            print(f"生成回复时出错: {e}")
            import traceback
            traceback.print_exc()
            
            # 返回默认回复
            return "抱歉，我遇到了一些问题，能再说一遍吗？", "眼泪"

    def _get_relevant_memories(self, message: str) -> str:
        """获取相关记忆"""
        try:
            memories = self.conversation_history.retrieve(message, n_results=2)
            if not memories:
                return "无补充信息"
                
            # 合并所有记忆，去除重复信息
            combined_memory = {}
            for memory in memories:
                # 解析记忆文本
                lines = memory.split('\n')
                for line in lines:
                    if '：' in line or ':' in line:
                        try:
                            key, value = line.replace('：', ':').split(':', 1)
                            key = key.strip()
                            value = value.strip()
                            if key and value:
                                combined_memory[key] = value
                        except Exception as e:
                            # 解析单行失败不应影响整体功能
                            logging.warning(f"解析记忆行时出错: {line}, 错误: {e}")
                            continue
            
            # 格式化输出
            if combined_memory:
                return "用户画像信息：\n" + "\n".join(f"{k}: {v}" for k, v in combined_memory.items())
            return "无补充信息"
        except Exception as e:
            # 记录错误但不影响聊天流程
            logging.error(f"获取相关记忆时出错: {str(e)}")
            return "无补充信息"

    def _get_relevant_category_memories(self, category: str) -> str:
        """获取与特定类别相关的记忆
        
        Args:
            category: 快捷提问类别
            
        Returns:
            str: 相关记忆文本
        """
        # 类别与关键词映射
        category_keywords = {
            "情感咨询师": ["情感", "恋爱", "喜欢", "爱情", "失恋"],
            "人际关系": ["朋友", "同学", "关系", "相处", "冲突", "沟通", "欺负", "孤立"],
            "学业问题": ["考试", "成绩", "学习", "课程", "作业", "论文", "学校"],
            "就业与职业规划压力": ["工作", "就业", "面试", "职业", "简历", "职场", "压力"],
            "精神健康障碍": ["焦虑", "抑郁", "失眠", "疲惫", "压力", "精神", "心理"],
            "自我认同与价值观冲突": ["自我", "价值", "意义", "冲突", "困惑", "方向", "认同"],
            "突发事件与危机情景": ["危机", "紧急", "突发", "事故", "创伤", "危险"]
        }
        
        # 首先检查用户信息中是否包含相关关键词
        if not self.user_info:
            return "无补充信息"
            
        # 获取当前类别的关键词
        keywords = category_keywords.get(category, [])
        if not keywords:
            return "无补充信息"
            
        # 在用户信息中搜索相关关键词
        relevant_info = []
        user_info_lines = self.user_info.split('\n')
        
        for line in user_info_lines:
            if any(keyword in line.lower() for keyword in keywords):
                relevant_info.append(line)
                
        if relevant_info:
            return "用户相关信息：\n" + "\n".join(relevant_info)
            
        return "无补充信息"

    async def _handle_successful_reply(self, message: str, reply_content: str, is_category: bool) -> None:
        """处理成功的回复"""
        # 记录助手回复并添加到对话历史
        self._log_conversation('assistant', reply_content)
        await self.conversation_history.add_dialog(message, reply_content, self.user_info_processor)
        print(f"对话已添加到历史记录，当前对话历史长度: {len(self.conversation_history.turns)}")
        
        # 在快速提问模式下不发送引导决策消息，因为现在使用xinli_agent管理整个引导过程
        if not is_category:
            # 检查是否需要发送引导决策的消息
            context = self.conversation_history.get_context()
            is_user_decision, _, _ = self.intent_extractor.recognizer.check_if_user_decision(message, context)
            
            # 如果是类别提问且不是用户决策的回复，则发送引导决策消息
            if message in ["情感咨询师", "人际关系", "学业问题", "就业与职业规划压力", 
                          "精神健康障碍", "自我认同与价值观冲突", "突发事件与危机情景"] and not is_user_decision:
                # 准备引导决策的消息模板
                guidance_templates = {
                    "nanaA": [
                        "你打算怎么做？", 
                        "你会选择哪种方式？", 
                        "你是打算接受还是拒绝？",
                        "你想要尝试一下吗？"
                    ],
                    "nanaB": [
                        "接下来你打算采取什么行动呢？", 
                        "在这些选择中，你更倾向于哪一种方案？",
                        "你对这个建议有什么想法呢？",
                        "听完我的建议，你是否已经有了决定？"
                    ],
                    "nanaC": [
                        "你觉得怎么样呀？想不想试试看这个方法？", 
                        "你会选择哪种方式处理这个问题呢？告诉我吧！",
                        "听完我说的，你有什么想法呀？快告诉我吧~",
                        "你决定好要怎么做了吗？分享给我听听吧！"
                    ]
                }
                
                # 根据当前使用的智能体选择合适的引导模板
                templates = guidance_templates.get(self.current_agent, guidance_templates["nanaA"])
                import random
                guidance_message = random.choice(templates)
                
                # 记录引导决策的消息
                self._log_conversation('assistant', guidance_message)
                
                # 将引导消息信息保存到conversation_history中的临时属性中，供后续TTS使用
                self.conversation_history.last_guidance_message = guidance_message
                
                # 将引导消息添加到对话历史
                # 注意：这里不触发归档，所以不传递user_info_processor
                await self.conversation_history.add_dialog(message="SYSTEM_GUIDANCE", reply=guidance_message)
        
        # 启动异步任务处理用户信息同步
        asyncio.create_task(self._process_user_info_sync(message, False))  # 在快速提问模式中不更新用户画像

    async def _process_user_info_sync(self, message, is_user_decision):
        """异步处理用户信息同步，不阻塞主回复流程
        
        Args:
            message: 用户消息
            is_user_decision: 是否是用户决策
        """
        try:
            # 检查是否有用户做出决策，如果有则强制同步
            force_update = is_user_decision
            
            # 每5次对话强制进行一次同步
            if len(self.conversation_history.turns) % 5 == 0:
                force_update = True
                print("每5次对话强制同步一次用户信息")
            
            if force_update:
                print("强制同步用户信息")
                synced = await self.conversation_history.sync_profile_to_user_info(self.user_info_processor, force_update)
                if synced:
                    # 更新内存中的用户信息
                    self.user_info = self.user_info_processor.user_info
                    print("成功将对话归纳总结同步到用户信息")
                    print("更新后的用户信息:")
                    print(self.user_info)
        except Exception as e:
            print(f"同步用户信息时出错: {e}")

    def _extract_recent_context(self, context: str, num_turns: int = 5) -> str:
        """从完整对话上下文中提取最近的几轮对话
        
        Args:
            context: 完整的对话上下文文本
            num_turns: 要提取的对话轮数
            
        Returns:
            str: 提取的最近几轮对话
        """
        lines = context.strip().split('\n')
        
        # 查找用户和助手的对话行
        dialogue_lines = []
        for line in lines:
            if line.startswith('用户:') or line.startswith('助手:'):
                dialogue_lines.append(line)
        
        # 提取最后num_turns轮对话（每轮包含用户和助手各一次发言）
        recent_lines = []
        if len(dialogue_lines) <= num_turns * 2:
            # 如果总行数不足num_turns轮，直接返回全部
            recent_lines = dialogue_lines
        else:
            # 否则提取最后num_turns轮
            recent_lines = dialogue_lines[-num_turns*2:]
        
        # 重新组合成文本
        recent_context = '\n'.join(recent_lines)
        
        return recent_context

    def _is_off_topic(self, message: str, context: str) -> bool:
        """检测用户回复是否偏离主题
        
        Args:
            message: 用户消息
            context: 对话上下文
            
        Returns:
            bool: 是否偏离主题
        """
        # 获取对话上下文的最后几轮
        lines = context.strip().split('\n')
        last_turns = []
        for i in range(len(lines)-1, -1, -1):
            if i > 0 and lines[i].startswith('用户：') and lines[i-1].startswith('助手：'):
                last_turns.append((lines[i-1][3:].strip(), lines[i][3:].strip()))
                if len(last_turns) >= 3:  # 增加到3轮，用于检测连续逃避
                    break
        
        # 如果没有足够的上下文，无法判断是否偏离主题
        if not last_turns:
            return False
        
        # 检查最新的回复是否与主题相关
        last_assistant_msg = last_turns[0][0]
        
        # 主题关键词
        topic_keywords = {
            "情感咨询师": ["情感", "恋爱", "喜欢", "爱情", "失恋", "伴侣", "关系"],
            "人际关系": ["朋友", "同学", "关系", "相处", "冲突", "沟通", "欺负", "孤立"],
            "学业问题": ["考试", "成绩", "学习", "课程", "作业", "论文", "学校"],
            "就业与职业规划压力": ["工作", "就业", "面试", "职业", "简历", "职场", "压力"],
            "精神健康障碍": ["焦虑", "抑郁", "失眠", "疲惫", "压力", "精神", "心理"],
            "自我认同与价值观冲突": ["自我", "价值", "意义", "冲突", "困惑", "方向", "认同"],
            "突发事件与危机情景": ["危机", "紧急", "突发", "事故", "创伤", "危险"]
        }
        
        # 检测助手上一条消息的问题类型
        for category, keywords in topic_keywords.items():
            if any(keyword in last_assistant_msg.lower() for keyword in keywords):
                # 检查用户回复是否包含相关关键词
                if not any(keyword in message.lower() for keyword in keywords):
                    # 如果用户回复不包含任何主题关键词，可能偏离主题
                    
                    # 最后检查是否是明显的离题内容
                    off_topic_indicators = ["今天天气", "吃什么", "你是谁", "打游戏", "玩", "睡觉"]
                    if any(indicator in message.lower() for indicator in off_topic_indicators):
                        return True
        
        return False

    def _count_consecutive_off_topic(self, context: str) -> int:
        """计算用户连续几次偏离主题
        
        Args:
            context: 对话上下文
            
        Returns:
            int: 连续偏离主题的次数
        """
        # 获取最近的对话轮次
        lines = context.strip().split('\n')
        turns = []
        for i in range(len(lines)-1, -1, -1):
            if i > 0 and lines[i].startswith('用户：') and lines[i-1].startswith('助手：'):
                turns.append((lines[i-1][3:].strip(), lines[i][3:].strip()))
                if len(turns) >= 5:  # 检查最近5轮对话
                    break
        
        # 如果轮次不足，返回0
        if len(turns) < 2:
            return 0
        
        # 检查连续的refocus信息
        refocus_count = 0
        for i in range(min(len(turns), 3)):  # 只检查最近3轮
            assistant_msg = turns[i][0]
            if "我们之前讨论的是" in assistant_msg and "你觉得" in assistant_msg:
                refocus_count += 1
            else:
                break
        
        return refocus_count

    def _determine_expression(self, text: str) -> str:
        """根据回复内容决定表情
        
        Args:
            text: 回复文本
            
        Returns:
            str: 表情名称
        """
        text = text.lower()
        
        # 情感词典
        emotion_dict = {
            "微笑": ["谢谢", "感谢", "很好", "不错", "很高兴", "很开心", "很荣幸", "祝贺", "恭喜"],
            "咪咪眼": ["理解", "明白", "知道了", "认同", "赞同", "支持", "建议", "推荐", "可以考虑"],
            "爱心": ["喜欢", "爱", "关心", "在意", "心疼", "心动", "呵护", "照顾", "疼爱", "宠爱"],
            "伤心": ["难过", "伤心", "悲伤", "遗憾", "痛苦", "哭", "眼泪", "负面", "失望"],
            "疑惑": ["为什么", "怎么会", "不明白", "不理解", "困惑", "疑问", "不确定", "是吗", "好吗"],
            "生气": ["抱歉", "对不起", "错误", "失败", "问题", "错了", "失误", "故障"]
        }
        
        # 查找情感关键词
        for expression, keywords in emotion_dict.items():
            for keyword in keywords:
                if keyword in text:
                    return expression
        
        # 如果是问句，用疑惑表情
        if "?" in text or "？" in text:
            return "疑惑"
        
        # 默认表情
        return "咪咪眼"

    def _format_guided_conversation_context(self, context: str, current_message: str) -> str:
        """格式化引导式对话的上下文，增强引导效果
        
        Args:
            context: 原始对话上下文
            current_message: 当前用户消息
            
        Returns:
            str: 格式化后的对话上下文
        """
        if not context:
            return f"用户: {current_message}"
            
        # 分离对话轮次
        turns = []
        lines = context.strip().split('\n')
        current_turn = {"role": None, "content": []}
        
        for line in lines:
            if line.startswith("用户："):
                if current_turn["role"] == "assistant" and current_turn["content"]:
                    turns.append(current_turn)
                    current_turn = {"role": "user", "content": [line[3:].strip()]}
                elif current_turn["role"] is None:
                    current_turn = {"role": "user", "content": [line[3:].strip()]}
                else:
                    current_turn["content"].append(line[3:].strip())
            elif line.startswith("助手："):
                if current_turn["role"] == "user" and current_turn["content"]:
                    turns.append(current_turn)
                    current_turn = {"role": "assistant", "content": [line[3:].strip()]}
                elif current_turn["role"] is None:
                    current_turn = {"role": "assistant", "content": [line[3:].strip()]}
                else:
                    current_turn["content"].append(line[3:].strip())
            elif line.strip():
                if current_turn["role"]:
                    current_turn["content"].append(line.strip())
                    
        # 添加最后一轮对话（如果有）
        if current_turn["role"] and current_turn["content"]:
            turns.append(current_turn)
            
        # 格式化对话历史，增强引导效果
        formatted_context = "对话历史：\n"
        for i, turn in enumerate(turns):
            role_prefix = "用户" if turn["role"] == "user" else "助手"
            content = " ".join(turn["content"])
            formatted_context += f"{role_prefix} {i+1}: {content}\n"
            
        # 添加当前用户消息
        formatted_context += f"\n当前用户输入: {current_message}"
        
        return formatted_context

    def _parse_response(self, response: str) -> dict:
        """尝试解析LLM回复的JSON格式
        
        Args:
            response: LLM原始回复
            
        Returns:
            dict: 解析后的响应字典，解析失败则返回None
        """
        if not response:
            return None
            
        try:
            # 尝试直接解析JSON
            if response.strip().startswith('{') and response.strip().endswith('}'):
                return json.loads(response)
                
            # 检查是否是双花括号格式
            if response.strip().startswith('{{') and response.strip().endswith('}}'):
                fixed = response.replace('{{', '{').replace('}}', '}')
                return json.loads(fixed)
                
            # 尝试在文本中查找JSON
            import re
            json_match = re.search(r'({.*})', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
        except Exception as e:
            print(f"解析回复JSON失败: {e}")
            
        # 如果不是JSON格式，尝试构造一个基本的回复格式
        try:
            # 移除前缀（如 "Assistant: "）
            clean_response = response
            for prefix in ["Assistant:", "助手:"]:
                if response.startswith(prefix):
                    clean_response = response[len(prefix):].strip()
                    break
                    
            return {"reply": clean_response, "expression": "咪咪眼"}
        except:
            return None
            
    def _fix_response_format(self, response: str) -> str:
        """尝试修复LLM回复的格式问题
        
        Args:
            response: LLM原始回复
            
        Returns:
            str: 修复后的回复文本
        """
        if not response:
            return ""
            
        try:
            # 如果回复不是JSON格式，尝试转换为JSON
            if not (response.strip().startswith('{') and response.strip().endswith('}')):
                # 构造基本的JSON格式
                return json.dumps({
                    "reply": response.strip(),
                    "expression": "nn眼"
                }, ensure_ascii=False)
                
            # 处理双花括号格式
            if response.strip().startswith('{{') and response.strip().endswith('}}'):
                return response.replace('{{', '{').replace('}}', '}')
                
            # 检查是否包含非标准引号
            if "'" in response and not ('"' in response):
                # 将单引号替换为双引号
                import re
                fixed = re.sub(r"'([^']*)':", r'"\1":', response)
                fixed = re.sub(r": *'([^']*)'", r': "\1"', fixed)
                return fixed
        except Exception as e:
            print(f"修复回复格式失败: {e}")
            
        return response