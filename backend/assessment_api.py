from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse
import os
import uuid
import shutil
import asyncio
from datetime import datetime
from typing import Dict
import markdown
import tempfile
import re
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListItem, ListFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm

# 从主应用导入所需服务和函数
# 这些需要在主应用中初始化并传递给路由器
# 此处为示例，实际使用时需调整
chat_service = None
extract_text_from_file = None
is_meaningless_input = None

# 创建路由器
assessment_router = APIRouter()

# 对话计数器和评估状态
DIALOG_COUNTER = 0
ASSESSMENT_READY = False

@assessment_router.get("/assessment_status")
async def get_assessment_status():
    """获取心理评估状态
    
    Returns:
        dict: 包含评估状态的响应
    """
    global DIALOG_COUNTER, ASSESSMENT_READY
    
    return JSONResponse(
        content={
            "success": True,
            "assessment_ready": ASSESSMENT_READY,
            "dialog_count": DIALOG_COUNTER
        }
    )

@assessment_router.post("/emotional_assessment")
async def emotional_assessment(file: UploadFile = File(...)):
    """上传PDF或图片文件进行情绪评估
    
    Args:
        file: 上传的文件，支持PDF、图片和文本文件
        
    Returns:
        dict: 包含处理结果的响应
    """
    try:
        # 检查文件类型
        file_extension = os.path.splitext(file.filename)[1].lower()
        supported_formats = ['.pdf', '.txt', '.doc', '.docx', '.png', '.jpg', '.jpeg']
        
        if file_extension not in supported_formats:
            return JSONResponse(
                content={
                    "success": False,
                    "message": f"不支持的文件格式，仅支持以下格式：{', '.join(supported_formats)}"
                }
            )
        
        # 确保上传目录存在
        os.makedirs("temp_uploads", exist_ok=True)
        
        # 保存上传的文件
        temp_file_path = os.path.join("temp_uploads", f"{uuid.uuid4()}{file_extension}")
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 提取文本内容
        file_content = extract_text_from_file(temp_file_path, file_extension)
        
        if not file_content or file_content.startswith("缺少") or file_content == "不支持的文件格式":
            return JSONResponse(
                content={
                    "success": False,
                    "message": f"文件内容提取失败或文件为空: {file_content}"
                }
            )
            
        # 使用chat_service中的LLM服务提取情绪信息并更新用户信息
        prompt = f"""请从以下检测报告中提取并分析量化数据，综合评估用户的心理状态。

基于以下维度进行分析：
1. 基本信息：提取姓名、性别、年龄等基本信息
2. 综合结果：分析活力状态和总体建议
3. 异常指标分析：文本中可能包含以下五个主要指标的数值，请提取并分析：
   - 攻击性/攻击倾向: 数值及其正常范围（通常为20-50），分析偏高或偏低的影响
   - 自信: 数值及其正常范围（通常为50-80），分析偏高或偏低的影响
   - 能量/活力: 数值及其正常范围（通常为20-40），分析偏高或偏低的影响
   - 压力: 数值及其正常范围（通常为15-45），分析偏高或偏低的影响
   - 抑郁: 数值及其正常范围（通常为10-30），分析偏高或偏低的影响
4. 潜在问题与建议：识别报告中的潜在心理问题，并提供相应建议
5. 数据矛盾点：指出报告中可能存在的数据不一致或错误
6. 整体结论：对用户当前心理状态给出整体评价

特别优先处理：文件内容末尾部分会包含"结构化指标数据"、"括号指标数据"和"关键指标数据"部分，这些是系统已经预处理并标准化的数据，提取准确度更高，请特别关注这部分数据作为主要分析依据。

请提供清晰的分析结果，格式如下：
```
关键信息总结：
[总结基本信息和主要发现]

异常指标分析：
攻击性: [数值] (正常范围20-50) - [分析影响]
自信: [数值] (正常范围50-80) - [分析影响]
能量: [数值] (正常范围20-40) - [分析影响]
压力: [数值] (正常范围15-45) - [分析影响]
抑郁: [数值] (正常范围10-30) - [分析影响]

潜在问题与建议：
[识别问题并提供建议]

综合结论：
[对用户心理状态的整体评价]
```

报告内容：
{file_content[:8000]}  # 增加文本长度上限以包含更多内容
"""
        
        # 使用chat_service中的llm_service
        analysis = await chat_service.llm_service.async_chat(prompt)
        
        # 将分析结果转换为用户信息格式
        user_info = f"""心理状态: 
{analysis}
"""
        
        # 更新用户信息
        from user_info_processor import UserInfoProcessor
        user_processor = UserInfoProcessor()
        user_processor.save_user_info(user_info)
        
        # 删除临时文件
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        
        return JSONResponse(
            content={
                "success": True,
                "message": "情绪评估完成，用户信息已更新"
            }
        )
    
    except Exception as e:
        print(f"情绪评估处理失败: {e}")
        return JSONResponse(
            content={
                "success": False,
                "message": f"处理失败: {str(e)}"
            }
        )

@assessment_router.get("/psychological_assessment")
async def psychological_assessment():
    """生成心理评估报告
    
    Returns:
        StreamingResponse: PDF报告文件流
    """
    global ASSESSMENT_READY
    
    if not ASSESSMENT_READY:
        return JSONResponse(
            content={
                "success": False,
                "message": "心理评估尚未就绪，需要20轮有效对话"
            },
            status_code=400
        )
    
    try:
        # 读取用户信息
        from user_info_processor import UserInfoProcessor
        user_processor = UserInfoProcessor()
        user_info = user_processor._load_user_info()
        
        if not user_info:
            return JSONResponse(
                content={
                    "success": False,
                    "message": "未找到用户信息"
                },
                status_code=404
            )
        
        # 读取心理评估提示词
        xinli_agent_path = os.path.join("prompts", "xinli_agent.txt")
        with open(xinli_agent_path, "r", encoding="utf-8") as f:
            xinli_prompt = f.read()
            
        # 构建完整提示词
        full_prompt = f"""{xinli_prompt}

## 任务
根据以下用户信息，生成一份全面、专业的心理评估报告。报告应包含对用户心理状态的评估、可能的心理问题诊断、具体的改善建议以及发展预测。

### 用户信息
{user_info}

### 特别说明
如果用户信息中包含"心理状态"部分，请特别关注这些数据，它来自于用户上传的心理状态检测报告，包含了量化的心理指标分析。

### 报告格式要求
1. 标题：心理测评报告
2. 基本信息：包括用户基本资料
3. 评估摘要：简要概括用户的心理健康状况
4. 详细分析：
   - 如果有心理状态检测数据，按照检测报告中的量化指标（如攻击性、自信、能量等）进行分析
   - 如果没有心理状态检测数据，按照一般心理维度（情绪状态、压力水平、社交状态等）进行分析
5. 诊断结果：指出可能存在的心理问题
6. 改善建议：针对性提出具体可行的改善方案
7. 发展预测：预测用户未来心理发展趋势
8. 总结建议：综合所有分析，给出总体建议

请以Markdown格式生成报告，使用# ## ###等标题层级，并合理使用列表、强调等格式。
"""
        
        # 使用LLM生成报告
        report_md = await chat_service.llm_service.async_chat(full_prompt)
        
        # 使用ReportLab将Markdown转换为PDF
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
            temp_pdf_path = temp_pdf.name
        
        # 解析Markdown文本
        styles = getSampleStyleSheet()
        
        # 创建自定义样式
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Title'],
            fontSize=24,
            alignment=1,  # 居中
            spaceAfter=20,
        )
        
        heading1_style = ParagraphStyle(
            'Heading1',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=12,
            spaceBefore=24,
            textColor=colors.darkblue,
        )
        
        heading2_style = ParagraphStyle(
            'Heading2',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=8,
            spaceBefore=16,
            textColor=colors.darkslategray,
        )
        
        heading3_style = ParagraphStyle(
            'Heading3',
            parent=styles['Heading3'],
            fontSize=14,
            spaceAfter=6,
            spaceBefore=12,
            textColor=colors.dimgrey,
        )
        
        normal_style = ParagraphStyle(
            'Normal',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=10,
        )
        
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.grey,
            alignment=1,  # 居中
            spaceBefore=36,
        )
        
        # 定义Markdown解析函数
        def convert_markdown_to_reportlab(md_text):
            """将Markdown文本转换为ReportLab元素列表"""
            elements = []
            
            # 按行解析Markdown
            lines = md_text.split('\n')
            i = 0
            
            current_list_items = []
            in_list = False
            
            while i < len(lines):
                line = lines[i].strip()
                
                # 标题处理
                if line.startswith('# '):
                    if in_list:
                        # 结束之前的列表
                        elements.append(ListFlowable(current_list_items, bulletType='bullet'))
                        current_list_items = []
                        in_list = False
                    
                    text = line[2:].strip()
                    elements.append(Paragraph(text, title_style))
                
                elif line.startswith('## '):
                    if in_list:
                        # 结束之前的列表
                        elements.append(ListFlowable(current_list_items, bulletType='bullet'))
                        current_list_items = []
                        in_list = False
                    
                    text = line[3:].strip()
                    elements.append(Paragraph(text, heading1_style))
                
                elif line.startswith('### '):
                    if in_list:
                        # 结束之前的列表
                        elements.append(ListFlowable(current_list_items, bulletType='bullet'))
                        current_list_items = []
                        in_list = False
                    
                    text = line[4:].strip()
                    elements.append(Paragraph(text, heading2_style))
                
                elif line.startswith('#### '):
                    if in_list:
                        # 结束之前的列表
                        elements.append(ListFlowable(current_list_items, bulletType='bullet'))
                        current_list_items = []
                        in_list = False
                    
                    text = line[5:].strip()
                    elements.append(Paragraph(text, heading3_style))
                
                # 列表项处理
                elif line.startswith('- ') or line.startswith('* '):
                    text = line[2:].strip()
                    # 处理嵌套的强调标记
                    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)  # 粗体
                    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)       # 斜体
                    
                    current_list_items.append(ListItem(Paragraph(text, normal_style)))
                    in_list = True
                
                # 数字列表
                elif re.match(r'^\d+\.\s', line):
                    text = re.sub(r'^\d+\.\s', '', line).strip()
                    # 处理嵌套的强调标记
                    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)  # 粗体
                    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)       # 斜体
                    
                    current_list_items.append(ListItem(Paragraph(text, normal_style)))
                    in_list = True
                
                # 段落处理
                elif line:
                    if in_list:
                        # 结束之前的列表
                        elements.append(ListFlowable(current_list_items, bulletType='bullet'))
                        current_list_items = []
                        in_list = False
                    
                    # 处理强调标记
                    line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)  # 粗体
                    line = re.sub(r'\*(.*?)\*', r'<i>\1</i>', line)       # 斜体
                    
                    elements.append(Paragraph(line, normal_style))
                
                # 空行处理
                elif not line and not in_list:
                    elements.append(Spacer(1, 0.2 * cm))
                
                i += 1
            
            # 处理最后的列表项（如果有）
            if in_list:
                elements.append(ListFlowable(current_list_items, bulletType='bullet'))
            
            # 添加页脚
            elements.append(Paragraph("本报告由AI助手生成，仅供参考，不构成医疗建议", footer_style))
            elements.append(Paragraph(f"生成日期：{datetime.now().strftime('%Y年%m月%d日')}", footer_style))
            
            return elements
        
        # 创建PDF文档
        buffer = BytesIO()
        doc = SimpleDocTemplate(temp_pdf_path, pagesize=A4, 
                               rightMargin=2*cm, leftMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
        
        # 将Markdown转换为ReportLab元素并生成PDF
        elements = convert_markdown_to_reportlab(report_md)
        doc.build(elements)
        
        # 返回PDF文件
        async def file_sender():
            with open(temp_pdf_path, 'rb') as f:
                yield await asyncio.to_thread(f.read)
            # 删除临时文件
            os.unlink(temp_pdf_path)
        
        return StreamingResponse(
            file_sender(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=psychological_assessment.pdf"
            }
        )
            
    except Exception as e:
        print(f"生成心理评估报告失败: {e}")
        return JSONResponse(
            content={
                "success": False,
                "message": f"生成报告失败: {str(e)}"
            },
            status_code=500
        )

@assessment_router.post("/parse_document")
async def parse_document(file: UploadFile = File(...)):
    """上传文件并返回解析后的原始文本内容（用于调试）
    
    Args:
        file: 上传的文件，支持PDF、图片和文本文件
        
    Returns:
        dict: 包含解析结果的响应
    """
    try:
        # 检查文件类型
        file_extension = os.path.splitext(file.filename)[1].lower()
        supported_formats = ['.pdf', '.txt', '.doc', '.docx', '.png', '.jpg', '.jpeg']
        
        if file_extension not in supported_formats:
            return JSONResponse(
                content={
                    "success": False,
                    "message": f"不支持的文件格式，仅支持以下格式：{', '.join(supported_formats)}"
                }
            )
        
        # 确保上传目录存在
        os.makedirs("temp_uploads", exist_ok=True)
        
        # 保存上传的文件
        temp_file_path = os.path.join("temp_uploads", f"{uuid.uuid4()}{file_extension}")
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 提取文本内容
        file_content = extract_text_from_file(temp_file_path, file_extension)
        
        # 删除临时文件
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        
        if not file_content or file_content.startswith("缺少") or file_content == "不支持的文件格式":
            return JSONResponse(
                content={
                    "success": False,
                    "message": f"文件内容提取失败或文件为空: {file_content}"
                }
            )
        
        return JSONResponse(
            content={
                "success": True,
                "text": file_content
            }
        )
    
    except Exception as e:
        print(f"文档解析失败: {e}")
        return JSONResponse(
            content={
                "success": False,
                "message": f"处理失败: {str(e)}"
            }
        )

def increment_dialog_counter(message: str):
    """增加有效对话计数
    
    Args:
        message: 用户消息
    """
    global DIALOG_COUNTER, ASSESSMENT_READY
    
    # 检查是否为有效消息
    if chat_service and not is_meaningless_input(message):
        DIALOG_COUNTER += 1
        print(f"对话计数增加: {DIALOG_COUNTER}")
        # 当对话数达到20轮时，设置评估状态为就绪
        if DIALOG_COUNTER >= 20 and not ASSESSMENT_READY:
            ASSESSMENT_READY = True
            print(f"对话计数达到 {DIALOG_COUNTER}，心理评估已就绪")

def init_router(app_chat_service, app_extract_text_fn, app_is_meaningless_input_fn):
    """初始化路由器，设置所需的服务和函数
    
    Args:
        app_chat_service: 主应用的聊天服务
        app_extract_text_fn: 主应用的文本提取函数
        app_is_meaningless_input_fn: 主应用的无意义输入判断函数
    """
    global chat_service, extract_text_from_file, is_meaningless_input
    chat_service = app_chat_service
    extract_text_from_file = app_extract_text_fn
    is_meaningless_input = app_is_meaningless_input_fn
    return assessment_router 