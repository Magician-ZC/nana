import re

# 心理状态模式
mental_state_patterns = [
    r"(?:我(?:感到|觉得)(?:有些|很|非常)?(焦虑|不安|紧张|压抑|沮丧|困惑))",
    r"(?:我(?:希望|想要|需要)(?:调整|改善|提升)自己的心理(?:状态|健康))",
    r"(?:我(?:希望|想要|需要)(?:获得|寻找|寻求)心理(?:咨询|疏导|帮助))",
    r"(?:我(?:正在|一直|总是)(?:为|因为)(.+?)(?:而)?(?:烦恼|担忧|焦虑))",
    r"(?:我(?:不知道|不确定|怀疑)(?:自己能否|是否能|是否适合)(.+?))",
    r"(?:我(?:希望|想要|需要)(?:保持|拥有|培养)(?:积极|健康|良好)的心态)",
    r"(?:我(?:经常|总是|常常)(?:感到|觉得)(?:有些|很|非常)?(压力大|紧张|不安))",
    r"(?:我(?:打算|计划|正在)(?:认真|仔细|深入)思考自己的(?:职业|人生|未来)(?:规划|方向))"
]

# 职业疑虑模式
career_doubt_patterns = [
    r"(?:我(?:不认为|不觉得|不相信)我(?:会|能|可以)是一个好(老师|医生|工程师|律师|职业))",
    r"(?:我(?:觉得|认为|发现)我不适合(?:当|做|成为)(老师|医生|工程师|律师|.+?))",
    r"(?:我对(?:自己|未来|职业发展)(?:感到|充满|有些?)(?:迷茫|困惑|不确定))",
    r"(?:我(?:不知道|没确定|无法确定)(?:自己|我)(?:未来|将来)(?:要|应该|能)做什么)"
]

# 情绪关键词及对应的具体描述
emotional_keywords = {
    "心理状态": "关注自身心理健康状况，希望保持良好的心理状态",
    "精神状态": "关注精神健康，可能需要调整作息和减压方法",
    "情绪问题": "正在经历情绪波动，需要情绪管理技巧",
    "心理健康": "注重心理健康，寻求平衡的生活方式",
    "心理压力": "面临较大心理压力，需要有效的减压方法",
    "抑郁": "可能存在抑郁情绪，建议寻求专业心理咨询",
    "焦虑": "正在经历焦虑情绪，需要学习缓解焦虑的方法",
    "恐惧": "面对某些事物存在恐惧心理，可能需要专业指导",
    "压力": "感到压力较大，需要学习压力管理技巧",
    "心理咨询": "有意识地寻求专业心理帮助，表现出积极态度",
    "职业规划": "正在思考职业发展方向，显示出规划意识",
    "职业思考": "对职业选择进行深入思考，寻求适合自己的发展道路"
}

def test_mental_patterns(message):
    # 先检查情绪关键词
    for keyword, description in emotional_keywords.items():
        if keyword in message:
            print(f"\n匹配到心理状态关键词: {keyword}\n")
            return True, description
    
    # 检查职业疑虑模式
    for pattern in career_doubt_patterns:
        match = re.search(pattern, message)
        if match:
            print(f"\n职业疑虑模式匹配到的表达: {match.group(0)}")
            print(f"捕获组数量: {len(match.groups())}")
            for i, group in enumerate(match.groups(), 1):
                if group:
                    print(f"捕获组 {i}: {group}")
            
            # 提取职业信息并构建更具体的描述
            career = match.groups()[0] if match.groups() else "职业"
            
            if "不适合" in match.group(0):
                return True, f"认为自己不适合从事{career}工作，可能需要职业规划指导"
            elif "不认为" in match.group(0) or "不觉得" in match.group(0):
                return True, f"对自己能否成为一名好{career}有疑虑和担忧，缺乏职业自信"
            elif "迷茫" in match.group(0) or "困惑" in match.group(0):
                return True, f"对职业发展感到迷茫和困惑，需要明确的职业定位"
            else:
                return True, f"对自己的职业选择和发展路径存在不确定性"
    
    # 检查一般心理状态模式
    for pattern in mental_state_patterns:
        match = re.search(pattern, message)
        if match:
            print(f"\n常规模式匹配到的表达: {match.group(0)}")
            print(f"捕获组数量: {len(match.groups())}")
            for i, group in enumerate(match.groups(), 1):
                if group:
                    print(f"捕获组 {i}: {group}")
            
            # 根据匹配的不同模式返回不同的描述
            if "积极" in match.group(0) or "良好" in match.group(0):
                return True, f"正在努力以积极心态面对压力，表现出良好的心理调适能力"
            elif "焦虑" in match.group(0) or "不安" in match.group(0) or "紧张" in match.group(0):
                emotion = "焦虑" if "焦虑" in match.group(0) else ("不安" if "不安" in match.group(0) else "紧张")
                return True, f"正在经历{emotion}情绪，建议学习放松技巧和寻求社交支持"
            elif "寻找" in match.group(0) or "寻求" in match.group(0) or "获得" in match.group(0):
                if "心理咨询" in match.group(0):
                    return True, f"希望获得专业心理咨询服务，表现出积极解决问题的态度"
                else:
                    return True, f"希望获得心理支持，寻求情绪调整方法"
            elif "压力大" in match.group(0):
                return True, f"感到压力较大，可能需要学习减压方法和时间管理技巧"
            elif "思考" in match.group(0) and ("职业" in match.group(0) or "未来" in match.group(0)):
                return True, f"正在认真思考未来职业发展方向，表现出职业规划的主动性"
            elif "调整" in match.group(0) or "改善" in match.group(0) or "提升" in match.group(0):
                return True, f"希望改善自己的心理状态，寻求变化和成长"
            else:
                emotion = match.groups()[0] if match.groups() and match.groups()[0] else "心理波动"
                return True, f"表现出{emotion}的情绪状态，需要适当的心理疏导"
    
    # 手动处理特殊情况
    if "压力很大" in message or "压力很重" in message:
        return True, "感到压力较大，可能需要学习压力管理和情绪调节技巧"
    
    if "职业规划" in message or "职业思考" in message:
        return True, "正在思考职业发展方向，寻求适合自己的职业定位"
    
    if "学习" in message and ("困难" in message or "压力" in message):
        return True, "学习过程中遇到困难，可能需要学习方法指导和心态调整"
    
    return False, ""

# 测试案例
test_cases = [
    "我不认为我会是一个好老师，但是我又不想做其他工作",
    "我想调整自己的心理状态，感觉最近压力很大",
    "我希望寻找心理咨询的帮助",
    "我觉得我不适合当老师，可能更适合做工程师",
    "我决定要积极面对考试压力",
    "最近学习很困难，我感到很焦虑",
    "我打算认真思考自己的职业规划",
    "我感到非常焦虑，不知道该怎么办",
    "我经常觉得压力很大"
]

# 运行测试
for test_message in test_cases:
    print(f"测试消息: {test_message}")
    is_mental_state, description = test_mental_patterns(test_message)
    print(f"识别结果: {is_mental_state}")
    print(f"心理状态描述: {description}")
    print("--------------------------------------------------") 