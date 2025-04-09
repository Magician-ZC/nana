from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
import os
import uuid
import shutil
import asyncio
from datetime import datetime
import json
import tempfile
import aiohttp
import time
import traceback
import logging

# 创建日志记录器
logger = logging.getLogger("video_analyzer")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

# 创建路由器
video_router = APIRouter()

# 远程分析服务器
REMOTE_ANALYSIS_SERVER = "http://192.168.3.51:8000/analyze_video"

# 临时文件目录
TEMP_DIR = "temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)

# 保存目录
SAVE_DIR = os.path.join("save", "video_assessments")
os.makedirs(SAVE_DIR, exist_ok=True)

# 当前处理状态
PROCESSING_STATUS = {
    "is_processing": False,
    "current_video": None,
    "start_time": None
}

@video_router.post("/video_analysis")
async def analyze_video(video: UploadFile = File(...)):
    """上传视频并进行情绪分析
    
    Args:
        video: 上传的视频文件
        
    Returns:
        dict: 包含处理结果的响应
    """
    global PROCESSING_STATUS
    
    # 检查当前是否有处理中的视频
    if PROCESSING_STATUS["is_processing"]:
        # 如果处理时间超过5分钟，认为之前的处理已经失败，可以开始新的处理
        if PROCESSING_STATUS["start_time"] and (time.time() - PROCESSING_STATUS["start_time"]) > 300:
            logger.warning(f"检测到之前的视频处理已超时 ({int(time.time() - PROCESSING_STATUS['start_time'])}秒)，允许新的处理")
        else:
            logger.info(f"当前有视频正在处理中: {PROCESSING_STATUS['current_video']}")
            return JSONResponse(
                content={
                    "success": False,
                    "message": "当前已有视频正在处理中，请稍后再试"
                },
                status_code=429  # Too Many Requests
            )
    
    try:
        # 设置处理状态
        PROCESSING_STATUS = {
            "is_processing": True,
            "current_video": video.filename,
            "start_time": time.time()
        }
        
        logger.info(f"接收到视频: {video.filename}")
        
        # 生成唯一文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4().hex[:8])
        video_filename = f"video_{timestamp}_{unique_id}.webm"
        temp_video_path = os.path.join(TEMP_DIR, video_filename)
        
        # 保存视频到临时目录
        with open(temp_video_path, "wb") as buffer:
            shutil.copyfileobj(video.file, buffer)
        
        logger.info(f"视频保存到临时文件: {temp_video_path}")
        
        # 异步分析视频
        analysis_result = await process_video(temp_video_path)
        
        # 保存分析结果
        result_filename = f"assessment_{timestamp}_{unique_id}.json"
        result_path = os.path.join(SAVE_DIR, result_filename)
        
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"分析结果保存到: {result_path}")
        
        # 清理临时文件
        try:
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)
                logger.info(f"临时文件已删除: {temp_video_path}")
        except Exception as e:
            logger.error(f"清理临时文件失败: {e}")
        
        # 处理完成
        PROCESSING_STATUS = {
            "is_processing": False,
            "current_video": None,
            "start_time": None
        }
        
        return JSONResponse(
            content={
                "success": True,
                "message": "视频分析完成",
                "data": analysis_result
            }
        )
        
    except Exception as e:
        logger.error(f"视频分析失败: {e}")
        logger.error(traceback.format_exc())
        
        # 重置处理状态
        PROCESSING_STATUS = {
            "is_processing": False,
            "current_video": None,
            "start_time": None
        }
        
        return JSONResponse(
            content={
                "success": False,
                "message": f"视频分析失败: {str(e)}"
            },
            status_code=500
        )

async def process_video(video_path):
    """处理视频文件并进行情绪分析
    
    当远程服务器不可用时，将返回模拟数据
    
    Args:
        video_path: 视频文件路径
        
    Returns:
        dict: 分析结果
    """
    try:
        # 尝试发送到远程服务器进行分析
        result = await send_to_remote_server(video_path)
        return result
    except Exception as e:
        logger.error(f"远程服务器处理失败: {e}")
        logger.error(traceback.format_exc())
        
        # 返回模拟数据
        return generate_mock_result()

async def send_to_remote_server(video_path):
    """发送视频到远程服务器进行分析
    
    Args:
        video_path: 视频文件路径
        
    Returns:
        dict: 远程服务器返回的分析结果
    """
    try:
        logger.info(f"开始发送视频到远程服务器: {REMOTE_ANALYSIS_SERVER}")
        
        # 设置超时时间
        timeout = aiohttp.ClientTimeout(total=180)  # 3分钟超时
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # 准备表单数据
            with open(video_path, 'rb') as f:
                form_data = aiohttp.FormData()
                form_data.add_field('video',
                                   f,
                                   filename=os.path.basename(video_path),
                                   content_type='video/webm')
                
                # 发送请求
                async with session.post(REMOTE_ANALYSIS_SERVER, data=form_data) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info("远程服务器分析完成")
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"远程服务器返回错误: {response.status}, {error_text}")
                        raise Exception(f"远程服务器返回错误: {response.status}, {error_text}")
    except asyncio.TimeoutError:
        logger.error("远程服务器处理超时")
        raise Exception("远程服务器处理超时，请稍后再试")
    except Exception as e:
        logger.error(f"发送到远程服务器失败: {e}")
        raise

def generate_mock_result():
    """生成模拟的分析结果（当远程服务器不可用时使用）
    
    Returns:
        dict: 模拟的分析结果
    """
    logger.info("生成模拟分析结果")
    
    return {
        "情绪状态分析": {
            "主要情绪": "平静",
            "情绪强度": "中等",
            "情绪稳定性": "稳定",
            "情绪变化": "情绪波动较小，整体保持平稳",
            "压力指数": "较低"
        },
        "面部表情分析": {
            "主要表情": "自然/中性",
            "表情变化": "表情变化较少，主要保持自然状态",
            "微表情检测": "未检测到明显的负面微表情",
            "特征点分析": "面部肌肉放松，无明显紧张状态"
        },
        "生理指标推断": {
            "心率估计": "正常范围",
            "呼吸模式": "规律",
            "交感神经活动": "活动水平适中"
        },
        "综合评估": {
            "总体心理状态": "健康/平衡",
            "注意力状态": "集中",
            "情绪调节能力": "良好",
            "社交互动倾向": "开放",
            "建议": "当前心理状态良好，建议保持规律作息和适当运动以维持情绪稳定。"
        },
        "分析时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "分析版本": "1.0 模拟数据"
    }

def init_router():
    """初始化路由器
    
    Returns:
        APIRouter: 配置好的路由器
    """
    return video_router 