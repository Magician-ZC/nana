import websocket
import datetime
import hashlib
import base64
import hmac
import json
from urllib.parse import urlencode
import time
import ssl
from datetime import datetime
from time import mktime
import _thread as thread
from wsgiref.handlers import format_date_time
from config import Config

class SuperTTSService:
    def __init__(self):
        self.app_id = Config.XFYUN_APP_ID
        self.api_key = Config.XFYUN_API_KEY
        self.api_secret = Config.XFYUN_API_SECRET
        self.url = Config.SUPER_TTS_URL
    
    def generate_audio(self, text: str) -> bytes:
        """
        使用科大讯飞超拟人语音合成API将文本转换为语音
        
        Args:
            text: 要转换的文本
            
        Returns:
            bytes: 音频数据
        """
        if not text:
            return b""
            
        # 检查文本长度
        if len(text.encode('utf-8')) > Config.TTS_TEXT_LENGTH_LIMIT * 3:  # 粗略估计：一个汉字约3字节
            print(f"文本过长，截断处理: {len(text)} > {Config.TTS_TEXT_LENGTH_LIMIT}")
            text = text[:Config.TTS_TEXT_LENGTH_LIMIT]  # 简单截断处理
            
        # 最大重试次数
        max_retries = 3
        retry_delay = 1  # 初始延迟1秒
        
        for attempt in range(max_retries):
            try:
                # 构建请求参数
                ws_url = self._get_ws_url()
                
                # 执行WebSocket请求获取音频数据
                audio_data = self._run_ws_request(ws_url, text)
                if audio_data:
                    return audio_data
                
                # 如果没有获取到音频数据，则抛出异常重试
                raise Exception("未收到有效的音频数据")
                
            except Exception as e:
                if attempt < max_retries - 1:  # 如果不是最后一次尝试
                    print(f"超拟人TTS错误 (尝试 {attempt + 1}): {str(e)}")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避策略
                else:
                    print(f"超拟人TTS错误: {max_retries}次尝试都失败。最后错误: {str(e)}")
                    return b""  # 返回空音频数据
                    
    def _get_ws_url(self):
        """构建带鉴权的WebSocket URL"""
        return self._assemble_ws_auth_url(self.url, "GET", self.api_key, self.api_secret)
        
    def _assemble_ws_auth_url(self, request_url, method="GET", api_key="", api_secret=""):
        """组装鉴权后的URL"""
        # 解析URL获取主机和路径
        host, path, schema = self._parse_url(request_url)
        
        # 生成时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))
        
        # 构建签名原始字符串
        signature_origin = f"host: {host}\ndate: {date}\n{method} {path} HTTP/1.1"
        
        # 使用HMAC-SHA256算法对签名字符串进行加密
        signature_sha = hmac.new(api_secret.encode('utf-8'), signature_origin.encode('utf-8'),
                                digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')
        
        # 构建Authorization字符串
        authorization_origin = f'api_key="{api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha}"'
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        
        # 构建鉴权参数
        values = {
            "host": host,
            "date": date,
            "authorization": authorization
        }
        
        # 返回带鉴权参数的URL
        return request_url + "?" + urlencode(values)
    
    def _parse_url(self, request_url):
        """解析URL获取schema、host和path"""
        # 找到协议分隔符位置
        schema_end = request_url.index("://")
        schema = request_url[:schema_end + 3]
        
        # 解析主机和路径
        host = request_url[schema_end + 3:]
        if "/" in host:
            path_start = host.index("/")
            path = host[path_start:]
            host = host[:path_start]
        else:
            path = "/"
            
        return host, path, schema
        
    def _run_ws_request(self, ws_url, text):
        """执行WebSocket请求获取音频数据"""
        audio_data = bytearray()
        websocket_connected = False
        websocket_error = None
        
        def on_message(ws, message):
            nonlocal audio_data
            try:
                # 解析JSON响应
                message = json.loads(message)
                
                # 检查是否有错误码
                if "header" in message and message["header"].get("code") != 0:
                    print(f"超拟人TTS错误: {message}")
                    return
                
                # 提取音频数据
                if "payload" in message and "audio" in message["payload"]:
                    audio = message["payload"]["audio"]["audio"]
                    audio_bytes = base64.b64decode(audio)
                    audio_data.extend(audio_bytes)
                    
                    # 检查是否是最后一帧数据
                    status = message["payload"]["audio"]["status"]
                    if status == 2:
                        print("超拟人TTS合成完成，关闭连接")
                        ws.close()
                
            except Exception as e:
                print(f"处理超拟人TTS响应时出错: {e}")
                
        def on_error(ws, error):
            nonlocal websocket_error
            websocket_error = error
            print(f"超拟人TTS WebSocket错误: {error}")
            
        def on_close(ws, close_status_code=None, close_msg=None):
            print("超拟人TTS WebSocket连接已关闭")
            
        def on_open(ws):
            nonlocal websocket_connected
            websocket_connected = True
            
            def run(*args):
                # 构建请求数据
                request_data = {
                    "header": {
                        "app_id": self.app_id,
                        "status": 2  # 一次性发送所有文本
                    },
                    "parameter": {
                        "oral": {
                            "oral_level": Config.SUPER_TTS_ORAL_LEVEL,
                            "spark_assist": Config.SUPER_TTS_SPARK_ASSIST,
                            "stop_split": Config.SUPER_TTS_STOP_SPLIT,
                            "remain": Config.SUPER_TTS_REMAIN
                        },
                        "tts": {
                            "vcn": Config.SUPER_TTS_VCN,
                            "speed": Config.TTS_SPEED,
                            "volume": Config.TTS_VOLUME,
                            "pitch": Config.TTS_PITCH,
                            "bgs": 0,
                            "reg": 0,
                            "rdn": 0,
                            "rhy": 0,
                            "audio": {
                                "encoding": "lame",  # mp3格式
                                "sample_rate": 24000,
                                "channels": 1,
                                "bit_depth": 16,
                                "frame_size": 0
                            }
                        }
                    },
                    "payload": {
                        "text": {
                            "encoding": "utf8",
                            "compress": "raw",
                            "format": "plain",
                            "status": 2,
                            "seq": 0,
                            "text": str(base64.b64encode(text.encode('utf-8')), "UTF8")
                        }
                    }
                }
                
                # 发送请求数据
                print("开始发送超拟人TTS请求...")
                ws.send(json.dumps(request_data))
                
            thread.start_new_thread(run, ())
            
        # 创建WebSocket连接
        websocket.enableTrace(False)
        print(f"连接超拟人TTS WebSocket URL: {ws_url}")
        
        ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        ws.on_open = on_open
        
        # 启动WebSocket连接
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
        
        # 检查连接结果
        if not websocket_connected:
            print("WebSocket连接失败")
            return None
            
        if websocket_error:
            print(f"WebSocket发生错误: {websocket_error}")
            return None
            
        if len(audio_data) == 0:
            print("未收到音频数据")
            return None
            
        # 返回音频数据
        return bytes(audio_data) 