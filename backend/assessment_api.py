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
import multiprocessing
import threading

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
# 评估处理状态追踪
PROCESSING_ASSESSMENT = False
PROCESSING_START_TIME = None

@assessment_router.get("/assessment_status")
async def get_assessment_status():
    """获取心理评估状态
    
    Returns:
        dict: 包含评估状态的响应
    """
    global DIALOG_COUNTER, ASSESSMENT_READY, PROCESSING_ASSESSMENT
    
    return JSONResponse(
        content={
            "success": True,
            "assessment_ready": ASSESSMENT_READY,
            "dialog_count": DIALOG_COUNTER,
            "processing_assessment": PROCESSING_ASSESSMENT
        }
    )

@assessment_router.get("/latest_assessment")
async def get_latest_assessment():
    """获取最新的情绪评估状态
    
    Returns:
        dict: 包含最新情绪评估状态的响应
    """
    try:
        # 检查save/assessments目录是否存在
        assessment_dir = os.path.join("save", "assessments")
        if not os.path.exists(assessment_dir):
            return JSONResponse(
                content={
                    "success": True,
                    "has_assessment": False,
                    "message": "未找到情绪评估记录"
                }
            )
        
        # 获取目录中的所有JSON文件
        assessment_files = [f for f in os.listdir(assessment_dir) if f.endswith('.json')]
        
        # 如果没有文件，返回没有评估
        if not assessment_files:
            return JSONResponse(
                content={
                    "success": True,
                    "has_assessment": False,
                    "message": "未找到情绪评估记录"
                }
            )
        
        # 按照文件名排序（文件名包含时间戳）
        assessment_files.sort(reverse=True)
        
        # 获取最新的评估文件
        latest_file = assessment_files[0]
        
        return JSONResponse(
            content={
                "success": True,
                "has_assessment": True,
                "file_path": os.path.join(assessment_dir, latest_file),
                "file_name": latest_file,
                "created_at": latest_file.replace("assessment_", "").replace(".json", "")
            }
        )
    
    except Exception as e:
        print(f"获取最新评估状态失败: {e}")
        return JSONResponse(
            content={
                "success": False,
                "message": f"获取评估状态失败: {str(e)}"
            }
        )

@assessment_router.get("/assessment_results")
async def get_assessment_results():
    """获取情绪评估结果
    
    Returns:
        dict: 包含情绪评估结果的响应
    """
    try:
        # 获取最新的评估文件
        assessment_dir = os.path.join("save", "assessments")
        if not os.path.exists(assessment_dir):
            return JSONResponse(
                content={
                    "success": False,
                    "message": "未找到情绪评估记录"
                }
            )
        
        # 获取目录中的所有JSON文件
        assessment_files = [f for f in os.listdir(assessment_dir) if f.endswith('.json')]
        
        # 如果没有文件，返回没有评估
        if not assessment_files:
            return JSONResponse(
                content={
                    "success": False,
                    "message": "未找到情绪评估记录"
                }
            )
        
        # 按照文件名排序（文件名包含时间戳）
        assessment_files.sort(reverse=True)
        
        # 获取最新的评估文件
        latest_file = assessment_files[0]
        file_path = os.path.join(assessment_dir, latest_file)
        
        # 读取JSON文件内容
        import json
        with open(file_path, "r", encoding="utf-8") as f:
            assessment_data = json.load(f)
        
        return JSONResponse(
            content={
                "success": True,
                "results": assessment_data,
                "file_name": latest_file,
                "created_at": latest_file.replace("assessment_", "").replace(".json", "")
            }
        )
    
    except Exception as e:
        print(f"获取评估结果失败: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            content={
                "success": False,
                "message": f"获取评估结果失败: {str(e)}"
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
    global PROCESSING_ASSESSMENT, PROCESSING_START_TIME
    
    # 如果当前已经有正在处理的评估，拒绝新的请求
    if PROCESSING_ASSESSMENT:
        return JSONResponse(
            content={
                "success": False,
                "message": "当前已有情绪评估正在处理中，请稍后再试"
            },
            status_code=429  # Too Many Requests
        )
    
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
        
        # 快速验证文件内容是否可以提取
        file_content = extract_text_from_file(temp_file_path, file_extension)
        
        if not file_content or file_content.startswith("缺少") or file_content == "不支持的文件格式":
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                
            return JSONResponse(
                content={
                    "success": False,
                    "message": f"文件内容提取失败或文件为空: {file_content}"
                }
            )
        
        # 设置评估处理状态
        PROCESSING_ASSESSMENT = True
        PROCESSING_START_TIME = datetime.now()
        
        # 启动后台线程进行详细分析
        assessment_thread = threading.Thread(
            target=process_assessment_in_background,
            args=(temp_file_path, file_extension, file_content),
            daemon=True
        )
        assessment_thread.start()
        
        # 立即返回成功响应，让用户知道文件已接收并开始处理
        return JSONResponse(
            content={
                "success": True,
                "message": "文件已上传，正在后台处理分析",
                "file_id": os.path.basename(temp_file_path),
                "processing": True
            }
        )
    
    except Exception as e:
        # 如果处理过程中出错，重置处理状态
        PROCESSING_ASSESSMENT = False
        PROCESSING_START_TIME = None
        
        print(f"情绪评估处理失败: {e}")
        return JSONResponse(
            content={
                "success": False,
                "message": f"处理失败: {str(e)}"
            }
        )

def process_assessment_in_background(temp_file_path, file_extension, file_content):
    """在后台处理情绪评估分析
    
    Args:
        temp_file_path: 临时文件路径
        file_extension: 文件扩展名
        file_content: 初步提取的文件内容
    """
    global PROCESSING_ASSESSMENT, PROCESSING_START_TIME
    
    try:
        print(f"开始后台处理情绪评估: {os.path.basename(temp_file_path)}")
        
        # 进行更深入的报告分析
        try:
            from config import Config
            
            # 检查是否可以使用增强的图像分析
            enhanced_analysis = ""
            if Config.VISION_MODEL_ENABLED and file_extension == '.pdf':
                print("对PDF进行增强图像分析...")
                # 如果是PDF，使用专用的视觉分析
                try:
                    from PyPDF2 import PdfReader
                    import fitz  # PyMuPDF
                    import base64
                    import cv2
                    import numpy as np
                    from pdf2image import convert_from_path
                    
                    # PDF页面转为图像进行分析
                    images = convert_from_path(temp_file_path, dpi=300)
                    
                    # 选择关键页面进行深度分析（通常报告中的图表/数据表在前几页）
                    # 如果PDF很短，分析所有页面；否则只分析前5页
                    pages_to_analyze = min(len(images), 5)
                    
                    for i in range(pages_to_analyze):
                        # 保存图像到临时文件
                        temp_img_path = f"temp_uploads/enhanced_page_{i+1}.png"
                        images[i].save(temp_img_path, "PNG")
                        
                        # 使用视觉模型分析
                        if chat_service and chat_service.llm_service and hasattr(chat_service.llm_service, 'analyze_image'):
                            with open(temp_img_path, "rb") as img_file:
                                img_base64 = base64.b64encode(img_file.read()).decode('utf-8')
                            
                            custom_prompt = f"""请详细分析这张情绪/心理评估报告图像，重点是:

1. 提取所有关键指标值，特别是"攻击性"、"自信"、"能量/活力"、"压力"、"抑郁"等，以及它们的数值
2. 识别每个指标的正常范围和当前值的意义（偏高/偏低/正常）
3. 解读图表、条形图或雷达图中的数据模式
4. 提取任何文字形式的结论或建议
5. 忽略页面上的装饰元素或广告

只关注与情绪状态或心理评估直接相关的数据。这是报告的第{i+1}页，请尽可能准确地提取所有数值型数据。"""
                            
                            # 使用同步版本的analyze_image，因为我们已经在后台线程中
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            image_analysis = loop.run_until_complete(chat_service.llm_service.analyze_image(img_base64, custom_prompt))
                            loop.close()
                            
                            if image_analysis and len(image_analysis.strip()) > 20:
                                enhanced_analysis += f"\n\n===== 第{i+1}页深度分析 =====\n{image_analysis}\n"
                        
                        # 清理临时文件
                        if os.path.exists(temp_img_path):
                            os.remove(temp_img_path)
                
                except Exception as pdf_analysis_error:
                    print(f"PDF页面分析错误: {pdf_analysis_error}")
                
                # 如果获得了增强分析，添加到文件内容中
                if enhanced_analysis:
                    file_content += "\n\n===增强图像分析结果===\n" + enhanced_analysis
            
        except Exception as enhanced_error:
            print(f"增强分析出错: {enhanced_error}")
        
        # 读取心理医生代理提示词
        xinli_agent_path = os.path.join("prompts", "xinli_agent.txt")
        try:
            with open(xinli_agent_path, "r", encoding="utf-8") as f:
                xinli_prompt = f.read()
        except Exception as e:
            xinli_prompt = "你是一位专业的精神心理科医师，擅长分析心理评估报告并提供专业建议。"
            print(f"心理医生代理提示词读取失败: {e}")
        
        # 使用chat_service中的LLM服务提取情绪信息并更新用户信息
        prompt = f"""{xinli_prompt}

## 任务
请分析以下心理/情绪评估报告，提取关键指标数据并生成结构化的专业分析报告。作为专业心理医师，请基于您的临床经验，对异常指标提供针对性的干预建议。

## 分析维度
1. 核心状态：提取活力状态、情绪稳定性、能量水平、脑疲劳度等核心状态指标
2. 关键指标：分析以下指标及其是否异常：
   - 攻击性：正常范围20-50
   - 自信：正常范围50-80
   - 能量/活力：正常20-40
   - 压力：正常范围20-40
   - 抑郁：正常范围20-50
   - 幸福感：正常范围30-60
   - 情绪波动：关注情绪变化量（百分比）
   - 注意力：关注注意力集中度及波动情况

## 报告格式要求
请按照以下结构提供分析结果：

```
一、核心状态分析
1. 当前总体状态（活力状态/平衡状态/消耗状态）
2. 情绪稳定性评估（包括情绪波动百分比）
3. 能量水平与脑疲劳度分析

二、重点指标异常
- 列出所有异常指标（超出正常范围的指标）
- 每个异常指标的当前值与正常范围对比
- 分析各异常指标对日常功能的具体影响

三、针对性干预建议
（针对每个异常指标，提供2-3条具体详细的专业干预建议）
1. 针对[异常指标A]:
   - [具体建议1]: 详细说明实施频率（如每周3次）、时长（如每次30分钟）、具体操作步骤，以及该方法如何影响该指标
   - [具体建议2]: 同样详细描述具体实践方法，包括必要的工具、环境设置和执行标准
   
2. 针对[异常指标B]:
   - [具体建议1]: 提供具体方法，如"每日记录3件微小成就（如'今天完成了工作报告'）"，并解释为何有效
   - [具体建议2]: 提供可量化的操作指南，包括实施频率、所需时间和具体方法
   
（如此类推，确保所有异常指标都有针对性、可执行的具体建议）
```

## 重要说明
1. 请特别关注报告中"结构化指标数据"、"括号指标数据"、"关键指标数据"和"增强图像分析结果"部分
2. 针对每个异常指标，请提供基于专业临床经验的具体干预建议，包括可执行的方法和技术
3. 建议必须具体、可量化、可操作，包含具体的频率（每天/每周几次）、时长（每次多少分钟）和操作方法
4. 使用专业术语命名方法，如「333运动法则」、「番茄工作法」、「社交行为实验」、「安全岛」想象技术等
5. 建议应体现专业性，引用认知行为疗法、正念训练、情绪调节等专业手段，说明其作用机制
6. 如果用户是儿童或青少年，请特别关注家庭和学校干预策略

另外，请在分析完成后，生成一个JSON格式的数据结构，包含以下三个主要部分：
1. "核心状态分析"：包含总体状态描述、情绪稳定性评估和能量水平分析
2. "重点指标异常"：列出所有异常指标及其详细信息
3. "针对性干预建议"：针对每个异常指标的具体建议

JSON结构示例：
```json
{{
  "核心状态分析": {{
    "总体状态": "这里填写具体描述",
    "情绪稳定性": "这里填写具体描述",
    "能量水平": "这里填写具体描述"
  }},
  "重点指标异常": [
    {{
      "指标名称": "这里填写指标名称",
      "当前值": "这里填写数值",
      "正常范围": "这里填写范围",
      "影响分析": "这里填写分析内容"
    }}
  ],
  "针对性干预建议": {{
    "异常指标名称": [
      {{
        "建议标题": "这里填写建议标题",
        "具体方法": "这里填写具体方法",
        "预期效果": "这里填写预期效果"
      }}
    ]
  }}
}}
```

报告内容：
{file_content[:10000]}  # 包含图像分析结果的文本内容
"""
        
        # 使用chat_service中的llm_service，增加token上限以获取更详细的分析
        # 由于我们在后台线程中，需要创建一个新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        analysis = loop.run_until_complete(chat_service.llm_service.async_chat(prompt, max_tokens=4000, temperature=0.2))
        loop.close()
        
        # 将分析结果转换为用户信息格式
        user_info = f"""心理状态评估报告: 
{analysis}
"""
        
        # 更新用户信息
        from user_info_processor import UserInfoProcessor
        user_processor = UserInfoProcessor()
        user_processor.save_user_info(user_info)
        
        # 提取JSON结构数据并保存为文件
        import json
        import re
        
        # 尝试从文本中提取JSON数据
        try:
            # 使用正则表达式查找JSON格式的内容
            json_match = re.search(r'```json\s*(.*?)\s*```', analysis, re.DOTALL)
            
            if json_match:
                json_text = json_match.group(1)
                assessment_data = json.loads(json_text)
            else:
                # 如果没有找到JSON格式，则手动构建结构
                print("未找到JSON格式数据，从文本内容中提取...")
                
                # 提取核心状态分析
                core_analysis_match = re.search(r'一、核心状态分析(.*?)二、重点指标异常', analysis, re.DOTALL)
                core_analysis_text = core_analysis_match.group(1).strip() if core_analysis_match else ""
                
                # 从核心状态分析中提取具体信息
                core_state_match = re.search(r'当前.*?(?:处于|状态[为是]).*?([活力|平衡|消耗]状态)', core_analysis_text, re.DOTALL)
                emotion_stability_match = re.search(r'情绪稳定性.*?(.*?)(?:[\n\r]|$)', core_analysis_text, re.DOTALL)
                energy_level_match = re.search(r'能量水平.*?(.*?)(?:[\n\r]|$)', core_analysis_text, re.DOTALL)
                
                core_state = core_state_match.group(1).strip() if core_state_match else "未提及"
                emotion_stability = emotion_stability_match.group(1).strip() if emotion_stability_match else "未提及"
                energy_level = energy_level_match.group(1).strip() if energy_level_match else "未提及"
                
                # 提取重点指标异常
                abnormal_indicators_match = re.search(r'二、重点指标异常(.*?)三、针对性干预建议', analysis, re.DOTALL)
                abnormal_indicators_text = abnormal_indicators_match.group(1).strip() if abnormal_indicators_match else ""
                
                # 从异常指标部分提取各指标
                abnormal_indicators = []
                indicator_pattern = r'([攻击性|自信|能量|活力|压力|抑郁|幸福感|情绪波动|注意力]+)(?:指标)?(?:偏高|偏低|异常|超出正常范围).*?(\d+\.?\d*)[/／]?(?:正常)?(?:范围)?.*?(\d+[-至]\d+|\d+[以上下]?).*?(?:影响|表现为|导致)(.*?)(?:[\n\r]|$)'
                indicator_matches = re.finditer(indicator_pattern, abnormal_indicators_text, re.DOTALL)
                
                for match in indicator_matches:
                    abnormal_indicators.append({
                        "指标名称": match.group(1).strip(),
                        "当前值": match.group(2).strip(),
                        "正常范围": match.group(3).strip(),
                        "影响分析": match.group(4).strip()
                    })
                
                # 如果没有匹配到具体指标，尝试提取整段文本
                if not abnormal_indicators:
                    # 按行分割，找出可能的指标行
                    lines = abnormal_indicators_text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('二、') and line.find(':') == -1 and line.find('：') == -1:
                            # 尝试提取指标名称
                            indicator_name_match = re.search(r'^[-\*•]?\s*([攻击性|自信|能量|活力|压力|抑郁|幸福感|情绪波动|注意力]+)', line)
                            if indicator_name_match:
                                abnormal_indicators.append({
                                    "指标名称": indicator_name_match.group(1).strip(),
                                    "当前值": "未明确提及",
                                    "正常范围": "未明确提及",
                                    "影响分析": line
                                })
                
                # 提取针对性干预建议
                intervention_match = re.search(r'三、针对性干预建议(.*?)$', analysis, re.DOTALL)
                intervention_text = intervention_match.group(1).strip() if intervention_match else ""
                
                # 从干预建议中提取各指标的建议
                intervention_suggestions = {}
                
                # 首先提取各个指标部分
                indicator_sections = re.split(r'\d+\.\s*针对\s*', intervention_text)
                
                # 第一个元素通常是空或标题，跳过
                for section in indicator_sections[1:] if len(indicator_sections) > 1 else []:
                    # 提取指标名称
                    indicator_name_match = re.search(r'^(.*?)[:：]', section)
                    if not indicator_name_match:
                        continue
                        
                    indicator_name = indicator_name_match.group(1).strip()
                    section_text = section[len(indicator_name) + 1:].strip()
                    
                    # 提取具体建议
                    suggestions = []
                    suggestion_matches = re.finditer(r'[-*•]?\s*(.*?)[:：](.*?)(?:[\n\r]|(?=-)|$)', section_text, re.DOTALL)
                    
                    for suggestion_match in suggestion_matches:
                        suggestions.append({
                            "建议标题": suggestion_match.group(1).strip(),
                            "具体方法": suggestion_match.group(2).strip(),
                            "预期效果": "提高生活质量和心理健康水平"  # 默认效果
                        })
                    
                    # 如果没有匹配到具体建议，尝试按行分割
                    if not suggestions:
                        lines = section_text.split('\n')
                        for line in lines:
                            line = line.strip()
                            if line and line.startswith('-') or line.startswith('*') or line.startswith('•'):
                                suggestions.append({
                                    "建议标题": "建议",
                                    "具体方法": line[1:].strip(),
                                    "预期效果": "提高生活质量和心理健康水平"
                                })
                    
                    intervention_suggestions[indicator_name] = suggestions
                
                # 构建最终的数据结构
                assessment_data = {
                    "核心状态分析": {
                        "总体状态": core_state,
                        "情绪稳定性": emotion_stability,
                        "能量水平": energy_level
                    },
                    "重点指标异常": abnormal_indicators,
                    "针对性干预建议": intervention_suggestions
                }
            
            # 创建保存目录
            os.makedirs("save/assessments", exist_ok=True)
            
            # 生成文件名
            assessment_file = os.path.join("save/assessments", f"assessment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            
            # 保存为JSON文件
            with open(assessment_file, "w", encoding="utf-8") as json_file:
                json.dump(assessment_data, json_file, ensure_ascii=False, indent=2)
                
            print(f"情绪评估结果已保存到文件: {assessment_file}")
                
        except Exception as json_error:
            print(f"保存JSON格式评估结果失败: {json_error}")
            import traceback
            traceback.print_exc()
        
        print(f"情绪评估后台处理完成: {os.path.basename(temp_file_path)}")
        
    except Exception as e:
        print(f"后台处理情绪评估失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 处理完成，重置处理状态
        PROCESSING_ASSESSMENT = False
        PROCESSING_START_TIME = None
        # 删除临时文件
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

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