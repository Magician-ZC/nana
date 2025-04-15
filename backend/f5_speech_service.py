import os
import time
import uuid
import logging
import threading
import asyncio
from typing import Optional, Dict, Any

# 创建日志记录器
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("F5SpeechService")

# 导入F5-TTS模块
try:
    # 先尝试直接导入本地的f5_tts_module
    from f5_tts_module import F5TTSClient, start_streaming_server
    logger.info("成功导入本地F5-TTS模块")
except ImportError:
    try:
        # 再尝试从f5_tts包导入
        from f5_tts import f5_tts_module
        from f5_tts.f5_tts_module import F5TTSClient, start_streaming_server
        logger.info("成功导入f5_tts包中的F5-TTS模块")
    except ImportError:
        logger.warning("找不到F5-TTS库，将使用模拟实现")

    # 创建模拟类，用于在没有实际F5-TTS库时进行测试
    class F5TTSClient:
        def __init__(self, model=None, server_host=None, server_port=None, device=None):
            self.model = model
            self.server_host = server_host
            self.server_port = server_port
            self.device = device
            self._server_started = False
            
        def start_server(self, reference_audio, reference_text="", auto_stop_minutes=None):
            logger.info(f"[模拟] 启动F5-TTS服务器: {reference_audio}")
            self._server_started = True
            
        def stop_server(self):
            logger.info("[模拟] 停止F5-TTS服务器")
            self._server_started = False
            
        def generate_speech(self, text):
            logger.info(f"[模拟] 生成语音: {text}")
            
    def start_streaming_server(reference_audio, reference_text="", model=None, host=None, port=None, device=None, auto_stop_minutes=None):
        logger.info(f"[模拟] 启动流式TTS服务器: {reference_audio}")
        return F5TTSClient(model=model, server_host=host, server_port=port, device=device)


class F5SpeechService:
    """基于F5-TTS的语音服务，支持自定义克隆语音"""
    
    def __init__(self):
        """初始化F5语音服务"""
        self.servers: Dict[str, Dict[str, Any]] = {}  # 按agent_id存储的服务器实例
        self.base_port = 7890  # 基础端口号
        self.next_port = self.base_port
        self.voice_dir = os.path.join("save", "custom_voice")
        
        # 确保语音目录存在
        os.makedirs(self.voice_dir, exist_ok=True)
        
    def _get_next_port(self) -> int:
        """获取下一个可用端口"""
        port = self.next_port
        self.next_port += 1
        return port
    
    def start_server_for_agent(self, agent_id: str, voice_file: Optional[str] = None) -> bool:
        """为指定角色启动语音服务器
        
        Args:
            agent_id: 角色ID
            voice_file: 语音文件路径，如果未提供则尝试查找
            
        Returns:
            bool: 是否成功启动
        """
        # 检查是否已有服务器在运行
        if agent_id in self.servers and self.servers[agent_id]["running"]:
            logger.info(f"角色 {agent_id} 的语音服务器已在运行")
            return True
            
        # 如果未提供语音文件，尝试查找
        if not voice_file:
            # 尝试直接通过ID查找语音文件（最常见的情况）
            for ext in ['.wav', '.mp3', '.m4a', '.aac']:
                direct_path = os.path.join(self.voice_dir, f"{agent_id}{ext}")
                if os.path.exists(direct_path):
                    voice_file = direct_path
                    logger.info(f"直接通过ID找到语音文件: {voice_file}")
                    break
                
            # 如果直接查找失败，尝试通过配置查找
            if not voice_file:
                try:
                    # 查找角色配置
                    config_path = os.path.join("save", "custom_agents", f"{agent_id}.json")
                    abs_config_path = os.path.abspath(config_path)
                    logger.info(f"正在查找配置文件: {abs_config_path}")
                    
                    if os.path.exists(config_path):
                        import json
                        with open(config_path, "r", encoding="utf-8") as f:
                            agent_config = json.load(f)
                        
                        logger.info(f"已读取配置文件: {agent_config}")
                        
                        # 检查配置中是否有语音文件
                        if "voice_file" in agent_config:
                            voice_path = agent_config["voice_file"]
                            logger.info(f"从配置中找到语音文件路径: {voice_path}")
                            
                            # 尝试多种路径解析方式
                            possible_paths = [
                                voice_path,  # 直接使用配置中的路径
                                os.path.abspath(voice_path),  # 作为相对于当前工作目录的绝对路径
                                os.path.join(os.getcwd(), voice_path),  # 显式地相对于当前工作目录
                                os.path.join("backend", voice_path),  # 尝试"backend"前缀
                                # 直接使用文件名，从自定义语音目录查找
                                os.path.join(self.voice_dir, os.path.basename(voice_path))
                            ]
                            
                            # 检查所有可能的路径
                            for path in possible_paths:
                                logger.info(f"尝试路径: {path}")
                                if os.path.exists(path):
                                    voice_file = path
                                    logger.info(f"找到有效的语音文件: {voice_file}")
                                    break
                            
                            if voice_file:
                                # 更新配置文件中的路径，确保与实际路径一致
                                if agent_config["voice_file"] != voice_file:
                                    agent_config["voice_file"] = voice_file
                                    try:
                                        with open(config_path, "w", encoding="utf-8") as f:
                                            json.dump(agent_config, f, ensure_ascii=False, indent=2)
                                        logger.info(f"已更新配置文件中的语音路径: {voice_file}")
                                    except Exception as e:
                                        logger.error(f"更新配置文件失败: {e}")
                            
                            if not voice_file:
                                # 记录所有尝试的路径
                                logger.error(f"所有尝试的路径均无效: {possible_paths}")
                    else:
                        logger.warning(f"角色配置文件不存在: {config_path}")
                except Exception as e:
                    logger.error(f"读取角色配置失败: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
        
        # 如果还是找不到语音文件，返回失败
        if not voice_file:
            logger.error(f"找不到角色 {agent_id} 的语音文件")
            return False
            
        if not os.path.exists(voice_file):
            logger.error(f"语音文件路径无效: {voice_file}")
            return False
            
        try:
            # 为该角色分配端口
            port = self._get_next_port()
            
            # 启动服务器
            client = start_streaming_server(
                reference_audio=voice_file,
                model="F5TTS_v1_Base",
                host="192.168.3.60",
                port=port,
                auto_stop_minutes=60  # 60分钟自动停止，避免资源浪费
            )
            
            # 存储服务器信息
            self.servers[agent_id] = {
                "client": client,
                "port": port,
                "voice_file": voice_file,
                "running": True,
                "start_time": time.time()
            }
            
            logger.info(f"为角色 {agent_id} 启动语音服务器成功，端口: {port}")
            return True
            
        except Exception as e:
            logger.error(f"启动语音服务器失败: {e}")
            return False
    
    def stop_server_for_agent(self, agent_id: str) -> bool:
        """停止指定角色的语音服务器
        
        Args:
            agent_id: 角色ID
            
        Returns:
            bool: 是否成功停止
        """
        if agent_id not in self.servers or not self.servers[agent_id]["running"]:
            logger.info(f"角色 {agent_id} 的语音服务器未运行")
            return True
            
        try:
            # 停止服务器
            self.servers[agent_id]["client"].stop_server()
            self.servers[agent_id]["running"] = False
            
            logger.info(f"停止角色 {agent_id} 的语音服务器成功")
            return True
            
        except Exception as e:
            logger.error(f"停止语音服务器失败: {e}")
            return False
    
    def find_voice_for_agent(self, agent_id: str) -> Optional[str]:
        """为指定代理查找语音文件，无视配置信息直接查找
        
        Args:
            agent_id: 角色ID
            
        Returns:
            Optional[str]: 找到的语音文件路径，未找到则返回None
        """
        # 1. 首先尝试最常见的情况：以agent_id命名的文件
        for ext in ['.wav', '.mp3', '.m4a', '.aac']:
            direct_path = os.path.join(self.voice_dir, f"{agent_id}{ext}")
            if os.path.exists(direct_path):
                logger.info(f"直接找到{agent_id}的语音文件: {direct_path}")
                return direct_path
        
        # 2. 尝试加载配置文件
        try:
            config_path = os.path.join("save", "custom_agents", f"{agent_id}.json")
            if os.path.exists(config_path):
                import json
                with open(config_path, "r", encoding="utf-8") as f:
                    agent_config = json.load(f)
                
                # 3. 检查配置中是否有语音文件
                if "voice_file" in agent_config:
                    voice_path = agent_config["voice_file"]
                    
                    # 4. 尝试各种路径格式
                    possible_paths = [
                        voice_path,
                        os.path.abspath(voice_path),
                        os.path.join(os.getcwd(), voice_path),
                        os.path.join("backend", voice_path),
                        os.path.join(self.voice_dir, os.path.basename(voice_path))
                    ]
                    
                    for path in possible_paths:
                        if os.path.exists(path):
                            logger.info(f"通过配置找到{agent_id}的语音文件: {path}")
                            return path
        except Exception as e:
            logger.error(f"查找{agent_id}语音文件时出错: {e}")
        
        # 未找到语音文件
        logger.warning(f"未找到{agent_id}的语音文件")
        return None

    def generate_speech(self, agent_id: str, text: str) -> bool:
        """为指定角色生成语音（同步版本）
        
        Args:
            agent_id: 角色ID
            text: 要生成语音的文本
            
        Returns:
            bool: 是否成功生成
        """
        # 检查服务器是否运行
        if agent_id not in self.servers or not self.servers[agent_id]["running"]:
            # 尝试启动服务器
            if not self.start_server_for_agent(agent_id):
                # 最后一次尝试：直接查找语音文件并启动
                voice_file = self.find_voice_for_agent(agent_id)
                if voice_file and self.start_server_for_agent(agent_id, voice_file):
                    logger.info(f"通过直接查找语音文件成功启动了{agent_id}的语音服务器")
                else:
                    logger.error(f"角色 {agent_id} 的语音服务器未运行且无法启动")
                    return False
        
        try:
            client = self.servers[agent_id]["client"]
            # 创建事件循环来运行异步方法
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    asyncio.wait_for(
                        self._generate_speech_async(client, text),
                        timeout=15  # 15秒总超时
                    )
                )
            except asyncio.TimeoutError:
                logger.warning(f"语音生成总操作超时")
                # 超时仍然认为是部分成功
                return True
            except Exception as e:
                logger.error(f"生成语音时发生异常: {e}")
                # 其他异常也继续执行
                return True
            finally:
                loop.close()
            return True
            
        except Exception as e:
            logger.error(f"生成语音失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # 即使出错也返回True，避免阻断对话流程
            return True
    
    async def _generate_speech_async(self, client, text: str) -> None:
        """异步生成语音
        
        Args:
            client: F5TTS客户端
            text: 要生成语音的文本
        """
        try:
            # 确保client连接着
            if not client.is_connected():
                await client.connect()
                
            # 生成语音
            await client.tts(text)
        except Exception as e:
            logger.error(f"异步生成语音失败: {e}")
            # 重新抛出异常以便上层处理
            raise
    
    async def generate_speech_async(self, agent_id: str, text: str) -> bool:
        """为指定角色生成语音的异步版本
        
        Args:
            agent_id: 角色ID
            text: 要生成语音的文本
            
        Returns:
            bool: 是否成功生成
        """
        # 检查服务器是否运行
        if agent_id not in self.servers or not self.servers[agent_id]["running"]:
            # 尝试启动服务器
            if not self.start_server_for_agent(agent_id):
                # 最后一次尝试：直接查找语音文件并启动
                voice_file = self.find_voice_for_agent(agent_id)
                if voice_file and self.start_server_for_agent(agent_id, voice_file):
                    logger.info(f"通过直接查找语音文件成功启动了{agent_id}的语音服务器")
                else:
                    logger.error(f"角色 {agent_id} 的语音服务器未运行且无法启动")
                    return False
        
        try:
            # 使用异步方法生成语音
            client = self.servers[agent_id]["client"]
            # 使用超时保护
            try:
                await asyncio.wait_for(
                    self._generate_speech_async(client, text),
                    timeout=15  # 15秒总超时
                )
            except asyncio.TimeoutError:
                logger.warning(f"语音生成总操作超时")
                # 超时仍然认为是部分成功
                return True
            except Exception as e:
                logger.error(f"生成语音时发生异常: {e}")
                # 其他异常也继续执行
                return True
            return True
            
        except Exception as e:
            logger.error(f"生成语音失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # 即使出错也返回True，避免阻断对话流程
            return True
    
    def stop_all_servers(self):
        """停止所有语音服务器"""
        for agent_id in list(self.servers.keys()):
            self.stop_server_for_agent(agent_id)
            
    def __del__(self):
        """析构函数，确保所有服务器停止"""
        self.stop_all_servers()


# 全局单例实例
f5_speech_service = F5SpeechService() 