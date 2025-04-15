#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
F5-TTS 流式语音合成模块
这个模块提供了一个简单的接口，用于使用F5-TTS进行流式语音合成。
支持语音克隆和流式语音生成功能。
"""

import os
import time
import asyncio
import logging
import subprocess
import threading
from typing import Optional, Union, Tuple, List, Callable
import numpy as np

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("F5TTS")

class F5TTSClient:
    """F5-TTS客户端，支持语音克隆和流式语音生成"""

    def __init__(
        self,
        model: str = "F5TTS_v1_Base",
        server_host: str = "192.168.3.60",
        server_port: int = 7860,
        device: Optional[str] = None,
        cache_dir: Optional[str] = None,
    ):
        """
        初始化F5-TTS客户端
        
        Args:
            model: 模型名称
            server_host: 服务器主机地址
            server_port: 服务器端口
            device: 使用的设备 (cuda, cpu等)
            cache_dir: 模型缓存目录
        """
        self.model = model
        self.server_host = server_host
        self.server_port = server_port
        self.device = device
        self.cache_dir = cache_dir
        self.server_process = None
        self._server_started = False
        self._async_loop = None

    def _import_api(self):
        """
        按需导入F5-TTS API，避免不必要的初始化
        """
        try:
            from f5_tts.api import F5TTS
            return F5TTS
        except ImportError:
            raise ImportError("找不到F5-TTS库。请安装F5-TTS: pip install f5_tts")

    def _import_socket_client(self):
        """
        按需导入socket客户端
        """
        try:
            from f5_tts.socket_client import listen_to_F5TTS
            return listen_to_F5TTS
        except ImportError:
            raise ImportError("找不到F5-TTS库。请安装F5-TTS: pip install f5_tts")

    def clone_voice(
        self,
        reference_audio: str,
        reference_text: str,
        target_text: str,
        output_file: str,
        remove_silence: bool = True,
        speed: float = 1.0,
        cfg_strength: float = 2.0,
        seed: Optional[int] = None,
    ) -> Tuple[np.ndarray, int, np.ndarray]:
        """
        克隆语音并生成音频文件
        
        Args:
            reference_audio: 参考音频文件路径
            reference_text: 参考音频文本 (留空则自动转录)
            target_text: 要生成语音的文本
            output_file: 输出音频文件路径
            remove_silence: 是否移除生成的音频中的静音部分
            speed: 语音速度
            cfg_strength: 条件引导强度
            seed: 随机种子
            
        Returns:
            元组: (音频数据, 采样率, 频谱图)
        """
        logger.info(f"使用非流式模式生成语音...")
        F5TTS = self._import_api()
        
        start_time = time.time()
        tts = F5TTS(model=self.model, device=self.device, hf_cache_dir=self.cache_dir)
        logger.info(f"模型加载耗时: {time.time() - start_time:.2f}秒")
        
        # 处理参考音频文本
        if not reference_text:
            logger.info("未提供参考文本，开始自动转录...")
            reference_text = tts.transcribe(reference_audio)
            logger.info(f"转录结果: {reference_text}")
        
        # 生成语音
        logger.info(f"开始生成语音...")
        generation_start = time.time()
        wav, sr, spec = tts.infer(
            ref_file=reference_audio,
            ref_text=reference_text,
            gen_text=target_text,
            file_wave=output_file,
            remove_silence=remove_silence,
            speed=speed,
            cfg_strength=cfg_strength,
            seed=seed
        )
        logger.info(f"语音生成耗时: {time.time() - generation_start:.2f}秒")
        
        return wav, sr, spec

    def start_server(
        self,
        reference_audio: str,
        reference_text: str = "",
        auto_stop_minutes: Optional[int] = None,
    ) -> None:
        """
        启动F5-TTS服务器，用于流式语音生成
        
        Args:
            reference_audio: 参考音频文件路径
            reference_text: 参考音频文本 (留空则自动转录)
            auto_stop_minutes: 服务器自动停止的分钟数 (None表示不自动停止)
        """
        if self._server_started:
            logger.info("服务器已经在运行中")
            return
        
        # 检查参考音频文件是否存在
        if not os.path.exists(reference_audio):
            raise FileNotFoundError(f"找不到参考音频文件: {reference_audio}")
        
        # 构建启动服务器的命令
        cmd = [
            "python", "-m", "f5_tts.socket_server",
            "--host", self.server_host,
            "--port", str(self.server_port),
            "--model", self.model,
            "--ref_audio", reference_audio
        ]
        
        if reference_text:
            cmd.extend(["--ref_text", reference_text])
            
        if self.device:
            cmd.extend(["--device", self.device])
            
        # 启动服务器进程
        logger.info(f"启动F5-TTS服务器...")
        self.server_process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # 给服务器启动时间
        time.sleep(5)
        self._server_started = True
        logger.info(f"F5-TTS服务器已启动 (PID: {self.server_process.pid})")
        
        # 如果设置了自动停止时间，创建一个计时器线程
        if auto_stop_minutes:
            def auto_stop():
                logger.info(f"服务器将在 {auto_stop_minutes} 分钟后自动停止")
                time.sleep(auto_stop_minutes * 60)
                self.stop_server()
                
            threading.Thread(target=auto_stop, daemon=True).start()

    def stop_server(self) -> None:
        """
        停止F5-TTS服务器
        """
        if self.server_process and self._server_started:
            logger.info("正在停止F5-TTS服务器...")
            self.server_process.terminate()
            self.server_process.wait(timeout=10)
            self._server_started = False
            logger.info("F5-TTS服务器已停止")

    async def _generate_stream(self, text: str) -> None:
        """
        向服务器发送文本，以流式方式生成语音
        
        Args:
            text: 要生成语音的文本
        """
        listen_to_F5TTS = self._import_socket_client()
        await listen_to_F5TTS(text, server_ip=self.server_host, server_port=self.server_port)

    def _get_or_create_event_loop(self):
        """
        获取或创建事件循环
        """
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def generate_speech(self, text: str) -> None:
        """
        向服务器发送文本，以流式方式生成语音 (同步版本)
        
        Args:
            text: 要生成语音的文本
        """
        if not self._server_started:
            raise RuntimeError("服务器未启动，请先调用 start_server() 方法")
        
        # 使用线程安全的方式调用协程
        try:
            # 尝试获取当前事件循环
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果当前循环正在运行中，使用新线程新循环
                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        new_loop.run_until_complete(self._generate_stream(text))
                    finally:
                        new_loop.close()
                
                thread = threading.Thread(target=run_in_thread)
                thread.daemon = True
                thread.start()
                thread.join(timeout=5)  # 等待最多5秒
            else:
                # 如果当前循环不在运行中，直接使用它
                loop.run_until_complete(self._generate_stream(text))
        except RuntimeError:
            # 如果出错，创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._generate_stream(text))
            finally:
                loop.close()

    async def generate_speech_async(self, text: str) -> None:
        """
        向服务器发送文本，以流式方式生成语音 (异步版本)
        
        Args:
            text: 要生成语音的文本
        """
        if not self._server_started:
            raise RuntimeError("服务器未启动，请先调用 start_server() 方法")
        
        await self._generate_stream(text)

    def transcribe(self, audio_file: str, language: Optional[str] = None) -> str:
        """
        转录音频文件
        
        Args:
            audio_file: 音频文件路径
            language: 语言代码 (可选)
            
        Returns:
            转录文本
        """
        F5TTS = self._import_api()
        tts = F5TTS(model=self.model)
        return tts.transcribe(audio_file, language)

    def __enter__(self):
        """
        上下文管理器入口
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        上下文管理器退出，确保停止服务器
        """
        self.stop_server()

# 便捷函数
def clone_voice(
    reference_audio: str,
    target_text: str,
    output_file: str = "output.wav",
    reference_text: str = "",
    model: str = "F5TTS_v1_Base",
    remove_silence: bool = True,
    speed: float = 1.0,
    cfg_strength: float = 2.0,
    device: Optional[str] = None,
) -> Tuple[np.ndarray, int, np.ndarray]:
    """
    便捷函数：克隆语音并生成音频文件
    
    Args:
        reference_audio: 参考音频文件路径
        target_text: 要生成语音的文本
        output_file: 输出音频文件路径
        reference_text: 参考音频文本 (留空则自动转录)
        model: 模型名称
        remove_silence: 是否移除生成的音频中的静音部分
        speed: 语音速度
        cfg_strength: 条件引导强度
        device: 使用的设备 (cuda, cpu等)
        
    Returns:
        元组: (音频数据, 采样率, 频谱图)
    """
    client = F5TTSClient(model=model, device=device)
    return client.clone_voice(
        reference_audio=reference_audio,
        reference_text=reference_text,
        target_text=target_text,
        output_file=output_file,
        remove_silence=remove_silence,
        speed=speed,
        cfg_strength=cfg_strength
    )


def start_streaming_server(
    reference_audio: str,
    reference_text: str = "",
    model: str = "F5TTS_v1_Base",
    host: str = "localhost",
    port: int = 9998,
    device: Optional[str] = None,
    auto_stop_minutes: Optional[int] = None,
) -> F5TTSClient:
    """
    便捷函数：启动流式TTS服务器
    
    Args:
        reference_audio: 参考音频文件路径
        reference_text: 参考音频文本 (留空则自动转录)
        model: 模型名称
        host: 服务器主机地址
        port: 服务器端口
        device: 使用的设备 (cuda, cpu等)
        auto_stop_minutes: 服务器自动停止的分钟数 (None表示不自动停止)
        
    Returns:
        F5TTSClient实例
    """
    client = F5TTSClient(model=model, server_host=host, server_port=port, device=device)
    client.start_server(reference_audio, reference_text, auto_stop_minutes)
    return client


# 示例使用
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="F5-TTS 流式语音合成")
    parser.add_argument("--mode", choices=["stream", "clone"], default="stream", help="运行模式")
    parser.add_argument("--ref_audio", required=True, help="参考音频文件路径")
    parser.add_argument("--ref_text", default="", help="参考音频文本")
    parser.add_argument("--text", help="要生成语音的文本")
    parser.add_argument("--output", default="output.wav", help="输出音频文件路径 (仅克隆模式)")
    parser.add_argument("--model", default="F5TTS_v1_Base", help="模型名称")
    parser.add_argument("--host", default="localhost", help="服务器主机地址")
    parser.add_argument("--port", type=int, default=9998, help="服务器端口")
    parser.add_argument("--device", help="使用的设备 (cuda, cpu等)")
    
    args = parser.parse_args()
    
    if args.mode == "clone":
        if not args.text:
            parser.error("克隆模式需要指定 --text 参数")
            
        # 克隆模式
        print(f"克隆语音: {args.ref_audio} -> {args.output}")
        clone_voice(
            reference_audio=args.ref_audio,
            reference_text=args.ref_text,
            target_text=args.text,
            output_file=args.output,
            model=args.model,
            device=args.device
        )
        print(f"语音已保存到: {args.output}")
        
    else:
        # 流式模式
        print(f"启动流式TTS服务器...")
        client = start_streaming_server(
            reference_audio=args.ref_audio,
            reference_text=args.ref_text,
            model=args.model,
            host=args.host,
            port=args.port,
            device=args.device
        )
        
        try:
            print("\n服务器已启动，你可以开始生成语音。")
            print("输入文本并按回车键生成语音，输入'quit'退出。")
            
            while True:
                text = input("\n> ")
                
                if text.lower() == 'quit':
                    break
                
                if text.strip():
                    client.generate_speech(text)
        
        finally:
            client.stop_server()
