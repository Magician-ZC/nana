import base64
import hashlib
import hmac
import json
import time
import websocket
from datetime import datetime
from time import mktime
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time
import _thread as thread
import ssl
from typing import Optional
from config import Config

class TTSService:
    def __init__(self, voice=None):
        self.app_id = Config.XFYUN_APP_ID
        self.api_key = Config.XFYUN_API_KEY
        self.api_secret = Config.XFYUN_API_SECRET
        self.voice = voice or Config.TTS_VCN  # 如果没有提供音色，使用默认配置
    
    def generate_audio(self, text: str) -> bytes:
        """
        使用讯飞API将文本转换为语音
        
        Args:
            text: 要转换的文本
            
        Returns:
            bytes: 音频数据
        """
        # 检查文本长度是否超出限制
        if len(text.encode('utf-8')) > Config.TTS_TEXT_LENGTH_LIMIT * 3:  # 粗略估计：一个汉字约3字节
            print(f"文本过长，截断处理: {len(text)} > {Config.TTS_TEXT_LENGTH_LIMIT}")
            text = text[:Config.TTS_TEXT_LENGTH_LIMIT]  # 简单截断处理
        
        max_retries = 3
        retry_delay = 1  # 初始延迟1秒
        
        for attempt in range(max_retries):
            try:
                # 创建WebSocket参数
                ws_param = self._create_ws_param(text)
                
                # 启用WebSocket连接
                result_data = self._run_tts_websocket(ws_param)
                if result_data:
                    return result_data
                    
                # 如果没有成功获取数据，进入重试
                raise Exception("未收到有效的音频数据")
                
            except Exception as e:
                if attempt < max_retries - 1:  # 如果不是最后一次尝试
                    print(f"TTS Error on attempt {attempt + 1}: {str(e)}")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避，每次失败后等待时间翻倍
                else:
                    print(f"TTS Error: All {max_retries} attempts failed. Last error: {str(e)}")
                    return b""  # 所有重试都失败后返回空音频数据
    
    def _create_ws_param(self, text):
        """创建WebSocket参数对象"""
        class WsParam:
            def __init__(self, app_id, api_key, api_secret, text, voice):
                self.APPID = app_id
                self.APIKey = api_key
                self.APISecret = api_secret
                self.Text = text
                
                # 公共参数(common)
                self.CommonArgs = {"app_id": self.APPID}
                # 业务参数(business)，从Config读取配置
                self.BusinessArgs = {
                    "aue": Config.TTS_AUE,  # 音频编码
                    "auf": Config.TTS_AUF,  # 音频采样率
                    "vcn": voice,  # 使用传入的音色
                    "tte": Config.TTS_TTE,  # 文本编码
                    "speed": Config.TTS_SPEED,  # 语速
                    "volume": Config.TTS_VOLUME,  # 音量
                    "pitch": Config.TTS_PITCH,  # 音高
                }
                self.Data = {"status": 2, "text": str(base64.b64encode(self.Text.encode('utf-8')), "UTF8")}
            
            def create_url(self):
                url = 'wss://tts-api.xfyun.cn/v2/tts'
                # 生成RFC1123格式的时间戳
                now = datetime.now()
                date = format_date_time(mktime(now.timetuple()))
                
                # 拼接字符串
                signature_origin = "host: " + "tts-api.xfyun.cn" + "\n"
                signature_origin += "date: " + date + "\n"
                signature_origin += "GET " + "/v2/tts " + "HTTP/1.1"
                # 进行hmac-sha256进行加密
                signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                                        digestmod=hashlib.sha256).digest()
                signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')
                
                authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
                    self.APIKey, "hmac-sha256", "host date request-line", signature_sha)
                authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
                # 将请求的鉴权参数组合为字典
                v = {
                    "authorization": authorization,
                    "date": date,
                    "host": "tts-api.xfyun.cn"
                }
                # 拼接鉴权参数，生成url
                url = url + '?' + urlencode(v)
                return url
                
        return WsParam(self.app_id, self.api_key, self.api_secret, text, self.voice)
    
    def _run_tts_websocket(self, ws_param):
        """运行TTS WebSocket连接并获取结果"""
        audio_data = bytearray()
        websocket_connected = False
        
        def on_message(ws, message):
            nonlocal audio_data
            try:
                message = json.loads(message)
                code = message["code"]
                if code != 0:
                    print(f"讯飞TTS错误: {message}")
                    return
                
                audio = message["data"]["audio"]
                audio_bytes = base64.b64decode(audio)
                audio_data.extend(audio_bytes)
                
                # 如果是最后一帧，关闭WebSocket连接
                if message["data"]["status"] == 2:
                    print("TTS合成完成，关闭连接")
                    ws.close()
            except Exception as e:
                print(f"处理消息时出错: {e}")
        
        def on_error(ws, error):
            print(f"WebSocket错误: {error}")
        
        def on_close(ws, close_status_code=None, close_msg=None):
            print("WebSocket连接已关闭")
        
        def on_open(ws):
            nonlocal websocket_connected
            websocket_connected = True
            def run(*args):
                d = {
                    "common": ws_param.CommonArgs,
                    "business": ws_param.BusinessArgs,
                    "data": ws_param.Data,
                }
                print("开始发送TTS请求...")
                ws.send(json.dumps(d))
            thread.start_new_thread(run, ())
        
        # 创建WebSocket连接
        websocket.enableTrace(False)
        ws_url = ws_param.create_url()
        
        print(f"连接TTS WebSocket URL: {ws_url}")
        
        ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        ws.on_open = on_open
        
        # 运行WebSocket
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
        
        if not websocket_connected:
            print("WebSocket连接失败")
            return None
            
        if len(audio_data) == 0:
            print("未收到音频数据")
            return None
            
        return bytes(audio_data) 