#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
F5-TTS模块使用示例
演示如何在现有项目中使用f5_tts.py模块
"""

import time
import asyncio
from f5_tts import F5TTSClient, clone_voice, start_streaming_server

# 示例1: 简单的语音克隆生成
def example_clone_voice():
    print("示例1: 语音克隆")
    print("-" * 50)
    
    # 使用便捷函数
    print("方法1: 使用便捷函数")
    start_time = time.time()
    wav, sr, spec = clone_voice(
        reference_audio="path/to/reference.wav",
        target_text="这是一段使用克隆音色生成的语音。听起来是不是很自然？",
        output_file="output_clone.wav"
    )
    print(f"生成完成，耗时: {time.time() - start_time:.2f}秒")
    print(f"输出文件: output_clone.wav")
    
    # 使用客户端对象
    print("\n方法2: 使用客户端对象")
    client = F5TTSClient(model="F5TTS_v1_Base")
    start_time = time.time()
    wav, sr, spec = client.clone_voice(
        reference_audio="path/to/reference.wav",
        reference_text="",  # 留空自动转录
        target_text="使用客户端对象生成的语音。可以更灵活地控制参数。",
        output_file="output_clone2.wav",
        speed=1.1,         # 语速稍快
        cfg_strength=2.5   # 增强音色相似度
    )
    print(f"生成完成，耗时: {time.time() - start_time:.2f}秒")
    print(f"输出文件: output_clone2.wav")
    print("-" * 50)

# 示例2: 流式语音生成
def example_streaming_tts():
    print("示例2: 流式语音生成")
    print("-" * 50)
    
    # 启动服务器
    client = start_streaming_server(
        reference_audio="path/to/reference.wav",
        model="F5TTS_v1_Base",
        auto_stop_minutes=10  # 10分钟后自动停止服务器
    )
    
    try:
        # 生成一些语音
        print("生成第一段语音...")
        client.generate_speech("这是流式生成的第一段语音。它会立即开始播放。")
        
        time.sleep(1)  # 等待前一段语音播放完毕
        
        print("生成第二段语音...")
        client.generate_speech("这是第二段语音。流式生成可以提供更快的响应。")
        
    finally:
        # 停止服务器
        client.stop_server()
    
    print("-" * 50)

# 示例3: 在现有应用中集成流式TTS
def example_integration():
    print("示例3: 在现有应用中集成")
    print("-" * 50)
    
    class MyApp:
        def __init__(self):
            # 初始化TTS客户端
            self.tts_client = F5TTSClient(
                model="F5TTS_v1_Base",
                server_host="localhost",
                server_port=9999
            )
            
        def initialize_tts(self, reference_audio):
            # 启动TTS服务器
            self.tts_client.start_server(reference_audio)
            
        def speak(self, text):
            # 生成语音
            self.tts_client.generate_speech(text)
            
        def shutdown(self):
            # 关闭TTS服务器
            self.tts_client.stop_server()
    
    # 使用示例
    app = MyApp()
    app.initialize_tts("path/to/reference.wav")
    
    app.speak("欢迎使用我的应用。这是一个集成了语音功能的演示。")
    time.sleep(3)  # 等待语音播放
    
    app.speak("您可以很容易地将流式TTS集成到您的应用中。")
    time.sleep(3)  # 等待语音播放
    
    app.shutdown()
    print("-" * 50)

# 示例4: 异步使用
async def example_async():
    print("示例4: 异步使用")
    print("-" * 50)
    
    client = F5TTSClient()
    client.start_server("path/to/reference.wav")
    
    try:
        # 异步生成语音
        await client.generate_speech_async("这是异步生成的语音。适合在异步应用中使用。")
        
        # 同时启动多个语音生成任务
        tasks = [
            client.generate_speech_async("第一个并行任务"),
            client.generate_speech_async("第二个并行任务"),
            client.generate_speech_async("第三个并行任务")
        ]
        
        # 等待所有任务完成
        for task in tasks:
            await task
            
    finally:
        client.stop_server()
    
    print("-" * 50)

# 主函数
def main():
    print("F5-TTS模块使用示例")
    print("=" * 50)
    
    # 运行示例
    example_clone_voice()
    
    example_streaming_tts()
    
    example_integration()
    
    # 异步示例需要使用事件循环运行
    asyncio.run(example_async())
    
    print("示例运行完毕")

if __name__ == "__main__":
    main()
