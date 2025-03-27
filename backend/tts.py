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
import threading

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
        # 检查文本是否超长
        max_text_length = Config.TTS_TEXT_LENGTH_LIMIT  # 讯飞TTS单次请求的字符限制
        if len(text) > max_text_length:
            print(f"文本过长({len(text)}字符)，进行分段处理")
            return self._process_long_text(text, max_text_length)
        
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
        
        print(f"超长文本已分割为{len(chunks)}段")
        
        # 处理每个文本块并合并音频
        combined_audio = bytearray()
        failed_chunks = 0
        max_failed_chunks = 3  # 最多允许连续失败的块数
        consecutive_failures = 0
        
        for i, chunk in enumerate(chunks):
            print(f"正在处理第{i+1}/{len(chunks)}段文本，长度: {len(chunk)}字符")
            
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
                    print(f"第{i+1}段文本处理失败")
            except Exception as e:
                consecutive_failures += 1
                failed_chunks += 1
                print(f"处理第{i+1}段文本时出错: {e}")
            
            # 每处理完一个块，添加短暂延迟避免API限流
            if i < len(chunks) - 1:  # 不是最后一块
                time.sleep(0.5)  # 添加0.5秒延迟
            
            # 如果连续失败次数过多，直接返回已处理的内容
            if consecutive_failures >= max_failed_chunks:
                print(f"连续{consecutive_failures}次失败，中止剩余处理")
                break
        
        # 如果全部块都失败了，尝试使用整个文本一次性转换(最后的回退尝试)
        if failed_chunks == len(chunks) and len(chunks) > 1:
            print("所有分块都失败，尝试一次性处理整个文本")
            try:
                # 确保文本长度不超过最大限制的2倍
                if len(text) > max_length * 2:
                    text = text[:max_length * 2]
                
                # 直接处理
                ws_param = self._create_ws_param(text)
                result_data = self._run_tts_websocket(ws_param)
                if result_data:
                    return result_data
            except Exception as e:
                print(f"最后一次尝试也失败: {e}")
        
        # 如果合并的音频为空，但文本非空，尝试简化方式处理
        if len(combined_audio) == 0 and text.strip():
            print("尝试简化模式处理文本")
            try:
                # 取首句或前N个字符
                simple_text = sentences[0] if sentences else text[:min(100, len(text))]
                
                # 直接处理
                ws_param = self._create_ws_param(simple_text)
                result_data = self._run_tts_websocket(ws_param)
                if result_data:
                    return result_data
            except Exception as e:
                print(f"简化模式处理失败: {e}")
        
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
                    print(f"TTS chunk Error on attempt {attempt + 1}: {str(e)}")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    print(f"TTS chunk Error: All {max_retries} attempts failed. Last error: {str(e)}")
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

    def _create_ws_param(self, text: str):
        """
        创建WebSocket连接参数
        
        Args:
            text: 要转换的文本
            
        Returns:
            dict: WebSocket连接参数
        """
        base_url = "wss://tts-api.xfyun.cn/v2/tts"
        
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))
        
        # 拼接字符串
        signature_origin = "host: " + "tts-api.xfyun.cn" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v2/tts " + "HTTP/1.1"
        
        # 进行hmac-sha256加密
        signature_sha = hmac.new(
            self.api_secret.encode('utf-8'),
            signature_origin.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        
        signature_sha_base64 = base64.b64encode(signature_sha).decode()
        authorization_origin = f'api_key="{self.api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode()
        
        # 获取并验证语速参数
        try:
            tts_speed = Config.TTS_SPEED
            # 确保语速在合理范围内
            if not isinstance(tts_speed, int) or tts_speed < 0:
                print(f"语速值无效 ({tts_speed})，使用默认值50")
                tts_speed = 50
            elif tts_speed > 100:
                print(f"语速值超出范围 ({tts_speed})，限制为100")
                tts_speed = 100
        except Exception as e:
            print(f"获取语速时出错: {e}，使用默认值50")
            tts_speed = 50
            
        # 设置请求参数
        v = {
            "common": {
                "app_id": self.app_id
            },
            "business": {
                "aue": Config.TTS_AUE,  # 音频编码
                "auf": Config.TTS_AUF,  # 音频采样率
                "vcn": self.voice,      # 发音人
                "tte": Config.TTS_TTE,  # 文本编码
                "speed": tts_speed,     # 使用验证后的语速
                "volume": Config.TTS_VOLUME,  # 音量
                "pitch": Config.TTS_PITCH,   # 音高
            },
            "data": {
                "text": base64.b64encode(text.encode('utf-8')).decode(),
                "status": 2
            }
        }
        
        # 拼接URL
        url = base_url + '?' + urlencode({
            'host': 'tts-api.xfyun.cn',
            'date': date,
            'authorization': authorization
        })
        
        return {
            'url': url,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps(v)
        }
    
    def _run_tts_websocket(self, ws_param):
        """
        运行WebSocket连接并处理TTS转换
        
        Args:
            ws_param: WebSocket连接参数
            
        Returns:
            bytes: 音频数据
        """
        audio_data = bytearray()
        connection_timeout = 10  # 连接超时时间(秒)
        receive_timeout = 15    # 接收数据超时时间(秒)
        result_ready = False
        websocket_error = None
        
        # 使用事件对象来控制超时
        connection_event = threading.Event()
        completion_event = threading.Event()
        
        def on_message(ws, message):
            nonlocal audio_data, result_ready
            try:
                message = json.loads(message)
                # 提取音频数据并解码
                if message["code"] == 0:
                    data = message["data"]["audio"]
                    audio = base64.b64decode(data)
                    audio_data.extend(audio)
                
                # 处理结束信号
                if message["code"] == 0 and message["data"]["status"] == 2:
                    result_ready = True
                    completion_event.set()  # 标记完成
                    ws.close()
            except Exception as e:
                print(f"处理WebSocket消息时出错: {e}")
                websocket_error = e
                completion_event.set()  # 出错时也标记完成
                ws.close()
                
        def on_error(ws, error):
            nonlocal websocket_error
            print(f"WebSocket错误: {error}")
            websocket_error = error
            completion_event.set()  # 出错时标记完成
            
        def on_close(ws, close_status_code=None, close_reason=None):
            print("WebSocket连接关闭")
            completion_event.set()  # 连接关闭时标记完成
            
        def on_open(ws):
            nonlocal connection_event
            connection_event.set()  # 标记连接已建立
            
            def run():
                try:
                    # 发送JSON格式的请求数据
                    ws.send(ws_param['body'])
                except Exception as e:
                    nonlocal websocket_error
                    print(f"发送WebSocket数据时出错: {e}")
                    websocket_error = e
                    completion_event.set()  # 出错时标记完成
                    ws.close()
            
            thread.start_new_thread(run, ())
        
        # 创建WebSocket对象
        ws = websocket.WebSocketApp(
            ws_param['url'],
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open,
            header=ws_param['headers']
        )
        
        # 在单独的线程中运行WebSocket连接
        ws_thread = threading.Thread(
            target=ws.run_forever,
            kwargs={"sslopt": {"cert_reqs": ssl.CERT_NONE}}
        )
        ws_thread.daemon = True  # 设置为后台线程
        ws_thread.start()
        
        # 等待连接建立，带超时
        if not connection_event.wait(connection_timeout):
            print(f"WebSocket连接超时(等待{connection_timeout}秒)")
            ws.close()
            return b""
            
        # 等待接收完成，带超时
        if not completion_event.wait(receive_timeout):
            print(f"WebSocket接收数据超时(等待{receive_timeout}秒)")
            ws.close()
            return b""
            
        # 检查是否有错误
        if websocket_error:
            print(f"WebSocket发生错误: {websocket_error}")
            return b""
            
        # 检查是否有有效数据
        if len(audio_data) == 0:
            print("未收到有效音频数据")
            return b""
        
        # 等待线程结束，但有超时限制
        ws_thread.join(2)
        if ws_thread.is_alive():
            print("WebSocket线程未能正常结束，强制继续")
        
        return bytes(audio_data) 