import os
import json
import time
import threading
import base64
import uuid
import shutil
import tempfile
import re
import math
import io
from collections import Counter
from typing import Optional, List, Dict, Any, Union, AsyncGenerator, Tuple
import asyncio
import logging
import random
import db_manager  # 导入新的数据库模块
import aiosqlite  # 添加aiosqlite导入
import requests
import urllib3
from generate_cert import get_local_ip

# 忽略SSL证书验证警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Form, File, UploadFile, Body, Header, Depends, HTTPException, Response
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from qiniu_uploader import QiniuUploader
from chat_service import ChatService
from tts import TTSService
from super_tts import SuperTTSService
from config import Config
from speech_service import SpeechService
from conversation import ConversationHistory
import assessment_api  # 导入评估API模块
# from f5_speech_service import f5_speech_service  # 导入F5语音服务
# from llm import LLMService  # 注释掉，因为我们使用chat_service中的LLM服务

# 初始化七牛云上传器
qiniu_uploader = QiniuUploader()

# 设置日志级别
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("main")

app = FastAPI()

# 设置日志记录器
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("main")

# CORS设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 在文件顶部加入全局缓存变量
REPORT_LIST_CACHE = {
    "data": None,
    "timestamp": 0,
    "auth_token": None
}
CACHE_TTL = 5  # 缓存有效期，5秒

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    agent_type: Optional[str] = None
    personality: Optional[str] = None
    is_category: Optional[bool] = False
    # 添加引导模式字段
    in_guidance_mode: Optional[bool] = None
    # 添加stream_chat所需字段
    history: Optional[List[Dict[str, str]]] = None
    model: Optional[str] = None
    agent_id: Optional[str] = None

class AgentRequest(BaseModel):
    agent_name: str
    session_id: Optional[str] = "default"

class CustomAgentRequest(BaseModel):
    name: str
    description: str
    model: str
    personality: str
    interests: str
    lifestyle: str
    values: str

class TTSSettingsRequest(BaseModel):
    enable_tts: bool
    enable_super_tts: bool
    enable_tts_global: Optional[bool] = True
    tts_voice: Optional[str] = None
    super_tts_voice: Optional[str] = None
    tts_speed: Optional[int] = None
    typing_speed: Optional[int] = None
    voice_input_mode: Optional[bool] = None
    voice_timeout: Optional[int] = None

class TTSSettings(BaseModel):
    enable_tts: bool
    enable_super_tts: bool
    enable_tts_global: Optional[bool] = True
    tts_voice: Optional[str] = None
    super_tts_voice: Optional[str] = None
    tts_voice_list: List[dict] = []
    super_tts_voice_list: List[dict] = []
    tts_speed: Optional[int] = None
    typing_speed: Optional[int] = None
    voice_input_mode: Optional[bool] = True
    voice_timeout: Optional[int] = 5

chat_service = ChatService()
tts_service = TTSService()
super_tts_service = SuperTTSService()
speech_service = SpeechService()
qiniu_uploader = QiniuUploader()
# llm_service = LLMService(Config.LLM_API_KEY, Config.LLM_API_URL)  # 注释掉，使用chat_service中的LLM服务

# 文本提取函数
def extract_text_from_file(file_path, file_extension):
    """从不同格式的文件中提取文本
    
    Args:
        file_path (str): 文件路径
        file_extension (str): 文件扩展名
        
    Returns:
        str: 提取的文本内容
    """
    if file_extension == '.txt':
        # 直接读取文本文件
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # 尝试使用其他编码
            with open(file_path, 'r', encoding='gbk') as f:
                return f.read()
    
    elif file_extension in ['.doc', '.docx']:
        try:
            # 使用python-docx库提取文本
            import docx
            doc = docx.Document(file_path)
            return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
        except ImportError:
            return "缺少python-docx库，无法解析Word文档。"
    
    elif file_extension in ['.jpg', '.jpeg', '.png']:
        # 对图片文件进行增强OCR处理
        try:
            import pytesseract
            from PIL import Image
            import cv2
            import numpy as np
            import base64
            import io
            
            # 读取图片并进行预处理
            img = cv2.imread(file_path)
            if img is None:
                return "无法读取图片文件"
                
            # 转换为灰度图
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # 自适应阈值处理，提高OCR准确率
            thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                          cv2.THRESH_BINARY, 11, 2)
            
            # 标准OCR识别
            standard_text = pytesseract.image_to_string(thresh, lang='chi_sim+eng')
            
            # 针对表格进行特殊处理
            try:
                # 表格边缘检测
                edges = cv2.Canny(gray, 50, 150, apertureSize=3)
                # 霍夫变换检测直线
                lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=100, maxLineGap=10)
                
                # 如果检测到足够的直线，可能是表格
                if lines is not None and len(lines) > 10:
                    print("检测到可能的表格，使用表格模式OCR...")
                    # 使用表格识别模式
                    table_data = pytesseract.image_to_data(thresh, lang='chi_sim+eng', output_type=pytesseract.Output.DICT)
                    
                    # 将表格数据转换为文本格式
                    table_text = "表格数据:\n"
                    for i in range(len(table_data['text'])):
                        if int(float(table_data['conf'][i])) > 60:  # 只保留置信度高的识别结果
                            if table_data['text'][i].strip():
                                table_text += f"{table_data['text'][i]} "
                            if table_data['text'][i].strip() and 'block_num' in table_data and i+1 < len(table_data['block_num']) and table_data['block_num'][i] != table_data['block_num'][i+1]:
                                table_text += "\n"
                    
                    standard_text += "\n\n表格OCR结果:\n" + table_text
            except Exception as table_err:
                print(f"表格检测错误: {table_err}")
            
            # 使用大模型分析图像内容 (如果启用了对应的API)
            try:
                if chat_service and chat_service.llm_service and hasattr(chat_service.llm_service, 'analyze_image'):
                    print("使用大模型分析图像内容...")
                    # 将图像转换为Base64编码
                    success, encoded_img = cv2.imencode('.jpg', img)
                    if success:
                        img_base64 = base64.b64encode(encoded_img).decode('utf-8')
                        # 使用大模型分析图像
                        image_analysis = chat_service.llm_service.analyze_image(img_base64)
                        if image_analysis:
                            standard_text += "\n\n图像内容分析:\n" + image_analysis
            except Exception as img_analysis_err:
                print(f"图像内容分析错误: {img_analysis_err}")
                
            return standard_text
        except ImportError:
            return "缺少图像处理或OCR库(opencv-python, pytesseract)，无法处理图片。"
        except Exception as e:
            print(f"图片OCR错误: {str(e)}")
            return f"OCR处理失败: {str(e)}"
    
    elif file_extension == '.pdf':
        try:
            # 使用多种方法提取PDF文本和图像内容
            text = ""
            
            # 1. 首先使用PyMuPDF (fitz)提取文本和图像
            try:
                import fitz  # PyMuPDF
                print("使用PyMuPDF提取PDF内容...")
                
                doc = fitz.open(file_path)
                extracted_images = []
                extracted_text = ""
                
                for page_num, page in enumerate(doc):
                    # 提取文本
                    page_text = page.get_text()
                    extracted_text += page_text + "\n\n"
                    
                    # 提取图像
                    image_list = page.get_images(full=True)
                    for img_index, img in enumerate(image_list):
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        
                        # 保存图像到临时文件
                        img_filename = f"temp_uploads/img_p{page_num+1}_{img_index+1}.png"
                        with open(img_filename, "wb") as img_file:
                            img_file.write(image_bytes)
                            
                        extracted_images.append(img_filename)
                
                # 如果提取了有效文本，使用它
                if len(extracted_text.strip()) > 100:
                    text = extracted_text
                
                # 处理提取出的图像
                images_text = ""
                for i, img_path in enumerate(extracted_images):
                    try:
                        # 对图像进行OCR
                        img = cv2.imread(img_path)
                        if img is not None:
                            # 转为灰度
                            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                            # 自适应阈值处理
                            thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                                          cv2.THRESH_BINARY, 11, 2)
                            # OCR识别
                            img_text = pytesseract.image_to_string(thresh, lang='chi_sim+eng')
                            
                            if len(img_text.strip()) > 5:  # 只添加有意义的OCR结果
                                images_text += f"\n图像{i+1}内容:\n{img_text}\n"
                                
                            # 使用大模型分析图像
                            try:
                                if chat_service and chat_service.llm_service and hasattr(chat_service.llm_service, 'analyze_image'):
                                    # 将图像转换为Base64编码
                                    success, encoded_img = cv2.imencode('.jpg', img)
                                    if success:
                                        img_base64 = base64.b64encode(encoded_img).decode('utf-8')
                                        # 使用大模型分析图像，专注于表格和图表
                                        llm_prompt = """请分析这张图片，特别注意其中可能包含的表格、图表或情绪评估相关的数据，如果有:
1. 表格数据：提取表格中的数值和标签，特别关注"攻击性"、"自信"、"能量"、"压力"、"抑郁"等指标及其数值
2. 图表数据：描述图表展示的趋势和重要数值点
3. 情绪评估数据：识别任何与心理或情绪状态相关的评分和解释

请以结构化格式返回所有数据，特别是数值型数据。"""
                                        image_analysis = chat_service.llm_service.analyze_image(img_base64, llm_prompt)
                                        if image_analysis and len(image_analysis.strip()) > 10:
                                            images_text += f"\n图像{i+1}深度分析:\n{image_analysis}\n"
                            except Exception as img_analysis_err:
                                print(f"图像内容分析错误: {img_analysis_err}")
                        
                        # 清理临时图像文件
                        if os.path.exists(img_path):
                            os.remove(img_path)
                    except Exception as img_proc_err:
                        print(f"图像处理错误: {img_proc_err}")
                
                # 将图像分析添加到文本结果
                if images_text:
                    text += "\n===提取的图像内容===\n" + images_text
            
            except ImportError:
                print("PyMuPDF未安装，跳过此方法")
            except Exception as pymupdf_error:
                print(f"PyMuPDF提取错误: {pymupdf_error}")
            
            # 2. 如果PyMuPDF提取不足，尝试使用PyPDF2
            if not text or len(text.strip()) < 100:
                try:
                    from PyPDF2 import PdfReader
                    print("使用PyPDF2提取PDF文本...")
                    reader = PdfReader(file_path)
                    pdf_text = ""
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            pdf_text += page_text + "\n\n"
                    
                    if len(pdf_text.strip()) > len(text.strip()):
                        text = pdf_text
                except Exception as pypdf_error:
                    print(f"PyPDF2提取错误: {pypdf_error}")
            
            # 3. 如果以上方法提取内容不足，使用PDF转图像+OCR方案
            if not text or len(text.strip()) < 100:
                print("PDF文本提取不足，使用PDF转图像+OCR方案进行识别...")
                try:
                    # 使用pdf2image和OCR处理
                    import pytesseract
                    from pdf2image import convert_from_path
                    import cv2
                    import numpy as np
                    
                    # 创建临时目录存储图像，方便后续处理
                    os.makedirs("temp_images", exist_ok=True)
                    
                    # 转换PDF为高分辨率图像
                    images = convert_from_path(file_path, dpi=300)
                    ocr_text = ""
                    
                    # 对每一页进行处理
                    for i, image in enumerate(images):
                        # 保存图像到临时文件
                        temp_img_path = f"temp_images/page_{i+1}.png"
                        image.save(temp_img_path, "PNG")
                        
                        # 使用OpenCV加载并处理图像
                        opencv_image = cv2.imread(temp_img_path)
                        if opencv_image is not None:
                            # 转为灰度
                            gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)
                            
                            # 应用自适应阈值
                            thresh = cv2.adaptiveThreshold(
                                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                cv2.THRESH_BINARY, 11, 2
                            )
                            
                            # 标准OCR识别
                            custom_config = r'--oem 1 --psm 3 -l chi_sim+eng'
                            page_text = pytesseract.image_to_string(thresh, config=custom_config)
                            
                            # 特殊处理：替换常见错误识别
                            replacements = {
                                '×Ô—¯': '自信',
                                '˘‰"â': '压力',
                                '×Ô˛Òµ÷‰Ú': '能量',
                                'ÒÖÓô': '抑郁',
                                'Éæ¾›Ö˚': '攻击性',
                                'O AM I C': 'OAMIC',
                                '0 AM I C': 'OAMIC',
                                '攻击 ': '攻击性 ',
                                '自信 ': '自信 ',
                                '能量 ': '能量 ',
                                '压力 ': '压力 ',
                                '抑郁 ': '抑郁 '
                            }
                            
                            for old, new in replacements.items():
                                page_text = page_text.replace(old, new)
                            
                            ocr_text += page_text + "\n\n"
                            
                            # 使用大模型分析图像内容
                            try:
                                if chat_service and chat_service.llm_service and hasattr(chat_service.llm_service, 'analyze_image'):
                                    # 将图像转换为Base64编码
                                    with open(temp_img_path, "rb") as img_file:
                                        img_base64 = base64.b64encode(img_file.read()).decode('utf-8')
                                    
                                    # 使用大模型分析图像，专注于情绪评估数据
                                    llm_prompt = """请分析这张图片，专注于情绪/心理评估相关的数据:
1. 识别图像中的表格、图表和文本
2. 提取所有与情绪评估相关的指标值，特别是"攻击性"、"自信"、"能量"、"压力"、"抑郁"等指标及其数值
3. 标注每个指标的数值范围（如果图片中有显示）
4. 理解图表中表示的情绪波动趋势

请以结构化格式返回所有发现的数据点和分析结果。特别强调数值型数据，如：攻击性：45，自信：70等。"""
                                    image_analysis = chat_service.llm_service.analyze_image(img_base64, llm_prompt)
                                    if image_analysis and len(image_analysis.strip()) > 10:
                                        ocr_text += f"\n页面{i+1}图像深度分析:\n{image_analysis}\n\n"
                            except Exception as img_analysis_err:
                                print(f"图像内容分析错误: {img_analysis_err}")
                        
                        # 清理临时文件
                        if os.path.exists(temp_img_path):
                            os.remove(temp_img_path)
                    
                    # 清理临时目录
                    try:
                        if os.path.exists("temp_images"):
                            os.rmdir("temp_images")
                    except:
                        pass
                    
                    # 使用OCR结果
                    if ocr_text.strip():
                        if len(text.strip()) < len(ocr_text.strip()):
                            text = ocr_text
                        else:
                            # 合并两种结果
                            text += "\n\n===OCR结果===\n\n" + ocr_text
                
                except Exception as ocr_error:
                    print(f"PDF OCR处理错误: {ocr_error}")
            
            # 后处理：修复常见的中文识别问题
            text = text.replace('？', '?').replace('，', ',').replace('：', ':')
            
            # 人工尝试识别关键指标数据
            import re
            
            # 尝试匹配"指标名称：数值"模式
            pattern = r'([a-zA-Z\u4e00-\u9fa5]+)[：:]\s*(\d+\.?\d*)'
            matches = re.findall(pattern, text)
            
            # 如果发现了这种模式，构建更结构化的表示
            if matches:
                structured_part = "\n结构化指标数据：\n"
                for name, value in matches:
                    # 清理名称，去除多余空格
                    clean_name = name.strip()
                    # 对关键指标名称进行特别处理
                    if '攻击' in clean_name:
                        clean_name = '攻击性'
                    elif '自信' in clean_name:
                        clean_name = '自信'
                    elif '能量' in clean_name or '活力' in clean_name:
                        clean_name = '能量'
                    elif '压力' in clean_name:
                        clean_name = '压力'
                    elif '抑郁' in clean_name:
                        clean_name = '抑郁'
                    structured_part += f"{clean_name}: {value}\n"
                
                # 将结构化部分添加到文本末尾
                text += structured_part
                
            # 另一种常见模式："指标名称"+"（数值）"或"[数值]"
            pattern2 = r'([a-zA-Z\u4e00-\u9fa5]+)[\(（\[\【](\d+\.?\d*)[\)）\]\】]'
            matches2 = re.findall(pattern2, text)
            
            if matches2:
                structured_part = "\n括号指标数据：\n"
                for name, value in matches2:
                    # 清理名称
                    clean_name = name.strip()
                    # 对关键指标名称进行特别处理
                    if '攻击' in clean_name:
                        clean_name = '攻击性'
                    elif '自信' in clean_name:
                        clean_name = '自信'
                    elif '能量' in clean_name or '活力' in clean_name:
                        clean_name = '能量'
                    elif '压力' in clean_name:
                        clean_name = '压力'
                    elif '抑郁' in clean_name:
                        clean_name = '抑郁'
                    structured_part += f"{clean_name}: {value}\n"
                
                # 将结构化部分添加到文本末尾
                text += structured_part
                
            # 直接添加常见指标的搜索结果
            indicators = ['攻击性', '自信', '能量', '压力', '抑郁']
            found_indicators = {}
            
            for indicator in indicators:
                # 查找包含指标名称的行
                lines = text.split('\n')
                for line in lines:
                    if indicator in line:
                        # 查找行中的数字
                        numbers = re.findall(r'\d+\.?\d*', line)
                        if numbers:
                            # 使用找到的第一个数字
                            found_indicators[indicator] = numbers[0]
                            break
            
            if found_indicators:
                structured_part = "\n关键指标数据：\n"
                for name, value in found_indicators.items():
                    structured_part += f"{name}: {value}\n"
                text += structured_part
                
            return text
        except Exception as e:
            print(f"PDF解析错误: {str(e)}")
            return f"无法解析PDF文档，请尝试其他格式或重新上传: {str(e)}"
    
    return "不支持的文件格式"

# 添加无意义输入判断函数
def is_meaningless_input(message: str, in_guidance_mode: bool = False) -> bool:
    """判断输入是否无意义（过短或过于简单）
    
    Args:
        message: 用户输入消息
        in_guidance_mode: 是否在引导模式下
        
    Returns:
        bool: 是否无意义
    """
    # 去除空白字符后的消息
    message = message.strip()
    
    # 如果消息为空，一定是无意义的
    if not message:
        return True
    
    # 在引导模式下，只有极短输入（1个字符）才被视为无意义
    # 因为引导模式下用户可能会用简短回复如"是"、"否"、"没有"等
    if in_guidance_mode:
        # 判断是否属于有意义的短回复
        meaningful_short_replies = [
            "是", "否", "好", "嗯", "恩", "对", "不", "行", "要", "哦", "嗯", "啊",
            "有", "无", "没", "可"
        ]
        
        # 如果是长度为1的字符，但在有意义的短回复列表中，不视为无意义
        if len(message) == 1 and message in meaningful_short_replies:
            return False
            
        # 只有长度为1且不在有意义短回复列表中的输入才算无意义
        return len(message) == 1
    
    # 非引导模式下使用原始标准
    # 如果消息太短，可能没有实际意义
    if len(message) < 2:
        return True
        
    # 常见无意义输入
    meaningless_inputs = [
        "你好", "hi", "hello", "嗨", "哈喽", "在吗", "在？", "测试", "test",
        "。", "，", "?", "？", "!", "！", "emmm", "hmm", "啊", "哦", "嗯",
        "666", "233", "haha", "哈哈", "呵呵", "123", "1", "2", "3", "一二三"
    ]
    
    # 检查是否是这些无意义输入
    if message.lower() in meaningless_inputs:
        return True
    
    return False

def generate_topic_suggestions():
    """生成话题建议
    
    当检测到无意义输入时，生成一些可能感兴趣的话题建议
    
    Returns:
        str: 话题建议文本
    """
    # 话题类别
    topic_categories = [
        {
            "category": "日常生活",
            "topics": ["你最近看了什么有趣的电影？", "最近有什么让你开心的事情吗？", "周末有什么计划？"]
        },
        {
            "category": "学习成长",
            "topics": ["最近在学习什么新技能？", "有什么你一直想学但还没开始的事情？", "你最近读了什么书？"]
        },
        {
            "category": "情感关系",
            "topics": ["最近人际关系中有什么烦恼吗？", "有什么事情让你感到困惑？", "与朋友或家人相处有什么有趣的事？"]
        },
        {
            "category": "兴趣爱好",
            "topics": ["你有什么特别的爱好？", "最近有接触什么新的兴趣吗？", "有什么想分享的创意想法？"]
        }
    ]
    
    import random
    # 随机选择两个类别
    selected_categories = random.sample(topic_categories, 2)
    
    # 构建回复
    response = "我注意到你的消息有点简短。如果你想聊天，这里有一些话题建议：\n\n"
    
    for category in selected_categories:
        response += f"**{category['category']}**\n"
        # 从每个类别中选择1-2个话题
        topics = random.sample(category['topics'], random.randint(1, min(2, len(category['topics']))))
        for topic in topics:
            response += f"- {topic}\n"
        response += "\n"
    
    response += "你可以选择一个话题，或者告诉我你想聊些什么！"
    
    return response

# 初始化评估API
assessment_api.init_router(chat_service, extract_text_from_file, is_meaningless_input)
app.include_router(assessment_api.assessment_router, prefix="/api")


# 在应用启动事件中检查并创建必要的目录
@app.on_event("startup")
async def startup_event():
    # 确保数据库已初始化
    await db_manager.init_db()
    
    # 确保所有必要的目录都存在
    ensure_directories_exist()
    
    # 打印启动信息
    print("应用已启动，API服务已就绪")
    
    # 初始化评估API路由
    assessment_api.init_router(
        app_chat_service=chat_service, 
        app_extract_text_fn=extract_text_from_file,
        app_is_meaningless_input_fn=is_meaningless_input
    )
    
    # 确保admin账户存在
    try:
        async with aiosqlite.connect(db_manager.DB_FILE) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT username FROM users WHERE username = ?", ("admin",)) as cursor:
                user = await cursor.fetchone()
                
                if not user:
                    logger.info("系统启动时创建admin账户")
                    register_result = await db_manager.register_user(
                        username="admin",
                        email="admin@example.com",
                        password="123456",
                        profile={
                            "display_name": "管理员",
                            "is_admin": True
                        }
                    )
                    
                    if register_result["success"]:
                        logger.info("Admin账户创建成功")
                    else:
                        logger.error(f"创建admin账户失败: {register_result['message']}")
    except Exception as e:
        logger.error(f"检查admin账户时出错: {str(e)}")
        import traceback
        traceback.print_exc()

# 添加确保目录存在的函数
def ensure_directories_exist():
    """确保应用需要的所有目录都存在"""
    # 创建保存目录
    os.makedirs("save", exist_ok=True)
    
    # 创建自定义智能体目录
    os.makedirs("save/custom_agents", exist_ok=True)
    
    # 创建临时上传目录
    os.makedirs("temp_uploads", exist_ok=True)
    
    # 创建日志目录
    os.makedirs("save/log", exist_ok=True)
    
    # 创建用户目录
    os.makedirs("save/users", exist_ok=True)
    
    # 创建记忆存储目录
    os.makedirs("save/memory", exist_ok=True)
    
    # 创建评估目录
    os.makedirs("save/assessments", exist_ok=True)
    
    print("所有必要的目录已创建")

# 确保保存自定义角色的目录存在
CUSTOM_AGENTS_DIR = "save/custom_agents"
TEMP_UPLOADS_DIR = "temp_uploads"
os.makedirs(CUSTOM_AGENTS_DIR, exist_ok=True)
os.makedirs(TEMP_UPLOADS_DIR, exist_ok=True)

# 删除自定义Agent语音目录
# CUSTOM_VOICE_DIR = os.path.join("save", "custom_voice")
# 确保目录存在
# os.makedirs(CUSTOM_VOICE_DIR, exist_ok=True)

@app.post("/api/extract_agent_info")
async def extract_agent_info(file: UploadFile = File(...)):
    """从上传的文件中提取Agent信息
    
    Args:
        file: 上传的文件
        
    Returns:
        dict: 包含提取结果的响应
    """
    try:
        # 检查文件类型
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in ['.txt', '.pdf', '.doc', '.docx']:
            return JSONResponse(
                content={
                    "success": False,
                    "message": "不支持的文件格式，仅支持txt、pdf、doc、docx"
                }
            )
        
        # 保存上传的文件
        temp_file_path = os.path.join(TEMP_UPLOADS_DIR, f"{uuid.uuid4()}{file_extension}")
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 提取文本内容
        file_content = extract_text_from_file(temp_file_path, file_extension)
        
        if not file_content or file_content == "不支持的文件格式":
            return JSONResponse(
                content={
                    "success": False,
                    "message": "文件内容提取失败或文件为空"
                }
            )
            
        # 使用chat_service中的LLM服务提取角色信息
        prompt = f"""请从以下文本中提取出一个可能的角色描述信息，包括：
1. 角色名称 (name)
2. 性格特征 (personality)
3. 兴趣爱好 (interests)
4. 生活习惯 (lifestyle)
5. 价值观 (values)
6. 角色标签 (tags)：请从这些词中选择最多4个最符合角色特点的标签：温柔体贴、阳光活泼、冷酷高傲、知性优雅、单纯天真、幽默风趣、古灵精怪、深沉内敛、率真直爽、浪漫多情、神秘莫测、坚毅果断、温暖治愈、机智敏锐、傲娇可爱

如果某些信息无法从文本中提取，可以留空。
请以JSON格式返回结果，如：
{{
  "name": "...",
  "personality": "...",
  "interests": "...",
  "lifestyle": "...",
  "values": "...",
  "tags": ["标签1", "标签2", ...]
}}

文本内容：
{file_content[:2000]}  # 限制文本长度
"""
        
        # 使用chat_service中的llm_service
        response = await chat_service.llm_service.async_chat(prompt)
        
        # 尝试解析LLM返回的JSON
        try:
            # 从回复中提取JSON部分
            start_index = response.find('{')
            end_index = response.rfind('}') + 1
            
            if start_index >= 0 and end_index > start_index:
                json_str = response[start_index:end_index]
                agent_info = json.loads(json_str)
                
                # 移除临时文件
                os.remove(temp_file_path)
                
                return JSONResponse(
                    content={
                        "success": True,
                        "name": agent_info.get("name", ""),
                        "personality": agent_info.get("personality", ""),
                        "interests": agent_info.get("interests", ""),
                        "lifestyle": agent_info.get("lifestyle", ""),
                        "values": agent_info.get("values", ""),
                        "tags": agent_info.get("tags", [])
                    }
                )
            else:
                raise ValueError("无法在回复中找到JSON格式数据")
                
        except Exception as e:
            print(f"解析LLM回复失败: {e}")
            print(f"LLM回复内容: {response}")
            
            # 移除临时文件
            os.remove(temp_file_path)
            
            return JSONResponse(
                content={
                    "success": False,
                    "message": f"解析文件信息失败: {str(e)}"
                }
            )
            
    except Exception as e:
        print(f"处理上传文件失败: {e}")
        return JSONResponse(
            content={
                "success": False,
                "message": f"处理文件失败: {str(e)}"
            }
        )

@app.post("/api/create_custom_agent")
async def create_custom_agent(request: CustomAgentRequest):
    """创建自定义角色
    
    Args:
        request: 角色信息
        
    Returns:
        dict: 包含创建结果的响应
    """
    try:
        # 生成唯一ID
        agent_id = f"custom_{uuid.uuid4().hex[:8]}"
        
        # 创建角色配置文件
        agent_config = {
            "id": agent_id,
            "name": request.name,
            "description": request.description,
            "model": request.model,
            "personality": request.personality,
            "interests": request.interests,
            "lifestyle": request.lifestyle,
            "values": request.values
        }
        
        with open(os.path.join(CUSTOM_AGENTS_DIR, f"{agent_id}.json"), "w", encoding="utf-8") as f:
            json.dump(agent_config, f, ensure_ascii=False, indent=2)
        
        # 先只写入角色基本信息
        agent_file_path = os.path.join(CUSTOM_AGENTS_DIR, f"{agent_id}.txt")
        with open(agent_file_path, "w", encoding="utf-8") as f:
            f.write(f"""你是一个名为{request.name}的角色。
{request.description}

性格特征：
{request.personality}

兴趣爱好：
{request.interests}

生活习惯：
{request.lifestyle}

价值观：
{request.values}
""")
        
        # 先尝试从nanaA.txt读取任务规则部分
        template_paths = ["prompts/nanaA.txt", "prompts/prompt_template.txt"]
        task_rules = None
        
        for template_path in template_paths:
            try:
                if os.path.exists(template_path):
                    with open(template_path, "r", encoding="utf-8") as template_file:
                        template_content = template_file.read()
                        
                        # 查找任务规则的起始位置
                        task_input_pos = template_content.find("任务输入:")
                        if task_input_pos > 0:
                            # 提取任务规则部分
                            task_rules = template_content[task_input_pos:]
                            break  # 找到有效模板即退出循环
            except Exception as e:
                print(f"读取模板 {template_path} 失败: {e}")
        
        # 如果找到了有效的任务规则，追加到角色文件中
        if task_rules:
            with open(agent_file_path, "a", encoding="utf-8") as agent_file:
                agent_file.write("\n" + task_rules)
        else:
            # 使用硬编码的任务规则作为后备方案 - 使用原始字符串避免处理大括号
            with open(agent_file_path, "a", encoding="utf-8") as agent_file:
                agent_file.write(r"""
任务输入:
用户的个人信息：
{user_info}

对话记录：
{chat_history}

用户的最新问题：
{user_message}

相关记忆：
{memory}

任务输出:
1. 回复内容
2. 表情
3. 用户个人信息（仅在用户明确提供新信息时才更新）

回复规则：
1. 对于普通对话，回复控制在15字以内
2. 对于快捷提问类别（如情感咨询师、人际关系等），需要提供专业且详细的回答，字数不限
3. 根据历史对话记录和补充信息回答问题
4. 当用户使用快捷提问类别且有相关的用户信息时，请根据这些信息提供个性化的专业建议
5. 提供建议时，仅关注解决方案和专业分析，不要在建议中附加引导用户做决策的问题
6. 当用户回复了决策（如"我决定原谅他"、"我选择继续努力"等）时，应立即更新相关用户信息，反映用户的最新选择和态度变化
7. 当用户回复或输入无意义的数字、不连贯的词组语句时，直接丢弃，不进入回复逻辑，过滤无意义内容

用户个人信息处理规则：
1. 当用户明确提供新的个人信息，或对建议做出选择和决策时，在输出中包含"user_info"字段
2. 如果用户没有提供新信息或没有做出明确决策，请勿包含"user_info"字段
3. 新的个人信息应该保持原有格式，不要随意添加不确定的信息
4. 当用户做出决策后，应更新相关的用户信息部分，如修改"最近状况"中的相关条目，反映用户的新选择

表情规则：
在以下表情选一个表情符合回复的内容
吐舌,黑脸,眼泪,脸红,nn眼,生气瘪嘴,死鱼眼,生气,咪咪眼,嘟嘴,钱钱眼,爱心,泪眼

输出格式：
必须输出以下JSON格式（仅在有新用户信息时才包含user_info字段）：
{{
  "reply": "<回答内容>",
  "expression": "<表情>"
}}

或者当用户提供了新的个人信息或做出了决策时：
{{
  "reply": "<回答内容>",
  "expression": "<表情>",
  "user_info": "<用户个人信息>"
}} """)
            
        return JSONResponse(
            content={
                "success": True,
                "message": f"成功创建角色 {request.name}",
                "agent_id": agent_id
            }
        )
    except Exception as e:
        print(f"创建自定义角色失败: {e}")
        return JSONResponse(
            content={
                "success": False,
                "message": f"创建角色失败: {str(e)}"
            }
        )

@app.get("/api/list_custom_agents")
async def list_custom_agents():
    """获取所有自定义角色列表
    
    Returns:
        dict: 包含自定义角色列表的响应
    """
    try:
        agents = []
        if not os.path.exists(CUSTOM_AGENTS_DIR):
            return JSONResponse(
                content={
                    "success": True,
                    "agents": []
                }
            )
            
        for filename in os.listdir(CUSTOM_AGENTS_DIR):
            if filename.endswith(".json"):
                try:
                    # 过滤掉外部智能体（从话题广场获取的智能体）
                    # 外部智能体的文件名格式为: custom_external_{agent_id}.json
                    if "external_" in filename:
                        print(f"跳过外部智能体: {filename}")
                        continue
                    
                    with open(os.path.join(CUSTOM_AGENTS_DIR, filename), "r", encoding="utf-8") as f:
                        agent_config = json.load(f)
                        # 确保agent_config包含所有必要字段
                        required_fields = ["id", "name", "description", "model", 
                                          "personality", "interests", "lifestyle", "values"]
                        for field in required_fields:
                            if field not in agent_config:
                                agent_config[field] = ""
                        agents.append(agent_config)
                except Exception as e:
                    print(f"读取自定义角色配置文件失败: {filename}, 错误: {e}")
        
        return JSONResponse(
            content={
                "success": True,
                "agents": agents
            }
        )
    except Exception as e:
        print(f"获取自定义角色列表失败: {e}")
        return JSONResponse(
            content={
                "success": False,
                "message": f"获取角色列表失败: {str(e)}"
            }
        )

@app.put("/api/update_custom_agent/{agent_id}")
async def update_custom_agent(agent_id: str, request: CustomAgentRequest):
    """更新自定义角色
    
    Args:
        agent_id: 角色ID
        request: 更新后的角色信息
        
    Returns:
        dict: 包含更新结果的响应
    """
    try:
        # 检查是否是自定义角色
        if not agent_id.startswith("custom_"):
            return JSONResponse(
                content={
                    "success": False,
                    "message": "只能更新自定义角色"
                }
            )
        
        # 检查是否是外部智能体（从话题广场获取的）
        if "external_" in agent_id:
            return JSONResponse(
                content={
                    "success": False,
                    "message": "外部智能体不能修改，它们由话题广场管理"
                }
            )
            
        # 检查角色是否存在
        config_path = os.path.join(CUSTOM_AGENTS_DIR, f"{agent_id}.json")
        if not os.path.exists(config_path):
            return JSONResponse(
                content={
                    "success": False,
                    "message": "角色不存在"
                }
            )
            
        # 更新角色配置文件
        agent_config = {
            "id": agent_id,
            "name": request.name,
            "description": request.description,
            "model": request.model,
            "personality": request.personality,
            "interests": request.interests,
            "lifestyle": request.lifestyle,
            "values": request.values
        }
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(agent_config, f, ensure_ascii=False, indent=2)
        
        # 读取现有的提示词文件，保留任务规则部分
        prompt_path = os.path.join(CUSTOM_AGENTS_DIR, f"{agent_id}.txt")
        task_rules = ""
        
        if os.path.exists(prompt_path):
            try:
                with open(prompt_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # 查找任务规则的起始位置
                    task_input_pos = content.find("任务输入:")
                    if task_input_pos > 0:
                        # 提取任务规则部分
                        task_rules = content[task_input_pos:]
            except Exception as e:
                print(f"读取现有提示词文件失败: {e}")
                # 如果读取失败，尝试从固定模板中读取
                template_paths = ["prompts/nanaA.txt", "prompts/prompt_template.txt"]
                for template_path in template_paths:
                    try:
                        if os.path.exists(template_path):
                            with open(template_path, "r", encoding="utf-8") as template_file:
                                template_content = template_file.read()
                                
                                # 查找任务规则的起始位置
                                task_input_pos = template_content.find("任务输入:")
                                if task_input_pos > 0:
                                    # 提取任务规则部分
                                    task_rules = template_content[task_input_pos:]
                                    break  # 找到有效模板即退出循环
                    except Exception as template_error:
                        print(f"读取模板 {template_path} 失败: {template_error}")
                
                # 如果仍然没有找到有效的任务规则，使用硬编码的后备方案
                if not task_rules:
                    task_rules = r"""任务输入:
用户的个人信息：
{user_info}

对话记录：
{chat_history}

用户的最新问题：
{user_message}

相关记忆：
{memory}

任务输出:
1. 回复内容
2. 表情
3. 用户个人信息（仅在用户明确提供新信息时才更新）

回复规则：
1. 对于普通对话，回复控制在15字以内
2. 对于快捷提问类别（如情感咨询师、人际关系等），需要提供专业且详细的回答，字数不限
3. 根据历史对话记录和补充信息回答问题
4. 当用户使用快捷提问类别且有相关的用户信息时，请根据这些信息提供个性化的专业建议
5. 提供建议时，仅关注解决方案和专业分析，不要在建议中附加引导用户做决策的问题
6. 当用户回复了决策（如"我决定原谅他"、"我选择继续努力"等）时，应立即更新相关用户信息，反映用户的最新选择和态度变化
7. 当用户回复或输入无意义的数字、不连贯的词组语句时，直接丢弃，不进入回复逻辑，过滤无意义内容

用户个人信息处理规则：
1. 当用户明确提供新的个人信息，或对建议做出选择和决策时，在输出中包含"user_info"字段
2. 如果用户没有提供新信息或没有做出明确决策，请勿包含"user_info"字段
3. 新的个人信息应该保持原有格式，不要随意添加不确定的信息
4. 当用户做出决策后，应更新相关的用户信息部分，如修改"最近状况"中的相关条目，反映用户的新选择

表情规则：
在以下表情选一个表情符合回复的内容
吐舌,黑脸,眼泪,脸红,nn眼,生气瘪嘴,死鱼眼,生气,咪咪眼,嘟嘴,钱钱眼,爱心,泪眼

输出格式：
必须输出以下JSON格式（仅在有新用户信息时才包含user_info字段）：
{{
  "reply": "<回答内容>",
  "expression": "<表情>"
}}

或者当用户提供了新的个人信息或做出了决策时：
{{
  "reply": "<回答内容>",
  "expression": "<表情>",
  "user_info": "<用户个人信息>"
}}"""
                
        # 更新角色提示词文件，保留任务规则部分
        with open(prompt_path, "w", encoding="utf-8") as f:
            # 写入角色基本信息
            f.write(f"""你是一个名为{request.name}的角色。
{request.description}

性格特征：
{request.personality}

兴趣爱好：
{request.interests}

生活习惯：
{request.lifestyle}

价值观：
{request.values}

""")
            # 追加任务规则部分
            f.write(task_rules)
            
        return JSONResponse(
            content={
                "success": True,
                "message": f"成功更新角色 {request.name}"
            }
        )
    except Exception as e:
        print(f"更新自定义角色失败: {e}")
        return JSONResponse(
            content={
                "success": False,
                "message": f"更新角色失败: {str(e)}"
            }
        )

@app.delete("/api/delete_custom_agent/{agent_id}")
async def delete_custom_agent(agent_id: str):
    """删除自定义角色
    
    Args:
        agent_id: 角色ID
        
    Returns:
        dict: 包含删除结果的响应
    """
    try:
        # 检查是否是自定义角色
        if not agent_id.startswith("custom_"):
            return JSONResponse(
                content={
                    "success": False,
                    "message": "只能删除自定义角色"
                }
            )
        
        # 检查是否是外部智能体（从话题广场获取的）
        if "external_" in agent_id:
            return JSONResponse(
                content={
                    "success": False,
                    "message": "外部智能体不能通过此接口删除，请在话题广场中退出使用即可"
                }
            )
            
        # 删除配置文件
        config_path = os.path.join(CUSTOM_AGENTS_DIR, f"{agent_id}.json")
        if os.path.exists(config_path):
            os.remove(config_path)
            
        # 删除提示词文件
        prompt_path = os.path.join(CUSTOM_AGENTS_DIR, f"{agent_id}.txt")
        if os.path.exists(prompt_path):
            os.remove(prompt_path)
            
        return JSONResponse(
            content={
                "success": True,
                "message": f"成功删除角色 {agent_id}"
            }
        )
    except Exception as e:
        print(f"删除自定义角色失败: {e}")
        return JSONResponse(
            content={
                "success": False,
                "message": f"删除角色失败: {str(e)}"
            }
        )

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    旧的非流式聊天API，已被弃用
    重定向到stream_chat接口
    """
    return JSONResponse(
        content={
            "message": "此接口已弃用，请使用/api/stream_chat",
            "success": False,
            "error": "API_DEPRECATED"
        },
        status_code=410  # Gone
    )

@app.post("/api/stream_chat")
async def stream_chat(request: ChatRequest):
    """流式聊天API，支持打字机式回复
    
    Args:
        request: 聊天请求参数
        
    Returns:
        StreamingResponse: 流式响应
    """
    async def generate_stream_response():
        """内部异步生成器函数，用于生成流式响应内容"""
        global client
        
        # 打印请求内容以进行调试
        print(f"\n{'='*80}")
        print(f"[stream_chat] 收到新请求")
        print(f"消息内容: {request.message}")
        print(f"会话ID: {request.session_id}")
        print(f"智能体类型: {request.agent_type}")
        print(f"是否快捷提问: {request.is_category}")
        print(f"{'='*80}\n")
        
        # 检查是否是无意义输入
        message_for_processing = request.message
        # 获取当前引导模式状态
        in_guidance_mode = chat_service.guidance_state["is_guiding"]

        # 在检测无意义输入时传递引导模式状态
        if is_meaningless_input(request.message, in_guidance_mode):
            if in_guidance_mode:
                # 在引导模式下，不替换为话题建议，而是发送一个特殊指令让模型继续相关主题的问题
                print(f"检测到引导模式下的无意义输入：{request.message}，转换为主题相关提问")
                message_for_processing = "SYSTEM_CONTINUE_GUIDANCE"
            else:
                # 在普通模式下，依然替换为话题建议请求
                print(f"检测到无意义输入：{request.message}，替换为话题建议请求")
                message_for_processing = "SYSTEM_TOPIC_SUGGESTIONS"
        
        # 删除F5-TTS相关代码
        use_f5_tts = False
        
        # 检查是否强制指定了引导模式状态
        forced_guidance_mode = getattr(request, 'in_guidance_mode', None)
        
        # 确定正确的引导状态 - 简化逻辑
        if forced_guidance_mode is not None:
            # 如果前端明确指定了引导模式状态，使用它
            print(f"前端明确指定了引导模式状态: {forced_guidance_mode}")
            
            if forced_guidance_mode:
                # 如果前端指示处于引导模式，确保后端状态同步
                if not chat_service.guidance_state["is_guiding"]:
                    print("前端指示处于引导模式，但后端状态未记录，更新后端状态")
                    chat_service.guidance_state["is_guiding"] = True
                    chat_service.guidance_state["category"] = request.message
                    chat_service.guidance_state["last_update_time"] = time.time()
                current_is_category = True
            else:
                # 如果前端明确指示不在引导模式，重置后端状态
                if chat_service.guidance_state["is_guiding"]:
                    print("前端指示不处于引导模式，重置引导状态")
                    chat_service._reset_guidance_state()
                current_is_category = False
        else:
            # 前端未指定引导模式状态，检查后端当前状态和消息内容
            
            # 检查是否是快捷提问类别 - 开始新引导
            is_quick_question = request.is_category or request.message in [
                "情感咨询师", "人际关系", "学业问题", "就业与职业规划压力", 
                "精神健康障碍", "自我认同与价值观冲突", "突发事件与危机情景"
            ]
            
            # 检查是否是明确的结束引导指令
            is_end_command = any(cmd in request.message for cmd in [
                "结束话题", "退出话题", "返回主菜单", "结束引导", "退出引导"
            ])
            
            # 简化判断逻辑：
            # 1. 如果是快捷提问类别，开始新引导
            # 2. 如果是明确的结束指令且当前在引导模式中，结束引导
            # 3. 其他情况保持当前状态
            if is_quick_question and not chat_service.guidance_state["is_guiding"]:
                # 开始新的引导
                print(f"检测到快捷提问类别: {request.message}，开始引导模式")
                chat_service.guidance_state["is_guiding"] = True
                chat_service.guidance_state["category"] = request.message
                chat_service.guidance_state["last_update_time"] = time.time()
                current_is_category = True
            elif is_end_command and chat_service.guidance_state["is_guiding"]:
                # 结束当前引导
                print(f"检测到结束引导指令: {request.message}，结束引导模式")
                chat_service._reset_guidance_state()
                current_is_category = False
            else:
                # 保持当前状态
                current_is_category = chat_service.guidance_state["is_guiding"]
                print(f"保持当前引导模式状态: {'处于引导模式中' if current_is_category else '非引导模式'}")
        
        # 打印最终决定的引导模式状态
        print(f"最终决定的引导模式状态: is_category={current_is_category}, 当前后端状态: is_guiding={chat_service.guidance_state['is_guiding']}")
        
        # 在引导模式下，强制使用xinli_agent (心理医生)而不是用户指定的agent
        agent_type = request.agent_type
        if current_is_category:
            print("检测到处于引导模式中，使用心理医生agent(xinli_agent)")
            agent_type = "xinli_agent"  # 强制使用心理医生agent
        
        # 【优化】使用流式生成来避免长时间等待
        print(f"[流式生成] 开始生成回复...")
        
        # 先发送开始指示
        yield json.dumps({"type": "start", "content": ""}) + "\n"
        
        # 准备流式生成所需的上下文信息
        # 切换智能体（如果需要）
        if agent_type:
            print(f"[流式生成] 切换智能体到: {agent_type}")
            chat_service.change_agent(agent_type, request.session_id)
        
        # 获取对话上下文和记忆
        print(f"[流式生成] 获取对话上下文和记忆...")
        context = chat_service.conversation_history.get_context()
        if current_is_category:
            memory_text = chat_service.main_agent._get_relevant_category_memories(message_for_processing)
        else:
            memory_text = chat_service.main_agent._get_relevant_memories(message_for_processing)
        
        print(f"[流式生成] 相关记忆: {memory_text if memory_text != '无补充信息' else '无'}")
        
        # 构建prompt
        prompt = chat_service.main_agent.prompt.format(
            user_info=chat_service.main_agent.user_info_processor.user_info if chat_service.main_agent.user_info_processor else "",
            chat_history=context,
            user_message=message_for_processing,
            memory=memory_text
        )
        
        print(f"[流式生成] 提示词已构建，长度: {len(prompt)} 字符")
        print(f"[流式生成] 调用LLM流式API...")
        
        # 使用流式API生成回复
        accumulated_response = ""
        in_think_tag = False
        json_buffer = ""
        response_text = ""
        extracted_expression = None
        is_summary = False
        
        try:
            # 调用LLM的流式生成API
            max_tokens = 2048 if current_is_category else 500
            print(f"[流式生成] LLM参数: max_tokens={max_tokens}, temperature={0.7 if current_is_category else 0.9}")
            
            chunk_count = 0
            async for chunk in chat_service.main_agent.llm_service.generate_streaming(
                prompt, 
                temperature=0.7 if current_is_category else 0.9,
                max_tokens=max_tokens
            ):
                chunk_count += 1
                if chunk_count == 1:
                    print(f"[流式生成] 开始接收LLM响应流...")
                
                accumulated_response += chunk
                
                # 检测并过滤 <think> 标签中的内容
                while True:
                    if not in_think_tag:
                        # 查找 <think> 开始标签
                        think_start = accumulated_response.find("<think>")
                        if think_start != -1:
                            # 发送 <think> 之前的内容
                            before_think = accumulated_response[:think_start]
                            if before_think:
                                json_buffer += before_think
                            accumulated_response = accumulated_response[think_start + 7:]  # 跳过 <think>
                            in_think_tag = True
                        else:
                            # 没有找到 <think>，处理当前内容
                            json_buffer += accumulated_response
                            accumulated_response = ""
                            break
                    else:
                        # 查找 </think> 结束标签
                        think_end = accumulated_response.find("</think>")
                        if think_end != -1:
                            # 跳过 <think>...</think> 中的内容
                            accumulated_response = accumulated_response[think_end + 8:]  # 跳过 </think>
                            in_think_tag = False
                        else:
                            # 还没有找到结束标签，继续等待
                            accumulated_response = ""
                            break
                
                # 尝试解析JSON（如果有完整的JSON）
                if json_buffer and not in_think_tag:
                    # 检查是否有完整的JSON
                    if '{' in json_buffer and '}' in json_buffer:
                        try:
                            # 尝试提取JSON
                            start_idx = json_buffer.find('{')
                            end_idx = json_buffer.rfind('}') + 1
                            if start_idx != -1 and end_idx > start_idx:
                                json_str = json_buffer[start_idx:end_idx]
                                parsed_json = json.loads(json_str)
                                
                                # 提取reply字段作为要显示的文本
                                if 'reply' in parsed_json:
                                    new_text = parsed_json['reply']
                                    # 发送新增的文本部分
                                    if len(new_text) > len(response_text):
                                        new_chars = new_text[len(response_text):]
                                        for char in new_chars:
                                            yield json.dumps({"type": "content", "content": char}) + "\n"
                                        response_text = new_text
                                    
                                    # 提取其他字段
                                    if 'expression' in parsed_json and not extracted_expression:
                                        extracted_expression = parsed_json['expression']
                                    if 'is_summary' in parsed_json:
                                        is_summary = parsed_json['is_summary']
                                
                                # 清空已处理的JSON
                                json_buffer = json_buffer[end_idx:]
                        except json.JSONDecodeError:
                            # JSON还不完整，继续累积
                            pass
            
            # 流式生成完毕，处理剩余的buffer
            if json_buffer.strip():
                # 如果buffer中还有内容但没有被解析为JSON，尝试最后一次解析
                try:
                    # 清理buffer
                    cleaned = json_buffer.strip()
                    if cleaned.startswith('{') and cleaned.endswith('}'):
                        parsed_json = json.loads(cleaned)
                        if 'reply' in parsed_json:
                            final_text = parsed_json['reply']
                            if len(final_text) > len(response_text):
                                new_chars = final_text[len(response_text):]
                                for char in new_chars:
                                    yield json.dumps({"type": "content", "content": char}) + "\n"
                                response_text = final_text
                            if 'expression' in parsed_json and not extracted_expression:
                                extracted_expression = parsed_json['expression']
                            if 'is_summary' in parsed_json:
                                is_summary = parsed_json['is_summary']
                except:
                    # 如果最终也无法解析，将buffer作为纯文本发送
                    if json_buffer and not response_text:
                        for char in json_buffer:
                            yield json.dumps({"type": "content", "content": char}) + "\n"
                        response_text = json_buffer
        
        except Exception as e:
            print(f"流式生成过程中出错: {e}")
            import traceback
            traceback.print_exc()
            error_msg = "抱歉，生成回复时遇到了问题。"
            for char in error_msg:
                yield json.dumps({"type": "content", "content": char}) + "\n"
            response_text = error_msg
        
        print(f"\n[流式生成] ✅ 完成!")
        print(f"[流式生成] 最终回复长度: {len(response_text)} 字符")
        print(f"[流式生成] 回复内容预览: {response_text[:100]}...")
        
        # 更新表情（如果有）
        if extracted_expression:
            chat_service.main_agent.expression = extracted_expression
            print(f"[流式生成] 表情: {extracted_expression}")
            # 发送表情数据
            yield json.dumps({
                "type": "metadata", 
                "expression": extracted_expression
            }) + "\n"
        
        # 检查是否应该结束引导（仅在引导模式下）
        if is_summary and chat_service.guidance_state["is_guiding"]:
            print("[引导模式] 检测到引导结束标记，重置引导状态")
            chat_service._reset_guidance_state()
        
        # 将助手的回复添加到对话历史中
        try:
            if request.message != "SYSTEM_GUIDANCE" and not request.message.startswith("SYSTEM_"):
                # 只有普通对话才添加到历史记录，系统消息不添加
                await chat_service.conversation_history.add_dialog(request.message, response_text)
                print(f"[对话历史] 已添加，当前轮数: {len(chat_service.conversation_history.turns)}")
        except Exception as e:
            print(f"[错误] 添加对话历史失败: {e}")
        
        # 发送结束指示
        print(f"[流式生成] 发送结束标记\n{'='*80}\n")
        yield json.dumps({"type": "end", "content": ""}) + "\n"
        
        # 【后台异步生成TTS音频】
        # 注意：音频生成会在后台进行，不阻塞响应
        # 这里我们不等待音频，因为流式响应已经完成
        
    # 返回流式响应
    return StreamingResponse(generate_stream_response(), media_type="text/event-stream")

@app.post("/api/change_agent")
async def change_agent(request: AgentRequest):
    success = chat_service.change_agent(request.agent_name, request.session_id)
    return JSONResponse(
        content={
            "success": success,
            "message": f"已切换到{request.agent_name}" if success else "切换失败，请检查智能体名称"
        }
    )

@app.post("/speech-to-text")
async def speech_to_text(audio: UploadFile = File(...)):
    """处理语音识别请求
    
    Args:
        audio: 上传的音频文件
        
    Returns:
        dict: 包含识别结果的响应
    """
    try:
        # 读取音频数据
        audio_data = await audio.read()
        
        # 调用语音识别服务
        text = await speech_service.process_audio(audio_data)
        
        return {"success": True, "text": text}
    except Exception as e:
        print(f"语音识别处理失败: {e}")
        return {"success": False, "error": str(e)}

@app.websocket("/chat")
async def chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            
            if data["type"] == "message":
                # 处理文本消息
                response_text, audio_data = await chat_service.get_response(
                    data["content"],
                    data.get("personality"),
                    session_id=data.get("session_id", "default"),
                    user_id=data.get("user_id", "default_user")
                )
                
                # 处理JSON格式回复
                if isinstance(response_text, str) and response_text.strip().startswith('{') and response_text.strip().endswith('}'):
                    try:
                        # 尝试解析JSON
                        response_json = json.loads(response_text)
                        if 'reply' in response_json:
                            # 只取reply字段的内容
                            response_text = response_json['reply']
                            print("WebSocket: 从JSON响应中提取reply字段")
                    except json.JSONDecodeError:
                        # 解析失败，保持原样
                        print("WebSocket: JSON解析失败，保持原始回复内容")
                
                # 构建响应
                response = {
                    "text": response_text,
                    "audio": base64.b64encode(audio_data).decode('ascii') if audio_data and len(audio_data) > 100 else "",
                    "expression": "咪咪眼"  # 默认表情
                }
                
                await websocket.send_json(response)
                
            elif data["type"] == "switch_user":
                # 处理用户切换
                username = data.get("username", "")
                session_id = data.get("session_id", "")
                
                if username and session_id:
                    success = await chat_service.switch_user(username, session_id)
                    await websocket.send_json({
                        "type": "switch_user_result",
                        "success": success,
                        "message": f"已切换到用户: {username}" if success else "切换用户失败"
                    })
                
    except Exception as e:
        print(f"WebSocket错误: {e}")
        traceback.print_exc()
    finally:
        await websocket.close()

async def normal_chat_flow(request: ChatRequest):
    """正常的聊天流程
    
    Args:
        request: 聊天请求
        
    Returns:
        dict: 聊天响应
    """
    
    # 在对话处理前，检查消息是否有效，如果无效则返回话题建议
    if is_meaningless_input(request.message):
        print(f"检测到无意义输入：{request.message}，返回话题建议")
        
        # 生成话题建议
        suggestion_text = generate_topic_suggestions()
        
        # 生成语音（如果启用）
        audio_base64 = ''
        if Config.is_tts_enabled() and chat_service.tts_service:
            try:
                audio_data = chat_service.tts_service.generate_audio(suggestion_text)
                if audio_data and len(audio_data) > 100:
                    audio_base64 = base64.b64encode(audio_data).decode('ascii')
            except Exception as e:
                print(f"为话题建议生成语音时出错: {e}")
        
        return JSONResponse(
            content={
                "message": suggestion_text,
                "audio": audio_base64,
                "expression": "咪咪眼",
                "use_f5_tts": False
            }
        )
    
    # 有效消息才增加计数  
    assessment_api.increment_dialog_counter(request.message)
    
    # 检查是否强制指定了引导模式状态
    forced_guidance_mode = getattr(request, 'in_guidance_mode', None)
    
    # 确定当前是否处于引导模式
    if forced_guidance_mode is not None:
        print(f"前端明确指定了引导模式状态: {forced_guidance_mode}")
        # 如果前端指定了模式，使用它
        if forced_guidance_mode:
            # 如果不是主动设置引导模式但前端传递了引导模式状态，确保后端状态同步
            if not chat_service.guidance_state["is_guiding"]:
                print("前端指示处于引导模式，但后端状态未记录，更新后端状态")
                chat_service.guidance_state["is_guiding"] = True
                chat_service.guidance_state["category"] = request.message
                chat_service.guidance_state["last_update_time"] = time.time()
            is_category = True
        else:
            # 如果前端强制关闭引导模式，重置状态
            if chat_service.guidance_state["is_guiding"]:
                print("前端指示不处于引导模式，但后端状态记录中，重置引导状态")
                chat_service._reset_guidance_state()
            is_category = False
    else:
        # 前端未指定引导模式状态，使用当前状态
        # 检查是否是快捷提问类别
        is_quick_question = request.is_category or request.message in [
            "情感咨询师", "人际关系", "学业问题", "就业与职业规划压力", 
            "精神健康障碍", "自我认同与价值观冲突", "突发事件与危机情景"
        ]
        
        # 如果是快捷提问，开始新的引导
        if is_quick_question and not chat_service.guidance_state["is_guiding"]:
            print("检测到快捷提问类别，开始新的引导会话")
            chat_service.guidance_state["is_guiding"] = True
            chat_service.guidance_state["category"] = request.message
            chat_service.guidance_state["last_update_time"] = time.time()
            is_category = True
        else:
            # 否则，保持当前状态
            # 关键：保持当前后端记录的引导状态，而不是使用请求的状态
            current_is_category = chat_service.guidance_state["is_guiding"]
            if current_is_category:
                print("保持当前引导模式状态: 处于引导模式中")
    
    print(f"最终决定的引导模式状态: is_category={is_category}, 当前后端状态: is_guiding={chat_service.guidance_state['is_guiding']}")
    
    # 在引导模式下，强制使用xinli_agent (心理医生)而不是用户指定的agent
    agent_type = request.agent_type
    if is_category:
        print("检测到处于引导模式中，使用心理医生agent(xinli_agent)")
        agent_type = "xinli_agent"  # 强制使用心理医生agent
    
    # 对话流程处理
    reply, audio_data = await chat_service.generate_reply(
        message=request.message,
        session_id=request.session_id,
        agent_type=agent_type,  # 使用可能被覆盖的agent_type
        personality=request.personality,
        is_category=is_category
    )
    
    # 增加原始回复日志以便调试
    print("-- /api/chat --")
    print("agent_type:", request.agent_type)
    print("personality:", request.personality)
    print("is_category:", is_category)
    print("原始回复:", reply)
    
    # 处理JSON格式回复，提取reply字段
    processed_reply, expression, is_summary = process_json_response(reply)
    
    # 优先使用处理后的内容
    if processed_reply:
        print(f"处理后的纯文本回复: {processed_reply}")
        reply = processed_reply
    else:
        # 即使process_json_response未识别出JSON，也再次检查是否为JSON格式
        if isinstance(reply, str) and reply.strip().startswith('{') and reply.strip().endswith('}'):
            try:
                # 尝试解析JSON
                reply_json = json.loads(reply)
                if 'reply' in reply_json:
                    # 只取reply字段的内容
                    reply = reply_json['reply']
                    print("额外检查：从JSON响应中提取reply字段")
                    
                    # 如果JSON中有表情信息，保存
                    if 'expression' in reply_json:
                        expression = reply_json['expression']
                        print(f"额外检查：从JSON中提取表情: {expression}")
            except json.JSONDecodeError:
                # 解析失败，保持原样
                print("额外JSON检查失败，保持原始回复内容")
    
    # 如果检测到引导结束标记，重置引导状态
    if is_summary and chat_service.guidance_state["is_guiding"]:
        print("在normal_chat_flow中检测到引导结束标记，重置引导状态")
        chat_service._reset_guidance_state()
    
    # 移除F5-TTS相关代码
    use_f5_tts = False
    
    # 处理音频数据
    audio_base64 = ''
    if audio_data and len(audio_data) > 100:
        audio_base64 = base64.b64encode(audio_data).decode('ascii')
    
    # 确保回复是纯文本，不再包含JSON格式
    response_data = {
        "message": reply,  # 处理后的纯文本回复
        "audio": audio_base64,
        "expression": expression or "咪咪眼", # 提供默认表情
        "use_f5_tts": use_f5_tts  # 保留字段但设为False
    }
    
    # 如果有引导决策消息，添加到响应中
    if hasattr(chat_service.main_agent.conversation_history, 'last_guidance_message'):
        guidance_message = chat_service.main_agent.conversation_history.last_guidance_message
        # 处理引导消息中可能包含的JSON
        guidance_text, guidance_expression, _ = process_json_response(guidance_message)
        response_data["guidance_message"] = guidance_text or guidance_message
        
        # 检查是否有引导决策的音频数据
        guidance_audio = None
        if hasattr(chat_service.main_agent.conversation_history, 'guidance_audio'):
            guidance_audio = chat_service.main_agent.conversation_history.guidance_audio
            
        if guidance_audio and len(guidance_audio) > 100:
            guidance_audio_base64 = base64.b64encode(guidance_audio).decode('ascii')
            response_data["guidance_audio"] = guidance_audio_base64
            print(f"引导决策音频已添加到响应，大小: {len(guidance_audio)} 字节")
    
    return JSONResponse(content=response_data)

@app.get("/api/tts_settings")
async def get_tts_settings(request: Request):
    """获取TTS设置

    Returns:
        dict: TTS设置
    """
    # 获取当前的会话ID
    session_id = None
    try:
        # 尝试从cookies获取
        cookies = request.cookies
        session_id = cookies.get("session_id")
        
        # 如果cookies中没有，尝试从请求头获取
        if not session_id:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                session_id = auth_header.split(" ")[1]
                
        print(f"获取TTS设置，会话ID: {session_id}")
    except Exception as e:
        print(f"获取会话ID时出错: {e}")
        pass
    
    # 默认使用系统配置
    settings = {
        "enable_tts": Config.ENABLE_TTS,
        "enable_super_tts": Config.ENABLE_SUPER_TTS,
        "enable_tts_global": Config.ENABLE_TTS_GLOBAL,
        "tts_voice": Config.TTS_VCN,
        "super_tts_voice": Config.SUPER_TTS_VCN,
        "tts_voice_list": Config.TTS_VOICE_LIST,
        "super_tts_voice_list": Config.SUPER_TTS_VOICE_LIST,
        "tts_speed": Config.TTS_SPEED,
        "typing_speed": Config.TYPING_SPEED,
        "voice_input_mode": getattr(Config, "VOICE_INPUT_MODE", True),
        "voice_timeout": getattr(Config, "VOICE_TIMEOUT", 5)
    }
    
    # 如果有会话ID，获取当前用户的设置
    if session_id:
        try:
            # 获取用户ID
            user = await db_manager.get_user_by_session(session_id)
            
            if user:
                username = user["username"]
                print(f"获取用户 {username} 的TTS设置")
                
                # 从数据库获取用户设置
                from user_info_manager import UserInfoManager
                user_info_manager = UserInfoManager(username)
                user_settings = await user_info_manager.get_ui_settings()
                
                if user_settings:
                    # 更新设置
                    settings.update(user_settings)
                    print(f"加载到用户 {username} 的设置: {user_settings}")
        except Exception as e:
            print(f"获取用户设置时出错: {e}")
    
    return settings

@app.post("/api/tts_settings")
async def update_tts_settings(request: Request):
    """更新TTS设置

    Returns:
        dict: 更新结果
    """
    try:
        # 获取请求数据
        data = await request.json()
        
        # 获取当前的会话ID
        session_id = None
        cookies = request.cookies
        session_id = cookies.get("session_id")
        
        # 如果cookies中没有，尝试从请求头获取
        if not session_id:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                session_id = auth_header.split(" ")[1]
        
        print(f"更新TTS设置，会话ID: {session_id}，设置: {data}")
        
        # 如果有会话ID，更新当前用户的设置
        if session_id:
            # 获取用户ID
            user = await db_manager.get_user_by_session(session_id)
            
            if user:
                username = user["username"]
                print(f"更新用户 {username} 的TTS设置为: {data}")
                
                # 更新用户设置到数据库
                from user_info_manager import UserInfoManager
                user_info_manager = UserInfoManager(username)
                success = await user_info_manager.update_ui_settings(data)
                
                if success:
                    # 同时更新全局配置
                    if "enable_tts" in data:
                        Config.ENABLE_TTS = data["enable_tts"]
                    if "enable_super_tts" in data:
                        Config.ENABLE_SUPER_TTS = data["enable_super_tts"]
                    if "enable_tts_global" in data:
                        Config.ENABLE_TTS_GLOBAL = data["enable_tts_global"]
                    if "tts_voice" in data:
                        Config.TTS_VCN = data["tts_voice"]
                    if "super_tts_voice" in data:
                        Config.SUPER_TTS_VCN = data["super_tts_voice"]
                    if "tts_speed" in data:
                        Config.TTS_SPEED = data["tts_speed"]
                    if "typing_speed" in data:
                        Config.TYPING_SPEED = data["typing_speed"]
                    if "voice_input_mode" in data:
                        Config.VOICE_INPUT_MODE = data["voice_input_mode"]
                    if "voice_timeout" in data:
                        Config.VOICE_TIMEOUT = data["voice_timeout"]
                    
                    # 通知聊天服务重新加载TTS服务
                    try:
                        # 首先尝试从app.state获取chat_service
                        if hasattr(request.app, 'state') and hasattr(request.app.state, 'chat_service'):
                            chat_service_instance = request.app.state.chat_service
                            print("从app.state获取chat_service成功")
                            chat_service_instance._refresh_tts_services()
                        elif 'chat_service' in globals():
                            # 如果不存在，使用全局变量
                            print("使用全局chat_service变量")
                            chat_service._refresh_tts_services()
                        else:
                            print("未找到chat_service实例，无法刷新TTS服务")
                        
                        print("TTS服务已刷新")
                    except Exception as e:
                        print(f"刷新TTS服务时出错: {e}")
                        import traceback
                        traceback.print_exc()
                    
                    return {"code": 0, "message": "设置更新成功"}
                else:
                    return {"code": 1, "message": "更新用户设置失败"}
        
        # 如果没有会话ID或用户不存在，只更新全局配置
        if "enable_tts" in data:
            Config.ENABLE_TTS = data["enable_tts"]
        if "enable_super_tts" in data:
            Config.ENABLE_SUPER_TTS = data["enable_super_tts"]
        if "enable_tts_global" in data:
            Config.ENABLE_TTS_GLOBAL = data["enable_tts_global"]
        if "tts_voice" in data:
            Config.TTS_VCN = data["tts_voice"]
        if "super_tts_voice" in data:
            Config.SUPER_TTS_VCN = data["super_tts_voice"]
        if "tts_speed" in data:
            Config.TTS_SPEED = data["tts_speed"]
        if "typing_speed" in data:
            Config.TYPING_SPEED = data["typing_speed"]
        if "voice_input_mode" in data:
            Config.VOICE_INPUT_MODE = data["voice_input_mode"]
        if "voice_timeout" in data:
            Config.VOICE_TIMEOUT = data["voice_timeout"]
        
        # 重新初始化TTS服务
        try:
            # 首先尝试从app.state获取chat_service
            if hasattr(request.app, 'state') and hasattr(request.app.state, 'chat_service'):
                chat_service_instance = request.app.state.chat_service
                print("从app.state获取chat_service成功")
                chat_service_instance._refresh_tts_services()
            elif 'chat_service' in globals():
                # 如果不存在，使用全局变量
                print("使用全局chat_service变量")
                chat_service._refresh_tts_services()
            else:
                print("未找到chat_service实例，无法刷新TTS服务")
            
            print("TTS服务已刷新")
        except Exception as e:
            print(f"刷新TTS服务时出错: {e}")
            import traceback
            traceback.print_exc()
        
        return {"code": 0, "message": "设置更新成功"}
    except Exception as e:
        print(f"更新TTS设置时出错: {e}")
        import traceback
        traceback.print_exc()
        return {"code": 1, "message": f"更新设置失败: {str(e)}"}

@app.post("/api/welcome_tts")
async def welcome_tts(request: dict = Body(...)):
    """为欢迎语生成TTS音频
    
    Args:
        request: 包含欢迎语文本和agent类型的请求
        
    Returns:
        dict: 包含音频数据的响应
    """
    try:
        message = request.get("message", "")
        agent_type = request.get("agent_type", "")
        
        if not message:
            return JSONResponse(
                content={
                    "success": False,
                    "message": "欢迎语文本不能为空"
                }
            )
        
        # 确保TTS服务使用最新的配置
        chat_service._refresh_tts_services()
        
        # 使用消息内容作为欢迎语
        welcome_text = message
        welcome_audio = None
        
        # 设置重试次数和超时控制
        max_attempts = 2
        tts_timeout = 10  # 10秒超时
        
        # 首先尝试使用首选TTS方式
        primary_tts_success = False
        tts_error = None
        
        # 根据配置决定使用哪个TTS服务
        if Config.is_super_tts_enabled() and chat_service.super_tts_service:
            # 优先尝试超拟人TTS
            try:
                print("欢迎语TTS: 尝试使用超拟人TTS生成语音...")
                
                # 启动超时控制
                import asyncio
                from concurrent.futures import ThreadPoolExecutor
                
                with ThreadPoolExecutor() as executor:
                    # 创建一个超时任务
                    tts_task = asyncio.get_event_loop().run_in_executor(
                        executor, 
                        chat_service.super_tts_service.generate_audio, 
                        welcome_text
                    )
                    
                    try:
                        # 等待任务完成，有超时限制
                        welcome_audio = await asyncio.wait_for(tts_task, timeout=tts_timeout)
                        
                        if welcome_audio and len(welcome_audio) > 100:
                            print(f"欢迎语超拟人TTS生成成功，音频大小: {len(welcome_audio)} 字节")
                            primary_tts_success = True
                        else:
                            print("欢迎语超拟人TTS生成失败: 生成的音频数据无效或过小")
                            tts_error = "音频数据无效或过小"
                    except asyncio.TimeoutError:
                        print(f"欢迎语超拟人TTS生成超时（{tts_timeout}秒）")
                        tts_error = f"超时（{tts_timeout}秒）"
                        
            except Exception as e:
                print(f"生成欢迎语超拟人语音时出错: {e}")
                tts_error = str(e)
        
        # 如果超拟人TTS失败且普通TTS可用，则降级使用普通TTS
        if not primary_tts_success and Config.is_tts_enabled() and chat_service.tts_service:
            try:
                print(f"欢迎语超拟人TTS失败（{tts_error}），降级使用普通TTS...")
                welcome_audio = chat_service.tts_service.generate_audio(welcome_text)
                
                if welcome_audio and len(welcome_audio) > 100:
                    print(f"欢迎语普通TTS生成成功，音频大小: {len(welcome_audio)} 字节")
                else:
                    print("欢迎语普通TTS生成失败: 生成的音频数据无效或过小")
            except Exception as e:
                print(f"生成欢迎语普通语音时也失败: {e}")
        
        # 如果首选方式是普通TTS
        elif not primary_tts_success and not Config.is_super_tts_enabled() and Config.is_tts_enabled() and chat_service.tts_service:
            try:
                print("欢迎语TTS: 尝试使用普通TTS生成语音...")
                welcome_audio = chat_service.tts_service.generate_audio(welcome_text)
                
                if welcome_audio and len(welcome_audio) > 100:
                    print(f"欢迎语普通TTS生成成功，音频大小: {len(welcome_audio)} 字节")
                else:
                    print("欢迎语普通TTS生成失败: 生成的音频数据无效或过小")
            except Exception as e:
                print(f"生成欢迎语普通语音时出错: {e}")
        
        audio_base64 = base64.b64encode(welcome_audio).decode('ascii') if welcome_audio else ''
        
        return JSONResponse(
            content={
                "success": bool(welcome_audio),
                "audio": audio_base64,
                "message": "TTS生成成功" if welcome_audio else "TTS生成失败，请检查语音服务配置"
            }
        )
    except Exception as e:
        print(f"生成欢迎语TTS失败: {e}")
        return JSONResponse(
            content={
                "success": False,
                "message": f"生成欢迎语TTS失败: {str(e)}"
            }
        )

# 新增七牛云视频上传相关API

class VideoUploadResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

async def get_token(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供有效的授权令牌")
    
    token = authorization.replace("Bearer ", "")
    return token

@app.post("/api/upload-video", response_model=VideoUploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    file_type: str = "avi",
    token: str = Depends(get_token)
):
    """
    处理视频上传到七牛云
    
    返回包含report_id的响应，前端可以使用report_id查询状态
    """
    try:
        # 强制使用AVI文件类型
        file_type = "avi"
        
        # 确保文件名使用avi扩展名
        original_filename = file.filename
        base_name = os.path.splitext(original_filename)[0]
        file.filename = f"{base_name}.avi"
        
        # 读取上传的视频文件内容
        file_content = await file.read()
        
        # 处理视频上传
        result = qiniu_uploader.process_video_upload(
            auth_token=token,
            video_data=file_content,
            file_name=file.filename,
            file_type=file_type
        )
        
        if not result.get("success", False):
            return JSONResponse(
                status_code=400,
                content=result
            )
            
        # 确保结果中包含report_id信息
        if "data" in result:
            # 检查report_id是否已经包含在结果中
            if "report_id" not in result["data"] and "etag" in result["data"]:
                etag = result["data"]["etag"]
                report_id = qiniu_uploader.etag_to_report_id.get(etag)
                if report_id:
                    result["data"]["report_id"] = report_id
                    logger.info(f"上传响应中添加report_id: {report_id}")
        
        logger.info(f"视频上传成功，返回数据: {result}")
        return result
    except Exception as e:
        logger.error(f"视频上传处理失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"视频上传处理失败: {str(e)}",
                "data": None
            }
        )

@app.post("/api/download-video-report")
async def download_video_report(request: Request):
    """
    代理情绪评估报告下载请求
    
    前端通过这个接口下载情绪评估报告，后端负责处理加密和授权
    """
    try:
        # 获取请求表单
        form_data = await request.form()
        sign = form_data.get("sign")
        content = form_data.get("content")
        timestamp = form_data.get("timestamp")
        
        # 获取授权头
        auth_header = request.headers.get("Authorization", "")
        auth_token = ""
        
        # 从Authorization头解析token
        if auth_header and auth_header.startswith("Bearer "):
            auth_token = auth_header.replace("Bearer ", "")
        
        # 如果没有token，使用默认测试token
        if not auth_token:
            auth_token = "25c90b21074f42049d4c3d1772709574"
        
        if not content:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "缺少必要的请求参数",
                    "data": None
                }
            )
            
        try:
            # 解密content参数
            decrypted_content = qiniu_uploader.decrypt_des(content)
            params = json.loads(decrypted_content)
            report_id = params.get("id")
            
            if not report_id:
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "message": "缺少报告ID参数",
                        "data": None
                    }
                )
            
            # 设置保存目录
            save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "save", "assessments")
            os.makedirs(save_dir, exist_ok=True)
            
            # 调用下载方法
            logger.info(f"请求下载情绪评估报告: ID={report_id}")
            report_path = qiniu_uploader.download_emotion_report(auth_token, report_id, save_dir)
            
            if not report_path:
                return JSONResponse(
                    status_code=404,
                    content={
                        "success": False,
                        "message": "报告下载失败或不存在",
                        "data": None
                    }
                )
            
            # 下载成功，启动对报告的自动分析（后台处理）
            logger.info(f"报告下载成功，启动自动情绪评估分析: {report_path}")
            
            # 创建一个后台任务来处理报告分析
            async def process_report_analysis(report_file_path):
                try:
                    # 使用新的通用函数进行处理
                    await process_assessment_from_report(report_file_path, "下载报告后")
                except Exception as analysis_error:
                    logger.error(f"报告自动分析失败: {str(analysis_error)}")
                    import traceback
                    logger.error(traceback.format_exc())
            
            # 创建后台任务处理报告分析
            asyncio.create_task(process_report_analysis(report_path))
            
            # 返回PDF文件
            with open(report_path, "rb") as f:
                file_content = f.read()
            
            # 返回文件内容
            return Response(
                content=file_content,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=emotion_report_{report_id}.pdf"
                }
            )
            
        except Exception as decrypt_error:
            logger.error(f"解密请求参数失败: {str(decrypt_error)}")
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": f"解析请求参数失败: {str(decrypt_error)}",
                    "data": None
                }
            )
            
    except Exception as e:
        logger.error(f"下载情绪评估报告失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"下载情绪评估报告失败: {str(e)}",
                "data": None
            }
        )

@app.get("/api/check-latest-report")
async def check_latest_report(request: Request, token: str = None, report_id: int = None):
    """
    检查最新报告状态并更新
    
    仅检查列表中的第一条报告状态，更高效地更新报告下载状态
    使用report_id作为状态字典的主键
    """
    try:
        # 获取授权令牌
        auth_token = token or ""
        if not auth_token:
            # 从Authorization头获取token
            auth_header = request.headers.get("Authorization", "")
            if auth_header and auth_header.startswith("Bearer "):
                auth_token = auth_header.replace("Bearer ", "")
        
        # 如果没有token，返回错误
        if not auth_token:
            auth_token = "25c90b21074f42049d4c3d1772709574"  # 默认测试token
        
        # 如果没有提供report_id，使用check_and_download_report获取最新状态
        if not report_id:
            status_result = qiniu_uploader.check_and_download_report(auth_token)
            if not status_result["success"]:
                return JSONResponse(
                    status_code=404,
                    content={
                        "success": False,
                        "message": status_result.get("message", "获取报告状态失败"),
                        "data": None
                    }
                )
                
            # 从check_and_download_report结果中提取report_id
            report_id = status_result.get("report_id")
            
        # 如果有report_id，记录到日志并更新状态
        logger.info(f"检查报告状态: report_id={report_id}")
        
        # 调用更新评估状态方法
        await update_assessment_status(auth_token, report_id)
        
        # 获取最新状态
        status_result = qiniu_uploader.get_latest_assessment_status(report_id=report_id)
        
        if not status_result["success"]:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": status_result["message"],
                    "data": None
                }
            )
        
        return JSONResponse(
            content={
                "success": True,
                "message": "检查最新报告状态成功",
                "data": {
                    "report_id": status_result.get("report_id"),
                    "upload_callback_status": status_result.get("upload_callback_status"),
                    "assessment_status": status_result.get("assessment_status"),
                    "report_downloaded": status_result.get("report_downloaded")
                }
            }
        )
    except Exception as e:
        logger.error(f"检查最新报告状态失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"检查最新报告状态失败: {str(e)}",
                "data": None
            }
        )

@app.post("/api/video/update_report_status")
async def update_report_status(request: Request):
    """
    更新报告下载状态
    
    前端可以通过这个接口告知后端报告已经被下载，更新状态
    """
    try:
        # 获取请求体
        data = await request.json()
        report_id = data.get("report_id")
        downloaded = data.get("downloaded", True)  # 默认为True
        
        if not report_id:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "缺少report_id参数",
                    "data": None
                }
            )

        # 记录操作
        logger.info(f"更新报告下载状态: report_id={report_id}, downloaded={downloaded}")
        
        # 获取当前状态
        if report_id in qiniu_uploader.report_status:
            # 更新下载状态
            current_status = qiniu_uploader.report_status[report_id]
            current_status["downloaded"] = downloaded
            
            # 记录状态更新操作
            logger.info(f"报告状态更新成功: {current_status}")
            
            return JSONResponse(
                content={
                    "success": True,
                    "message": "更新报告状态成功",
                    "data": {
                        "report_id": report_id,
                        "upload_callback_status": current_status.get("upload_callback", False),
                        "assessment_status": current_status.get("assessment", False),
                        "report_downloaded": current_status.get("downloaded", False)
                    }
                }
            )
        else:
            # 如果没有找到状态记录，初始化一个新记录
            qiniu_uploader.report_status[report_id] = {
                "upload_callback": True,  # 假设已完成上传回调
                "assessment": True,       # 假设已完成评估
                "downloaded": downloaded
            }
            
            logger.info(f"初始化报告状态: report_id={report_id}, downloaded={downloaded}")
            
            return JSONResponse(
                content={
                    "success": True,
                    "message": "初始化报告状态成功",
                    "data": {
                        "report_id": report_id,
                        "upload_callback_status": True,
                        "assessment_status": True,
                        "report_downloaded": downloaded
                    }
                }
            )
    
    except Exception as e:
        logger.error(f"更新报告状态失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"更新报告状态失败: {str(e)}",
                "data": None
            }
        )

# 全局轮询线程管理器
POLLING_THREADS = {}  # 键: etag/report_id, 值: {thread: Thread, start_time: timestamp}

@app.post("/api/video/status")
async def video_status(request: Request):
    """
    统一的视频状态接口 - 合并上传状态查询和启动轮询功能
    
    功能：
    1. 获取视频上传和评估状态
    2. 可选择性地启动后端轮询检查视频评估状态
    
    支持参数：
    - auth_token：授权令牌
    - start_polling：是否启动轮询
    """
    try:
        # 获取请求体
        data = await request.json()
            
        # 获取授权令牌 - 如果请求中包含则使用，否则使用默认测试令牌
        auth_token = data.get("auth_token", "")
        
        # 检查是否需要启动轮询
        start_polling = data.get("start_polling", False)
        
        # 直接检查最新报告并下载（如果需要）
        status_result = qiniu_uploader.check_and_download_report(auth_token)
        
        if not status_result["success"]:
            logger.warning(f"获取状态失败: {status_result.get('message', '未知错误')}")
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "无法获取视频状态",
                    "data": None
                }
            )
        
        # 从状态结果中获取信息
        current_report_id = status_result.get("report_id")
        report_status = status_result.get("status")
        upload_callback_status = status_result.get("upload_callback_status", False)
        assessment_status = status_result.get("assessment_status", False)
        report_downloaded = status_result.get("report_downloaded", False)
        
        # 如果报告被下载，处理文档分析
        if "report_path" in status_result and status_result["report_path"]:
            report_path = status_result["report_path"]
            logger.info(f"报告已下载，启动文档分析: {report_path}")
            # 创建异步任务处理文档分析
            asyncio.create_task(process_assessment_from_report(report_path, "video_status下载"))
            
            # 如果报告已下载，检查并关闭对应的轮询线程
            if current_report_id and current_report_id in POLLING_THREADS:
                thread_info = POLLING_THREADS.get(current_report_id)
                if thread_info and thread_info.get('thread') and thread_info['thread'].is_alive():
                    logger.info(f"报告已下载，终止轮询线程: report_id={current_report_id}")
                    # 清除线程信息，使轮询在下一次检查时停止
                    POLLING_THREADS.pop(current_report_id, None)
                    logger.info(f"已移除轮询线程信息: report_id={current_report_id}")
        
        # 如果报告已下载完成，不需要启动轮询
        if report_downloaded:
            start_polling = False
            # 再次检查并关闭对应的轮询线程
            if current_report_id and current_report_id in POLLING_THREADS:
                logger.info(f"报告已标记为下载完成，关闭轮询: report_id={current_report_id}")
                POLLING_THREADS.pop(current_report_id, None)
        
        # 处理启动轮询请求 - 只有当明确请求启动轮询且上传回调状态为True且评估状态未完成时才启动
        polling_started = False
        thread_id = None
        
        # 全局轮询管理 - 仅在需要轮询且状态未完成时启动
        if start_polling and upload_callback_status and not assessment_status and current_report_id:
            # 创建唯一的轮询键 - 使用report_id
            polling_key = current_report_id
            
            # 检查是否已有轮询线程
            thread_info = POLLING_THREADS.get(polling_key)
            
            if thread_info and isinstance(thread_info.get("thread"), threading.Thread) and thread_info["thread"].is_alive():
                logger.info(f"已有轮询线程正在运行: polling_key={polling_key}, thread_id={thread_info['thread'].ident}, 运行时间={int(time.time() - thread_info['start_time'])}秒")
                polling_started = True
                thread_id = thread_info["thread"].ident
            else:
                # 启动新的轮询线程
                logger.info(f"为键{polling_key}创建新的轮询线程")
                
                # 如果有旧的死亡线程，清理它
                if thread_info:
                    logger.info(f"清理旧的轮询线程: polling_key={polling_key}, thread_id={thread_info['thread'].ident if thread_info.get('thread') else 'None'}")
                    POLLING_THREADS.pop(polling_key, None)
                
                # 创建新的轮询线程
                polling_thread = threading.Thread(
                    target=qiniu_uploader.poll_report_status,
                    args=(auth_token, current_report_id),
                    daemon=True
                )
                    
                # 启动线程
                polling_thread.start()
                thread_id = polling_thread.ident
                
                # 保存线程信息到全局管理器
                POLLING_THREADS[polling_key] = {
                    "thread": polling_thread,
                    "start_time": time.time()
                }
                
                logger.info(f"启动轮询线程: polling_key={polling_key}, thread_id={thread_id}")
                polling_started = True
                
                # 清理过期的线程 - 检查所有已记录线程
                for key, info in list(POLLING_THREADS.items()):
                    if key != polling_key and info.get("thread") and not info["thread"].is_alive():
                        logger.info(f"清理过期线程: key={key}, thread_id={info['thread'].ident}")
                        POLLING_THREADS.pop(key, None)
        
        # 返回最终状态
        return JSONResponse(
            content={
                "success": True,
                "message": "获取状态成功",
                "data": {
                    "report_id": current_report_id,
                    "status": report_status,
                    "upload_callback_status": upload_callback_status,
                    "assessment_status": assessment_status,
                    "report_downloaded": report_downloaded,
                    "polling_started": polling_started,
                    "polling_thread_id": thread_id
                }
            }
        )
    except Exception as e:
        logger.error(f"获取视频状态失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"获取视频状态失败: {str(e)}",
                "data": None
            }
        )


# 全局缓存报告列表
REPORT_LIST_CACHE = {
    "data": None,
    "timestamp": 0,
    "auth_token": None
}
CACHE_TTL = 5  # 缓存有效期，5秒

async def get_cached_report_list(auth_token: str):
    """获取缓存的报告列表，如果缓存过期则重新获取"""
    global REPORT_LIST_CACHE
    
    current_time = time.time()
    # 如果缓存未过期且auth_token一致，使用缓存
    if (REPORT_LIST_CACHE["data"] and 
        current_time - REPORT_LIST_CACHE["timestamp"] < CACHE_TTL and
        REPORT_LIST_CACHE["auth_token"] == auth_token):
        logger.info("使用缓存的报告列表")
        return REPORT_LIST_CACHE["data"]
    
    # 重新获取报告列表
    report_list = qiniu_uploader.get_emotion_report_list(auth_token)
    
    # 更新缓存
    REPORT_LIST_CACHE["data"] = report_list
    REPORT_LIST_CACHE["timestamp"] = current_time
    REPORT_LIST_CACHE["auth_token"] = auth_token
    
    return report_list

async def update_assessment_status(auth_token: str, report_id: str = None):
    """
    更新情绪评估状态
    
    从七牛云服务器获取最新状态并更新本地状态
    此方法已被简化，主要使用check_and_download_report替代
    
    Args:
        auth_token: 授权令牌
        report_id: 报告ID (可选)
    """
    # 如果上传回调为False，则不执行任何操作
    if report_id and report_id in qiniu_uploader.report_status:
        status = qiniu_uploader.report_status[report_id]
        if not status.get("upload_callback", False):
            logger.info(f"上传回调为False，不进行状态更新: report_id={report_id}")
        return
    
    if not report_id:
        # this is a new_line, no problem
        # 如果没有报告ID，直接使用check_and_download_report
        result = qiniu_uploader.check_and_download_report(auth_token)
        logger.info(f"使用check_and_download_report更新状态: {result}")
        return
    
    logger.info(f"更新情绪评估状态: report_id={report_id}")
    
    # 获取报告列表
    report_list = await get_cached_report_list(auth_token)
    
    if not report_list:
        logger.warning("未获取到报告列表")
        return
    
    # 在列表中查找指定的report_id
    target_report = None
    for report in report_list:
        if str(report.get("id", "")) == str(report_id):
            target_report = report
            break
            
    if not target_report:
        logger.warning(f"未找到指定的报告ID: {report_id}")
        return
        
    # 获取报告状态
    report_status = target_report.get("status")
    
    # 更新状态
    if report_status == 1:  # 完成状态
        logger.info(f"发现已完成的报告: id={report_id}")
        
        # 设置保存目录
        save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "save", "assessments")
        os.makedirs(save_dir, exist_ok=True)
        
        # 下载报告
        report_path = qiniu_uploader.download_emotion_report(auth_token, report_id, save_dir)
        
        if report_path:
            logger.info(f"报告下载成功: {report_path}")
            
            # 更新状态
            qiniu_uploader.report_status[report_id] = {
                "upload_callback": True,
                "assessment": 2,  # 2表示报告已生成
                "downloaded": True
            }
            
            # 下载完成后，只调用情绪评估文档分析接口，不进行其他操作
            logger.info(f"报告下载完成，进行文档分析: {report_path}")
            
            # 此处应调用情绪评估的文档分析接口
            # 创建后台任务处理报告分析
            asyncio.create_task(process_assessment_from_report(report_path, "状态更新后"))
        else:
            logger.error(f"报告下载失败: id={report_id}")
    else:
        logger.info(f"报告状态未完成(status={report_status}): id={report_id}")
        
        # 更新状态
        qiniu_uploader.report_status[report_id] = {
            "upload_callback": True,
            "assessment": False if report_status != 1 else 2,
            "downloaded": False
        }

# 新增辅助函数处理报告情绪评估分析 - 用于合并重复代码
async def process_assessment_from_report(report_path, context=""):
    """
    从报告文件进行情绪评估分析的通用函数
    
    Args:
        report_path: 报告文件路径
        context: 上下文信息，用于日志
    
    Returns:
        assessment_result: 评估结果
    """
    try:
        # 创建文件对象以供assessment_api使用
        filename = os.path.basename(report_path)
        with open(report_path, "rb") as f:
            file_content = f.read()
        
        from fastapi import UploadFile
        import io
        from datetime import datetime
        import json
        
        # 创建类似于UploadFile的对象
        file_obj = io.BytesIO(file_content)
        upload_file = UploadFile(
            filename=filename,
            file=file_obj,
        )
        
        # 调用情绪评估API
        from assessment_api import emotional_assessment
        
        # 执行情绪评估分析
        context_str = f"在{context}" if context else ""
        logger.info(f"开始{context_str}执行情绪评估分析: {filename}")
        result = await emotional_assessment(upload_file)
        logger.info(f"{context_str}情绪评估分析完成: {result}")
        
        # 如果分析成功，保存结果
        if hasattr(result, "status_code") and result.status_code == 200:
            try:
                # 确保结果是JSON格式
                if isinstance(result.body, dict):
                    result_data = result.body
                else:
                    try:
                        result_data = json.loads(result.body)
                    except:
                        logger.warning(f"{context_str}无法解析评估结果为JSON: {result.body}")
                        return result
                
                # 只保存包含实际情绪评估数据的结果
                # 检查是否包含核心情绪分析数据或是初始状态消息
                if isinstance(result_data, dict) and (
                    "核心状态分析" in result_data or 
                    "重点指标异常" in result_data or 
                    "针对性干预建议" in result_data
                ):
                    # 包含真正的评估结果，保存为JSON文件
                    assessment_dir = os.path.join("save", "assessments")
                    os.makedirs(assessment_dir, exist_ok=True)
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    result_file = os.path.join(assessment_dir, f"assessment_{timestamp}.json")
                    
                    with open(result_file, "w", encoding="utf-8") as f:
                        json.dump(result_data, f, ensure_ascii=False, indent=2)
                    
                    logger.info(f"{context_str}情绪评估分析成功，结果已保存到: {result_file}")
                else:
                    # 这是一个初始状态消息，不保存
                    logger.info(f"{context_str}收到初始状态消息，不保存为JSON文件: {result_data}")
            except Exception as save_error:
                logger.error(f"{context_str}保存评估结果失败: {str(save_error)}")
                import traceback
                logger.error(traceback.format_exc())
        else:
            logger.warning(f"{context_str}情绪评估分析完成，但可能存在问题: {result}")
            
        return result
        
    except Exception as analysis_error:
        logger.error(f"{context_str}情绪评估分析失败: {str(analysis_error)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

@app.get("/api/get_agent_config")
async def get_agent_config(agent_id: str):
    """
    获取角色配置信息
    
    Args:
        agent_id: 角色ID
        
    Returns:
        dict: 包含角色配置的响应
    """
    try:
        # 检查角色是否存在
        config_path = os.path.join(CUSTOM_AGENTS_DIR, f"{agent_id}.json")
        if not os.path.exists(config_path):
            return JSONResponse(
                content={
                    "success": False,
                    "message": "指定的角色不存在"
                }
            )
        
        # 加载角色配置
        with open(config_path, "r", encoding="utf-8") as f:
            agent_config = json.load(f)
        
        # 检查是否有语音文件，验证文件是否存在
        if "voice_file" in agent_config:
            if os.path.exists(agent_config["voice_file"]):
                print(f"找到角色 {agent_id} 的语音文件: {agent_config['voice_file']}")
            else:
                print(f"角色 {agent_id} 的语音文件不存在: {agent_config['voice_file']}")
                # 不删除字段，保留路径信息
        
        return JSONResponse(
            content={
                "success": True,
                "message": "获取角色配置成功",
                "config": agent_config
            }
        )
    except Exception as e:
        print(f"获取角色配置失败: {e}")
        return JSONResponse(
            content={
                "success": False,
                "message": f"获取角色配置失败: {str(e)}"
            }
        )

@app.get("/api/remove_agent_voice")
async def remove_agent_voice(agent_id: str):
    """
    移除角色的语音文件
    
    Args:
        agent_id: 角色ID
        
    Returns:
        dict: 包含操作结果的响应
    """
    try:
        # 检查角色是否存在
        config_path = os.path.join(CUSTOM_AGENTS_DIR, f"{agent_id}.json")
        if not os.path.exists(config_path):
            return JSONResponse(
                content={
                    "success": False,
                    "message": "指定的角色不存在"
                }
            )
        
        # 加载角色配置
        with open(config_path, "r", encoding="utf-8") as f:
            agent_config = json.load(f)
        
        # 检查是否有语音文件
        if "voice_file" in agent_config:
            voice_filepath = agent_config["voice_file"]
            
            # 从配置中移除语音文件字段
            del agent_config["voice_file"]
            
            # 保存更新后的配置
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(agent_config, f, ensure_ascii=False, indent=2)
            
            # 尝试删除语音文件（如果存在）
            if os.path.exists(voice_filepath):
                try:
                    os.remove(voice_filepath)
                    print(f"已删除语音文件: {voice_filepath}")
                except Exception as e:
                    print(f"删除语音文件失败: {e}")
            
            return JSONResponse(
                content={
                    "success": True,
                    "message": "已移除角色的语音文件"
                }
            )
        else:
            return JSONResponse(
                content={
                    "success": True,
                    "message": "该角色没有绑定语音文件"
                }
            )
    except Exception as e:
        print(f"移除语音文件失败: {e}")
        return JSONResponse(
            content={
                "success": False,
                "message": f"移除语音文件失败: {str(e)}"
            }
        )

def process_json_response(response_text):
    """处理可能是JSON格式的回复文本
    
    统一处理JSON格式的回复，提取其中的reply字段和expression字段
    
    Args:
        response_text: 可能是JSON格式的回复文本
        
    Returns:
        tuple: (处理后的回复文本, 表情, 是否是引导结束)
    """
    reply = response_text
    expression = None
    is_summary = False
    
    # 首先检查是否为空
    if not response_text or not response_text.strip():
        return reply, expression, is_summary
    
    # 移除<think>标签及其内容
    if '<think>' in response_text:
        print("检测到<think>标签，正在移除思考过程内容")
        import re
        think_pattern = r'<think>.*?</think>'
        cleaned_text = re.sub(think_pattern, '', response_text, flags=re.DOTALL).strip()
        
        # 如果移除后为空，说明只有思考过程没有实际回复
        if not cleaned_text:
            print("警告: 回复只包含思考过程，没有实际内容")
            return "嗯...我在想该怎么回答你呢。", None, False
        
        response_text = cleaned_text
        reply = response_text
        print(f"移除<think>标签后的回复: {response_text}")
    
    # 处理带有```json标记的回复
    if '```json' in response_text:
        try:
            # 提取```json和```之间的内容
            pattern = r'```json\s*(.*?)\s*```'
            match = re.search(pattern, response_text, re.DOTALL)
            if match:
                json_content = match.group(1).strip()
                print(f"检测到```json标记，提取JSON内容: {json_content}")
                
                # 解析JSON
                data = json.loads(json_content)
                if 'reply' in data:
                    reply = data['reply']
                    print(f"从```json标记中提取reply内容: {reply}")
                    
                    if 'expression' in data:
                        expression = data['expression']
                        print(f"从```json标记中提取表情: {expression}")
                        
                    if 'is_summary' in data and data['is_summary']:
                        is_summary = True
                        print("从```json标记中检测到引导结束标记")
                        
                    return reply, expression, is_summary
        except json.JSONDecodeError:
            print("```json标记内容不是有效的JSON格式，继续处理")
        except Exception as e:
            print(f"处理```json标记回复时出错: {e}")
    
    # 处理双花括号格式 {{...}}
    if response_text.strip().startswith('{{') and response_text.strip().endswith('}}'):
        try:
            # 去除双花括号
            json_content = response_text.strip()[2:-2].strip()
            print("检测到双花括号格式，已修正为标准JSON")
            
            # 解析JSON
            data = json.loads(json_content)
            if 'reply' in data:
                reply = data['reply']
                print(f"从双花括号JSON中提取reply内容: {reply}")
                
                if 'expression' in data:
                    expression = data['expression']
                    print(f"从双花括号JSON中提取表情: {expression}")
                    
                if 'is_summary' in data and data['is_summary']:
                    is_summary = True
                    print("从双花括号JSON中检测到引导结束标记")
                    
                return reply, expression, is_summary
        except json.JSONDecodeError:
            print("双花括号内容不是有效的JSON格式，继续处理")
        except Exception as e:
            print(f"处理双花括号JSON回复时出错: {e}")
    
    # 处理标准JSON格式 {...}
    try:
        # 检查是否是JSON格式
        if response_text.strip().startswith('{') and response_text.strip().endswith('}'):
            print("检测到标准JSON格式回复，提取reply字段")
            reply_data = json.loads(response_text.strip())
            if "reply" in reply_data:
                # 提取reply字段
                reply = reply_data["reply"]
                print(f"从标准JSON中提取reply内容: {reply}")
                
                # 如果JSON中有表情信息，保存
                if "expression" in reply_data:
                    expression = reply_data["expression"]
                    print(f"从标准JSON中提取表情: {expression}")
                
                # 检查是否是引导结束
                if "is_summary" in reply_data and reply_data["is_summary"]:
                    is_summary = True
                    print("从标准JSON中检测到引导结束标记")
    except json.JSONDecodeError:
        # 如果不是JSON格式，直接使用完整回复
        print("回复不是有效的JSON格式，使用原始回复内容")
    except Exception as e:
        print(f"处理标准JSON回复时出错: {e}")
    
    return reply, expression, is_summary

# 添加结束引导模式的API请求模型
class EndGuidanceRequest(BaseModel):
    session_id: str
    agent_type: Optional[str] = None

# 添加重置引导模式的API端点
@app.post("/api/end_guidance")
async def end_guidance(request: EndGuidanceRequest):
    """结束引导式对话模式
    
    Args:
        request: 请求体，包含会话ID和智能体类型
    
    Returns:
        dict: 操作结果
    """
    try:
        print(f"收到结束引导模式请求: {request}")
        
        # 重置全局聊天服务的引导状态
        chat_service._reset_guidance_state()
        
        return {
            "success": True,
            "message": "引导模式已重置"
        }
    except Exception as e:
        print(f"重置引导模式时发生错误: {e}")
        return {
            "success": False,
            "message": f"重置引导模式失败: {str(e)}"
        }

# 聊天历史API请求模型
class ChatHistoryRequest(BaseModel):
    username: str
    messages: List[Dict[str, Any]]

# 聊天历史同步API请求模型
class ChatHistorySyncRequest(BaseModel):
    username: str
    last_sync_time: Optional[str] = None

# 添加两个新API端点来保存和加载聊天历史

@app.post("/api/save_chat_history")
async def save_chat_history(request: ChatHistoryRequest, authorization: Optional[str] = Header(None)):
    """保存用户的聊天历史到后端数据库
    
    Args:
        request: 请求体，包含用户名和消息列表
        authorization: 可选的授权头，可能包含会话ID
    
    Returns:
        保存结果
    """
    try:
        username = request.username
        messages = request.messages
        
        # 尝试从授权头获取会话ID
        session_id = None
        if authorization and authorization.startswith("Bearer "):
            session_id = authorization.replace("Bearer ", "")
            # 验证会话有效性
            if session_id:
                session_result = await db_manager.verify_session(session_id)
                if session_result["success"]:
                    # 如果会话有效，使用会话中的用户名
                    session_username = session_result["user"]["username"]
                    # 如果请求的用户名不匹配会话用户名，优先使用会话用户名
                    if session_username != username:
                        logger.warning(f"请求用户名 {username} 与会话用户名 {session_username} 不匹配，使用会话用户名")
                        username = session_username
                else:
                    logger.warning(f"会话验证失败: {session_result.get('message')}")
        
        # 当用户名为admin时，特殊处理确保能保存
        if username == "admin":
            logger.info("处理admin用户的聊天历史保存")
            
            # 确保用户存在于数据库中
            async with aiosqlite.connect(db_manager.DB_FILE) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT username FROM users WHERE username = ?", ("admin",)) as cursor:
                    user = await cursor.fetchone()
                    
                    if not user:
                        logger.info("Admin用户不存在，尝试创建")
                        # 创建admin用户
                        register_result = await db_manager.register_user(
                            username="admin",
                            email="admin@example.com",
                            password="123456",
                            profile={"display_name": "管理员", "is_admin": True}
                        )
                        
                        if not register_result["success"]:
                            logger.error(f"创建admin用户失败: {register_result['message']}")
                            return {"success": False, "message": f"创建admin用户失败: {register_result['message']}"}
        
        # 使用数据库模块保存聊天历史
        success = await db_manager.save_user_chat_history(username, messages)
        
        if success:
            return {"success": True, "message": "聊天历史保存成功"}
        else:
            return {"success": False, "message": "聊天历史保存失败"}
    except Exception as e:
        logger.error(f"保存聊天历史失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"success": False, "message": f"保存聊天历史失败: {str(e)}"}

@app.get("/api/load_chat_history/{username}")
async def load_chat_history(username: str, authorization: Optional[str] = Header(None)):
    """从数据库加载用户的聊天历史
    
    Args:
        username: 用户名
        authorization: 可选的授权头，可能包含会话ID
        
    Returns:
        用户的聊天历史
    """
    try:
        # 尝试从授权头获取会话ID
        if authorization and authorization.startswith("Bearer "):
            session_id = authorization.replace("Bearer ", "")
            # 验证会话有效性
            if session_id:
                session_result = await db_manager.verify_session(session_id)
                if session_result["success"]:
                    # 如果会话有效，使用会话中的用户名
                    session_username = session_result["user"]["username"]
                    # 如果请求的用户名不匹配会话用户名，优先使用会话用户名
                    if session_username != username:
                        logger.warning(f"请求用户名 {username} 与会话用户名 {session_username} 不匹配，使用会话用户名")
                        username = session_username
                else:
                    logger.warning(f"会话验证失败: {session_result.get('message')}")
        
        # 当用户名为admin时，特殊处理
        if username == "admin":
            logger.info("加载admin用户的聊天历史")
            
            # 检查admin用户是否存在
            async with aiosqlite.connect(db_manager.DB_FILE) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT username FROM users WHERE username = ?", ("admin",)) as cursor:
                    user = await cursor.fetchone()
                    
                    if not user:
                        logger.warning("Admin用户不存在，无法加载聊天历史")
                        return {
                            "success": False, 
                            "messages": [], 
                            "message": "Admin用户不存在，无法加载聊天历史"
                        }
        
        # 使用数据库模块加载聊天历史
        messages = await db_manager.load_user_chat_history(username)
        
        return {
            "success": True, 
            "messages": messages, 
            "last_updated": time.time(),
            "update_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        }
    except Exception as e:
        logger.error(f"加载聊天历史失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"success": False, "messages": [], "message": f"加载聊天历史失败: {str(e)}"}

# 添加新的API端点，用于清除用户的聊天历史
@app.delete("/api/clear_chat_history/{username}")
async def clear_chat_history(username: str):
    """清除用户的聊天历史
    
    Args:
        username: 用户名
    
    Returns:
        清除结果
    """
    try:
        # 使用数据库模块清除聊天历史
        success = await db_manager.clear_user_chat_history(username)
        
        if success:
            return {"success": True, "message": "聊天历史清除成功"}
        else:
            return {"success": False, "message": "聊天历史清除失败"}
    except Exception as e:
        logger.error(f"清除聊天历史失败: {str(e)}")
        return {"success": False, "message": f"清除聊天历史失败: {str(e)}"}

# 添加新的API端点，用于获取所有用户
@app.get("/api/list_chat_users")
async def list_chat_users():
    """获取所有有聊天历史的用户
    
    Returns:
        用户列表
    """
    try:
        # 使用数据库模块获取所有用户
        users = await db_manager.get_all_users()
        
        return {"success": True, "users": users}
    except Exception as e:
        logger.error(f"获取用户列表失败: {str(e)}")
        return {"success": False, "users": [], "message": f"获取用户列表失败: {str(e)}"}

# 添加应用启动事件处理器，初始化数据库
@app.on_event("startup")
async def startup_event():
    # 确保数据库已初始化
    await db_manager.init_db()
    logger.info("应用启动时初始化数据库成功")
    
    try:
        # 将chat_service设置为应用的状态
        app.state.chat_service = chat_service
        logger.info("应用启动时chat_service已设置到app.state")
    except Exception as e:
        logger.error(f"应用启动时设置chat_service到app.state失败: {e}")
        import traceback
        traceback.print_exc()

# 添加新的用户管理API端点

# 用户注册API
@app.post("/api/register")
async def register_user(request: Request):
    """用户注册API
    
    Request Body:
        username: 用户名
        email: 电子邮箱
        password: 密码
        profile: 可选的用户资料数据
    
    Returns:
        注册结果
    """
    try:
        data = await request.json()
        username = data.get("username", "")
        email = data.get("email", "")
        password = data.get("password", "")
        profile = data.get("profile", {})
        
        if not username or not email or not password:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "用户名、邮箱和密码不能为空"}
            )
        
        # 调用db_manager进行用户注册
        result = await db_manager.register_user(username, email, password, profile)
        
        if not result["success"]:
            return JSONResponse(
                status_code=400,
                content=result
            )
        
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"用户注册API错误: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"服务器错误: {str(e)}"}
        )

# 用户登录API
@app.post("/api/login")
async def login_user(request: Request):
    try:
        # 检查是否是外部请求或自动登录
        body = await request.json()
        username = body.get("username", "admin")
        password = body.get("password", "123456")
        
        # 如果是admin账号，需要特殊处理
        if username == "admin":
            # 先尝试验证admin账号是否存在
            admin_auth_result = await db_manager.authenticate_user(username, password)
            
            # 如果admin账户不存在或验证失败
            if not admin_auth_result["success"]:
                logger.info("Admin账户验证失败，检查是否存在")
                
                # 检查账户是否存在但密码不匹配
                async with aiosqlite.connect(db_manager.DB_FILE) as db:
                    db.row_factory = aiosqlite.Row
                    async with db.execute(
                        "SELECT username FROM users WHERE username = ?",
                        (username,)
                    ) as cursor:
                        user_exists = await cursor.fetchone()
                
                if user_exists:
                    # 账户存在但密码不匹配，重置admin密码
                    logger.info("Admin账户存在但密码不匹配，重置密码")
                    
                    # 生成新的密码哈希
                    password_hash, salt = db_manager.hash_password(password)
                    
                    # 更新密码
                    async with aiosqlite.connect(db_manager.DB_FILE) as db:
                        await db.execute(
                            "UPDATE users SET password_hash = ?, salt = ? WHERE username = ?",
                            (password_hash, salt, username)
                        )
                        await db.commit()
                    
                    # 重新尝试验证
                    admin_auth_result = await db_manager.authenticate_user(username, password)
                else:
                    # 账户不存在，创建admin账户
                    logger.info("Admin账户不存在，创建新账户")
                    register_result = await db_manager.register_user(
                        username="admin",
                        email="admin@example.com",
                        password="123456",
                        profile={
                            "display_name": "管理员",
                            "is_admin": True
                        }
                    )
                    
                    if not register_result["success"]:
                        logger.error(f"创建admin账户失败: {register_result['message']}")
                        return JSONResponse(
                            status_code=500,
                            content={"success": False, "message": f"创建admin账户失败: {register_result['message']}"}
                        )
                    
                    logger.info("Admin账户创建成功，重新尝试验证")
                    admin_auth_result = await db_manager.authenticate_user(username, password)
            
            # 验证成功，使用正确的session_id和用户信息
            if admin_auth_result["success"]:
                session_id = admin_auth_result["session_id"]
                user_info = admin_auth_result["user"]
                
                # 切换到admin用户状态
                await chat_service.switch_user(username, session_id)
                
                logger.info(f"Admin账户登录成功，会话ID: {session_id}")
                
                # 返回成功响应
                return {
                    "success": True,
                    "data": {
                        "user": user_info,
                        "session_id": session_id
                    }
                }
            else:
                # 如果仍然验证失败，返回错误
                logger.error(f"Admin账户验证失败: {admin_auth_result['message']}")
                return JSONResponse(
                    status_code=401,
                    content={"success": False, "message": f"验证失败: {admin_auth_result['message']}"}
                )
        else:
            # 其他账号走正常验证逻辑
            result = await db_manager.authenticate_user(username, password)
            
            if result["success"]:
                # 认证成功，获取会话ID
                session_id = result["session_id"]
                
                # 切换用户状态
                await chat_service.switch_user(username, session_id)
                
                # 返回用户信息和会话ID
                return {
                    "success": True,
                    "data": {
                        "user": result["user"],
                        "session_id": session_id
                    }
                }
            else:
                # 认证失败
                return {
                    "success": False,
                    "message": result["message"]
                }
    
    except Exception as e:
        logging.error(f"登录时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"success": False, "message": f"登录时出错: {str(e)}"}

# 验证会话API
@app.post("/api/verify_session")
async def verify_user_session(request: Request):
    """验证用户会话API
    
    Request Body:
        session_id: 会话ID
    
    Returns:
        验证结果，包含用户信息
    """
    try:
        data = await request.json()
        session_id = data.get("session_id", "")
        
        if not session_id:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "会话ID不能为空"}
            )
        
        # 调用db_manager验证会话
        result = await db_manager.verify_session(session_id)
        
        if not result["success"]:
            return JSONResponse(
                status_code=401,
                content=result
            )
        
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"验证会话API错误: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"服务器错误: {str(e)}"}
        )

# 用户登出API
@app.post("/api/logout")
async def logout_user(request: Request):
    """用户登出API
    
    Request Body:
        session_id: 会话ID
    
    Returns:
        登出结果
    """
    try:
        data = await request.json()
        session_id = data.get("session_id", "")
        
        if not session_id:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "会话ID不能为空"}
            )
        
        # 获取当前用户信息用于日志
        user_info = await db_manager.get_user_by_session(session_id)
        current_username = user_info.get("username", "unknown") if user_info else "unknown"
        
        # 调用db_manager删除会话
        result = await db_manager.logout_user(session_id)
        
        # 登出成功后，切换回默认用户
        if result["success"]:
            print(f"用户 {current_username} 登出成功，切换回默认用户")
            # 切换到默认用户状态
            await chat_service.switch_user("default_user", "default_session")
        
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"用户登出API错误: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"服务器错误: {str(e)}"}
        )

# 更新用户资料API
@app.post("/api/update_profile")
async def update_user_profile(request: Request):
    """更新用户资料API
    
    Request Body:
        session_id: 会话ID
        username: 用户名
        profile_data: 要更新的资料数据
    
    Returns:
        更新结果
    """
    try:
        data = await request.json()
        session_id = data.get("session_id", "")
        username = data.get("username", "")
        profile_data = data.get("profile_data", {})
        
        if not session_id or not username:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "会话ID和用户名不能为空"}
            )
        
        # 先验证会话
        session_result = await db_manager.verify_session(session_id)
        if not session_result["success"]:
            return JSONResponse(
                status_code=401,
                content=session_result
            )
        
        # 确保当前会话用户和请求的用户名匹配
        if session_result["user"]["username"] != username:
            return JSONResponse(
                status_code=403,
                content={"success": False, "message": "无权更新其他用户的资料"}
            )
        
        # 调用db_manager更新资料
        result = await db_manager.update_user_profile(username, profile_data)
        
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"更新用户资料API错误: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"服务器错误: {str(e)}"}
        )

# 修改密码API
@app.post("/api/change_password")
async def change_user_password(request: Request):
    """修改用户密码API
    
    Request Body:
        session_id: 会话ID
        username: 用户名
        current_password: 当前密码
        new_password: 新密码
    
    Returns:
        修改结果
    """
    try:
        data = await request.json()
        session_id = data.get("session_id", "")
        username = data.get("username", "")
        current_password = data.get("current_password", "")
        new_password = data.get("new_password", "")
        
        if not session_id or not username or not current_password or not new_password:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "会话ID、用户名、当前密码和新密码不能为空"}
            )
        
        # 先验证会话
        session_result = await db_manager.verify_session(session_id)
        if not session_result["success"]:
            return JSONResponse(
                status_code=401,
                content=session_result
            )
        
        # 确保当前会话用户和请求的用户名匹配
        if session_result["user"]["username"] != username:
            return JSONResponse(
                status_code=403,
                content={"success": False, "message": "无权修改其他用户的密码"}
            )
        
        # 调用db_manager修改密码
        result = await db_manager.change_password(username, current_password, new_password)
        
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"修改密码API错误: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"服务器错误: {str(e)}"}
        )

# 忘记密码请求API
@app.post("/api/forgot_password")
async def forgot_password(request: Request):
    """忘记密码请求API
    
    Request Body:
        email: 电子邮箱
    
    Returns:
        结果，包含重置令牌
    """
    try:
        data = await request.json()
        email = data.get("email", "")
        
        if not email:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "电子邮箱不能为空"}
            )
        
        # 调用db_manager生成重置令牌
        result = await db_manager.generate_password_reset_token(email)
        
        # 注意：在实际应用中，应该发送邮件，而不是直接返回令牌
        # 这里简化处理，直接返回令牌信息
        
        if not result["success"]:
            return JSONResponse(
                status_code=400,
                content=result
            )
        
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"忘记密码API错误: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"服务器错误: {str(e)}"}
        )

# 重置密码API
@app.post("/api/reset_password")
async def reset_password(request: Request):
    """重置密码API
    
    Request Body:
        reset_token: 重置令牌
        new_password: 新密码
    
    Returns:
        重置结果
    """
    try:
        data = await request.json()
        reset_token = data.get("reset_token", "")
        new_password = data.get("new_password", "")
        
        if not reset_token or not new_password:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "重置令牌和新密码不能为空"}
            )
        
        # 调用db_manager重置密码
        result = await db_manager.reset_password_with_token(reset_token, new_password)
        
        if not result["success"]:
            return JSONResponse(
                status_code=400,
                content=result
            )
        
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"重置密码API错误: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"服务器错误: {str(e)}"}
        )

# 获取用户列表API
@app.get("/api/list_users")
async def list_users():
    """获取用户列表API
    
    Returns:
        用户列表
    """
    try:
        # 在实际应用中，应该添加管理员权限验证
        # 这里简化处理，直接返回用户列表
        
        users = await db_manager.get_all_users()
        
        return JSONResponse(content={"success": True, "users": users})
    except Exception as e:
        logger.error(f"获取用户列表API错误: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"服务器错误: {str(e)}"}
        )

# 添加外部智能体平台的配置
# 获取本地IP
LOCAL_IP = get_local_ip()

# 外部智能体平台配置
ENABLE_EXTERNAL_AGENTS = False  # 是否启用外部智能体功能
EXTERNAL_AGENT_PLATFORM_URL = f"https://192.168.3.60:1443/console/api"
EXTERNAL_AGENT_PLATFORM_EMAIL = "zc710932004@gmail.com"
EXTERNAL_AGENT_PLATFORM_PASSWORD = "admin123"

# 存储外部平台的访问令牌
external_platform_token = None

# 添加获取外部平台令牌的函数
async def get_external_platform_token(force_refresh=False):
    global external_platform_token
    
    # 如果强制刷新，则清除现有令牌
    if force_refresh:
        external_platform_token = None
    
    # 如果已有令牌，则直接返回
    if external_platform_token:
        return external_platform_token
    
    try:
        # 忽略SSL证书验证（仅用于开发环境）
        login_url = f"{EXTERNAL_AGENT_PLATFORM_URL}/login"
        login_data = {
            "email": EXTERNAL_AGENT_PLATFORM_EMAIL,
            "password": EXTERNAL_AGENT_PLATFORM_PASSWORD,
            "language": "zh-Hans",
            "remember_me": True
        }
        
        # 设置超时时间，避免长时间等待
        response = requests.post(
            login_url, 
            json=login_data, 
            verify=False,
            timeout=5  # 减少超时时间，避免长时间等待
        )
        
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, dict) and "data" in data:
                    data_obj = data.get("data")
                    if isinstance(data_obj, dict) and "access_token" in data_obj:
                        external_platform_token = data_obj.get("access_token")
                        logging.info("成功获取外部平台访问令牌")
                        return external_platform_token
            except json.JSONDecodeError:
                logging.error(f"解析外部平台响应失败，响应内容: {response.text[:100]}...")
        
        # 如果响应不成功或解析失败，返回None
        logging.error(f"获取外部平台访问令牌失败: HTTP {response.status_code}")
        return None
        
    except requests.exceptions.Timeout:
        logging.warning("获取外部平台访问令牌超时（外部智能体功能不可用）")
        return None
    except requests.exceptions.ConnectionError:
        logging.warning("连接外部平台失败（外部智能体功能不可用），请检查网络或服务器状态")
        return None
    except Exception as e:
        logging.warning(f"获取外部平台访问令牌时出错（外部智能体功能不可用）: {str(e)}")
        return None

# 添加外部智能体模型
class ExternalAgentModel(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    icon_background: Optional[str] = None
    pre_prompt: Optional[str] = None

@app.get("/api/external_agents")
async def get_external_agents():
    """
    获取外部智能体平台的智能体列表
    """
    # 检查是否启用外部智能体功能
    if not ENABLE_EXTERNAL_AGENTS:
        return {"success": True, "agents": [], "message": "外部智能体功能未启用"}
    
    try:
        # 最多重试一次（首次 + 刷新令牌后重试）
        for attempt in range(2):
            # 获取访问令牌
            if attempt == 0:
                token = await get_external_platform_token()
            else:
                # 第二次尝试：强制刷新令牌
                logging.warning("令牌已过期，正在重新获取令牌...")
                token = await get_external_platform_token(force_refresh=True)
            
            if not token:
                if attempt == 0:
                    continue  # 第一次失败，尝试刷新令牌
                else:
                    return {"success": False, "message": "重新获取访问令牌失败"}
            
            # 构建请求头
            headers = {
                "Authorization": f"Bearer {token}"
            }
            
            # 请求智能体列表
            agents_url = f"{EXTERNAL_AGENT_PLATFORM_URL}/apps?page=1&limit=30&name=&is_created_by_me=false"
            response = requests.get(agents_url, headers=headers, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                
                # 提取所需的智能体信息
                agents = []
                if data and isinstance(data, dict):
                    # 安全地获取data列表
                    agent_list = data.get("data", [])
                    if agent_list and isinstance(agent_list, list):
                        for agent in agent_list:
                            if not agent or not isinstance(agent, dict):
                                continue
                                
                            if agent.get("mode") == "chat":
                                # 检查是否包含"心理"标签
                                tags = agent.get("tags", [])
                                has_psychology_tag = False
                                if tags and isinstance(tags, list):
                                    for tag in tags:
                                        if tag and isinstance(tag, dict) and tag.get("name") == "心理":
                                            has_psychology_tag = True
                                            break
                                
                                # 只处理包含"心理"标签的智能体
                                if has_psychology_tag:
                                    # 安全地获取model_config
                                    model_config = agent.get("model_config", {}) or {}
                                    pre_prompt = ""
                                    if model_config and isinstance(model_config, dict):
                                        pre_prompt = model_config.get("pre_prompt", "")
                                    
                                    # 添加智能体信息
                                    agents.append({
                                        "id": agent.get("id", ""),
                                        "name": agent.get("name", "默认智能体"),
                                        "description": agent.get("description", ""),
                                        "icon": agent.get("icon", ""),
                                        "icon_background": agent.get("icon_background", ""),
                                        "pre_prompt": pre_prompt
                                    })
                    
                return {"success": True, "agents": agents}
            
            elif response.status_code == 401 and attempt == 0:
                # 第一次遇到401错误，继续下一次循环（刷新令牌）
                logging.info("成功重新获取令牌，正在重试请求...")
                continue
            else:
                # 其他错误或第二次仍然401，直接返回错误
                logging.error(f"获取智能体列表API返回错误: {response.status_code}, {response.text}")
                return {
                    "success": False, 
                    "message": f"获取智能体列表失败: HTTP {response.status_code}"
                }
        
        # 如果循环结束仍未成功，返回失败
        return {"success": False, "message": "获取智能体列表失败，请稍后再试"}
    
    except Exception as e:
        logging.error(f"获取外部智能体列表时出错: {str(e)}")
        return {
            "success": False, 
            "message": f"获取智能体列表时出错，请稍后再试"
        }

@app.post("/api/switch_external_agent")
async def switch_external_agent(request: dict = Body(...)):
    """
    切换到外部智能体
    """
    try:
        agent_id = request.get("agent_id")
        agent_name = request.get("name", "外部智能体")
        # 同时检查prompt和pre_prompt两个字段
        agent_prompt = request.get("prompt") or request.get("pre_prompt")
        session_id = request.get("session_id", "default")
        
        # 记录请求信息用于调试
        logging.info(f"切换外部智能体请求: agent_id={agent_id}, name={agent_name}, session_id={session_id}")
        
        if not agent_id:
            logging.error("切换外部智能体失败: 缺少agent_id")
            return {"success": False, "message": "缺少agent_id参数"}
        
        if not agent_prompt:
            logging.info("前端未提供prompt或pre_prompt，尝试从外部API获取")
            
            # 最多重试一次（首次 + 刷新令牌后重试）
            for attempt in range(2):
                # 获取访问令牌
                if attempt == 0:
                    token = await get_external_platform_token()
                else:
                    # 第二次尝试：强制刷新令牌
                    logging.warning("令牌已过期，正在重新获取令牌...")
                    token = await get_external_platform_token(force_refresh=True)
                
                if not token:
                    if attempt == 0:
                        continue  # 第一次失败，尝试刷新令牌
                    else:
                        logging.error("重新获取访问令牌失败")
                        # 使用默认提示词
                        agent_prompt = f"你是{agent_name}，一个有用的AI助手。请用友善、专业的态度回答用户问题。"
                        logging.warning(f"无法获取智能体提示词，使用默认提示词: {agent_prompt}")
                        break
                
                # 构建请求头
                headers = {
                    "Authorization": f"Bearer {token}"
                }
                
                # 请求智能体详情
                try:
                    agent_url = f"{EXTERNAL_AGENT_PLATFORM_URL}/apps/{agent_id}"
                    response = requests.get(
                        agent_url, 
                        headers=headers, 
                        verify=False,
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        logging.info(f"获取到智能体响应: {data.keys()}")
                        
                        # 处理不同的响应结构
                        prompt = ""
                        if "data" in data and "model_config" in data["data"]:
                            prompt = data["data"]["model_config"].get("pre_prompt", "")
                            logging.info("从model_config.pre_prompt获取智能体提示词")
                        elif "model_config" in data:
                            prompt = data["model_config"].get("pre_prompt", "")
                            logging.info("直接从model_config.pre_prompt获取智能体提示词")
                        
                        # 如果还是找不到，尝试其他可能的字段
                        if not prompt and "data" in data:
                            if "prompt" in data["data"]:
                                prompt = data["data"]["prompt"]
                                logging.info("从data.prompt获取智能体提示词")
                            elif "pre_prompt" in data["data"]:
                                prompt = data["data"]["pre_prompt"]
                                logging.info("从data.pre_prompt获取智能体提示词")
                        
                        # 如果仍然没有找到提示词
                        if not prompt:
                            logging.error(f"智能体详情中未找到提示词，响应数据: {data}")
                        
                        # 成功获取到提示词
                        agent_prompt = prompt
                        break
                        
                    elif response.status_code == 401 and attempt == 0:
                        # 第一次遇到401错误，继续下一次循环（刷新令牌）
                        logging.info("成功重新获取令牌，正在重试请求...")
                        continue
                    else:
                        # 其他错误或第二次仍然401
                        logging.error(f"获取智能体详情失败: HTTP {response.status_code}, {response.text}")
                        if attempt == 1:  # 第二次尝试也失败了
                            break
                        
                except Exception as e:
                    logging.error(f"获取智能体详情时出错: {str(e)}")
                    if attempt == 1:  # 第二次尝试也失败了
                        break
            
            # 如果仍然无法获取提示词，使用默认提示词
            if not agent_prompt:
                agent_prompt = f"你是{agent_name}，一个有用的AI助手。请用友善、专业的态度回答用户问题。"
                logging.warning(f"无法获取智能体提示词，使用默认提示词: {agent_prompt}")
        
        # 确保保存目录存在
        custom_agents_dir = os.path.join("save", "custom_agents")
        os.makedirs(custom_agents_dir, exist_ok=True)
        
        # 创建临时自定义角色，使用external_前缀
        custom_agent_id = f"custom_external_{agent_id}"
        custom_agent_path = os.path.join(custom_agents_dir, f"{custom_agent_id}.txt")
        custom_config_path = os.path.join(custom_agents_dir, f"{custom_agent_id}.json")
        
        logging.info(f"保存文件路径: prompt={custom_agent_path}, config={custom_config_path}")
        
        try:
            # 保存提示词文件
            with open(custom_agent_path, "w", encoding="utf-8") as f:
                f.write(agent_prompt)
                
            # 保存配置文件
            config = {
                "id": custom_agent_id,
                "name": agent_name,
                "description": request.get("description", ""),
                "personality": "helpful",
                "interests": [],
                "lifestyle": "",
                "values": ""
            }
            with open(custom_config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
                
            logging.info(f"成功保存智能体文件: {custom_agent_id}")
        except Exception as e:
            logging.error(f"保存智能体文件时出错: {str(e)}")
            return {"success": False, "message": f"保存智能体文件时出错: {str(e)}"}
        
        # 切换智能体
        try:
            success = chat_service.change_agent(custom_agent_id, session_id)
            if success:
                logging.info(f"成功切换到智能体: {custom_agent_id}")
                return {"success": True, "message": f"已切换到智能体: {agent_name}"}
            else:
                logging.error(f"chat_service.change_agent 方法返回 False")
                return {"success": False, "message": "切换智能体失败，请检查智能体配置"}
        except Exception as e:
            logging.error(f"调用change_agent方法时出错: {str(e)}")
            return {"success": False, "message": f"切换智能体时出错: {str(e)}"}
    
    except Exception as e:
        logging.error(f"切换外部智能体时出错: {str(e)}")
        return {"success": False, "message": f"切换智能体时出错: {str(e)}"}

@app.post("/api/reset_default_agent")
async def reset_default_agent(request: dict = Body(...)):
    """
    重置为默认智能体
    """
    try:
        session_id = request.get("session_id", "default")
        
        # 切换回默认智能体
        # chat_service = get_chat_service()  # 错误的调用
        # 直接使用全局chat_service变量
        success = chat_service.change_agent("nanaA", session_id)
        
        return {"success": success, "message": "已重置为默认智能体" if success else "重置智能体失败"}
    
    except Exception as e:
        logging.error(f"重置默认智能体时出错: {str(e)}")
        return {"success": False, "message": f"重置智能体时出错: {str(e)}"}

# 修改现有的登录处理函数，支持自动登录
@app.get("/")
async def root():
    # 自动重定向到主界面
    return RedirectResponse(url="/index.html")

@app.get("/api/external_agent/{agent_id}")
async def get_external_agent(agent_id: str):
    """
    获取外部智能体平台的特定智能体详情
    """
    try:
        # 最多重试一次（首次 + 刷新令牌后重试）
        for attempt in range(2):
            # 获取访问令牌
            if attempt == 0:
                token = await get_external_platform_token()
            else:
                # 第二次尝试：强制刷新令牌
                logging.warning("令牌已过期，正在重新获取令牌...")
                token = await get_external_platform_token(force_refresh=True)
            
            if not token:
                if attempt == 0:
                    continue  # 第一次失败，尝试刷新令牌
                else:
                    return {"success": False, "message": "重新获取访问令牌失败"}
            
            # 构建请求头
            headers = {
                "Authorization": f"Bearer {token}"
            }
            
            # 请求智能体详情
            agent_url = f"{EXTERNAL_AGENT_PLATFORM_URL}/apps/{agent_id}"
            response = requests.get(agent_url, headers=headers, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data:
                    agent_data = data["data"]
                    pre_prompt = agent_data.get("model_config", {}).get("pre_prompt", "")
                    
                    agent = {
                        "id": agent_data.get("id", ""),
                        "name": agent_data.get("name", ""),
                        "description": agent_data.get("description", ""),
                        "icon": agent_data.get("icon", ""),
                        "icon_background": agent_data.get("icon_background", ""),
                        "pre_prompt": pre_prompt
                    }
                    
                    return {"success": True, "agent": agent}
                else:
                    return {"success": False, "message": "无法解析智能体详情数据"}
                    
            elif response.status_code == 401 and attempt == 0:
                # 第一次遇到401错误，继续下一次循环（刷新令牌）
                logging.info("成功重新获取令牌，正在重试请求...")
                continue
            else:
                # 其他错误或第二次仍然401，直接返回错误
                status_code = response.status_code
                message = response.text
                return {"success": False, "message": f"获取智能体详情失败: HTTP {status_code} - {message}"}
        
        # 如果循环结束仍未成功，返回失败
        return {"success": False, "message": "获取智能体详情失败，请稍后再试"}
    
    except Exception as e:
        logging.error(f"获取外部智能体详情时出错: {str(e)}")
        return {"success": False, "message": f"获取智能体详情时出错: {str(e)}"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8666, reload=True, ssl_keyfile=None, ssl_certfile=None)