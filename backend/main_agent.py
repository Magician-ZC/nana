from llm import LLMService
from typing import List, Dict, Tuple
import os
from datetime import datetime
from conversation import ConversationHistory
from user_info_processor import UserInfoProcessor
from intent_extractor import IntentExtractor

class MainAgent:
    def __init__(self, llm_service: LLMService, conversation_history: ConversationHistory):
        self.conversation_history = conversation_history
        self.llm_service = llm_service
        self.current_agent = "nanaA"  # 默认使用娜娜A
        self.prompt_template = ""  # 用于存储自定义提示词
        self._load_prompt_template()
            
        # 确保日志和个人信息目录存在
        self.log_dir = 'save/log'
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 初始化用户信息处理器和意图提取器
        self.user_info_processor = UserInfoProcessor('save/me.txt')
        self.intent_extractor = IntentExtractor()
        
        # 获取用户信息
        self.user_info = self.user_info_processor.user_info
    
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
            self.current_agent = config["id"]
            self.prompt_template = prompt
            return True
        except Exception as e:
            print(f"设置自定义智能体失败: {e}")
            return False

    def _log_conversation(self, role: str, content: str) -> None:
        """记录对话到日志文件"""
        current_date = datetime.now().strftime('%Y%m%d')
        current_time = datetime.now().strftime('%H:%M:%S')
        log_file = os.path.join(self.log_dir, f'{current_date}.txt')
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f'[{current_time}] {role.capitalize()}: {content}\n')
        
    async def reply(self, message: str, personality: str = None, is_category: bool = False) -> Tuple[str, str]:
        """生成回复
        
        Args:
            message: 用户消息
            personality: 可选的性格描述，用于调整回复风格
            is_category: 是否是快捷提问类别
            
        Returns:
            Tuple[str, str]: (回复内容, 表情)
        """
        # 记录用户消息
        self._log_conversation('user', message)
        
        # 获取当前对话轮数
        turns_count = len(self.conversation_history.turns) + 1  # +1 是因为当前消息还未添加
        
        # 获取相关记忆
        memory_text = self._get_relevant_memories(message)
        print("相关记忆:", memory_text)
        
        # 特殊处理快捷提问类别
        if is_category:
            print(f"检测到快捷提问类别: {message}")
            # 获取与该类别相关的记忆
            category_memory = self._get_relevant_category_memories(message)
            if category_memory != "无补充信息":
                memory_text = category_memory
                print(f"找到与类别[{message}]相关的记忆: {memory_text}")
        
        # 生成回复，传入性格参数
        reply_content, expression = await self._generate_reply(message, memory_text, personality, is_category)
        
        # 处理回复
        if reply_content:
            await self._handle_successful_reply(message, reply_content)

        # 检查是否需要发送对话总结 (每10轮对话)
        if turns_count % 10 == 0 and turns_count >= 10:
            print(f"已经进行了{turns_count}轮对话，准备发送对话总结")
            # 确保先添加当前对话
            await self.conversation_history.add_dialog(message, reply_content, self.user_info_processor)
            
            # 触发归档并获取总结 - 使用异步方式在后台处理，不阻塞主流程
            import asyncio
            asyncio.create_task(self._process_dialog_summary(turns_count))
        
        return reply_content, expression

    async def _process_dialog_summary(self, turns_count):
        """异步处理对话总结任务，避免阻塞主回复流程
        
        Args:
            turns_count: 当前对话轮数
        """
        try:
            # 触发归档并获取总结
            summary_profile = await self.conversation_history._auto_archive(self.user_info_processor)
            
            if summary_profile:
                # 确保更新用户信息
                print("从归档总结更新用户信息")
                updated_info = self.user_info_processor.get_user_info()
                if updated_info != self.user_info:
                    print("用户信息已更新")
                    self.user_info = updated_info
                
                # 在用户下一次提问后，将总结作为系统消息添加到对话历史
                await self.conversation_history.add_dialog("SYSTEM_GUIDANCE", 
                    f"【系统消息】根据我们的对话，我整理了一些要点：\n\n{summary_profile}", 
                    None)
                
                print("对话总结已添加到对话历史，将在用户下一次提问后显示")
        except Exception as e:
            print(f"处理对话总结时发生错误: {e}")

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
        
        # 如果提供了性格描述，添加到提示词中
        personality_prompt = ""
        if personality:
            personality_prompt = f"\n请以以下性格特点回复: {personality}"
        
        # 如果是快捷提问类别，添加相应的指导
        category_prompt = ""
        if is_category:
            category_prompt = f"\n用户点击了快捷提问类别按钮：{message}。请针对该类别提供专业且详细的回答，字数不限。如果用户信息中包含与该类别相关的内容，请重点针对这些信息进行深入分析并给出专业建议。请使用专业咨询师的语气，确保回答全面、有针对性且对用户有实际帮助。不要在回答中引导用户做出决策。"
        
        # 检查是否是用户对建议的回复/决策
        is_user_decision, decision_type, decision_content = self.intent_extractor.recognizer.check_if_user_decision(message, context)

        # 检查用户是否提供了新的个人信息
        has_new_info, info_type, info_content, career_intent = self.intent_extractor.check_for_new_user_info(message)
        
        decision_prompt = ""
        if is_user_decision:
            print(f"检测到用户决策: 类型={decision_type}, 内容={decision_content}")
            decision_prompt = f"\n检测到用户正在回复之前的建议并做出决策，决策类型：{decision_type}，决策内容：{decision_content}。请理解用户的选择，并相应地更新用户信息，尤其是'最近状况'部分中的相关条目。例如，如果用户决定'原谅同学'，请将'人际关系'中的相关描述更新为'尝试接纳同学并改善关系'等反映新决策的描述。重要：一定要在回复中包含user_info字段，更新用户信息以反映此次决策。"
        elif has_new_info:
            print(f"检测到用户提供了新的{info_type}信息: {info_content}")
            if info_type == "爱好":
                decision_prompt = f"\n检测到用户提供了新的爱好信息。请更新用户信息中的'爱好'字段，将'{info_content}'添加到现有爱好列表中。重要：一定要在回复中包含user_info字段，更新后的爱好应包括原有爱好和新爱好'{info_content}'。"
            else:
                decision_prompt = f"\n检测到用户提供了新的{info_type}信息：'{info_content}'。请更新用户信息中的'{info_type}'字段。重要：一定要在回复中包含user_info字段，更新后的信息应反映用户提供的新内容。"
        
        # 添加提示词，请求只在必要时更新用户信息
        update_info_prompt = "\n注意：当用户明确提供新的个人信息，或对建议做出选择和决策时，才在'user_info'字段中返回更新后的用户信息。如果用户没有提供新信息或没有做出明确决策，请不要在回复中包含'user_info'字段。"
        
        prompt = self.prompt_template.format(
            chat_history=context,
            user_message=message,
            memory=memory_text,
            user_info=self.user_info
        ) + personality_prompt + category_prompt + decision_prompt + update_info_prompt
        
        # 获取LLM回复
        reply = await self.llm_service.generate_response(prompt, is_json=True)
        if not reply:
            return "对不起，我现在有点累了，能稍后再聊吗？", "生气"
        
        # 检查是否有用户信息更新，只有在有更新时才保存
        if "user_info" in reply:
            user_info_value = reply["user_info"]
            # 检查user_info是否为字典类型（可能是直接返回了JSON对象）
            if isinstance(user_info_value, dict):
                # 将字典转换为字符串格式
                if "最近状况" in user_info_value and isinstance(user_info_value["最近状况"], dict):
                    # 处理最近状况特殊格式
                    status_text = ""
                    index = 1
                    for key, value in user_info_value["最近状况"].items():
                        status_text += f"{index}. {key}: {value}\n"
                        index += 1
                    user_info_value["最近状况"] = status_text.strip()
                
                # 构建完整的用户信息字符串
                user_info_str = ""
                basic_info_keys = ["姓名", "年龄", "性别", "学校", "专业", "年级", "爱好"]
                
                # 基本信息部分
                for key in basic_info_keys:
                    if key in user_info_value and user_info_value[key]:
                        user_info_str += f"{key}: {user_info_value[key]}\n"
                
                user_info_str += "\n"
                
                # 最近状况部分
                if "最近状况" in user_info_value:
                    user_info_str += "最近状况: \n" + user_info_value["最近状况"] + "\n"
                
                # 其他信息部分
                for key in user_info_value:
                    if key not in basic_info_keys and key != "最近状况" and user_info_value[key]:
                        user_info_str += f"{key}: {user_info_value[key]}\n"
                
                # 使用转换后的字符串进行更新检查
                if self.user_info_processor.has_substantial_changes(self.user_info, user_info_str):
                    print("检测到用户信息更新，正在保存...")
                    self.user_info_processor.save_user_info(user_info_str)
                    # 更新内存中的用户信息
                    self.user_info = self.user_info_processor.user_info
                else:
                    print("没有检测到实质性的用户信息变化，跳过更新")
            elif isinstance(user_info_value, str) and user_info_value.strip():
                # 如果是已经格式化的字符串
                if self.user_info_processor.has_substantial_changes(self.user_info, user_info_value):
                    print("检测到用户信息更新，正在保存...")
                    self.user_info_processor.save_user_info(user_info_value)
                    # 更新内存中的用户信息
                    self.user_info = self.user_info_processor.user_info
                else:
                    print("没有检测到实质性的用户信息变化，跳过更新")
        elif is_user_decision or has_new_info:
            # 如果检测到决策或新个人信息但没有返回user_info，强制要求模型更新用户信息
            print("检测到用户决策或新个人信息，但模型未返回user_info，尝试再次请求...")
            # 添加更明确的提示
            force_update_prompt = ""
            if is_user_decision:
                force_update_prompt = prompt + "\n\n重要提示：用户已经做出决策，必须更新用户信息并在回复中包含user_info字段，反映用户的最新决策。如果不知道如何更新，至少保持原有信息完整并返回。"
            else:  # has_new_info
                if info_type == "爱好":
                    force_update_prompt = prompt + f"\n\n重要提示：用户提供了新的爱好信息'{info_content}'，必须更新用户信息中的爱好字段并在回复中包含完整的user_info字段。新的爱好'{info_content}'应该添加到现有爱好列表中，格式为'编程、游戏、看书、{info_content}'。"
                else:
                    force_update_prompt = prompt + f"\n\n重要提示：用户提供了新的{info_type}信息'{info_content}'，必须更新用户信息中的{info_type}字段并在回复中包含完整的user_info字段。新的{info_type}信息应该替换现有内容或适当添加到相应部分。"
            
            retry_reply = await self.llm_service.generate_response(force_update_prompt, is_json=True)
            
            if "user_info" in retry_reply and retry_reply["user_info"].strip():
                print("成功获取更新后的用户信息")
                self.user_info_processor.save_user_info(retry_reply["user_info"])
                self.user_info = self.user_info_processor.user_info
                return retry_reply.get("reply", reply.get("reply", "")), retry_reply.get("expression", reply.get("expression", ""))
            elif has_new_info:
                # 如果两次尝试都失败，但确实有新信息，则手动更新信息
                print(f"自动更新用户{info_type}信息...")
                updated_info = self.user_info_processor.manually_update_user_info(info_type, info_content, career_intent)
                if updated_info:
                    self.user_info_processor.save_user_info(updated_info)
                    self.user_info = self.user_info_processor.user_info
        
        return reply.get("reply", ""), reply.get("expression", "")

    def _get_relevant_memories(self, message: str) -> str:
        """获取相关记忆"""
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
                    key, value = line.replace('：', ':').split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    if key and value:
                        combined_memory[key] = value
        
        # 格式化输出
        if combined_memory:
            return "用户画像信息：\n" + "\n".join(f"{k}: {v}" for k, v in combined_memory.items())
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

    async def _handle_successful_reply(self, message: str, reply_content: str) -> None:
        """处理成功的回复"""
        # 记录助手回复并添加到对话历史
        self._log_conversation('assistant', reply_content)
        await self.conversation_history.add_dialog(message, reply_content, self.user_info_processor)
        
        # 检查是否需要发送引导决策的消息
        context = self.conversation_history.get_context()
        is_user_decision, _, _ = self.intent_extractor.recognizer.check_if_user_decision(message, context)
        is_category = any(category in message for category in [
            "情感咨询师", "人际关系", "学业问题", "就业与职业规划压力", 
            "精神健康障碍", "自我认同与价值观冲突", "突发事件与危机情景"
        ])
        
        # 如果是类别提问且不是用户决策的回复，则发送引导决策消息
        if is_category and not is_user_decision:
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
        import asyncio
        asyncio.create_task(self._process_user_info_sync(message, is_user_decision))

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