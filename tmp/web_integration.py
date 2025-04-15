#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
F5-TTS Web应用集成示例
演示如何将F5-TTS流式TTS集成到Flask Web应用中
"""

import os
import time
import threading
from flask import Flask, request, jsonify, send_file, Response, stream_with_context

# 导入我们的F5-TTS模块
from f5_tts import F5TTSClient, start_streaming_server

app = Flask(__name__)

# TTS客户端
tts_client = None
reference_audio_path = "path/to/default_reference.wav"

# 状态变量
is_server_running = False
server_start_time = None
last_activity_time = None

# 配置
AUTO_SHUTDOWN_MINUTES = 30  # 无活动30分钟后自动关闭服务器
CHECK_INTERVAL = 60  # 每分钟检查一次服务器状态

# 启动TTS服务器
def start_tts_server(ref_audio, ref_text=""):
    global tts_client, is_server_running, server_start_time
    
    if is_server_running:
        return {"status": "already_running"}
    
    try:
        tts_client = start_streaming_server(
            reference_audio=ref_audio,
            reference_text=ref_text,
            host="localhost",
            port=9997  # 使用不同端口避免冲突
        )
        
        is_server_running = True
        server_start_time = time.time()
        update_activity_time()
        
        # 启动监控线程
        threading.Thread(target=monitor_server_activity, daemon=True).start()
        
        return {"status": "success", "message": "TTS服务器已启动"}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

# 更新最后活动时间
def update_activity_time():
    global last_activity_time
    last_activity_time = time.time()

# 监控服务器活动
def monitor_server_activity():
    global is_server_running, tts_client
    
    while is_server_running:
        time.sleep(CHECK_INTERVAL)
        
        # 检查最后活动时间
        if last_activity_time and (time.time() - last_activity_time) > (AUTO_SHUTDOWN_MINUTES * 60):
            print(f"TTS服务器超过{AUTO_SHUTDOWN_MINUTES}分钟无活动，正在关闭...")
            if tts_client:
                tts_client.stop_server()
            is_server_running = False
            break

# API路由
@app.route('/api/tts/status', methods=['GET'])
def get_tts_status():
    """获取TTS服务器状态"""
    global is_server_running, server_start_time
    
    status = {
        "running": is_server_running,
        "uptime": time.time() - server_start_time if is_server_running else None,
        "reference_audio": os.path.basename(reference_audio_path) if is_server_running else None
    }
    
    return jsonify(status)

@app.route('/api/tts/start', methods=['POST'])
def api_start_tts():
    """启动TTS服务器"""
    global reference_audio_path
    
    data = request.json or {}
    ref_audio = data.get('reference_audio', reference_audio_path)
    ref_text = data.get('reference_text', '')
    
    # 确保引用音频存在
    if not os.path.exists(ref_audio):
        return jsonify({"status": "error", "message": f"引用音频文件不存在: {ref_audio}"})
    
    reference_audio_path = ref_audio
    result = start_tts_server(ref_audio, ref_text)
    
    return jsonify(result)

@app.route('/api/tts/stop', methods=['POST'])
def api_stop_tts():
    """停止TTS服务器"""
    global tts_client, is_server_running
    
    if not is_server_running:
        return jsonify({"status": "not_running"})
    
    try:
        if tts_client:
            tts_client.stop_server()
        is_server_running = False
        return jsonify({"status": "success", "message": "TTS服务器已停止"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/tts/generate', methods=['POST'])
def api_generate_speech():
    """生成语音（非流式，返回音频文件）"""
    global tts_client, reference_audio_path
    
    data = request.json or {}
    text = data.get('text')
    ref_audio = data.get('reference_audio', reference_audio_path)
    ref_text = data.get('reference_text', '')
    
    if not text:
        return jsonify({"status": "error", "message": "缺少text参数"})
    
    # 如果服务器未运行，启动它
    if not is_server_running:
        result = start_tts_server(ref_audio, ref_text)
        if result["status"] != "success" and result["status"] != "already_running":
            return jsonify(result)
    
    # 创建临时输出文件
    output_file = f"temp_output_{int(time.time())}.wav"
    
    try:
        # 使用本地模式生成
        from f5_tts import clone_voice
        clone_voice(
            reference_audio=ref_audio,
            reference_text=ref_text,
            target_text=text,
            output_file=output_file
        )
        
        # 更新活动时间
        update_activity_time()
        
        # 返回文件
        return send_file(
            output_file,
            mimetype="audio/wav",
            as_attachment=True,
            download_name="speech.wav"
        )
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    
    finally:
        # 清理临时文件
        if os.path.exists(output_file):
            try:
                os.remove(output_file)
            except:
                pass

@app.route('/api/tts/stream', methods=['POST'])
def api_stream_speech():
    """流式生成语音（返回音频流）"""
    global tts_client, is_server_running, reference_audio_path
    
    data = request.json or {}
    text = data.get('text')
    ref_audio = data.get('reference_audio', reference_audio_path)
    ref_text = data.get('reference_text', '')
    
    if not text:
        return jsonify({"status": "error", "message": "缺少text参数"})
    
    # 如果服务器未运行，启动它
    if not is_server_running:
        result = start_tts_server(ref_audio, ref_text)
        if result["status"] != "success" and result["status"] != "already_running":
            return jsonify(result)
    
    # 使用流式模式生成
    update_activity_time()
    tts_client.generate_speech(text)
    
    return jsonify({"status": "success", "message": "语音已流式生成"})

@app.route('/api/tts/transcribe', methods=['POST'])
def api_transcribe():
    """转录音频文件"""
    # 检查文件是否上传
    if 'audio' not in request.files:
        return jsonify({"status": "error", "message": "未找到音频文件"})
    
    audio_file = request.files['audio']
    
    # 保存上传的文件
    temp_path = f"temp_upload_{int(time.time())}.wav"
    audio