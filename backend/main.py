from fastapi import FastAPI, WebSocket, UploadFile, File, Body, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import base64
from chat_service import ChatService
from tts import TTSService
from super_tts import SuperTTSService
from config import Config
from speech_service import SpeechService
from qiniu_uploader import QiniuUploader
import uvicorn
import json
import asyncio
import os
import uuid
import shutil
import tempfile
import time
import re
import math
from collections import Counter
import assessment_api  # 导入评估API模块
import video_analyzer  # 导入视频分析模块
# from llm import LLMService  # 注释掉，因为我们使用chat_service中的LLM服务

app = FastAPI()

# CORS设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    agent_type: Optional[str] = None
    personality: Optional[str] = None
    is_category: Optional[bool] = False

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

class TTSSettings(BaseModel):
    enable_tts: bool
    enable_super_tts: bool
    tts_voice: str
    super_tts_voice: str
    tts_voice_list: list
    super_tts_voice_list: list
    tts_speed: int
    typing_speed: int

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

# 初始化视频分析API
video_router = video_analyzer.init_router()
app.include_router(video_router, prefix="/api")

# 确保保存自定义角色的目录存在
CUSTOM_AGENTS_DIR = "save/custom_agents"
TEMP_UPLOADS_DIR = "temp_uploads"
os.makedirs(CUSTOM_AGENTS_DIR, exist_ok=True)
os.makedirs(TEMP_UPLOADS_DIR, exist_ok=True)

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
        request: 聊天请求
        
    Returns:
        StreamingResponse: 流式响应
    """
    async def generate_stream_response():
        try:
            # 验证请求数据
            if not request.message or not request.message.strip():
                yield json.dumps({
                    "type": "metadata",
                    "expression": "生气",
                    "error": "消息内容不能为空"
                }) + "\n"
                
                yield json.dumps({
                    "type": "complete",
                    "content": "请输入有效的消息内容"
                }) + "\n"
                return
            
            # API层也检测是否是无意义输入，避免网络请求开销
            if not request.is_category and is_meaningless_input(request.message):
                print(f"API层检测到无意义输入: '{request.message}'，返回模板回复")
                
                # 根据当前智能体选择合适的模板回复
                agent_type = request.agent_type or "nanaA"
                template_replies = {
                    "nanaA": "喵~？你在说什么呀，我听不懂...",
                    "nanaB": "抱歉，我没有理解你的意思。能请你说得更清楚一些吗？",
                    "nanaC": "咦？这是什么意思呀？再说一次好不好~"
                }
                reply_content = template_replies.get(agent_type, "我没明白你的意思，能说得更清楚些吗？")
                
                # 返回元数据
                yield json.dumps({
                    "type": "metadata",
                    "expression": "疑惑",
                    "message_id": int(time.time() * 1000)
                }) + "\n"
                
                # 逐字发送回复内容
                for char in reply_content:
                    chunk = {
                        "type": "chunk",
                        "content": char
                    }
                    yield json.dumps(chunk) + "\n"
                    await asyncio.sleep(0.01)  # 模拟打字效果
                
                # 发送完成信号
                yield json.dumps({
                    "type": "complete",
                    "content": reply_content
                }) + "\n"
                
                return
            
            # 生成回复
            reply, audio_data, expression, guidance_message = await chat_service.generate_reply(
                request.message, 
                request.session_id,
                agent_type=request.agent_type,
                personality=request.personality,
                is_category=request.is_category
            )
            
            # 用于调试输出
            print("-- /api/stream_chat --")
            print("agent_type:", request.agent_type)
            print("personality:", request.personality)
            print("is_category:", request.is_category)
            print("reply:", reply)
            print("expression:", expression)
            print("audio_data 大小:", len(audio_data) if audio_data else 0, "字节")
            
            # 检查是否获取到有效回复
            if not reply:
                yield json.dumps({
                    "type": "metadata",
                    "expression": "生气",
                    "error": "未能生成有效回复"
                }) + "\n"
                
                yield json.dumps({
                    "type": "complete",
                    "content": "抱歉，我现在无法回答。请稍后再试。"
                }) + "\n"
                return
            
            # 先发送表情和引导消息的元数据
            metadata = {
                "type": "metadata",
                "expression": expression,
                "message_id": int(time.time() * 1000)  # 添加唯一消息ID
            }
            
            if guidance_message:
                metadata["guidance_message"] = guidance_message
                
                # 检查是否有引导决策的音频数据
                guidance_audio = None
                if hasattr(chat_service.main_agent.conversation_history, 'guidance_audio'):
                    guidance_audio = chat_service.main_agent.conversation_history.guidance_audio
                    
                if guidance_audio and len(guidance_audio) > 100:
                    guidance_audio_base64 = base64.b64encode(guidance_audio).decode('ascii')
                    metadata["guidance_audio"] = guidance_audio_base64
                    print(f"引导决策音频已添加到流式响应元数据，大小: {len(guidance_audio)} 字节")
            
            yield json.dumps(metadata) + "\n"
            
            # 如果有音频数据，处理后发送
            if audio_data and len(audio_data) > 100:  # 确保音频数据长度合理
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
                    if len(chunks) > 1:
                        last_chunk = {
                            "type": "audio_end",
                            "chunk_index": len(chunks) - 1,
                            "audio_chunk": chunks[-1]
                        }
                        yield json.dumps(last_chunk) + "\n"
                    
                    print("音频分片发送完成")
                else:
                    # 音频数据不大，一次性发送
                    try:
                        audio_message = {
                            "type": "audio",
                            "audio": base64_audio
                        }
                        yield json.dumps(audio_message) + "\n"
                        print("完整音频数据发送成功")
                    except Exception as audio_error:
                        print(f"发送音频数据时出错: {audio_error}")
            elif not audio_data:
                # 如果没有音频数据，记录这个情况
                print("没有收到音频数据，跳过音频发送")
            
            # 逐字发送回复内容，确保每个字符都是有效的
            for char in reply:
                chunk = {
                    "type": "chunk",
                    "content": char
                }
                yield json.dumps(chunk) + "\n"
                
                # 使用配置中的打字速度，转换为秒，添加错误处理
                try:
                    typing_speed = Config.TYPING_SPEED
                    # 确保打字速度在合理范围内
                    if not isinstance(typing_speed, int) or typing_speed < 10:
                        typing_speed = 38  # 使用默认值
                    elif typing_speed > 200:
                        typing_speed = 200
                        
                    typing_delay = typing_speed / 1000.0
                    # 确保延迟时间不会太长
                    if typing_delay > 0.2:
                        print(f"打字延迟过长 ({typing_delay}秒)，限制为0.2秒")
                        typing_delay = 0.2
                        
                    await asyncio.sleep(typing_delay)
                except Exception as e:
                    print(f"处理打字延迟时出错: {e}")
                    # 使用默认延迟
                    await asyncio.sleep(0.038)
            
            # 发送完成标记
            complete = {
                "type": "complete"
            }
            
            yield json.dumps(complete) + "\n"
            
        except asyncio.CancelledError:
            # 处理客户端取消请求
            print("客户端取消了请求")
            raise
        except Exception as e:
            # 处理所有其他异常
            print(f"流式聊天生成出错: {str(e)}")
            error_metadata = {
                "type": "metadata",
                "expression": "生气",
                "error": "服务器处理错误"
            }
            yield json.dumps(error_metadata) + "\n"
            
            error_message = {
                "type": "complete",
                "content": "抱歉，处理您的请求时出现了错误。请稍后再试。"
            }
            yield json.dumps(error_message) + "\n"
    
    return StreamingResponse(
        generate_stream_response(),
        media_type="application/x-ndjson"
    )

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

    audio_base64 = base64.b64encode(audio_data).decode('ascii') if audio_data else ''
    
    response_data = {
        "message": reply,
        "audio": audio_base64,
        "expression": expression
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

# 这里添加TTS设置的API端点
@app.get("/api/tts_settings")
async def get_tts_settings():
    """获取当前TTS设置
    
    Returns:
        dict: 包含TTS设置的响应
    """
    return JSONResponse(
        content={
            "enable_tts": Config.ENABLE_TTS,
            "enable_super_tts": Config.ENABLE_SUPER_TTS,
            "tts_voice": Config.TTS_VCN,
            "super_tts_voice": Config.SUPER_TTS_VCN,
            "tts_voice_list": Config.TTS_VOICE_LIST,
            "super_tts_voice_list": Config.SUPER_TTS_VOICE_LIST,
            "tts_speed": Config.TTS_SPEED,
            "typing_speed": Config.TYPING_SPEED
        }
    )

@app.post("/api/tts_settings")
async def update_tts_settings(settings: TTSSettingsRequest):
    """更新TTS设置
    
    Args:
        settings: 新的TTS设置
        
    Returns:
        dict: 包含更新结果的响应
    """
    try:
        # 只能启用一种TTS，或者都不启用
        if settings.enable_tts and settings.enable_super_tts:
            return JSONResponse(
                content={
                    "success": False,
                    "message": "只能启用一种TTS服务"
                }
            )
            
        # 更新配置
        Config.ENABLE_TTS = settings.enable_tts
        Config.ENABLE_SUPER_TTS = settings.enable_super_tts
        
        # 更新音色配置
        if settings.tts_voice:
            # 验证音色是否在列表中
            if any(voice["value"] == settings.tts_voice for voice in Config.TTS_VOICE_LIST):
                Config.TTS_VCN = settings.tts_voice
        
        if settings.super_tts_voice:
            # 验证音色是否在列表中
            if any(voice["value"] == settings.super_tts_voice for voice in Config.SUPER_TTS_VOICE_LIST):
                Config.SUPER_TTS_VCN = settings.super_tts_voice
        
        # 更新语速设置
        updated_tts_speed = None
        if settings.tts_speed is not None:
            try:
                # 确保值是整数类型
                speed_value = int(settings.tts_speed)
                # 验证语速值是否在有效范围内
                if 0 <= speed_value <= 100:
                    Config.TTS_SPEED = speed_value
                    updated_tts_speed = speed_value
                else:
                    print(f"语速值超出范围(0-100): {speed_value}")
                    Config.TTS_SPEED = max(0, min(100, speed_value))  # 限制在有效范围内
                    updated_tts_speed = Config.TTS_SPEED
            except (ValueError, TypeError) as e:
                print(f"语速值类型错误: {e}")
                # 如果转换失败，使用默认值
                Config.TTS_SPEED = 50
        
        # 更新打字速度设置
        updated_typing_speed = None
        if settings.typing_speed is not None:
            try:
                # 确保值是整数类型
                typing_value = int(settings.typing_speed)
                # 验证打字速度值是否在有效范围内 (10-200ms)
                if 10 <= typing_value <= 200:
                    Config.TYPING_SPEED = typing_value
                    updated_typing_speed = typing_value
                else:
                    print(f"打字速度值超出范围(10-200): {typing_value}")
                    Config.TYPING_SPEED = max(10, min(200, typing_value))  # 限制在有效范围内
                    updated_typing_speed = Config.TYPING_SPEED
            except (ValueError, TypeError) as e:
                print(f"打字速度值类型错误: {e}")
                # 如果转换失败，使用默认值
                Config.TYPING_SPEED = 38
        
        # 使用刷新服务方法，确保使用最新的音色配置
        chat_service._refresh_tts_services()
            
        print(f"设置已更新: TTS={Config.ENABLE_TTS}, SuperTTS={Config.ENABLE_SUPER_TTS}, 语速={Config.TTS_SPEED}, 打字速度={Config.TYPING_SPEED}")
        
        # 将更新后的设置写入配置文件
        if updated_tts_speed is not None or updated_typing_speed is not None:
            await update_config_file(
                tts_speed=updated_tts_speed,
                typing_speed=updated_typing_speed,
                tts_voice=settings.tts_voice if settings.tts_voice else None,
                super_tts_voice=settings.super_tts_voice if settings.super_tts_voice else None,
                enable_tts=settings.enable_tts,
                enable_super_tts=settings.enable_super_tts
            )
            
        return JSONResponse(
            content={
                "success": True,
                "message": "TTS设置已更新并写入配置文件",
                "enable_tts": Config.ENABLE_TTS,
                "enable_super_tts": Config.ENABLE_SUPER_TTS,
                "tts_voice": Config.TTS_VCN,
                "super_tts_voice": Config.SUPER_TTS_VCN,
                "tts_speed": Config.TTS_SPEED,
                "typing_speed": Config.TYPING_SPEED
            }
        )
    except Exception as e:
        print(f"更新TTS设置失败: {e}")
        return JSONResponse(
            content={
                "success": False,
                "message": f"更新TTS设置失败: {str(e)}"
            }
        )

async def update_config_file(tts_speed=None, typing_speed=None, tts_voice=None, 
                           super_tts_voice=None, enable_tts=None, enable_super_tts=None):
    """更新配置文件中的TTS设置
    
    Args:
        tts_speed: 语速值
        typing_speed: 打字速度值
        tts_voice: TTS音色
        super_tts_voice: 超拟人TTS音色
        enable_tts: 是否启用普通TTS
        enable_super_tts: 是否启用超拟人TTS
    """
    try:
        config_file_path = os.path.join(os.path.dirname(__file__), 'config.py')
        
        # 读取当前配置文件内容
        with open(config_file_path, 'r', encoding='utf-8') as file:
            config_content = file.read()
        
        # 更新配置内容
        if tts_speed is not None:
            # 使用正则表达式替换TTS_SPEED的值
            config_content = re.sub(
                r'TTS_SPEED\s*=\s*\d+',
                f'TTS_SPEED = {tts_speed}',
                config_content
            )
            
        if typing_speed is not None:
            # 使用正则表达式替换TYPING_SPEED的值
            config_content = re.sub(
                r'TYPING_SPEED\s*=\s*\d+',
                f'TYPING_SPEED = {typing_speed}',
                config_content
            )
            
        if tts_voice is not None:
            # 使用正则表达式替换TTS_VCN的值
            config_content = re.sub(
                r'TTS_VCN\s*=\s*"[^"]+"',
                f'TTS_VCN = "{tts_voice}"',
                config_content
            )
            
        if super_tts_voice is not None:
            # 使用正则表达式替换SUPER_TTS_VCN的值
            config_content = re.sub(
                r'SUPER_TTS_VCN\s*=\s*"[^"]+"',
                f'SUPER_TTS_VCN = "{super_tts_voice}"',
                config_content
            )
            
        if enable_tts is not None:
            # 使用正则表达式替换ENABLE_TTS的值
            config_content = re.sub(
                r'ENABLE_TTS\s*=\s*(True|False)',
                f'ENABLE_TTS = {str(enable_tts)}',
                config_content
            )
            
        if enable_super_tts is not None:
            # 使用正则表达式替换ENABLE_SUPER_TTS的值
            config_content = re.sub(
                r'ENABLE_SUPER_TTS\s*=\s*(True|False)',
                f'ENABLE_SUPER_TTS = {str(enable_super_tts)}',
                config_content
            )
        
        # 写入更新后的配置文件
        with open(config_file_path, 'w', encoding='utf-8') as file:
            file.write(config_content)
            
        print(f"配置文件已更新：{config_file_path}")
        
    except Exception as e:
        print(f"更新配置文件失败: {e}")
        raise

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
        
        # 根据配置决定使用哪个TTS服务
        if Config.is_tts_enabled() and chat_service.tts_service:
            try:
                print("欢迎语TTS: 尝试使用普通TTS生成语音...")
                welcome_audio = chat_service.tts_service.generate_audio(welcome_text)
                if welcome_audio and len(welcome_audio) > 100:
                    print(f"欢迎语普通TTS生成成功，音频大小: {len(welcome_audio)} 字节")
                else:
                    print("欢迎语普通TTS生成失败: 生成的音频数据无效或过小")
            except Exception as e:
                print(f"生成欢迎语普通语音时出错: {e}")
        elif Config.is_super_tts_enabled() and chat_service.super_tts_service:
            try:
                print("欢迎语TTS: 尝试使用超拟人TTS生成语音...")
                welcome_audio = chat_service.super_tts_service.generate_audio(welcome_text)
                if welcome_audio and len(welcome_audio) > 100:
                    print(f"欢迎语超拟人TTS生成成功，音频大小: {len(welcome_audio)} 字节")
                else:
                    print("欢迎语超拟人TTS生成失败: 生成的音频数据无效或过小")
            except Exception as e:
                print(f"生成欢迎语超拟人语音时出错: {e}")
        
        audio_base64 = base64.b64encode(welcome_audio).decode('ascii') if welcome_audio else ''
        
        return JSONResponse(
            content={
                "success": True,
                "audio": audio_base64
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
            
        return result
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"视频上传处理失败: {str(e)}",
                "data": None
            }
        )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8666, reload=True)