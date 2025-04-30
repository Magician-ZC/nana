import asyncio
import websockets
import json
import logging
import ssl
from typing import Optional, Dict, Any

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SensevoiceService")

class StreamingSensevoiceService:
    """基于streaming-sensevoice的语音识别服务"""
    
    def __init__(self, ws_url: str = "wss://192.168.3.60:8000/api/realtime/ws", fallback_urls: list = None):
        """初始化服务
        
        Args:
            ws_url: 首选WebSocket服务器URL
            fallback_urls: 备选WebSocket服务器URL列表
        """
        self.ws_url = ws_url
        self.fallback_urls = fallback_urls or []
        self.connected = False
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        
    async def connect(self) -> bool:
        """连接到WebSocket服务器，如果主URL失败，尝试备选URL
        
        Returns:
            bool: 连接是否成功
        """
        # First try the primary URL
        if await self._try_connect(self.ws_url):
            return True
            
        # If it fails, try fallback URLs
        for url in self.fallback_urls:
            logger.info(f"尝试连接到备选服务器: {url}")
            if await self._try_connect(url):
                # Update the main URL to the successful one
                self.ws_url = url
                return True
                
        return False
        
    async def _try_connect(self, url: str) -> bool:
        """尝试连接到指定URL
        
        Args:
            url: WebSocket服务器URL
        
        Returns:
            bool: 连接是否成功
        """
        try:
            # 创建SSL上下文以处理自签名证书
            if url.startswith('wss'):
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            else:
                ssl_context = None
                
            # 连接到WebSocket服务器
            logger.info(f"尝试连接到WebSocket服务器: {url}")
            
            # Add more detailed exception handling and connection options
            try:
            self.ws = await websockets.connect(
                    url,
                ssl=ssl_context,
                    ping_interval=20,  # 增加心跳包频率
                    ping_timeout=10,   # 减少ping超时时间
                    close_timeout=5,   # 关闭超时时间
                    max_size=None,     # 不限制消息大小
                    compression=None   # 禁用压缩以简化处理
            )
            self.connected = True
                logger.info(f"已成功连接到语音识别服务器: {url}")
            return True
            except (websockets.exceptions.InvalidStatusCode, 
                    websockets.exceptions.InvalidHandshake) as e:
                logger.error(f"WebSocket握手失败: {e}")
                self.connected = False
                return False
            except (websockets.exceptions.ConnectionClosed, 
                    websockets.exceptions.ConnectionClosedError) as e:
                logger.error(f"WebSocket连接关闭: {e}")
                self.connected = False
                return False
        except Exception as e:
            logger.error(f"连接到语音识别服务器失败: {e}")
            self.connected = False
            return False
            
    async def disconnect(self) -> None:
        """断开与WebSocket服务器的连接"""
        if self.ws:
            try:
            await self.ws.close()
            logger.info("已断开与语音识别服务器的连接")
            except Exception as e:
                logger.error(f"断开WebSocket连接时出错: {e}")
        self.connected = False
        
    async def process_audio(self, audio_data: bytes) -> str:
        """处理音频数据并返回识别结果
        
        Args:
            audio_data: 音频数据（MP3或WAV格式）
            
        Returns:
            str: 识别结果文本
        """
        if not self.connected or not self.ws:
            logger.info("WebSocket未连接，尝试连接...")
            if not await self.connect():
                logger.error("无法连接到语音识别服务器")
                return ""
                
        try:
            # 发送音频数据
            await self.ws.send(audio_data)
            logger.info(f"已发送音频数据，大小: {len(audio_data)} 字节")
            
            # 接收识别结果
            result_text = ""
            final_results = []
            
            # 接收所有响应
            while True:
                try:
                    # 设置超时时间，避免无限等待
                    response = await asyncio.wait_for(self.ws.recv(), timeout=5.0)
                    
                    # 如果是文本消息，解析JSON
                    if isinstance(response, str):
                        try:
                            data = json.loads(response)
                            logger.debug(f"收到响应: {data}")
                            
                            if data.get("type") == "TranscriptionResponse":
                                # 获取转录结果文本
                                raw_text = data.get("data", {}).get("raw_text", "")
                                is_final = data.get("is_final", False)
                                
                                logger.info(f"识别文本: {raw_text}, 是否最终: {is_final}")
                                
                                # 如果是最终结果，添加到最终结果列表
                                if is_final and raw_text:
                                    final_results.append(raw_text)
                                    
                                # 记录当前结果文本
                                result_text = raw_text
                                
                            elif data.get("type") == "end":
                                # 结束消息，可以结束循环
                                logger.info("收到结束消息")
                                break
                        except json.JSONDecodeError:
                            logger.warning(f"收到非JSON格式的文本消息: {response}")
                    
                except asyncio.TimeoutError:
                    logger.warning("等待语音识别结果超时")
                    break
                    
            # 使用最终结果，如果没有则使用最后一次的结果文本
            final_text = " ".join(final_results) if final_results else result_text
            logger.info(f"语音识别最终结果: {final_text}")
            
            return final_text
            
        except Exception as e:
            logger.error(f"处理音频数据失败: {e}")
            # 如果连接断开，尝试重新连接
            self.connected = False
            return ""
            
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.disconnect() 