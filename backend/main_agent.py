from llm import LLMService
from typing import List, Dict, Tuple
import os
from datetime import datetime
from conversation import ConversationHistory
from user_info_processor import UserInfoProcessor
from intent_extractor import IntentExtractor
import asyncio
import json

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
            self.current_agent = config["id"]
            self.prompt_template = prompt
            return True
        except Exception as e:
            print(f"设置自定义智能体失败: {e}")
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
        else:
            # 英文消息中至少要有一个完整单词(至少3个字母)
            import re
            
            # 修改检测策略：三重检查
            # 1. 首先检查是否与常见英文单词相似
            # 常见的1000个英文单词的前缀（为了便于匹配，只使用常见单词的前3-4个字母作为前缀检查）
            common_word_prefixes = ["the", "and", "for", "are", "but", "not", "you", "all", "any", "can", "had", "her", "was", "one", 
                                   "our", "out", "day", "get", "has", "him", "his", "how", "man", "new", "now", "old", "see", "two", 
                                   "way", "who", "boy", "did", "its", "let", "put", "say", "she", "too", "use", "that", "with", "have", 
                                   "this", "will", "your", "from", "they", "know", "want", "been", "good", "much", "some", "time"]
            
            # 检查输入是否与任何常见单词前缀匹配
            input_lower = message.lower()
            prefix_match = False
            
            for prefix in common_word_prefixes:
                if input_lower.startswith(prefix) or any(word.startswith(prefix) for word in input_lower.split()):
                    prefix_match = True
                    break
            
            # 2. 检查是否含有元音字母和合理的辅音元音分布
            vowel_pattern = re.compile(r'[aeiou]')
            has_vowels = bool(vowel_pattern.search(input_lower))
            
            # 计算元音和辅音比例
            vowel_count = sum(c in 'aeiou' for c in input_lower)
            consonant_count = sum(c in 'bcdfghjklmnpqrstvwxyz' for c in input_lower)
            total_letters = vowel_count + consonant_count
            
            # 检查字母组合是否像自然语言（元音通常占20%-60%）
            natural_vowel_ratio = (total_letters > 0) and (0.2 <= vowel_count / total_letters <= 0.6)
            
            # 3. 检查特有的无意义输入模式
            # a. 检查辅音连续超过3个或元音连续超过3个（自然英语单词中很少有这种情况）
            max_consecutive_consonants = 0
            max_consecutive_vowels = 0
            current_consonants = 0
            current_vowels = 0
            
            for c in input_lower:
                if c in 'aeiou':
                    current_vowels += 1
                    current_consonants = 0
                    if current_vowels > max_consecutive_vowels:
                        max_consecutive_vowels = current_vowels
                elif c in 'bcdfghjklmnpqrstvwxyz':
                    current_consonants += 1
                    current_vowels = 0
                    if current_consonants > max_consecutive_consonants:
                        max_consecutive_consonants = current_consonants
                else:
                    current_consonants = 0
                    current_vowels = 0
            
            unnatural_consonant_pattern = max_consecutive_consonants > 3
            unnatural_vowel_pattern = max_consecutive_vowels > 3
            
            # b. 检查是否有重复的辅音-元音模式（如"sasasa"或"dadada"）
            has_repetitive_pattern = False
            if len(message) >= 4:
                # 提取2-3个字符的可能重复模式
                for pattern_length in [2, 3]:
                    if len(message) >= pattern_length * 2:
                        pattern = message[:pattern_length]
                        repetitions = 1
                        
                        for i in range(pattern_length, len(message), pattern_length):
                            if i + pattern_length <= len(message) and message[i:i+pattern_length] == pattern:
                                repetitions += 1
                            else:
                                break
                        
                        # 如果同一模式重复出现至少2次，且占据消息长度的大部分
                        if repetitions >= 2 and (repetitions * pattern_length) / len(message) > 0.6:
                            has_repetitive_pattern = True
                            break
            
            # 综合判断是否是有意义的文本：
            # 1. 与常见单词前缀匹配，且有合理的元音辅音分布
            # 2. 没有不自然的辅音/元音连续模式
            # 3. 没有明显的重复模式
            has_meaningful_text = (prefix_match or natural_vowel_ratio) and not (unnatural_consonant_pattern or unnatural_vowel_pattern or has_repetitive_pattern)
            
            # 额外的安全检查：如果是常见的无意义输入模式如"asdasd"，"qwerty"，直接判定为无意义
            common_random_inputs = ["asdf", "qwer", "zxcv", "hjkl", "wasd", "qwerty", "asdasd", "dfdfdf", "jkjk", "ghgh", "sdfsd", "asdasdasd", "qwerty"]
            if any(rand_input in input_lower for rand_input in common_random_inputs):
                has_meaningful_text = False
        
        return not has_meaningful_text

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
        
        # 在引导模式下不获取相关记忆
        memory_text = "无补充信息"  # 默认初始化
        if not is_category:
            # 如果不是引导模式，获取相关记忆
            memory_text = self._get_relevant_memories(message)
            print("相关记忆:", memory_text)
        else:
            # 引导模式下不使用用户记忆
            print("引导模式中，不使用用户记忆信息")
        
        # 生成回复，传入性格参数
        reply_content, expression = await self._generate_reply(message, memory_text, personality, is_category)
        
        # 处理回复，添加到对话历史
        if reply_content:
            await self._handle_successful_reply(message, reply_content, is_category)

        # 检查是否需要发送对话总结 (每10轮对话)
        if turns_count % 10 == 0 and turns_count >= 10 and message != "SYSTEM_GUIDANCE":
            print(f"已经进行了{turns_count}轮对话，准备发送对话总结")
            
            # 启动异步任务处理对话归档，不等待其完成
            asyncio.create_task(self._process_dialog_summary(turns_count))
            print("已在后台启动对话归档任务")
        
        return reply_content, expression

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
        """带显式上下文的生成回复方法
        
        Args:
            message: 用户消息
            context: 对话上下文
            memory_text: 相关记忆文本
            personality: 可选的性格描述，用于调整回复风格
            is_category: 是否是快捷提问类别
            
        Returns:
            Tuple[str, str]: (回复内容, 表情)
        """
        # 处理系统消息
        if message == "SYSTEM_TOPIC_SUGGESTIONS":
            print("收到话题建议系统消息，生成话题建议")
            # 导入并调用generate_topic_suggestions函数
            from main import generate_topic_suggestions
            suggestion_text = generate_topic_suggestions()
            expression = "微笑"  # 使用友好的表情
            return suggestion_text, expression
            
        # 如果提供了性格描述，添加到提示词中
        personality_prompt = ""
        if personality:
            personality_prompt = f"\n请以以下性格特点回复: {personality}"
        
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
        
        # 在快速提问模式下，使用xinli_agent提示词；否则使用原agent提示词
        if is_category:
            # 读取xinli_agent提示词
            xinli_agent_path = os.path.join("prompts", "xinli_agent.txt")
            with open(xinli_agent_path, "r", encoding="utf-8") as f:
                xinli_prompt = f.read()
            
            # 增强上下文格式，提高记忆能力
            try:
                enhanced_context = self._format_guided_conversation_context(context, message)
                print(f"使用增强的引导式对话上下文:\n{enhanced_context}")
            except Exception as e:
                print(f"格式化引导式对话上下文时出错: {e}")
                # 出错时使用原始上下文
                enhanced_context = context
            
            # 检查是否是用户回复了无关内容
            is_off_topic = self._is_meaningless_input(message) or self._is_off_topic(message, context)
            consecutive_off_topic = self._count_consecutive_off_topic(context)
            
            # 检查是否是用户表示想要停止话题
            exit_guidance_keywords = ["结束话题", "结束引导", "不想聊了", "换个话题", "不想继续", "结束对话", "不想讨论这个", "不讨论", "换话题", "算了", "不聊了", "结束"]
            is_exit_request = any(keyword in message for keyword in exit_guidance_keywords) or message.strip() == "结束"
            
            if is_exit_request:
                # 用户请求结束，直接生成总结
                off_topic_hint = """
用户表示想要结束话题。请生成一个简短的总结，包括以下内容：
1. 对讨论内容的简要回顾
2. 给出的主要建议或观点
3. 一个友好的结束语，表示用户随时可以重新讨论这个话题

请确保将is_summary设置为true，以便系统知道对话已经结束。
"""
            elif is_off_topic:
                if consecutive_off_topic >= 2:  # 连续3次偏离主题（当前这次+之前2次）
                    off_topic_hint = """
当前检测到用户已连续多次回复了无关内容或离题内容。用户可能对当前的主题不感兴趣或有其他顾虑。
请尝试以下几种策略之一（每次只选择一种，避免重复之前已尝试的策略）：

1. 直接询问用户是否想结束当前话题，例如："我注意到您似乎对这个话题不太感兴趣，是否想换一个话题讨论？"
2. 尝试理解用户可能不想讨论当前话题的原因，例如："您是否有什么顾虑让您不想讨论这个话题？"
3. 提供一个完全不同的思路或角度，例如："也许我们可以从一个全新的角度来思考这个问题..."
4. 分享一个相关的小故事或案例，引起用户兴趣
5. 尝试将用户的无关话题与当前主题建立某种联系，顺着用户的思路稍微引导

请确保您的回应是真诚的、尊重的，并且避免显得过于坚持或重复。每次只使用一种新的策略，不要重复使用同一种策略。
"""
                else:
                    off_topic_hint = """
当前检测到用户可能回复了无关内容或离题内容。请先温和地回应用户的话题，然后巧妙地将对话引导回主题。
例如："我理解您现在想讨论[离题内容]，这确实是个有趣的话题。不过，为了更好地帮助您解决当前的问题，我们可以先回到刚才的讨论..."

千万不要表现出不耐烦或指责用户离题，而是要理解并尊重用户的想法，然后自然地引导回来。
"""
            else:
                off_topic_hint = ""
            
            # 获取引导模式的局部用户信息
            try:
                # 直接使用LLM服务的chat_service属性
                chat_service = self.llm_service.chat_service if hasattr(self.llm_service, 'chat_service') else None
                guided_user_info = chat_service.guided_user_info if chat_service else None
            except Exception as e:
                print(f"获取引导用户信息时出错: {e}")
                # 如果出错，使用全局用户信息
                guided_user_info = self.user_info
            
            category_prompt = f"""
{xinli_prompt}

## 当前任务
用户点击了快捷提问类别按钮：{message}。请以专业心理医生的身份，通过引导式提问帮助用户逐步明确和解决他们的问题。
{off_topic_hint}
### 引导式提问规则
1. 每次只提出一个问题，等待用户回答
2. 根据用户的回答，逐步深入探究问题的核心
3. 使用开放式问题，避免引导性提问
4. 保持专业、温和的语气
5. 当用户偏离主题时，温和地将话题拉回
6. 当用户明确表示要结束话题时，直接生成总结并结束引导
7. 即使用户回复无关内容，也不要放弃引导，而是要温和地将话题拉回
8. 当用户连续多次偏离主题时，不要重复相同的提问方式，而要尝试新的引导策略
9. 当用户询问之前提到过的信息时，请准确回忆并回答，不要编造

请仔细阅读以下对话历史和用户信息，理解用户的处境和顾虑，为其提供精确的引导：

用户信息：
{guided_user_info if guided_user_info else "无可用用户信息"}

{enhanced_context}

### 信息收集规则
1. 当用户提供了重要信息（如科目困难、具体困扰、感受等），请在回复JSON中添加user_info字段
2. user_info字段应包含键值对，如 "user_info": {{"数学困难": "几何证明题", "学习态度": "感到无趣"}}
3. 每次对话添加1-2个关键信息，不要过度解读
4. 不要虚构信息，只记录用户明确表达的内容
5. 逐步积累这些信息，以便更好地理解用户

请回复JSON格式，包含以下字段：
{{
    "reply": "你的回复内容，面向用户的提问或建议",
    "expression": "推荐的表情（微笑、皱眉、咪咪眼、爱心、伤心、生气等）",
    "is_question": true/false,    // 回复是否包含问题
    "is_summary": false,          // 是否是总结（只有在引导结束时才为true）
    "question_type": "initial",   // 问题类型：initial（初始问题）、follow_up（跟进问题）、refocus（重新聚焦问题）、summary（总结）
    "user_info": {{               // 可选，仅当发现用户提供了重要信息时添加
        "key1": "value1",
        "key2": "value2"
    }}
}}

注：请确保你的JSON格式完全正确，并仔细考虑表情与内容的匹配。
"""
            prompt = category_prompt
        else:
            # 使用当前智能体的提示词模板
            prompt = f"{self.prompt_template}{personality_prompt}{decision_prompt}{update_info_prompt}\n\n用户信息：\n{self.user_info}\n\n当前对话记录：\n{context}\n\n当前所有对话相关的历史记忆：\n{memory_text}\n\n用户: {message}\n助手:"
        
        # 使用引导模式时，不需要额外添加用户消息，因为xinli_agent提示词中已包含引导
        if is_category and not prompt.endswith("助手:"):
            prompt = prompt
            
        # 确定使用的温度参数，引导模式（is_category=True）使用更低的温度，保持对话聚焦
        temperature = 0.3 if is_category else 0.7
        
        # 生成回复
        try:
            reply = await self.llm_service.generate_response(
                message=prompt,
                temperature=temperature,
                is_json=is_category,  # 引导模式使用JSON格式输出
                max_tokens=1024
            )
            
            if is_category:
                # 在引导模式下，表情从JSON中获取
                try:
                    if isinstance(reply, dict) and 'expression' in reply:
                        expression = reply.get('expression', '咪咪眼')
                    else:
                        expression = '咪咪眼'  # 默认表情
                    
                    # 确保回复是JSON格式的字符串
                    if isinstance(reply, dict):
                        reply = json.dumps(reply, ensure_ascii=False)
                    
                except Exception as e:
                    print(f"解析表情时出错: {e}")
                    expression = '咪咪眼'  # 默认表情
            else:
                # 标准模式分析回复，生成合适的表情
                expression = self._determine_expression(reply)
                
                # 检查回复中是否包含用户信息更新
                if '"user_info"' in reply or "'user_info'" in reply:
                    # 尝试从回复中提取用户信息并更新
                    await self._process_user_info_sync(message, is_user_decision)
            
            return reply, expression
            
        except Exception as e:
            error_msg = f"生成回复时出错: {str(e)}"
            print(error_msg)
            
            # 在错误情况下提供基本回复
            if is_category:
                # 生成一个有效的JSON回复
                error_reply = {
                    "reply": "抱歉，我遇到了一些问题。能请您重新表述一下您的情况吗？",
                    "expression": "疑惑",
                    "is_question": True,
                    "is_summary": False,
                    "question_type": "follow_up"
                }
                return json.dumps(error_reply, ensure_ascii=False), "疑惑"
            else:
                return "抱歉，我遇到了一些技术问题。您能换个方式提问，或者稍后再试吗？", "生气"

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