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
from typing import Optional, List, Dict, Any, Union
import asyncio
import logging

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Form, File, UploadFile, Body, Header, Depends, HTTPException, Response
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
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
from f5_speech_service import f5_speech_service  # 导入F5语音服务
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
    tts_voice: Optional[str] = None
    super_tts_voice: Optional[str] = None
    tts_speed: Optional[int] = None
    typing_speed: Optional[int] = None
    voice_input_mode: Optional[bool] = None
    voice_timeout: Optional[int] = None

class TTSSettings(BaseModel):
    enable_tts: bool
    enable_super_tts: bool
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
def is_meaningless_input(message: str) -> bool:
    """判断输入是否无意义（过短或过于简单）
    
    Args:
        message: 用户输入消息
        
    Returns:
        bool: 是否无意义
    """
    # 如果消息太短，可能没有实际意义
    if len(message.strip()) < 2:
        return True
        
    # 常见无意义输入
    meaningless_inputs = [
        "你好", "hi", "hello", "嗨", "哈喽", "在吗", "在？", "测试", "test",
        "。", "，", "?", "？", "!", "！", "emmm", "hmm", "啊", "哦", "嗯",
        "666", "233", "haha", "哈哈", "呵呵"
    ]
    
    # 检查是否是这些无意义输入
    if message.strip().lower() in meaningless_inputs:
        return True
    
    return False

# 初始化评估API
assessment_api.init_router(chat_service, extract_text_from_file, is_meaningless_input)
app.include_router(assessment_api.assessment_router, prefix="/api")


# 确保保存自定义角色的目录存在
CUSTOM_AGENTS_DIR = "save/custom_agents"
TEMP_UPLOADS_DIR = "temp_uploads"
os.makedirs(CUSTOM_AGENTS_DIR, exist_ok=True)
os.makedirs(TEMP_UPLOADS_DIR, exist_ok=True)

# 自定义Agent语音目录
CUSTOM_VOICE_DIR = os.path.join("save", "custom_voice")
# 确保目录存在
os.makedirs(CUSTOM_VOICE_DIR, exist_ok=True)

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
    return await normal_chat_flow(request)

@app.post("/api/stream_chat")
async def stream_chat(request: ChatRequest):
    """流式聊天API，支持打字机式回复
    
    Args:
        request: 聊天请求参数
        
    Returns:
        StreamingResponse: 流式响应
    """
    global client
    
    # 打印请求内容以进行调试
    print(f"stream_chat API接收到请求: {request}")
    
    # 使用统一的方式获取完整回复，然后再分批提供给流式接口
    async def generate_stream_response():
        try:
            # 准备对话内容
            conversation_history = request.history or [{"role": "user", "content": request.message}]
            
            # 追踪历史记录
            # 如果是第一次对话，用户的消息已经通过conversation_history.add_dialog添加
            # 如果存在历史记录，则从服务器角度看，该消息是新消息，需要添加到对话历史中
            if request.history:
                # 这意味着前端传递了历史记录，我们需要同步最新的用户消息到conversation_history
                await chat_service.conversation_history.add_dialog(message=request.message, reply="")
            
            model_name = request.model or "gpt-3.5-turbo"
            agent_id = request.agent_id
            message = request.message
            
            # 判断是否是引导式提问
            is_quick_question = request.is_category or False
            
            print(f"处理stream_chat请求: message={request.message}, agent_type={request.agent_type}, agent_id={agent_id}")
            print(f"是否是快捷提问: {is_quick_question}")
            print(f"使用对话历史: {conversation_history}")
            print(f"使用模型: {model_name}")
            
            # 检查是否是结束引导的明确指令
            exit_guidance_keywords = ["结束话题", "结束引导", "不想聊了", "换个话题", "不想继续", "结束对话", "不想讨论这个", "不讨论", "换话题", "算了", "不聊了", "结束"]
            is_exit_guidance = (chat_service.guidance_state["is_guiding"] and 
                           (any(keyword in message for keyword in exit_guidance_keywords) or message.strip() == "结束"))
            
            # 如果用户表示想要结束话题，直接结束引导
            if is_exit_guidance:
                print(f"用户请求结束引导，直接结束：{message}")
                chat_service.guidance_state["confirmed_exit"] = True
                
                # 获取对话轮数
                conversation_turns = len(chat_service.conversation_history.turns)
                print(f"当前对话轮数: {conversation_turns}")
                
                # 根据对话轮数决定是否生成总结
                if conversation_turns > 5:
                    print(f"对话轮数 > 5，生成会话总结")
                    
                    # 获取最近的对话内容用于生成总结（最多5轮）
                    recent_turns = chat_service.conversation_history.turns[-5:]
                    
                    try:
                        # 使用chat_service的方法生成总结
                        summary_response = await chat_service._get_conversation_summary(recent_turns)
                        reply_text = f"{summary_response}\n\n已结束当前话题。您还有其他想讨论的问题吗？"
                    except Exception as e:
                        print(f"生成对话总结时出错: {e}")
                        reply_text = "已结束当前话题。您还有其他想讨论的问题吗？"
                else:
                    # 对话轮数少于5轮，使用默认回复
                    print(f"对话轮数 <= 5，使用默认结束回复")
                    reply_text = "已结束当前话题。您还有其他想讨论的问题吗？"
                
                # 先发送回复类型指示
                yield json.dumps({"type": "start", "content": ""}) + "\n"
                yield json.dumps({"type": "content", "content": reply_text}) + "\n"
                yield json.dumps({"type": "end", "content": ""}) + "\n"
                
                # 重置引导状态
                chat_service._reset_guidance_state()
                
                # 生成语音
                audio_data = None
                if Config.is_tts_enabled() and chat_service.tts_service:
                    try:
                        print("为结束引导回复生成普通TTS...")
                        audio_data = chat_service.tts_service.generate_audio(reply_text)
                        if audio_data and len(audio_data) > 100:
                            base64_audio = base64.b64encode(audio_data).decode('ascii')
                            audio_response = {
                                "type": "audio",
                                "audio_data": base64_audio
                            }
                            yield json.dumps(audio_response) + "\n"
                    except Exception as e:
                        print(f"为结束引导回复生成普通语音时出错: {e}")
                
                if (not audio_data or len(audio_data) < 100) and Config.is_super_tts_enabled() and chat_service.super_tts_service:
                    try:
                        print("为结束引导回复生成超拟人TTS...")
                        audio_data = chat_service.super_tts_service.generate_audio(reply_text)
                        if audio_data and len(audio_data) > 100:
                            base64_audio = base64.b64encode(audio_data).decode('ascii')
                            audio_response = {
                                "type": "audio",
                                "audio_data": base64_audio
                            }
                            yield json.dumps(audio_response) + "\n"
                    except Exception as e:
                        print(f"为结束引导回复生成超拟人语音时出错: {e}")
                
                return
                
            # 处理引导式提问状态
            if is_quick_question and not chat_service.guidance_state["is_guiding"]:
                print(f"开始引导式提问：{message}")
                chat_service.guidance_state["is_guiding"] = True
                chat_service.guidance_state["current_category"] = message
                chat_service.guidance_state["question_count"] = 0
                chat_service.guidance_state["conversation_summary"] = []
                chat_service.guidance_state["off_topic_count"] = 0
                chat_service.guidance_state["last_strategies"] = []
                chat_service.guidance_state["awaiting_exit_confirmation"] = False
                chat_service.guidance_state["confirmed_exit"] = False
            
            # 默认使用常规TTS
            use_f5_tts = False
            
            # 检查是否是自定义角色且启用了F5TTS语音
            if agent_id and agent_id.startswith("custom_"):
                # 检查角色配置中是否有语音文件
                config_path = os.path.join(CUSTOM_AGENTS_DIR, f"{agent_id}.json")
                print(f"检查自定义角色配置: {config_path}")
                
                try:
                    if os.path.exists(config_path):
                        with open(config_path, "r", encoding="utf-8") as f:
                            agent_config = json.load(f)
                        
                        print(f"角色配置内容: {agent_config}")
                        
                        # 无论是否在配置中有voice_file，都尝试查找语音文件
                        # 先检查配置中的路径
                        voice_exists = False
                        voice_file_path = None
                        
                        if "voice_file" in agent_config:
                            voice_file_path = agent_config["voice_file"]
                            print(f"配置中找到语音文件路径: {voice_file_path}")
                        else:
                            print(f"配置中未声明语音文件路径，将尝试通过其他方式查找")
                        
                        # 尝试多种路径解析方式
                        possible_paths = []
                        
                        # 如果配置中有路径，添加到可能路径
                        if voice_file_path:
                            possible_paths.extend([
                                voice_file_path,  # 直接使用配置中的路径
                                os.path.abspath(voice_file_path),  # 作为绝对路径
                                os.path.join(os.getcwd(), voice_file_path),  # 相对于当前工作目录
                                # 尝试从自定义语音目录查找文件名
                                os.path.join(CUSTOM_VOICE_DIR, os.path.basename(voice_file_path))
                            ])
                        
                        # 无论配置如何，总是尝试使用agent_id查找
                        for ext in ['.wav', '.mp3', '.m4a', '.aac']:
                            direct_path = os.path.join(CUSTOM_VOICE_DIR, f"{agent_id}{ext}")
                            possible_paths.append(direct_path)
                        
                        # 检查所有可能的路径
                        for path in possible_paths:
                            print(f"尝试路径: {path}")
                            if os.path.exists(path):
                                voice_file_path = path
                                voice_exists = True
                                print(f"找到有效的语音文件: {voice_file_path}")
                                
                                # 更新配置文件以确保下次能直接找到
                                if not agent_config.get("voice_file") or agent_config["voice_file"] != voice_file_path:
                                    agent_config["voice_file"] = voice_file_path
                                    try:
                                        with open(config_path, "w", encoding="utf-8") as f:
                                            json.dump(agent_config, f, ensure_ascii=False, indent=2)
                                        print(f"已更新配置文件中的语音路径: {voice_file_path}")
                                    except Exception as config_error:
                                        print(f"更新配置文件失败: {config_error}")
                                
                                break
                            
                        if voice_exists:
                            use_f5_tts = True
                            print(f"将使用F5-TTS，语音文件: {voice_file_path}")
                            
                            # 预启动F5TTS服务器
                            f5_server_started = f5_speech_service.start_server_for_agent(agent_id)
                            print(f"F5-TTS服务器启动状态: {f5_server_started}")
                        else:
                            print(f"在所有尝试的路径中均未找到语音文件: {possible_paths}")
                    else:
                        print(f"角色配置文件不存在: {config_path}")
                except Exception as e:
                    print(f"检查语音配置时出错: {e}")
                    import traceback
                    print(traceback.format_exc())
            
            # 设置正确的引导状态标志
            current_is_category = is_quick_question or chat_service.guidance_state["is_guiding"]
            
            # 使用对话历史生成回复
            full_response, audio_data = await chat_service.generate_response(
                conversation_history, 
                model_name,
                stream=False,  # 首先获取完整回复
                agent_id=agent_id,
                is_category=current_is_category  # 传递是否快捷提问的标志
            )
            
            # 如果是引导模式且收到JSON格式的回复，需要提取实际的回复文本
            if chat_service.guidance_state["is_guiding"]:
                try:
                    reply_data = json.loads(full_response)
                    if "reply" in reply_data:
                        # 这是引导模式返回的JSON格式
                        response_text = reply_data["reply"]
                        # 检查是否应该结束引导
                        if reply_data.get("is_summary", False) or chat_service.guidance_state.get("confirmed_exit", False):
                            print("检测到引导结束标记，重置引导状态")
                            chat_service._reset_guidance_state()
                    else:
                        response_text = full_response
                except json.JSONDecodeError:
                    response_text = full_response
            else:
                response_text = full_response
            
            # 将助手的回复添加到对话历史中
            try:
                if message != "SYSTEM_GUIDANCE" and not message.startswith("SYSTEM_"):
                    # 只有普通对话才添加到历史记录，系统消息不添加
                    await chat_service.conversation_history.add_dialog(message="ASSISTANT_REPLY", reply=response_text)
                    print(f"已将助手回复添加到对话历史，当前对话轮数: {len(chat_service.conversation_history.turns)}")
            except Exception as e:
                print(f"添加助手回复到对话历史时出错: {e}")
            
            # 分词发送回复
            tokens = response_text.split(" ")
            
            accumulated_text = ""
            chunk_size = 3  # 每个块的token数量
            
            # 先发送回复类型指示
            yield json.dumps({"type": "start", "content": ""}) + "\n"
            
            # 按块发送回复
            for i in range(0, len(tokens), chunk_size):
                chunk_tokens = tokens[i:i+chunk_size]
                chunk_text = " ".join(chunk_tokens)
                accumulated_text += chunk_text + " "  # 添加空格以确保词之间有间隔
                
                # 发送文本块
                yield json.dumps({"type": "content", "content": chunk_text}) + "\n"
                
                # 小的延迟以模拟打字效果
                await asyncio.sleep(0.05)  # 增加延迟以使打字效果更明显
            
            # 发送表情数据（如果有）
            if hasattr(chat_service.main_agent, 'expression') and chat_service.main_agent.expression:
                yield json.dumps({
                    "type": "metadata", 
                    "expression": chat_service.main_agent.expression
                }) + "\n"
            
            # 发送结束指示
            yield json.dumps({"type": "end", "content": ""}) + "\n"
            
            # 如果使用F5TTS
            if use_f5_tts:
                # 使用F5-TTS生成语音，不需要返回音频数据
                try:
                    if asyncio.iscoroutinefunction(f5_speech_service.generate_speech_async):
                        # 使用异步版本
                        voice_generated = await f5_speech_service.generate_speech_async(agent_id, response_text)
                    else:
                        # 如果异步版本不可用，回退到同步版本
                        voice_generated = f5_speech_service.generate_speech(agent_id, response_text)
                    
                    print(f"F5-TTS语音生成状态: {voice_generated}")
                except Exception as e:
                    print(f"F5-TTS语音生成出错: {e}")
                    import traceback
                    print(traceback.format_exc())
                
                # 发送使用F5-TTS的通知
                yield json.dumps({
                    "type": "f5_tts_notification",
                    "message": "使用F5-TTS流式生成语音"
                }) + "\n"
            
            # 如果有音频数据且不使用F5TTS，处理后发送
            elif audio_data and len(audio_data) > 100:  # 确保音频数据长度合理
                # 对于大型音频数据进行分片处理
                MAX_CHUNK_SIZE = 32 * 1024  # 32KB 分片大小，避免JSON解析问题
                base64_audio = base64.b64encode(audio_data).decode('ascii')
                
                # 检查音频数据大小
                audio_size = len(base64_audio)
                print(f"Base64编码后的音频大小: {audio_size} 字符")
                
                if audio_size > MAX_CHUNK_SIZE:
                    # 如果音频过大，分片发送
                    chunks = []
                    for i in range(0, audio_size, MAX_CHUNK_SIZE):
                        chunks.append(base64_audio[i:i+MAX_CHUNK_SIZE])
                    
                    print(f"音频数据过大，分为 {len(chunks)} 个片段发送")
                    
                    # 发送第一个分片作为开始
                    first_chunk = {
                        "type": "audio_start",
                        "total_chunks": len(chunks),
                        "chunk_index": 0,
                        "audio_chunk": chunks[0]
                    }
                    yield json.dumps(first_chunk) + "\n"
                    
                    # 发送中间分片
                    for i in range(1, len(chunks) - 1):
                        chunk = {
                            "type": "audio_chunk",
                            "chunk_index": i,
                            "audio_chunk": chunks[i]
                        }
                        yield json.dumps(chunk) + "\n"
                    
                    # 发送最后一个分片
                    last_chunk = {
                        "type": "audio_end",
                        "chunk_index": len(chunks) - 1,
                        "audio_chunk": chunks[-1]
                    }
                    yield json.dumps(last_chunk) + "\n"
                else:
                    # 如果音频较小，直接一次性发送
                    audio_response = {
                        "type": "audio",
                        "audio_data": base64_audio
                    }
                    yield json.dumps(audio_response) + "\n"
            
        except Exception as e:
            error_info = str(e)
            print(f"流式聊天出错: {error_info}")
            import traceback
            print(traceback.format_exc())
            
            # 报告错误
            yield json.dumps({
                "type": "error",
                "error": error_info
            }) + "\n"
    
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
                response = await chat_service.get_response(
                    data["content"],
                    data.get("personality")
                )
                await websocket.send_json(response)
                
    except Exception as e:
        print(f"WebSocket错误: {e}")
    finally:
        await websocket.close()

async def normal_chat_flow(request: ChatRequest):
    """正常的聊天流程
    
    Args:
        request: 聊天请求
        
    Returns:
        dict: 聊天响应
    """
    
    # 在对话处理前，检查消息是否有效，如果有效则增加计数
    if not is_meaningless_input(request.message):
        assessment_api.increment_dialog_counter(request.message)
    
    # 对话流程处理
    reply, audio_data, expression, guidance_message = await chat_service.generate_reply(
        request.message, 
        request.session_id,
        agent_type=request.agent_type,
        personality=request.personality,
        is_category=request.is_category
    )
    
    print("-- /api/chat --")
    print("agent_type:", request.agent_type)
    print("personality:", request.personality)
    print("is_category:", request.is_category)
    print("reply:", reply)
    print("expression:", expression)
    if guidance_message:
        print("guidance_message:", guidance_message)

    # 检查是否是自定义角色且启用了F5TTS语音
    use_f5_tts = False
    agent_id = request.agent_type
    
    if agent_id and agent_id.startswith("custom_"):
        # 检查角色配置中是否有语音文件
        config_path = os.path.join(CUSTOM_AGENTS_DIR, f"{agent_id}.json")
        print(f"检查自定义角色配置: {config_path}")
        
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                agent_config = json.load(f)
            
            print(f"角色配置内容: {agent_config}")
            
            # 如果有语音文件，使用F5TTS
            if "voice_file" in agent_config and os.path.exists(agent_config["voice_file"]):
                use_f5_tts = True
                voice_file_path = agent_config["voice_file"]
                print(f"找到有效的语音文件: {voice_file_path}")
                
                # 启动F5TTS服务器并生成语音
                print(f"使用F5TTS为自定义角色{agent_id}生成语音")
                f5_server_started = f5_speech_service.start_server_for_agent(agent_id)
                print(f"F5-TTS服务器启动状态: {f5_server_started}")
                
                if f5_server_started:
                    voice_generated = f5_speech_service.generate_speech(agent_id, reply)
                    print(f"F5-TTS语音生成状态: {voice_generated}")
            else:
                if "voice_file" in agent_config:
                    print(f"语音文件不存在: {agent_config['voice_file']}")
                else:
                    print(f"未配置语音文件")
        else:
            print(f"角色配置文件不存在: {config_path}")
    
    # 只在不使用F5TTS时才传递音频数据
    audio_base64 = ''
    if not use_f5_tts and audio_data and len(audio_data) > 100:
        audio_base64 = base64.b64encode(audio_data).decode('ascii')
    
    response_data = {
        "message": reply,
        "audio": audio_base64,
        "expression": expression,
        "use_f5_tts": use_f5_tts  # 添加标志指示前端是否使用了F5TTS
    }
    
    # 如果有引导决策消息，添加到响应中
    if guidance_message:
        response_data["guidance_message"] = guidance_message
        
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
async def get_tts_settings():
    """获取TTS设置

    Returns:
        dict: TTS设置
    """
    return {
        "enable_tts": Config.ENABLE_TTS,
        "enable_super_tts": Config.ENABLE_SUPER_TTS,
        "tts_voice": Config.TTS_VCN,
        "super_tts_voice": Config.SUPER_TTS_VCN,
        "tts_voice_list": Config.TTS_VOICE_LIST,
        "super_tts_voice_list": Config.SUPER_TTS_VOICE_LIST,
        "tts_speed": Config.TTS_SPEED,
        "typing_speed": Config.TYPING_SPEED,
        "voice_input_mode": getattr(Config, "VOICE_INPUT_MODE", True),
        "voice_timeout": getattr(Config, "VOICE_TIMEOUT", 5)
    }

@app.post("/api/tts_settings")
async def update_tts_settings(settings: TTSSettingsRequest):
    """更新TTS设置

    Args:
        settings: 新的TTS设置

    Returns:
        dict: 更新结果
    """
    try:
        # 检查TTS设置是否有冲突
        if settings.enable_tts and settings.enable_super_tts:
            return {"success": False, "message": "不能同时启用普通TTS和超拟人TTS"}
        
        # 更新启用状态
        Config.ENABLE_TTS = settings.enable_tts
        Config.ENABLE_SUPER_TTS = settings.enable_super_tts
        
        # 更新语音配置
        if settings.tts_voice:
            # 检查是否为有效的TTS音色
            if any(voice["value"] == settings.tts_voice for voice in Config.TTS_VOICE_LIST):
                Config.TTS_VCN = settings.tts_voice
            
        if settings.super_tts_voice:
            # 检查是否为有效的超拟人TTS音色
            if any(voice["value"] == settings.super_tts_voice for voice in Config.SUPER_TTS_VOICE_LIST):
                Config.SUPER_TTS_VCN = settings.super_tts_voice
                
        # 更新语速
        if settings.tts_speed is not None:
            try:
                speed_value = int(settings.tts_speed)
                if 0 <= speed_value <= 100:
                    Config.TTS_SPEED = speed_value
            except (ValueError, TypeError):
                pass
    
        # 更新打字速度
        if settings.typing_speed is not None:
            try:
                typing_value = int(settings.typing_speed)
                if 10 <= typing_value <= 200:
                    Config.TYPING_SPEED = typing_value
            except (ValueError, TypeError):
                pass
        
        # 更新语音输入模式设置
        if settings.voice_input_mode is not None:
            Config.VOICE_INPUT_MODE = settings.voice_input_mode
            
        # 更新语音输入超时设置
        if settings.voice_timeout is not None:
            try:
                timeout_value = int(settings.voice_timeout)
                if 2 <= timeout_value <= 10:
                    Config.VOICE_TIMEOUT = timeout_value
            except (ValueError, TypeError):
                pass

        # 返回成功
        return {
            "success": True,
            "message": "设置更新成功",
            "data": {
                "tts_voice": settings.tts_voice if settings.tts_voice else None,
                "super_tts_voice": settings.super_tts_voice if settings.super_tts_voice else None,
                "enable_tts": settings.enable_tts,
                "enable_super_tts": settings.enable_super_tts,
                "tts_speed": Config.TTS_SPEED,
                "typing_speed": Config.TYPING_SPEED,
                "voice_input_mode": Config.VOICE_INPUT_MODE if hasattr(Config, "VOICE_INPUT_MODE") else True,
                "voice_timeout": Config.VOICE_TIMEOUT if hasattr(Config, "VOICE_TIMEOUT") else 5
            }
        }
    except Exception as e:
        # 处理异常情况
        return {"success": False, "message": f"更新设置失败: {str(e)}"}

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

@app.post("/api/upload_custom_voice")
async def upload_custom_voice(
    file: UploadFile = File(...),
    agent_id: str = Form(None)
):
    """
    上传自定义角色语音
    
    Args:
        file: 上传的音频文件
        agent_id: 角色ID (可选)
        
    Returns:
        dict: 包含上传结果的响应
    """
    try:
        # 验证文件类型
        file_extension = os.path.splitext(file.filename)[1].lower()
        allowed_extensions = ['.wav', '.mp3', '.m4a', '.aac']
        
        if file_extension not in allowed_extensions:
            return JSONResponse(
                content={
                    "success": False,
                    "message": f"不支持的文件类型。请上传以下类型的音频文件: {', '.join(allowed_extensions)}"
                }
            )
        
        # 检查文件大小
        file_size_limit = 5 * 1024 * 1024  # 5MB
        file_content = await file.read()
        
        if len(file_content) > file_size_limit:
            return JSONResponse(
                content={
                    "success": False,
                    "message": f"文件大小超过限制 (5MB)"
                }
            )
        
        # 如果提供了agent_id，检查该角色是否存在
        if agent_id:
            config_path = os.path.join(CUSTOM_AGENTS_DIR, f"{agent_id}.json")
            if not os.path.exists(config_path):
                return JSONResponse(
                    content={
                        "success": False,
                        "message": "指定的角色不存在"
                    }
                )
        
        # 生成临时文件名进行保存
        temp_filename = f"temp_voice_{uuid.uuid4().hex}{file_extension}"
        temp_filepath = os.path.join(CUSTOM_VOICE_DIR, temp_filename)
        
        # 将文件内容写入临时文件
        with open(temp_filepath, "wb") as f:
            f.write(file_content)
            
        return JSONResponse(
            content={
                "success": True,
                "message": "语音上传成功",
                "file_path": temp_filepath,
                "file_name": temp_filename
            }
        )
    except Exception as e:
        print(f"语音上传失败: {e}")
        return JSONResponse(
            content={
                "success": False,
                "message": f"语音上传失败: {str(e)}"
            }
        )

@app.post("/api/bind_voice_to_agent")
async def bind_voice_to_agent(
    agent_id: str = Form(...),
    voice_file: str = Form(...)
):
    """
    将语音绑定到角色
    
    Args:
        agent_id: 角色ID
        voice_file: 临时语音文件名
        
    Returns:
        dict: 包含绑定结果的响应
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
        
        # 检查临时语音文件是否存在
        temp_filepath = os.path.join(CUSTOM_VOICE_DIR, voice_file)
        if not os.path.exists(temp_filepath):
            return JSONResponse(
                content={
                    "success": False,
                    "message": "指定的语音文件不存在"
                }
            )
        
        # 获取文件扩展名
        file_extension = os.path.splitext(voice_file)[1].lower()
        
        # 创建以角色名命名的语音文件
        agent_voice_filename = f"{agent_id}{file_extension}"
        agent_voice_filepath = os.path.join(CUSTOM_VOICE_DIR, agent_voice_filename)
        
        # 复制临时文件到目标位置
        shutil.copy2(temp_filepath, agent_voice_filepath)
        
        # 更新角色配置，添加语音文件路径
        agent_config["voice_file"] = agent_voice_filepath
        
        # 保存更新后的角色配置
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(agent_config, f, ensure_ascii=False, indent=2)
        
        return JSONResponse(
            content={
                "success": True,
                "message": "语音成功绑定到角色",
                "voice_path": agent_voice_filepath
            }
        )
    except Exception as e:
        print(f"绑定语音失败: {e}")
        return JSONResponse(
            content={
                "success": False,
                "message": f"绑定语音失败: {str(e)}"
            }
        )

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

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8666, reload=True)