from typing import Optional, Tuple
from llm import LLMService
from tts import TTSService
from super_tts import SuperTTSService
from config import Config
from main_agent import MainAgent
from conversation import ConversationHistory
import os
import json
import asyncio
from embedding import EmbeddingService
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

class ChatService:
    def __init__(self):
        # 初始化LLM服务
        self.llm_service = LLMService(Config.LLM_API_KEY, Config.LLM_API_URL)
        
        # 初始化TTS服务（根据配置决定是否创建实例）
        self._refresh_tts_services()
         
        # 初始化对话历史和主Agent
        self.conversation_history = ConversationHistory(max_turns=Config.MAX_TURNS)
        self.main_agent = MainAgent(self.llm_service, self.conversation_history)
        
        # 自定义agent目录
        self.custom_agents_dir = "save/custom_agents"
        os.makedirs(self.custom_agents_dir, exist_ok=True)
        
        # 初始化向量服务用于快速回复
        self.embedding_service = EmbeddingService(
            Config.EMBEDDING_API_KEY,  # 使用专门的Embedding API密钥
            Config.EMBEDDING_API_URL,
            Config.EMBEDDING_MODEL,
            Config.EMBEDDING_DIMENSION
        )
        
        # 加载向量数据库 (如果存在)
        self.vector_db = self._load_vector_db()

    def _load_vector_db(self):
        """加载向量数据库，如果不存在则返回空数据库"""
        vector_db_path = "save/vector_db.json"
        if os.path.exists(vector_db_path):
            try:
                with open(vector_db_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载向量数据库失败: {e}")
        return {"questions": [], "embeddings": [], "answers": []}

    def _is_user_info_related(self, message: str) -> bool:
        """判断用户消息是否与个人信息相关"""
        personal_keywords = [
            "我的", "我是", "我们", "我想", "我要", "我有", "我感觉", "我觉得", 
            "我喜欢", "我讨厌", "我的家", "我的工作", "我的学习", "我的健康",
            "我的朋友", "我的家人", "我的情感", "我最近", "我今天", "我昨天",
            "你记得我", "你知道我", "还记得我", "帮我", "告诉我", "我多大",
            "你认识我", "我们见过", "我们聊过", "你了解我", "名字", "年龄", 
            "性别", "专业", "学校", "工作", "家庭", "爱好", "能力", "性格"
        ]
        
        for keyword in personal_keywords:
            if keyword in message:
                return True
        return False

    def _refresh_tts_services(self):
        """根据当前配置刷新TTS服务实例"""
        # 普通TTS服务
        self.tts_service = TTSService(Config.TTS_VCN) if Config.is_tts_enabled() else None
        # 超拟人TTS服务
        self.super_tts_service = SuperTTSService(Config.SUPER_TTS_VCN) if Config.is_super_tts_enabled() else None

    def change_agent(self, agent_name: str, session_id: str) -> bool:
        """
        切换智能体
        :param agent_name: 智能体名称
        :param session_id: 会话ID
        :return: 是否成功切换
        """
        if agent_name in ["nanaA", "nanaB", "nanaC"]:
            return self.main_agent.set_agent(agent_name)
        elif agent_name.startswith("custom_"):
            # 加载自定义角色
            config_path = os.path.join(self.custom_agents_dir, f"{agent_name}.json")
            prompt_path = os.path.join(self.custom_agents_dir, f"{agent_name}.txt")
            
            if os.path.exists(config_path) and os.path.exists(prompt_path):
                try:
                    # 读取配置文件
                    with open(config_path, "r", encoding="utf-8") as f:
                        config = json.load(f)
                    
                    # 读取提示词文件
                    with open(prompt_path, "r", encoding="utf-8") as f:
                        prompt = f.read()
                    
                    # 设置自定义角色
                    return self.main_agent.set_custom_agent(prompt, config)
                except Exception as e:
                    print(f"加载自定义角色失败: {e}")
                    return False
            else:
                print(f"自定义角色文件不存在: {agent_name}")
                return False
        return False
        
    async def fast_reply(self, message: str) -> Tuple[str, str]:
        """
        使用向量检索快速生成回复，不涉及用户信息处理
        
        Args:
            message: 用户消息
            
        Returns:
            Tuple[str, str]: (回复文本, 表情)
        """
        try:
            # 首先检查向量数据库是否为空
            if not self.vector_db or not self.vector_db.get("embeddings") or len(self.vector_db["embeddings"]) == 0:
                print("向量数据库为空，无法使用快速回复")
                return None, None
                
            # 获取消息的向量表示
            try:
                embedding = self.embedding_service.get_embedding(message)
                if not embedding:
                    print("无法获取消息的向量表示，跳过快速回复")
                    return None, None
            except Exception as e:
                print(f"获取向量表示时出错: {e}")
                return None, None
                
            # 计算与所有已知问题的相似度
            try:
                similarities = []
                for stored_embedding in self.vector_db["embeddings"]:
                    similarity = cosine_similarity([embedding], [stored_embedding])[0][0]
                    similarities.append(similarity)
                    
                # 找到最相似的问题
                max_similarity_index = np.argmax(similarities)
                max_similarity = similarities[max_similarity_index]
                
                # 如果相似度超过阈值，返回对应回答
                if max_similarity > 0.85:  # 设置一个相对严格的阈值
                    answer = self.vector_db["answers"][max_similarity_index]
                    # 随机选择一个适合的表情
                    expression = "开心"  # 默认表情
                    
                    print(f"使用向量检索快速回复，相似度: {max_similarity:.4f}")
                    return answer, expression
            except Exception as e:
                print(f"计算相似度时出错: {e}")
                return None, None
                
        except Exception as e:
            print(f"快速回复处理出错: {e}")
            
        return None, None

    async def generate_reply(self, message: str, session_id: str, agent_type: Optional[str] = None, personality: Optional[str] = None, is_category: bool = False) -> Tuple[str, Optional[bytes], str, Optional[str]]:
        """
        生成回复
        :param message: 用户消息
        :param session_id: 会话ID
        :param agent_type: 智能体类型
        :param personality: 智能体的性格描述
        :param is_category: 是否是快捷提问类别
        :return: (回复文本, 语音数据, 表情, 引导决策消息)
        """
        try:
            print(f"[generate_reply] 开始处理消息: '{message}'")
            print(f"[generate_reply] 参数: agent_type={agent_type}, session_id={session_id}, is_category={is_category}")
            
            # 确保消息非空
            if not message or not message.strip():
                print("[generate_reply] 消息为空，返回默认回复")
                return "请输入有效的消息内容", None, "生气", None
            
            # 确保TTS服务使用最新的配置
            self._refresh_tts_services()
            
            # 如果收到新的agent_type，先切换智能体
            if agent_type:
                print(f"[generate_reply] 切换智能体: {agent_type}")
                self.change_agent(agent_type, session_id)
            
            # 对于非分类问题，尝试快速回复
            reply = None
            expression = None
            guidance_message = None
            
            if not is_category and not self._is_user_info_related(message):
                # 尝试使用向量检索进行快速回复
                print("[generate_reply] 尝试使用向量检索进行快速回复...")
                reply, expression = await self.fast_reply(message)
                if reply:
                    print(f"[generate_reply] 快速回复成功: '{reply}'")
            
            # 如果快速回复未成功，使用完整流程
            if not reply:
                print("[generate_reply] 快速回复未成功，使用完整流程...")
                # 使用 MainAgent 生成回复和表情，传入性格描述和快捷提问标志
                reply, expression = await self.main_agent.reply(message, personality=personality, is_category=is_category)
                print(f"[generate_reply] 主智能体回复结果: reply='{reply}', expression='{expression}'")
                
                # 检查是否有引导决策消息
                if hasattr(self.main_agent.conversation_history, 'guidance_message'):
                    guidance_message = self.main_agent.conversation_history.guidance_message
                    print(f"[generate_reply] 获取到引导决策消息: '{guidance_message}'")
            
            # 确保回复不为None
            if reply is None:
                print("[generate_reply] 警告: 回复为None，设置为默认回复")
                reply = "抱歉，我现在无法理解您的问题。请换一种方式提问。"
            
            # 确保回复是字符串类型
            if not isinstance(reply, str):
                print(f"[generate_reply] 警告: 回复不是字符串类型，而是 {type(reply)}，转换为字符串")
                try:
                    reply = str(reply)
                except:
                    reply = "抱歉，处理消息时出现错误。"
            
            # 确保回复内容不为空字符串
            if reply.strip() == "":
                print("[generate_reply] 警告: 回复为空字符串，设置为默认回复")
                reply = "抱歉，我现在无法回答您的问题。请稍后再试。"
            
            # 确保表情不为None
            if expression is None:
                print("[generate_reply] 警告: 表情为None，设置为默认表情")
                expression = "思考"
            
            # 生成语音数据
            audio_data = None
            if Config.is_tts_enabled() or Config.is_super_tts_enabled():
                print(f"[generate_reply] 开始生成语音，TTS状态: 普通TTS={Config.is_tts_enabled()}, 超拟人TTS={Config.is_super_tts_enabled()}")
                if Config.is_super_tts_enabled() and self.super_tts_service:
                    audio_data = await self.super_tts_service.async_tts(reply, Config.TTS_SPEED)
                    if audio_data:
                        print(f"[generate_reply] 超拟人TTS成功生成音频，大小: {len(audio_data)} 字节")
                elif Config.is_tts_enabled() and self.tts_service:
                    audio_data = await self.tts_service.async_tts(reply, Config.TTS_SPEED)
                    if audio_data:
                        print(f"[generate_reply] 普通TTS成功生成音频，大小: {len(audio_data)} 字节")
                
                if not audio_data:
                    print("[generate_reply] 警告: 未能生成语音数据")
            
            print(f"[generate_reply] 处理完成，返回结果: 回复={reply[:30]}{'...' if len(reply) > 30 else ''}, 音频大小={len(audio_data) if audio_data else 0}字节, 表情={expression}")
            return reply, audio_data, expression, guidance_message
            
        except Exception as e:
            print(f"[generate_reply] 生成回复时发生错误: {e}")
            # 发生错误时返回默认回复
            return "抱歉，系统遇到了问题。请稍后再试。", None, "生气", None