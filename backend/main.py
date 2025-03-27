from fastapi import FastAPI, WebSocket, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import base64
from chat_service import ChatService
from tts import TTSService
from super_tts import SuperTTSService
from config import Config
from speech_service import SpeechService
import uvicorn
import json
import asyncio
import os
import uuid
import shutil
import tempfile
import time
import re
# from llm import LLMService  # 注释掉，因为我们使用chat_service中的LLM服务

app = FastAPI()

# CORS设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    agent_type: Optional[str] = None
    personality: Optional[str] = None
    is_category: Optional[bool] = False

class AgentRequest(BaseModel):
    agent_name: str
    session_id: Optional[str] = "default"

class CustomAgentRequest(BaseModel):
    name: str
    description: str
    model: str
    personality: str
    interests: str
    lifestyle: str
    values: str

class TTSSettingsRequest(BaseModel):
    enable_tts: bool
    enable_super_tts: bool
    tts_voice: Optional[str] = None
    super_tts_voice: Optional[str] = None
    tts_speed: Optional[int] = None
    typing_speed: Optional[int] = None

class TTSSettings(BaseModel):
    enable_tts: bool
    enable_super_tts: bool
    tts_voice: str
    super_tts_voice: str
    tts_voice_list: list
    super_tts_voice_list: list
    tts_speed: int
    typing_speed: int

chat_service = ChatService()
tts_service = TTSService()
super_tts_service = SuperTTSService()
speech_service = SpeechService()
# llm_service = LLMService(Config.LLM_API_KEY, Config.LLM_API_URL)  # 注释掉，使用chat_service中的LLM服务

# 确保保存自定义角色的目录存在
CUSTOM_AGENTS_DIR = "save/custom_agents"
TEMP_UPLOADS_DIR = "temp_uploads"
os.makedirs(CUSTOM_AGENTS_DIR, exist_ok=True)
os.makedirs(TEMP_UPLOADS_DIR, exist_ok=True)

# 文本提取函数
def extract_text_from_file(file_path, file_extension):
    """从不同格式的文件中提取文本
    
    Args:
        file_path (str): 文件路径
        file_extension (str): 文件扩展名
        
    Returns:
        str: 提取的文本内容
    """
    if file_extension == '.txt':
        # 直接读取文本文件
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # 尝试使用其他编码
            with open(file_path, 'r', encoding='gbk') as f:
                return f.read()
    
    elif file_extension in ['.doc', '.docx']:
        try:
            # 使用python-docx库提取文本
            import docx
            doc = docx.Document(file_path)
            return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
        except ImportError:
            return "缺少python-docx库，无法解析Word文档。"
    
    elif file_extension == '.pdf':
        try:
            # 使用PyPDF2提取文本
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except ImportError:
            return "缺少PyPDF2库，无法解析PDF文档。"
    
    return "不支持的文件格式"

@app.post("/api/extract_agent_info")
async def extract_agent_info(file: UploadFile = File(...)):
    """从上传的文件中提取Agent信息
    
    Args:
        file: 上传的文件
        
    Returns:
        dict: 包含提取结果的响应
    """
    try:
        # 检查文件类型
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in ['.txt', '.pdf', '.doc', '.docx']:
            return JSONResponse(
                content={
                    "success": False,
                    "message": "不支持的文件格式，仅支持txt、pdf、doc、docx"
                }
            )
        
        # 保存上传的文件
        temp_file_path = os.path.join(TEMP_UPLOADS_DIR, f"{uuid.uuid4()}{file_extension}")
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 提取文本内容
        file_content = extract_text_from_file(temp_file_path, file_extension)
        
        if not file_content or file_content == "不支持的文件格式":
            return JSONResponse(
                content={
                    "success": False,
                    "message": "文件内容提取失败或文件为空"
                }
            )
            
        # 使用chat_service中的LLM服务提取角色信息
        prompt = f"""请从以下文本中提取出一个可能的角色描述信息，包括：
1. 角色名称 (name)
2. 性格特征 (personality)
3. 兴趣爱好 (interests)
4. 生活习惯 (lifestyle)
5. 价值观 (values)
6. 角色标签 (tags)：请从这些词中选择最多4个最符合角色特点的标签：温柔体贴、阳光活泼、冷酷高傲、知性优雅、单纯天真、幽默风趣、古灵精怪、深沉内敛、率真直爽、浪漫多情、神秘莫测、坚毅果断、温暖治愈、机智敏锐、傲娇可爱

如果某些信息无法从文本中提取，可以留空。
请以JSON格式返回结果，如：
{{
  "name": "...",
  "personality": "...",
  "interests": "...",
  "lifestyle": "...",
  "values": "...",
  "tags": ["标签1", "标签2", ...]
}}

文本内容：
{file_content[:2000]}  # 限制文本长度
"""
        
        # 使用chat_service中的llm_service
        response = await chat_service.llm_service.async_chat(prompt)
        
        # 尝试解析LLM返回的JSON
        try:
            # 从回复中提取JSON部分
            start_index = response.find('{')
            end_index = response.rfind('}') + 1
            
            if start_index >= 0 and end_index > start_index:
                json_str = response[start_index:end_index]
                agent_info = json.loads(json_str)
                
                # 移除临时文件
                os.remove(temp_file_path)
                
                return JSONResponse(
                    content={
                        "success": True,
                        "name": agent_info.get("name", ""),
                        "personality": agent_info.get("personality", ""),
                        "interests": agent_info.get("interests", ""),
                        "lifestyle": agent_info.get("lifestyle", ""),
                        "values": agent_info.get("values", ""),
                        "tags": agent_info.get("tags", [])
                    }
                )
            else:
                raise ValueError("无法在回复中找到JSON格式数据")
                
        except Exception as e:
            print(f"解析LLM回复失败: {e}")
            print(f"LLM回复内容: {response}")
            
            # 移除临时文件
            os.remove(temp_file_path)
            
            return JSONResponse(
                content={
                    "success": False,
                    "message": f"解析文件信息失败: {str(e)}"
                }
            )
            
    except Exception as e:
        print(f"处理上传文件失败: {e}")
        return JSONResponse(
            content={
                "success": False,
                "message": f"处理文件失败: {str(e)}"
            }
        )

@app.post("/api/create_custom_agent")
async def create_custom_agent(request: CustomAgentRequest):
    """创建自定义角色
    
    Args:
        request: 角色信息
        
    Returns:
        dict: 包含创建结果的响应
    """
    try:
        # 生成唯一ID
        agent_id = f"custom_{uuid.uuid4().hex[:8]}"
        
        # 创建角色配置文件
        agent_config = {
            "id": agent_id,
            "name": request.name,
            "description": request.description,
            "model": request.model,
            "personality": request.personality,
            "interests": request.interests,
            "lifestyle": request.lifestyle,
            "values": request.values
        }
        
        with open(os.path.join(CUSTOM_AGENTS_DIR, f"{agent_id}.json"), "w", encoding="utf-8") as f:
            json.dump(agent_config, f, ensure_ascii=False, indent=2)
        
        # 先只写入角色基本信息
        agent_file_path = os.path.join(CUSTOM_AGENTS_DIR, f"{agent_id}.txt")
        with open(agent_file_path, "w", encoding="utf-8") as f:
            f.write(f"""你是一个名为{request.name}的角色。
{request.description}

性格特征：
{request.personality}

兴趣爱好：
{request.interests}

生活习惯：
{request.lifestyle}

价值观：
{request.values}
""")
        
        # 先尝试从nanaA.txt读取任务规则部分
        template_paths = ["prompts/nanaA.txt", "prompts/prompt_template.txt"]
        task_rules = None
        
        for template_path in template_paths:
            try:
                if os.path.exists(template_path):
                    with open(template_path, "r", encoding="utf-8") as template_file:
                        template_content = template_file.read()
                        
                        # 查找任务规则的起始位置
                        task_input_pos = template_content.find("任务输入:")
                        if task_input_pos > 0:
                            # 提取任务规则部分
                            task_rules = template_content[task_input_pos:]
                            break  # 找到有效模板即退出循环
            except Exception as e:
                print(f"读取模板 {template_path} 失败: {e}")
        
        # 如果找到了有效的任务规则，追加到角色文件中
        if task_rules:
            with open(agent_file_path, "a", encoding="utf-8") as agent_file:
                agent_file.write("\n" + task_rules)
        else:
            # 使用硬编码的任务规则作为后备方案 - 使用原始字符串避免处理大括号
            with open(agent_file_path, "a", encoding="utf-8") as agent_file:
                agent_file.write(r"""
任务输入:
用户的个人信息：
{user_info}

对话记录：
{chat_history}

用户的最新问题：
{user_message}

相关记忆：
{memory}

任务输出:
1. 回复内容
2. 表情
3. 用户个人信息（仅在用户明确提供新信息时才更新）

回复规则：
1. 对于普通对话，回复控制在15字以内
2. 对于快捷提问类别（如情感咨询师、人际关系等），需要提供专业且详细的回答，字数不限
3. 根据历史对话记录和补充信息回答问题
4. 当用户使用快捷提问类别且有相关的用户信息时，请根据这些信息提供个性化的专业建议
5. 提供建议时，仅关注解决方案和专业分析，不要在建议中附加引导用户做决策的问题
6. 当用户回复了决策（如"我决定原谅他"、"我选择继续努力"等）时，应立即更新相关用户信息，反映用户的最新选择和态度变化

用户个人信息处理规则：
1. 当用户明确提供新的个人信息，或对建议做出选择和决策时，在输出中包含"user_info"字段
2. 如果用户没有提供新信息或没有做出明确决策，请勿包含"user_info"字段
3. 新的个人信息应该保持原有格式，不要随意添加不确定的信息
4. 当用户做出决策后，应更新相关的用户信息部分，如修改"最近状况"中的相关条目，反映用户的新选择

表情规则：
在以下表情选一个表情符合回复的内容
吐舌,黑脸,眼泪,脸红,nn眼,生气瘪嘴,死鱼眼,生气,咪咪眼,嘟嘴,钱钱眼,爱心,泪眼

输出格式：
必须输出以下JSON格式（仅在有新用户信息时才包含user_info字段）：
{{
  "reply": "<回答内容>",
  "expression": "<表情>"
}}

或者当用户提供了新的个人信息或做出了决策时：
{{
  "reply": "<回答内容>",
  "expression": "<表情>",
  "user_info": "<用户个人信息>"
}} """)
            
        return JSONResponse(
            content={
                "success": True,
                "message": f"成功创建角色 {request.name}",
                "agent_id": agent_id
            }
        )
    except Exception as e:
        print(f"创建自定义角色失败: {e}")
        return JSONResponse(
            content={
                "success": False,
                "message": f"创建角色失败: {str(e)}"
            }
        )

@app.get("/api/list_custom_agents")
async def list_custom_agents():
    """获取所有自定义角色列表
    
    Returns:
        dict: 包含自定义角色列表的响应
    """
    try:
        agents = []
        if not os.path.exists(CUSTOM_AGENTS_DIR):
            return JSONResponse(
                content={
                    "success": True,
                    "agents": []
                }
            )
            
        for filename in os.listdir(CUSTOM_AGENTS_DIR):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(CUSTOM_AGENTS_DIR, filename), "r", encoding="utf-8") as f:
                        agent_config = json.load(f)
                        # 确保agent_config包含所有必要字段
                        required_fields = ["id", "name", "description", "model", 
                                          "personality", "interests", "lifestyle", "values"]
                        for field in required_fields:
                            if field not in agent_config:
                                agent_config[field] = ""
                        agents.append(agent_config)
                except Exception as e:
                    print(f"读取自定义角色配置文件失败: {filename}, 错误: {e}")
        
        return JSONResponse(
            content={
                "success": True,
                "agents": agents
            }
        )
    except Exception as e:
        print(f"获取自定义角色列表失败: {e}")
        return JSONResponse(
            content={
                "success": False,
                "message": f"获取角色列表失败: {str(e)}"
            }
        )

@app.put("/api/update_custom_agent/{agent_id}")
async def update_custom_agent(agent_id: str, request: CustomAgentRequest):
    """更新自定义角色
    
    Args:
        agent_id: 角色ID
        request: 更新后的角色信息
        
    Returns:
        dict: 包含更新结果的响应
    """
    try:
        # 检查是否是自定义角色
        if not agent_id.startswith("custom_"):
            return JSONResponse(
                content={
                    "success": False,
                    "message": "只能更新自定义角色"
                }
            )
            
        # 检查角色是否存在
        config_path = os.path.join(CUSTOM_AGENTS_DIR, f"{agent_id}.json")
        if not os.path.exists(config_path):
            return JSONResponse(
                content={
                    "success": False,
                    "message": "角色不存在"
                }
            )
            
        # 更新角色配置文件
        agent_config = {
            "id": agent_id,
            "name": request.name,
            "description": request.description,
            "model": request.model,
            "personality": request.personality,
            "interests": request.interests,
            "lifestyle": request.lifestyle,
            "values": request.values
        }
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(agent_config, f, ensure_ascii=False, indent=2)
        
        # 读取现有的提示词文件，保留任务规则部分
        prompt_path = os.path.join(CUSTOM_AGENTS_DIR, f"{agent_id}.txt")
        task_rules = ""
        
        if os.path.exists(prompt_path):
            try:
                with open(prompt_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # 查找任务规则的起始位置
                    task_input_pos = content.find("任务输入:")
                    if task_input_pos > 0:
                        # 提取任务规则部分
                        task_rules = content[task_input_pos:]
            except Exception as e:
                print(f"读取现有提示词文件失败: {e}")
                # 如果读取失败，尝试从固定模板中读取
                template_paths = ["prompts/nanaA.txt", "prompts/prompt_template.txt"]
                for template_path in template_paths:
                    try:
                        if os.path.exists(template_path):
                            with open(template_path, "r", encoding="utf-8") as template_file:
                                template_content = template_file.read()
                                
                                # 查找任务规则的起始位置
                                task_input_pos = template_content.find("任务输入:")
                                if task_input_pos > 0:
                                    # 提取任务规则部分
                                    task_rules = template_content[task_input_pos:]
                                    break  # 找到有效模板即退出循环
                    except Exception as template_error:
                        print(f"读取模板 {template_path} 失败: {template_error}")
                
                # 如果仍然没有找到有效的任务规则，使用硬编码的后备方案
                if not task_rules:
                    task_rules = r"""任务输入:
用户的个人信息：
{user_info}

对话记录：
{chat_history}

用户的最新问题：
{user_message}

相关记忆：
{memory}

任务输出:
1. 回复内容
2. 表情
3. 用户个人信息（仅在用户明确提供新信息时才更新）

回复规则：
1. 对于普通对话，回复控制在15字以内
2. 对于快捷提问类别（如情感咨询师、人际关系等），需要提供专业且详细的回答，字数不限
3. 根据历史对话记录和补充信息回答问题
4. 当用户使用快捷提问类别且有相关的用户信息时，请根据这些信息提供个性化的专业建议
5. 提供建议时，仅关注解决方案和专业分析，不要在建议中附加引导用户做决策的问题
6. 当用户回复了决策（如"我决定原谅他"、"我选择继续努力"等）时，应立即更新相关用户信息，反映用户的最新选择和态度变化

用户个人信息处理规则：
1. 当用户明确提供新的个人信息，或对建议做出选择和决策时，在输出中包含"user_info"字段
2. 如果用户没有提供新信息或没有做出明确决策，请勿包含"user_info"字段
3. 新的个人信息应该保持原有格式，不要随意添加不确定的信息
4. 当用户做出决策后，应更新相关的用户信息部分，如修改"最近状况"中的相关条目，反映用户的新选择

表情规则：
在以下表情选一个表情符合回复的内容
吐舌,黑脸,眼泪,脸红,nn眼,生气瘪嘴,死鱼眼,生气,咪咪眼,嘟嘴,钱钱眼,爱心,泪眼

输出格式：
必须输出以下JSON格式（仅在有新用户信息时才包含user_info字段）：
{{
  "reply": "<回答内容>",
  "expression": "<表情>"
}}

或者当用户提供了新的个人信息或做出了决策时：
{{
  "reply": "<回答内容>",
  "expression": "<表情>",
  "user_info": "<用户个人信息>"
}}"""
                
        # 更新角色提示词文件，保留任务规则部分
        with open(prompt_path, "w", encoding="utf-8") as f:
            # 写入角色基本信息
            f.write(f"""你是一个名为{request.name}的角色。
{request.description}

性格特征：
{request.personality}

兴趣爱好：
{request.interests}

生活习惯：
{request.lifestyle}

价值观：
{request.values}

""")
            # 追加任务规则部分
            f.write(task_rules)
            
        return JSONResponse(
            content={
                "success": True,
                "message": f"成功更新角色 {request.name}"
            }
        )
    except Exception as e:
        print(f"更新自定义角色失败: {e}")
        return JSONResponse(
            content={
                "success": False,
                "message": f"更新角色失败: {str(e)}"
            }
        )

@app.delete("/api/delete_custom_agent/{agent_id}")
async def delete_custom_agent(agent_id: str):
    """删除自定义角色
    
    Args:
        agent_id: 角色ID
        
    Returns:
        dict: 包含删除结果的响应
    """
    try:
        # 检查是否是自定义角色
        if not agent_id.startswith("custom_"):
            return JSONResponse(
                content={
                    "success": False,
                    "message": "只能删除自定义角色"
                }
            )
            
        # 删除配置文件
        config_path = os.path.join(CUSTOM_AGENTS_DIR, f"{agent_id}.json")
        if os.path.exists(config_path):
            os.remove(config_path)
            
        # 删除提示词文件
        prompt_path = os.path.join(CUSTOM_AGENTS_DIR, f"{agent_id}.txt")
        if os.path.exists(prompt_path):
            os.remove(prompt_path)
            
        return JSONResponse(
            content={
                "success": True,
                "message": f"成功删除角色 {agent_id}"
            }
        )
    except Exception as e:
        print(f"删除自定义角色失败: {e}")
        return JSONResponse(
            content={
                "success": False,
                "message": f"删除角色失败: {str(e)}"
            }
        )

@app.post("/api/chat")
async def chat(request: ChatRequest):
    return await normal_chat_flow(request)

@app.post("/api/stream_chat")
async def stream_chat(request: ChatRequest):
    """流式聊天API，支持打字机式回复
    
    Args:
        request: 聊天请求
        
    Returns:
        StreamingResponse: 流式响应
    """
    async def generate_stream_response():
        try:
            # 验证请求数据
            if not request.message or not request.message.strip():
                yield json.dumps({
                    "type": "metadata",
                    "expression": "生气",
                    "error": "消息内容不能为空"
                }) + "\n"
                
                yield json.dumps({
                    "type": "complete",
                    "content": "请输入有效的消息内容"
                }) + "\n"
                return
            
            # 生成回复
            reply, audio_data, expression, guidance_message = await chat_service.generate_reply(
                request.message, 
                request.session_id,
                agent_type=request.agent_type,
                personality=request.personality,
                is_category=request.is_category
            )
            
            # 用于调试输出
            print("-- /api/stream_chat --")
            print("agent_type:", request.agent_type)
            print("personality:", request.personality)
            print("is_category:", request.is_category)
            print("reply:", reply)
            print("expression:", expression)
            print("audio_data 大小:", len(audio_data) if audio_data else 0, "字节")
            
            # 检查是否获取到有效回复
            if not reply:
                yield json.dumps({
                    "type": "metadata",
                    "expression": "生气",
                    "error": "未能生成有效回复"
                }) + "\n"
                
                yield json.dumps({
                    "type": "complete",
                    "content": "抱歉，我现在无法回答。请稍后再试。"
                }) + "\n"
                return
            
            # 先发送表情和引导消息的元数据
            metadata = {
                "type": "metadata",
                "expression": expression,
                "message_id": int(time.time() * 1000)  # 添加唯一消息ID
            }
            
            if guidance_message:
                metadata["guidance_message"] = guidance_message
                
            yield json.dumps(metadata) + "\n"
            
            # 如果有音频数据，处理后发送
            if audio_data and len(audio_data) > 100:  # 确保音频数据长度合理
                # 对于大型音频数据进行分片处理
                MAX_CHUNK_SIZE = 32 * 1024  # 32KB 分片大小，避免JSON解析问题
                base64_audio = base64.b64encode(audio_data).decode('ascii')
                
                # 检查音频数据大小
                audio_size = len(base64_audio)
                print(f"Base64编码后的音频大小: {audio_size} 字符")
                
                if audio_size > MAX_CHUNK_SIZE:
                    # 如果音频过大，分片发送
                    chunks = []
                    for i in range(0, audio_size, MAX_CHUNK_SIZE):
                        chunks.append(base64_audio[i:i+MAX_CHUNK_SIZE])
                    
                    print(f"音频数据过大，分为 {len(chunks)} 个片段发送")
                    
                    # 发送第一个分片作为开始
                    first_chunk = {
                        "type": "audio_start",
                        "total_chunks": len(chunks),
                        "chunk_index": 0,
                        "audio_chunk": chunks[0]
                    }
                    yield json.dumps(first_chunk) + "\n"
                    
                    # 发送中间分片
                    for i in range(1, len(chunks) - 1):
                        chunk = {
                            "type": "audio_chunk",
                            "chunk_index": i,
                            "audio_chunk": chunks[i]
                        }
                        yield json.dumps(chunk) + "\n"
                    
                    # 发送最后一个分片
                    if len(chunks) > 1:
                        last_chunk = {
                            "type": "audio_end",
                            "chunk_index": len(chunks) - 1,
                            "audio_chunk": chunks[-1]
                        }
                        yield json.dumps(last_chunk) + "\n"
                    
                    print("音频分片发送完成")
                else:
                    # 音频数据不大，一次性发送
                    try:
                        audio_message = {
                            "type": "audio",
                            "audio": base64_audio
                        }
                        yield json.dumps(audio_message) + "\n"
                        print("完整音频数据发送成功")
                    except Exception as audio_error:
                        print(f"发送音频数据时出错: {audio_error}")
            elif not audio_data:
                # 如果没有音频数据，记录这个情况
                print("没有收到音频数据，跳过音频发送")
            
            # 逐字发送回复内容，确保每个字符都是有效的
            for char in reply:
                chunk = {
                    "type": "chunk",
                    "content": char
                }
                yield json.dumps(chunk) + "\n"
                
                # 使用配置中的打字速度，转换为秒，添加错误处理
                try:
                    typing_speed = Config.TYPING_SPEED
                    # 确保打字速度在合理范围内
                    if not isinstance(typing_speed, int) or typing_speed < 10:
                        typing_speed = 38  # 使用默认值
                    elif typing_speed > 200:
                        typing_speed = 200
                        
                    typing_delay = typing_speed / 1000.0
                    # 确保延迟时间不会太长
                    if typing_delay > 0.2:
                        print(f"打字延迟过长 ({typing_delay}秒)，限制为0.2秒")
                        typing_delay = 0.2
                        
                    await asyncio.sleep(typing_delay)
                except Exception as e:
                    print(f"处理打字延迟时出错: {e}")
                    # 使用默认延迟
                    await asyncio.sleep(0.038)
            
            # 发送完成标记
            complete = {
                "type": "complete"
            }
            
            yield json.dumps(complete) + "\n"
            
        except asyncio.CancelledError:
            # 处理客户端取消请求
            print("客户端取消了请求")
            raise
        except Exception as e:
            # 处理所有其他异常
            print(f"流式聊天生成出错: {str(e)}")
            error_metadata = {
                "type": "metadata",
                "expression": "生气",
                "error": "服务器处理错误"
            }
            yield json.dumps(error_metadata) + "\n"
            
            error_message = {
                "type": "complete",
                "content": "抱歉，处理您的请求时出现了错误。请稍后再试。"
            }
            yield json.dumps(error_message) + "\n"
    
    return StreamingResponse(
        generate_stream_response(),
        media_type="application/x-ndjson"
    )

@app.post("/api/change_agent")
async def change_agent(request: AgentRequest):
    success = chat_service.change_agent(request.agent_name, request.session_id)
    return JSONResponse(
        content={
            "success": success,
            "message": f"已切换到{request.agent_name}" if success else "切换失败，请检查智能体名称"
        }
    )

@app.post("/speech-to-text")
async def speech_to_text(audio: UploadFile = File(...)):
    """处理语音识别请求
    
    Args:
        audio: 上传的音频文件
        
    Returns:
        dict: 包含识别结果的响应
    """
    try:
        # 读取音频数据
        audio_data = await audio.read()
        
        # 调用语音识别服务
        text = await speech_service.process_audio(audio_data)
        
        return {"success": True, "text": text}
    except Exception as e:
        print(f"语音识别处理失败: {e}")
        return {"success": False, "error": str(e)}

@app.websocket("/chat")
async def chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            
            if data["type"] == "message":
                # 处理文本消息
                response = await chat_service.get_response(
                    data["content"],
                    data.get("personality")
                )
                await websocket.send_json(response)
                
    except Exception as e:
        print(f"WebSocket错误: {e}")
    finally:
        await websocket.close()

async def normal_chat_flow(request: ChatRequest):
    reply, audio_data, expression, guidance_message = await chat_service.generate_reply(
        request.message, 
        request.session_id,
        agent_type=request.agent_type,
        personality=request.personality,
        is_category=request.is_category
    )
    
    print("-- /api/chat --")
    print("agent_type:", request.agent_type)
    print("personality:", request.personality)
    print("is_category:", request.is_category)
    print("reply:", reply)
    print("expression:", expression)
    if guidance_message:
        print("guidance_message:", guidance_message)

    audio_base64 = base64.b64encode(audio_data).decode('ascii') if audio_data else ''
    
    response_data = {
        "message": reply,
        "audio": audio_base64,
        "expression": expression
    }
    
    # 如果有引导决策消息，添加到响应中
    if guidance_message:
        response_data["guidance_message"] = guidance_message
    
    return JSONResponse(content=response_data)

# 这里添加TTS设置的API端点
@app.get("/api/tts_settings")
async def get_tts_settings():
    """获取当前TTS设置
    
    Returns:
        dict: 包含TTS设置的响应
    """
    return JSONResponse(
        content={
            "enable_tts": Config.ENABLE_TTS,
            "enable_super_tts": Config.ENABLE_SUPER_TTS,
            "tts_voice": Config.TTS_VCN,
            "super_tts_voice": Config.SUPER_TTS_VCN,
            "tts_voice_list": Config.TTS_VOICE_LIST,
            "super_tts_voice_list": Config.SUPER_TTS_VOICE_LIST,
            "tts_speed": Config.TTS_SPEED,
            "typing_speed": Config.TYPING_SPEED
        }
    )

@app.post("/api/tts_settings")
async def update_tts_settings(settings: TTSSettingsRequest):
    """更新TTS设置
    
    Args:
        settings: 新的TTS设置
        
    Returns:
        dict: 包含更新结果的响应
    """
    try:
        # 只能启用一种TTS，或者都不启用
        if settings.enable_tts and settings.enable_super_tts:
            return JSONResponse(
                content={
                    "success": False,
                    "message": "只能启用一种TTS服务"
                }
            )
            
        # 更新配置
        Config.ENABLE_TTS = settings.enable_tts
        Config.ENABLE_SUPER_TTS = settings.enable_super_tts
        
        # 更新音色配置
        if settings.tts_voice:
            # 验证音色是否在列表中
            if any(voice["value"] == settings.tts_voice for voice in Config.TTS_VOICE_LIST):
                Config.TTS_VCN = settings.tts_voice
        
        if settings.super_tts_voice:
            # 验证音色是否在列表中
            if any(voice["value"] == settings.super_tts_voice for voice in Config.SUPER_TTS_VOICE_LIST):
                Config.SUPER_TTS_VCN = settings.super_tts_voice
        
        # 更新语速设置
        updated_tts_speed = None
        if settings.tts_speed is not None:
            try:
                # 确保值是整数类型
                speed_value = int(settings.tts_speed)
                # 验证语速值是否在有效范围内
                if 0 <= speed_value <= 100:
                    Config.TTS_SPEED = speed_value
                    updated_tts_speed = speed_value
                else:
                    print(f"语速值超出范围(0-100): {speed_value}")
                    Config.TTS_SPEED = max(0, min(100, speed_value))  # 限制在有效范围内
                    updated_tts_speed = Config.TTS_SPEED
            except (ValueError, TypeError) as e:
                print(f"语速值类型错误: {e}")
                # 如果转换失败，使用默认值
                Config.TTS_SPEED = 50
        
        # 更新打字速度设置
        updated_typing_speed = None
        if settings.typing_speed is not None:
            try:
                # 确保值是整数类型
                typing_value = int(settings.typing_speed)
                # 验证打字速度值是否在有效范围内 (10-200ms)
                if 10 <= typing_value <= 200:
                    Config.TYPING_SPEED = typing_value
                    updated_typing_speed = typing_value
                else:
                    print(f"打字速度值超出范围(10-200): {typing_value}")
                    Config.TYPING_SPEED = max(10, min(200, typing_value))  # 限制在有效范围内
                    updated_typing_speed = Config.TYPING_SPEED
            except (ValueError, TypeError) as e:
                print(f"打字速度值类型错误: {e}")
                # 如果转换失败，使用默认值
                Config.TYPING_SPEED = 38
        
        # 使用刷新服务方法，确保使用最新的音色配置
        chat_service._refresh_tts_services()
            
        print(f"设置已更新: TTS={Config.ENABLE_TTS}, SuperTTS={Config.ENABLE_SUPER_TTS}, 语速={Config.TTS_SPEED}, 打字速度={Config.TYPING_SPEED}")
        
        # 将更新后的设置写入配置文件
        if updated_tts_speed is not None or updated_typing_speed is not None:
            await update_config_file(
                tts_speed=updated_tts_speed,
                typing_speed=updated_typing_speed,
                tts_voice=settings.tts_voice if settings.tts_voice else None,
                super_tts_voice=settings.super_tts_voice if settings.super_tts_voice else None,
                enable_tts=settings.enable_tts,
                enable_super_tts=settings.enable_super_tts
            )
            
        return JSONResponse(
            content={
                "success": True,
                "message": "TTS设置已更新并写入配置文件",
                "enable_tts": Config.ENABLE_TTS,
                "enable_super_tts": Config.ENABLE_SUPER_TTS,
                "tts_voice": Config.TTS_VCN,
                "super_tts_voice": Config.SUPER_TTS_VCN,
                "tts_speed": Config.TTS_SPEED,
                "typing_speed": Config.TYPING_SPEED
            }
        )
    except Exception as e:
        print(f"更新TTS设置失败: {e}")
        return JSONResponse(
            content={
                "success": False,
                "message": f"更新TTS设置失败: {str(e)}"
            }
        )

async def update_config_file(tts_speed=None, typing_speed=None, tts_voice=None, 
                           super_tts_voice=None, enable_tts=None, enable_super_tts=None):
    """更新配置文件中的TTS设置
    
    Args:
        tts_speed: 语速值
        typing_speed: 打字速度值
        tts_voice: TTS音色
        super_tts_voice: 超拟人TTS音色
        enable_tts: 是否启用普通TTS
        enable_super_tts: 是否启用超拟人TTS
    """
    try:
        config_file_path = os.path.join(os.path.dirname(__file__), 'config.py')
        
        # 读取当前配置文件内容
        with open(config_file_path, 'r', encoding='utf-8') as file:
            config_content = file.read()
        
        # 更新配置内容
        if tts_speed is not None:
            # 使用正则表达式替换TTS_SPEED的值
            config_content = re.sub(
                r'TTS_SPEED\s*=\s*\d+',
                f'TTS_SPEED = {tts_speed}',
                config_content
            )
            
        if typing_speed is not None:
            # 使用正则表达式替换TYPING_SPEED的值
            config_content = re.sub(
                r'TYPING_SPEED\s*=\s*\d+',
                f'TYPING_SPEED = {typing_speed}',
                config_content
            )
            
        if tts_voice is not None:
            # 使用正则表达式替换TTS_VCN的值
            config_content = re.sub(
                r'TTS_VCN\s*=\s*"[^"]+"',
                f'TTS_VCN = "{tts_voice}"',
                config_content
            )
            
        if super_tts_voice is not None:
            # 使用正则表达式替换SUPER_TTS_VCN的值
            config_content = re.sub(
                r'SUPER_TTS_VCN\s*=\s*"[^"]+"',
                f'SUPER_TTS_VCN = "{super_tts_voice}"',
                config_content
            )
            
        if enable_tts is not None:
            # 使用正则表达式替换ENABLE_TTS的值
            config_content = re.sub(
                r'ENABLE_TTS\s*=\s*(True|False)',
                f'ENABLE_TTS = {str(enable_tts)}',
                config_content
            )
            
        if enable_super_tts is not None:
            # 使用正则表达式替换ENABLE_SUPER_TTS的值
            config_content = re.sub(
                r'ENABLE_SUPER_TTS\s*=\s*(True|False)',
                f'ENABLE_SUPER_TTS = {str(enable_super_tts)}',
                config_content
            )
        
        # 写入更新后的配置文件
        with open(config_file_path, 'w', encoding='utf-8') as file:
            file.write(config_content)
            
        print(f"配置文件已更新：{config_file_path}")
        
    except Exception as e:
        print(f"更新配置文件失败: {e}")
        raise

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8666, reload=True)