import asyncio
import websockets
import json
from config import Config

class SpeechService:
    def __init__(self):
        self.ws_url = "wss://iat-api.xfyun.cn/v2/iat"
        self.app_id = Config.XFYUN_APP_ID
        self.api_key = Config.XFYUN_API_KEY
        self.api_secret = Config.XFYUN_API_SECRET
        
    async def process_audio(self, audio_data: bytes) -> str:
        """处理音频数据并返回识别结果
        
        Args:
            audio_data: 音频数据
            
        Returns:
            str: 识别结果文本
        """
        try:
            # 连接科大讯飞WebSocket
            async with websockets.connect(self.ws_url) as websocket:
                # 发送鉴权信息
                auth_params = self._get_auth_params()
                await websocket.send(json.dumps(auth_params))
                
                # 发送音频数据
                await websocket.send(audio_data)
                
                # 接收识别结果
                result_text = ""
                while True:
                    response = await websocket.recv()
                    data = json.loads(response)
                    
                    # 提取识别文本
                    if data.get("data") and data["data"].get("result"):
                        result = data["data"]["result"]
                        if "ws" in result:
                            text = "".join(
                                word["cw"][0]["w"]
                                for word in result["ws"]
                                if word.get("cw")
                            )
                            result_text += text
                    
                    # 检查是否识别完成
                    if data.get("code") != 0:
                        break
                        
                return result_text.strip()
                
        except Exception as e:
            print(f"语音识别出错: {e}")
            return ""
            
    def _get_auth_params(self) -> dict:
        """生成鉴权参数"""
        return {
            "common": {
                "app_id": self.app_id,
            },
            "business": {
                "language": "zh_cn",
                "domain": "iat",
                "accent": "mandarin",
                "vad_eos": 3000,
            },
            "data": {
                "status": 0,
                "format": "audio/wav",
                "encoding": "raw",
            }
        } 