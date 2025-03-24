from typing import List
import chromadb
from chromadb.config import Settings
from chromadb.api.types import EmbeddingFunction
from datetime import datetime
import uuid
from embedding import EmbeddingService
from config import Config

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
        
    async def add_dialog(self, user_message: str, assistant_message: str):
        """添加新对话，并在需要时触发自动归档"""
        turn = ConversationTurn(user_message, assistant_message)
        self.turns.append(turn)
        
        # 当对话数量达到最大值时，自动归档一半的对话
        if len(self.turns) >= self.max_turns:
            await self._auto_archive()
            
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
        llm_service = LLMService()
        
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
                return summary
        except Exception as e:
            print(f"生成用户画像时出错：{e}")
            
        # 如果生成失败，返回默认文本
        return "无法生成用户画像"

    async def _auto_archive(self):
        """自动归档一半的对话"""
        if not self.turns:
            return
            
        # 计算要归档的对话数量
        archive_count = len(self.turns) // 2
        
        # 准备归档内容
        archive_turns = self.turns[:archive_count]
        
        # 对对话进行总结
        summary = await self._summarize_dialog(archive_turns)
        
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

