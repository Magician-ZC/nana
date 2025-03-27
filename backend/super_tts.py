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
    def __init__(self, voice=None):
        self.app_id = Config.XFYUN_APP_ID
        self.api_key = Config.XFYUN_API_KEY
        self.api_secret = Config.XFYUN_API_SECRET
        self.url = Config.SUPER_TTS_URL
        self.voice = voice or Config.SUPER_TTS_VCN  # 如果没有提供音色，使用默认配置
    
    def generate_audio(self, text: str) -> bytes:
        """
        使用超拟人音色API将文本转换为语音
        
        Args:
            text: 要转换的文本
            
        Returns:
            bytes: 音频数据
        """
        # 检查文本是否超长
        max_text_length = Config.SUPER_TTS_TEXT_LENGTH_LIMIT or 150  # 默认150字符限制
        if len(text) > max_text_length:
            print(f"超拟人TTS文本过长({len(text)}字符)，进行分段处理")
            return self._process_long_text(text, max_text_length)
        
        max_retries = 3
        retry_delay = 1  # 初始延迟1秒
        
        for attempt in range(max_retries):
            try:
                # 创建API调用所需的参数
                audio_data = self._call_super_tts_api(text)
                if audio_data:
                    return audio_data
                
                raise Exception("未收到有效的音频数据")
            except Exception as e:
                if attempt < max_retries - 1:  # 如果不是最后一次尝试
                    print(f"Super TTS Error on attempt {attempt + 1}: {str(e)}")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避，每次失败后等待时间翻倍
                else:
                    print(f"Super TTS Error: All {max_retries} attempts failed. Last error: {str(e)}")
                    return b""  # 所有重试都失败后返回空音频数据

    def _process_long_text(self, text: str, max_length: int) -> bytes:
        """
        处理超长文本，分段转换为语音并合并
        
        Args:
            text: 要转换的长文本
            max_length: 单次转换的最大字符数
            
        Returns:
            bytes: 合并后的音频数据
        """
        # 按句子分割长文本
        sentences = self._split_into_sentences(text)
        
        # 将句子组合成适当长度的段落
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # 如果单个句子已经超过限制，需要进一步分割
            if len(sentence) > max_length:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                
                # 分割长句子
                start = 0
                while start < len(sentence):
                    end = min(start + max_length, len(sentence))
                    chunks.append(sentence[start:end])
                    start = end
            
            # 正常处理句子
            elif len(current_chunk) + len(sentence) <= max_length:
                current_chunk += sentence
            else:
                chunks.append(current_chunk)
                current_chunk = sentence
        
        # 添加最后一个块
        if current_chunk:
            chunks.append(current_chunk)
        
        print(f"超拟人TTS: 超长文本已分割为{len(chunks)}段")
        
        # 处理每个文本块并合并音频
        combined_audio = bytearray()
        failed_chunks = 0
        max_failed_chunks = 3  # 最多允许连续失败的块数
        consecutive_failures = 0
        
        for i, chunk in enumerate(chunks):
            print(f"超拟人TTS: 正在处理第{i+1}/{len(chunks)}段文本，长度: {len(chunk)}字符")
            
            if not chunk.strip():  # 跳过空白段落
                continue
            
            # 为每段文本生成音频
            try:
                # 如果前面的请求连续失败，添加更长的延迟
                if consecutive_failures > 0:
                    delay_time = min(consecutive_failures * 2, 10)  # 最多等待10秒
                    print(f"因连续失败{consecutive_failures}次，等待{delay_time}秒后继续")
                    time.sleep(delay_time)
                
                audio_data = self._generate_audio_for_chunk(chunk)
                if audio_data:
                    combined_audio.extend(audio_data)
                    consecutive_failures = 0  # 重置连续失败计数
                else:
                    consecutive_failures += 1
                    failed_chunks += 1
                    print(f"超拟人TTS: 第{i+1}段文本处理失败")
            except Exception as e:
                consecutive_failures += 1
                failed_chunks += 1
                print(f"超拟人TTS: 处理第{i+1}段文本时出错: {e}")
            
            # 每处理完一个块，添加短暂延迟避免API限流
            if i < len(chunks) - 1:  # 不是最后一块
                time.sleep(0.5)  # 添加0.5秒延迟
            
            # 如果连续失败次数过多，直接返回已处理的内容
            if consecutive_failures >= max_failed_chunks:
                print(f"超拟人TTS: 连续{consecutive_failures}次失败，中止剩余处理")
                break
        
        # 如果全部块都失败了，尝试使用整个文本一次性转换(最后的回退尝试)
        if failed_chunks == len(chunks) and len(chunks) > 1:
            print("超拟人TTS: 所有分块都失败，尝试一次性处理整个文本")
            try:
                # 确保文本长度不超过最大限制的1.5倍
                if len(text) > max_length * 1.5:
                    text = text[:int(max_length * 1.5)]
                
                # 直接处理
                result_data = self._call_super_tts_api(text)
                if result_data:
                    return result_data
            except Exception as e:
                print(f"超拟人TTS: 最后一次尝试也失败: {e}")
        
        # 如果合并的音频为空，但文本非空，尝试简化方式处理
        if len(combined_audio) == 0 and text.strip():
            print("超拟人TTS: 尝试简化模式处理文本")
            try:
                # 取首句或前N个字符
                simple_text = sentences[0] if sentences else text[:min(80, len(text))]
                
                # 直接处理
                result_data = self._call_super_tts_api(simple_text)
                if result_data:
                    return result_data
            except Exception as e:
                print(f"超拟人TTS: 简化模式处理失败: {e}")
        
        return bytes(combined_audio)

    def _generate_audio_for_chunk(self, text: str) -> bytes:
        """为单个文本块生成音频
        
        Args:
            text: 文本块
            
        Returns:
            bytes: 音频数据
        """
        max_retries = 2
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                # 调用API生成音频
                result_data = self._call_super_tts_api(text)
                if result_data:
                    return result_data
                
                # 如果没有成功获取数据，进入重试
                raise Exception("未收到有效的音频数据")
                
            except Exception as e:
                if attempt < max_retries - 1:  # 如果不是最后一次尝试
                    print(f"Super TTS chunk Error on attempt {attempt + 1}: {str(e)}")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    print(f"Super TTS chunk Error: All {max_retries} attempts failed. Last error: {str(e)}")
                    return b""

    def _split_into_sentences(self, text: str) -> list:
        """将文本分割成句子
        
        Args:
            text: 要分割的文本
            
        Returns:
            list: 句子列表
        """
        # 中文句子分割符
        separators = ["。", "！", "？", "；", "…", "\n"]
        sentences = []
        current_sentence = ""
        
        for char in text:
            current_sentence += char
            
            if char in separators:
                sentences.append(current_sentence)
                current_sentence = ""
        
        # 添加最后一个句子（如果有）
        if current_sentence:
            sentences.append(current_sentence)
        
        return sentences

    def _call_super_tts_api(self, text: str) -> bytes:
        """调用超拟人TTS API

        Args:
            text: 文本内容

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
        connection_timeout = 10  # 连接超时时间(秒)
        receive_timeout = 20    # 接收数据超时时间(秒)
        result_ready = False
        
        import threading
        
        # 使用事件对象来控制超时
        connection_event = threading.Event()
        completion_event = threading.Event()
        
        def on_message(ws, message):
            nonlocal audio_data, result_ready
            try:
                # 解析JSON响应
                message = json.loads(message)
                
                # 检查是否有错误码
                if "header" in message and message["header"].get("code") != 0:
                    print(f"超拟人TTS错误: {message}")
                    nonlocal websocket_error
                    websocket_error = f"超拟人TTS API返回错误: {message['header'].get('message', '未知错误')}"
                    completion_event.set()  # 出错时标记完成
                    ws.close()
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
                        result_ready = True
                        completion_event.set()  # 标记完成
                        ws.close()
                
            except Exception as e:
                print(f"处理超拟人TTS响应时出错: {e}")
                websocket_error = e
                completion_event.set()  # 出错时标记完成
                ws.close()
                
        def on_error(ws, error):
            nonlocal websocket_error
            websocket_error = error
            print(f"超拟人TTS WebSocket错误: {error}")
            completion_event.set()  # 出错时标记完成
            
        def on_close(ws, close_status_code=None, close_msg=None):
            print("超拟人TTS WebSocket连接已关闭")
            completion_event.set()  # 连接关闭时标记完成
            
        def on_open(ws):
            nonlocal websocket_connected
            websocket_connected = True
            connection_event.set()  # 标记连接已建立
            
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
                            "vcn": self.voice,  # 使用实例的音色设置
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
                
                try:
                    # 发送请求数据
                    print("开始发送超拟人TTS请求...")
                    ws.send(json.dumps(request_data))
                except Exception as e:
                    nonlocal websocket_error
                    print(f"发送超拟人TTS请求时出错: {e}")
                    websocket_error = e
                    completion_event.set()  # 出错时标记完成
                    ws.close()
                
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
        
        # 在单独的线程中运行WebSocket连接
        import threading
        ws_thread = threading.Thread(
            target=ws.run_forever,
            kwargs={"sslopt": {"cert_reqs": ssl.CERT_NONE}}
        )
        ws_thread.daemon = True  # 设置为后台线程
        ws_thread.start()
        
        # 等待连接建立，带超时
        if not connection_event.wait(connection_timeout):
            print(f"超拟人TTS WebSocket连接超时(等待{connection_timeout}秒)")
            ws.close()
            return None
            
        # 等待接收完成，带超时
        if not completion_event.wait(receive_timeout):
            print(f"超拟人TTS接收数据超时(等待{receive_timeout}秒)")
            ws.close()
            return None
            
        # 检查连接结果
        if not websocket_connected:
            print("超拟人TTS WebSocket连接失败")
            return None
            
        if websocket_error:
            print(f"超拟人TTS WebSocket发生错误: {websocket_error}")
            return None
            
        if len(audio_data) == 0:
            print("超拟人TTS未收到音频数据")
            return None
            
        # 等待线程结束，但有超时限制
        ws_thread.join(2)
        if ws_thread.is_alive():
            print("超拟人TTS WebSocket线程未能正常结束，强制继续")
            
        # 返回音频数据
        return bytes(audio_data) 