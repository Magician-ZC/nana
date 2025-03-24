from fastapi import FastAPI, WebSocket, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import base64
from chat_service import ChatService
from tts import TTSService
from config import Config
from speech_service import SpeechService
import uvicorn
import json
import asyncio

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

class AgentRequest(BaseModel):
    agent_name: str
    session_id: Optional[str] = "default"

chat_service = ChatService()
tts_service = TTSService(Config.FISH_API_KEY, Config.FISH_REFERENCE_ID)
speech_service = SpeechService()

@app.post("/api/chat")
async def chat(request: ChatRequest):
    return await normal_chat_flow(request)

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
    reply, audio_data, expression = await chat_service.generate_reply(
        request.message, 
        request.session_id,
        agent_type=request.agent_type,
        personality=request.personality
    )
    
    print("-- /api/chat --")
    print("agent_type:", request.agent_type)
    print("personality:", request.personality)
    print("reply:", reply)
    print("expression:", expression)

    audio_base64 = base64.b64encode(audio_data).decode('ascii') if audio_data else ''
    
    return JSONResponse(
        content={
            "message": reply,
            "audio": audio_base64,
            "expression": expression
        }
    )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)