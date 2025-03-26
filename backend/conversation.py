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
        
        print(f"对话历史: 当前共有{len(self.turns)}轮对话")
        
        # 当对话数量达到10轮且不是系统引导消息时，触发自动归档
        if len(self.turns) >= 10 and message != "SYSTEM_GUIDANCE":
            print(f"对话数量达到{len(self.turns)}轮，触发自动归档")
            await self._auto_archive(user_info_processor)
            
    async def _summarize_dialog(self, turns: List[ConversationTurn]) -> str:
        """对对话进行总结，生成用户人物画像
        
        Args:
            turns: 对话轮次列表
            
        Returns:
            str: 用户人物画像总结
        """
        # 提取所有对话内容
        all_text = "\n".join([f"用户: {turn.ask}\n助手: {turn.answer}" for turn in turns])
        
        # 使用LLM生成用户画像
        from llm import LLMService
        llm_service = LLMService(api_key=Config.LLM_API_KEY, api_url=Config.LLM_API_URL)
        
        prompt = f"""请你仔细分析以下对话内容，并对这段对话进行全面而详细的总结。
                
                你需要总结的方面包括：
                1. 对话主题（对话主要讨论了什么内容）
                2. 用户关注点（用户最关心的问题或事情）
                3. 用户情感状态（用户的情绪变化和表现）
                4. 用户人物特征分析，包括：
                   - 性格特征
                   - 兴趣爱好
                   - 生活习惯
                   - 价值观
                5. 对话中提到的关键事实（如用户提到的具体经历、活动、人物等）
                6. 用户可能面临的问题
                7. 助手提供的主要建议

                对话内容：
                {all_text}

                请以JSON格式返回，包含以下字段：
                {{
                    "conversation_topic": "对话主题的详细描述",
                    "user_focus": "用户关注点的详细描述",
                    "emotional_state": "用户情感状态的详细描述",
                    "personality": "性格特征的详细描述",
                    "interests": "兴趣爱好的详细描述",
                    "lifestyle": "生活习惯的详细描述",
                    "values": "价值观的详细描述",
                    "key_facts": "对话中提到的关键事实的详细描述",
                    "user_issues": "用户可能面临的问题的详细描述",
                    "assistant_suggestions": "助手提供的主要建议的详细描述"
                }}
                
                重要提示：请确保分析全面且深入，捕捉对话中的隐含信息和细节。如果某些信息在对话中未提及，请在相应字段中标注"未提及"。
                """
        
        try:
            response = await llm_service.generate_response(prompt, is_json=True)
            if response:
                # 将JSON格式转换为易读的文本格式
                summary = "对话归纳总结：\n\n"
                summary += f"对话主题：{response.get('conversation_topic', '未提及')}\n\n"
                summary += f"用户关注点：{response.get('user_focus', '未提及')}\n\n"
                summary += f"情感状态：{response.get('emotional_state', '未提及')}\n\n"
                summary += "用户人物画像：\n"
                summary += f"- 性格特征：{response.get('personality', '未提及')}\n"
                summary += f"- 兴趣爱好：{response.get('interests', '未提及')}\n"
                summary += f"- 生活习惯：{response.get('lifestyle', '未提及')}\n"
                summary += f"- 价值观：{response.get('values', '未提及')}\n\n"
                summary += f"关键事实：{response.get('key_facts', '未提及')}\n\n"
                summary += f"用户问题：{response.get('user_issues', '未提及')}\n\n"
                summary += f"助手建议：{response.get('assistant_suggestions', '未提及')}\n"
                return summary, response
        except Exception as e:
            print(f"生成对话总结时出错：{e}")
            
        # 如果生成失败，返回默认文本
        return "无法生成对话总结", None

    async def _auto_archive(self, user_info_processor=None):
        """自动归档一半的对话
        
        Args:
            user_info_processor: 可选的UserInfoProcessor实例，用于同步用户信息
        """
        if not self.turns:
            return
            
        # 计算要归档的对话数量 (降低阈值，每10次对话就进行归档)
        archive_count = min(10, len(self.turns) // 2)
        
        if archive_count < 3:  # 确保至少有3轮对话才进行归档
            archive_count = 3
        
        # 准备归档内容
        archive_turns = self.turns[:archive_count]
        
        # 对对话进行总结
        summary, raw_profile = await self._summarize_dialog(archive_turns)
        
        print("\n==== 开始对话归档 ====")
        print(f"归档轮数: {archive_count}/{len(self.turns)}")
        print("归档总结:")
        print(summary)
        print("==== 归档完成 ====\n")
        
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
            
            print("\n==== 开始用户信息同步 ====")
            print("对话总结生成完成，准备更新用户信息")
            
            # 保存原始用户信息用于对比
            original_user_info = user_info_processor.user_info

            # 将用户画像信息转换为用户信息格式
            user_info_text = self._convert_profile_to_user_info(raw_profile, user_info_processor.user_info)
            
            # 判断是否有实质性变化
            if user_info_processor.has_substantial_changes(original_user_info, user_info_text):
                print("检测到用户信息有实质性变化，进行同步更新")
                print("更改前的用户信息:")
                print("----------------------------------------")
                print(original_user_info)
                print("----------------------------------------")
                print("更改后的用户信息:")
                print("----------------------------------------")
                print(user_info_text)
                print("----------------------------------------")
                user_info_processor.save_user_info(user_info_text)
                print("用户信息已成功更新")
                print("==== 用户信息同步完成 ====\n")
                return True
            else:
                print("未检测到用户信息有实质性变化，跳过更新")
                print("==== 用户信息同步完成 ====\n")
            
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
        if "interests" in profile and profile["interests"] != "未知" and profile["interests"] != "未提及":
            interests = profile["interests"]
            if "爱好" in info_dict:
                # 解析现有爱好，确保它是一个列表
                if info_dict["爱好"].startswith("[") and info_dict["爱好"].endswith("]"):
                    try:
                        import ast
                        current_hobbies = ast.literal_eval(info_dict["爱好"])
                    except:
                        # 如果解析失败，按常规方式分割
                        current_hobbies = info_dict["爱好"].replace("[", "").replace("]", "").split("、")
                else:
                    current_hobbies = info_dict["爱好"].split("、")
                
                # 清理列表项
                current_hobbies = [h.strip().strip("'\"") for h in current_hobbies if h.strip()]
                
                # 从用户画像中提取潜在的爱好
                new_hobbies = re.findall(r'([^，,、。.;；]+)(?:、|，|,|。|；|;|$)', interests)
                for hobby in new_hobbies:
                    hobby = hobby.strip()
                    if hobby and len(hobby) > 1 and hobby not in current_hobbies:
                        current_hobbies.append(hobby)
                
                if current_hobbies:
                    info_dict["爱好"] = "、".join(current_hobbies)
            else:
                info_dict["爱好"] = interests.replace("，", "、").replace(",", "、")
        
        # 获取状态词典
        status_dict = self._parse_status_section(info_dict.get("最近状况", ""))
        
        # 2. 更新心理状态
        if ("emotional_state" in profile and profile["emotional_state"] not in ["未知", "未提及"]) or \
           ("personality" in profile and profile["personality"] not in ["未知", "未提及"]):
            mental_state = ""
            if "emotional_state" in profile and profile["emotional_state"] not in ["未知", "未提及"]:
                mental_state += profile["emotional_state"]
            if "personality" in profile and profile["personality"] not in ["未知", "未提及"]:
                if mental_state:
                    mental_state += "。"
                mental_state += profile["personality"]
            
            # 如果已有心理状态信息，整合而不是替换
            if "心理状态" in status_dict and status_dict["心理状态"]:
                current_mental = status_dict["心理状态"]
                # 避免重复信息
                if mental_state and not any(part in current_mental for part in mental_state.split("。")):
                    status_dict["心理状态"] = f"{current_mental}。{mental_state}"
            else:
                status_dict["心理状态"] = mental_state.strip()
        
        # 3. 更新价值观
        if "values" in profile and profile["values"] not in ["未知", "未提及"]:
            if "价值观" in info_dict and info_dict["价值观"]:
                # 整合现有价值观信息
                current_values = info_dict["价值观"]
                new_values = profile["values"]
                # 避免重复信息
                if not any(part in current_values for part in new_values.split("。")):
                    info_dict["价值观"] = f"{current_values}。{new_values}"
            else:
                info_dict["价值观"] = profile["values"]
        
        # 4. 更新生活习惯
        if "lifestyle" in profile and profile["lifestyle"] not in ["未知", "未提及"]:
            if "生活习惯" in status_dict and status_dict["生活习惯"]:
                # 整合现有生活习惯信息
                current_lifestyle = status_dict["生活习惯"]
                new_lifestyle = profile["lifestyle"]
                # 避免重复信息
                if not any(part in current_lifestyle for part in new_lifestyle.split("。")):
                    status_dict["生活习惯"] = f"{current_lifestyle}。{new_lifestyle}"
            else:
                status_dict["生活习惯"] = profile["lifestyle"]
        
        # 5. 处理其他关键信息
        if "user_issues" in profile and profile["user_issues"] not in ["未知", "未提及"]:
            # 根据用户问题更新相关状态字段
            issues = profile["user_issues"]
            # 学习相关问题
            if any(kw in issues.lower() for kw in ["学习", "考试", "成绩", "课程"]):
                if "学习情况" in status_dict:
                    # 整合，避免重复
                    if not any(part in status_dict["学习情况"] for part in issues.split("。")):
                        status_dict["学习情况"] = f"{status_dict['学习情况']}。{issues}"
                else:
                    status_dict["学习情况"] = issues
            
            # 人际关系问题
            if any(kw in issues.lower() for kw in ["人际", "关系", "朋友", "同学", "孤立"]):
                if "人际关系" in status_dict:
                    # 整合，避免重复
                    if not any(part in status_dict["人际关系"] for part in issues.split("。")):
                        status_dict["人际关系"] = f"{status_dict['人际关系']}。{issues}"
                else:
                    status_dict["人际关系"] = issues
        
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

