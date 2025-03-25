from typing import List
import chromadb
from chromadb.config import Settings
from chromadb.api.types import EmbeddingFunction
from datetime import datetime
import uuid
from embedding import EmbeddingService
from config import Config
import re

class APIEmbeddingFunction(EmbeddingFunction):
    def __init__(self):
        self.embedding_service = EmbeddingService(
            api_key=Config.EMBEDDING_API_KEY,
            api_url=Config.EMBEDDING_API_URL,
            model=Config.EMBEDDING_MODEL,
            dimension=Config.EMBEDDING_DIMENSION
        )
        
    def __call__(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for text in texts:
            try:
                embedding = self.embedding_service.get_embedding(text)
                if embedding is None:
                    embedding = [0.0] * Config.EMBEDDING_DIMENSION
                embeddings.append(embedding)
            except Exception as e:
                print(f"获取embedding时出错喵: {e}")
                embedding = [0.0] * Config.EMBEDDING_DIMENSION
                embeddings.append(embedding)
        return embeddings


class ConversationTurn:
    def __init__(self, ask: str, answer: str):
        self.ask = ask
        self.answer = answer

    def __str__(self):
        return f"user: {self.ask}\nassistant: {self.answer}"


class ConversationHistory:
    def __init__(self, max_turns: int = 20):
        self.turns = []
        self.max_turns = max_turns

        # 初始化向量数据库客户端
        self.client = chromadb.Client(Settings(
            persist_directory="save/memory",
            is_persistent=True
        ))
        
        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name="memory",
            embedding_function=APIEmbeddingFunction()
        )
        
    async def add_dialog(self, message: str, reply: str, user_info_processor=None):
        """添加新对话，并在需要时触发自动归档
        
        Args:
            message: 用户消息（或特殊标识SYSTEM_GUIDANCE）
            reply: 助手回复
            user_info_processor: 可选的UserInfoProcessor实例，用于同步用户信息
        """
        turn = ConversationTurn(message, reply)
        self.turns.append(turn)
        
        # 当对话数量达到最大值且不是系统引导消息时，自动归档一半的对话
        if len(self.turns) >= self.max_turns and message != "SYSTEM_GUIDANCE":
            await self._auto_archive(user_info_processor)
            
    async def _summarize_dialog(self, turns: List[ConversationTurn]) -> str:
        """对对话进行总结，生成用户人物画像
        
        Args:
            turns: 对话轮次列表
            
        Returns:
            str: 用户人物画像总结
        """
        # 提取所有对话内容
        all_text = "\n".join([f"{turn.ask}\n{turn.answer}" for turn in turns])
        
        # 使用LLM生成用户画像
        from llm import LLMService
        llm_service = LLMService(api_key=Config.LLM_API_KEY, api_url=Config.LLM_API_URL)
        
        prompt = f"""请根据以下对话内容，分析并总结用户的人物画像，包括：
                1. 性格特征
                2. 兴趣爱好
                3. 生活习惯
                4. 价值观
                5. 其他重要信息

                对话内容：
                {all_text}

                请以JSON格式返回，包含以下字段：
                {{
                    "personality": "性格特征描述",
                    "interests": "兴趣爱好描述",
                    "lifestyle": "生活习惯描述",
                    "values": "价值观描述",
                    "other_info": "其他重要信息"
                }}
                """
        
        try:
            response = await llm_service.generate_response(prompt, is_json=True)
            if response:
                # 将JSON格式转换为易读的文本格式
                summary = "用户人物画像：\n"
                summary += f"性格特征：{response.get('personality', '未知')}\n"
                summary += f"兴趣爱好：{response.get('interests', '未知')}\n"
                summary += f"生活习惯：{response.get('lifestyle', '未知')}\n"
                summary += f"价值观：{response.get('values', '未知')}\n"
                summary += f"其他信息：{response.get('other_info', '未知')}\n"
                return summary, response
        except Exception as e:
            print(f"生成用户画像时出错：{e}")
            
        # 如果生成失败，返回默认文本
        return "无法生成用户画像", None

    async def _auto_archive(self, user_info_processor=None):
        """自动归档一半的对话
        
        Args:
            user_info_processor: 可选的UserInfoProcessor实例，用于同步用户信息
        """
        if not self.turns:
            return
            
        # 计算要归档的对话数量
        archive_count = len(self.turns) // 2
        
        # 准备归档内容
        archive_turns = self.turns[:archive_count]
        
        # 对对话进行总结
        summary, raw_profile = await self._summarize_dialog(archive_turns)
        
        print("以下内容将被归档：")
        print(summary)
        print("--------------------------------")
        
        # 保存到向量数据库
        self.collection.add(
            documents=[summary],
            metadatas=[{
                "timestamp": datetime.now().isoformat(),
                "type": "user_profile"
            }],
            ids=[str(uuid.uuid4())]
        )
        
        # 移除已归档的对话
        self.turns = self.turns[archive_count:]
        
        # 如果提供了user_info_processor，尝试同步用户信息
        if user_info_processor and raw_profile:
            try:
                # 将用户画像信息转换为用户信息格式
                user_info_text = self._convert_profile_to_user_info(raw_profile, user_info_processor.user_info)
                
                # 判断是否有实质性变化
                if user_info_processor.has_substantial_changes(user_info_processor.user_info, user_info_text):
                    print("归档时检测到用户信息有实质性变化，进行同步更新")
                    user_info_processor.save_user_info(user_info_text)
                    return True, raw_profile
            except Exception as e:
                print(f"归档时同步用户信息出错: {e}")
        
        return raw_profile
        
    def get_context(self) -> str:
        """获取格式化后的对话上下文"""
        return "\n".join(str(turn) for turn in self.turns)
        
    def retrieve(self, user_message: str, n_results: int = 3) -> List[str]:
        """获取与用户消息最相关的历史记忆"""
        results = self.collection.query(
            query_texts=[user_message],
            n_results=n_results,
            include=['documents', 'metadatas'],
            where={"type": "user_profile"}  # 只查询用户画像类型的记忆
        )
        
        # 只返回用户画像类型的记忆
        if results['documents'] and results['metadatas']:
            return [doc for doc, meta in zip(results['documents'][0], results['metadatas'][0]) 
                   if meta.get('type') == 'user_profile']
        return []
    
    async def sync_profile_to_user_info(self, user_info_processor, force_update=False):
        """将用户画像同步到用户信息
        
        Args:
            user_info_processor: UserInfoProcessor实例
            force_update: 是否强制更新，即使没有达到最大对话轮次
            
        Returns:
            bool: 是否成功同步
        """
        if not self.turns:
            return False
        
        # 如果没有达到最大对话轮次且不是强制更新，则不进行同步
        if len(self.turns) < self.max_turns and not force_update:
            return False
        
        try:
            # 对当前所有对话进行总结
            summary, raw_profile = await self._summarize_dialog(self.turns)
            if not raw_profile:
                return False
            
            # 将用户画像信息转换为用户信息格式
            user_info_text = self._convert_profile_to_user_info(raw_profile, user_info_processor.user_info)
            
            # 判断是否有实质性变化
            if user_info_processor.has_substantial_changes(user_info_processor.user_info, user_info_text):
                print("检测到用户信息有实质性变化，进行同步更新")
                user_info_processor.save_user_info(user_info_text)
                return True
            
            return False
        except Exception as e:
            print(f"同步用户信息时出错: {e}")
            return False
        
    def _convert_profile_to_user_info(self, profile, current_user_info):
        """将用户画像转换为用户信息格式
        
        Args:
            profile: 用户画像JSON数据
            current_user_info: 当前用户信息文本
            
        Returns:
            str: 更新后的用户信息文本
        """
        # 如果没有当前用户信息，创建基本结构
        if not current_user_info:
            user_info = ""
        else:
            user_info = current_user_info
        
        # 解析当前用户信息
        info_dict = {}
        current_key = None
        current_value = []
        
        lines = user_info.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 检查是否是新的键值对
            if ":" in line or "：" in line:
                # 如果已有键，先保存之前的
                if current_key:
                    info_dict[current_key] = "\n".join(current_value)
                    current_value = []
                
                # 解析新的键值对
                parts = line.replace("：", ":").split(":", 1)
                if len(parts) == 2:
                    current_key = parts[0].strip()
                    value = parts[1].strip()
                    if value:  # 如果值不为空，直接保存
                        current_value.append(value)
                    else:  # 否则可能是多行值的开始
                        current_key = parts[0].strip()
            else:
                # 继续添加到当前值
                if current_key:
                    current_value.append(line)
        
        # 保存最后一个键值对
        if current_key and current_value:
            info_dict[current_key] = "\n".join(current_value)
        
        # 更新用户信息
        # 1. 更新兴趣爱好
        if "interests" in profile and profile["interests"] != "未知":
            interests = profile["interests"]
            if "爱好" in info_dict:
                current_hobbies = info_dict["爱好"].split("、")
                # 从用户画像中提取潜在的爱好
                new_hobbies = re.findall(r'([^，,、。.;；]+)(?:、|，|,|。|；|;|$)', interests)
                for hobby in new_hobbies:
                    hobby = hobby.strip()
                    if hobby and len(hobby) > 1 and hobby not in current_hobbies:
                        current_hobbies.append(hobby)
                info_dict["爱好"] = "、".join(current_hobbies)
            else:
                info_dict["爱好"] = interests.replace("，", "、").replace(",", "、")
        
        # 获取状态词典
        status_dict = self._parse_status_section(info_dict.get("最近状况", ""))
        
        # 2. 更新心理状态
        if ("personality" in profile and profile["personality"] != "未知") or \
           ("other_info" in profile and profile["other_info"] != "未知"):
            mental_state = profile.get("personality", "") + " " + profile.get("other_info", "")
            status_dict["心理状态"] = mental_state.strip()
        
        # 3. 更新价值观
        if "values" in profile and profile["values"] != "未知":
            info_dict["价值观"] = profile["values"]
        
        # 4. 更新生活习惯
        if "lifestyle" in profile and profile["lifestyle"] != "未知":
            status_dict["生活习惯"] = profile["lifestyle"]
        
        # 将更新后的状态词典重新格式化并更新到info_dict
        if status_dict:
            info_dict["最近状况"] = self._format_status_section(status_dict, 
                                                        is_numbered=info_dict.get("最近状况", "").strip().startswith("1."))
        
        # 重构用户信息文本
        user_info_text = ""
        basic_info_keys = ["姓名", "年龄", "性别", "学校", "专业", "年级", "爱好"]
        
        # 基本信息部分
        for key in basic_info_keys:
            if key in info_dict and info_dict[key]:
                user_info_text += f"{key}: {info_dict[key]}\n"
        
        user_info_text += "\n"
        
        # 最近状况部分
        if "最近状况" in info_dict:
            user_info_text += "最近状况: \n" + info_dict["最近状况"] + "\n"
        
        # 其他信息
        for key in info_dict:
            if key not in basic_info_keys and key != "最近状况" and info_dict[key]:
                user_info_text += f"{key}: {info_dict[key]}\n"
        
        return user_info_text.strip()
        
    def _parse_status_section(self, status_text):
        """解析最近状况部分，提取每个条目的键和值
        
        Args:
            status_text: 最近状况文本
            
        Returns:
            dict: 状态词典 {键: 值}
        """
        status_dict = {}
        status_lines = status_text.split("\n")
        
        for line in status_lines:
            if ":" in line or "：" in line:
                parts = line.replace("：", ":").split(":", 1)
                if len(parts) == 2:
                    full_key = parts[0].strip()
                    value = parts[1].strip()
                    
                    # 提取实际键（去掉序号）
                    if full_key.startswith(tuple("0123456789")):
                        try:
                            # 尝试解析"1. 键"格式
                            key = full_key.split(".", 1)[1].strip()
                        except:
                            # 处理其他格式
                            key = full_key.rstrip("0123456789.").strip()
                    else:
                        key = full_key
                        
                    status_dict[key] = value
                    
        return status_dict
        
    def _format_status_section(self, status_dict, is_numbered=True):
        """格式化状态词典为文本
        
        Args:
            status_dict: 状态词典 {键: 值}
            is_numbered: 是否使用编号格式
            
        Returns:
            str: 格式化后的状态文本
        """
        if not status_dict:
            return ""
            
        if is_numbered:
            # 使用编号格式
            items = []
            for i, (key, value) in enumerate(status_dict.items(), 1):
                items.append(f"{i}. {key}: {value}")
            return "\n".join(items)
        else:
            # 使用普通格式
            items = []
            for key, value in status_dict.items():
                items.append(f"{key}: {value}")
            return "\n".join(items)


if __name__ == "__main__":
    async def main():
        conversation_history = ConversationHistory(max_turns=20)
        #conversation_history.add_dialog("广州有什么好吃的", "有烧鹅")
        #conversation_history.add_dialog("最近有什么电影看", "有流浪地球2")
        
        # 使用 await 调用异步方法
        #await conversation_history.archive(1, 1, "电影推荐")
        #await conversation_history.archive(0, 0, "广州有什么好吃的")
        
        memories = conversation_history.retrieve("广州美食", n_results=1)
        print("--------------------------------")
        print(memories)

    # 运行异步主函数
    asyncio.run(main())

