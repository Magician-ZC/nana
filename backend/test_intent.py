import re

class IntentRecognizer:
    """意图识别器，用于识别用户输入中的各类意图"""
    
    def __init__(self):
        # 初始化心理状态模式
        self.mental_state_patterns = [
            r"(?:我(?:感到|觉得)(?:有些|很|非常)?(焦虑|不安|紧张|压抑|沮丧|困惑))",
            r"(?:我(?:希望|想要|需要)(?:调整|改善|提升)自己的心理(?:状态|健康))",
            r"(?:我(?:希望|想要|需要)(?:获得|寻找|寻求)心理(?:咨询|疏导|帮助))",
            r"(?:我(?:正在|一直|总是)(?:为|因为)(.+?)(?:而)?(?:烦恼|担忧|焦虑))",
            r"(?:我(?:不知道|不确定|怀疑)(?:自己能否|是否能|是否适合)(.+?))",
            r"(?:我(?:希望|想要|需要)(?:保持|拥有|培养)(?:积极|健康|良好)的心态)",
            r"(?:我(?:经常|总是|常常)(?:感到|觉得)(?:有些|很|非常)?(压力大|紧张|不安))",
            r"(?:我(?:打算|计划|正在)(?:认真|仔细|深入)思考自己的(?:职业|人生|未来)(?:规划|方向))"
        ]
        
        # 初始化职业疑虑模式
        self.career_doubt_patterns = [
            r"(?:我(?:不认为|不觉得|不相信)我(?:会|能|可以)是一个好(老师|医生|工程师|律师|职业))",
            r"(?:我(?:觉得|认为|发现)我不适合(?:当|做|成为)(老师|医生|工程师|律师|.+?))",
            r"(?:我对(?:自己|未来|职业发展)(?:感到|充满|有些?)(?:迷茫|困惑|不确定))",
            r"(?:我(?:不知道|没确定|无法确定)(?:自己|我)(?:未来|将来)(?:要|应该|能)做什么)"
        ]
        
        # 初始化情绪关键词及对应的描述
        self.emotional_keywords = {
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
        
        # 初始化学习状况模式
        self.learning_patterns = [
            r"(?:我(?:想|希望|准备)(?:提高|改善|提升)(?:自己的)?(?:学习|成绩|考试|课程)(?:表现|水平|成绩|效率))",
            r"(?:我(?:在|对)(?:学习|考试|课程|作业)(?:上|方面)(?:遇到|有)(?:了)?(?:困难|问题|障碍))",
            r"(?:我(?:的)?(?:学习|成绩|考试)(?:状况|情况|水平|效率)(?:不理想|不好|下降|很差))",
            r"(?:我(?:想|希望)(?:学会|掌握|理解)(?:如何|怎样)?(?:高效|有效|科学)(?:地)?(?:学习|复习|记忆))"
        ]
        
        # 人际关系模式
        self.relationship_patterns = [
            r"(?:我(?:和|跟|与)(?:我的)?(?:朋友|同学|同事|室友|伙伴|父母|家人|亲人)(?:关系|相处)(?:不好|紧张|有问题))",
            r"(?:我(?:不知道|不清楚|不确定)(?:如何|怎样)(?:与|和|跟)(?:他人|别人|周围的人)(?:相处|交流|沟通))",
            r"(?:我(?:经常|总是|老是)(?:感到|觉得)(?:孤独|孤单|寂寞|被孤立|被排斥))",
            r"(?:我(?:希望|想要|渴望)(?:改善|提升|修复)(?:我的)?(?:人际关系|社交能力|沟通技巧))"
        ]
        
        # 价值观模式
        self.values_patterns = [
            r"(?:我(?:认为|觉得|相信)(?:最重要|最有价值|最关键)的是(?:什么|如何|怎样)?(?:.+?))",
            r"(?:对我(?:来说|而言)(?:最重要|最有意义|最有价值)的(?:事情|事|方面)是(?:.+?))",
            r"(?:我(?:想要|希望|渴望)(?:追求|找到|实现)(?:人生的)?(?:意义|价值|目标|使命))",
            r"(?:我(?:经常|常常|总是)(?:思考|反思|怀疑)(?:自己的)?(?:人生|生活|存在)(?:意义|价值|目标|方向))"
        ]
    
    def recognize_mental_state(self, message):
        """识别心理状态意图"""
        # 先检查情绪关键词
        for keyword, description in self.emotional_keywords.items():
            if keyword in message:
                return True, description
        
        # 检查职业疑虑模式
        for pattern in self.career_doubt_patterns:
            match = re.search(pattern, message)
            if match:
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
        for pattern in self.mental_state_patterns:
            match = re.search(pattern, message)
            if match:
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
    
    def recognize_learning_situation(self, message):
        """识别学习状况意图"""
        for pattern in self.learning_patterns:
            match = re.search(pattern, message)
            if match:
                if "提高" in match.group(0) or "改善" in match.group(0) or "提升" in match.group(0):
                    return True, "希望提高学习成绩和效率，表现出积极的学习态度"
                elif "困难" in match.group(0) or "问题" in match.group(0) or "障碍" in match.group(0):
                    return True, "在学习过程中遇到困难，需要相关学习方法指导"
                elif "不理想" in match.group(0) or "不好" in match.group(0) or "下降" in match.group(0) or "很差" in match.group(0):
                    return True, "学习成绩不理想，可能需要调整学习策略和方法"
                elif "高效" in match.group(0) or "有效" in match.group(0) or "科学" in match.group(0):
                    return True, "追求高效学习方法，希望提升学习能力"
                else:
                    return True, "关注学习状况，希望取得进步"
        
        # 检查学习关键词
        learning_keywords = ["学习方法", "学习技巧", "提高成绩", "学习困难", "记忆力", "学习效率"]
        for keyword in learning_keywords:
            if keyword in message:
                return True, f"关注{keyword}，希望提升学习能力"
        
        return False, ""
    
    def recognize_relationship(self, message):
        """识别人际关系意图"""
        for pattern in self.relationship_patterns:
            match = re.search(pattern, message)
            if match:
                if "不好" in match.group(0) or "紧张" in match.group(0) or "有问题" in match.group(0):
                    relation_type = ""
                    if "朋友" in match.group(0):
                        relation_type = "朋友"
                    elif "同学" in match.group(0):
                        relation_type = "同学"
                    elif "同事" in match.group(0):
                        relation_type = "同事"
                    elif "室友" in match.group(0):
                        relation_type = "室友"
                    elif "父母" in match.group(0) or "家人" in match.group(0) or "亲人" in match.group(0):
                        relation_type = "家人"
                    
                    if relation_type:
                        return True, f"与{relation_type}关系紧张，需要改善人际沟通方式"
                    else:
                        return True, "人际关系存在问题，需要人际交往指导"
                
                elif "不知道" in match.group(0) or "不清楚" in match.group(0) or "不确定" in match.group(0):
                    return True, "社交能力不足，需要提升人际交往技巧"
                
                elif "孤独" in match.group(0) or "孤单" in match.group(0) or "寂寞" in match.group(0):
                    return True, "感到孤独和社交孤立，需要社交支持和心理疏导"
                
                elif "改善" in match.group(0) or "提升" in match.group(0) or "修复" in match.group(0):
                    return True, "希望改善人际关系，提升社交能力"
                
                else:
                    return True, "关注人际关系状况，希望建立健康的社交网络"
        
        # 检查人际关系关键词
        relationship_keywords = ["人际关系", "社交能力", "沟通技巧", "交友", "相处方式", "人际交往"]
        for keyword in relationship_keywords:
            if keyword in message:
                return True, f"关注{keyword}，希望建立良好的人际关系"
        
        return False, ""
    
    def recognize_values(self, message):
        """识别价值观意图"""
        for pattern in self.values_patterns:
            match = re.search(pattern, message)
            if match:
                if "最重要" in match.group(0) or "最有价值" in match.group(0) or "最关键" in match.group(0):
                    return True, "在思考个人价值观和人生重要性排序"
                elif "意义" in match.group(0) or "价值" in match.group(0) or "目标" in match.group(0) or "使命" in match.group(0):
                    return True, "在寻找人生的意义和价值，希望确立清晰的人生目标"
                elif "思考" in match.group(0) or "反思" in match.group(0) or "怀疑" in match.group(0):
                    return True, "对人生价值进行深入思考，寻求内心的确定性"
                else:
                    return True, "关注个人价值观的确立，希望找到生活的意义"
        
        # 检查价值观关键词
        values_keywords = ["价值观", "人生意义", "生活目标", "人生方向", "生活理念", "人生哲学"]
        for keyword in values_keywords:
            if keyword in message:
                return True, f"关注{keyword}，希望建立清晰的人生价值体系"
        
        return False, ""
    
    def recognize_intent(self, message):
        """识别用户消息的主要意图"""
        intents = {
            "mental_state": self.recognize_mental_state(message),
            "learning_situation": self.recognize_learning_situation(message),
            "relationship": self.recognize_relationship(message),
            "values": self.recognize_values(message)
        }
        
        # 筛选所有有效的意图结果
        valid_intents = {intent_type: info for intent_type, (is_valid, info) in intents.items() if is_valid}
        
        if valid_intents:
            return valid_intents
        else:
            return None


# 测试意图识别
def test_intent_recognition():
    recognizer = IntentRecognizer()
    
    test_messages = [
        "我不认为我会是一个好老师，但是我又不想做其他工作",
        "我想调整自己的心理状态，感觉最近压力很大",
        "我希望寻找心理咨询的帮助",
        "我觉得我不适合当老师，可能更适合做工程师",
        "我决定要积极面对考试压力",
        "最近学习很困难，我感到很焦虑",
        "我打算认真思考自己的职业规划",
        "我感到非常焦虑，不知道该怎么办",
        "我经常觉得压力很大",
        "我和我的室友关系很紧张，不知道怎么解决",
        "我希望提高自己的学习成绩，但总是记不住知识点",
        "我对未来感到迷茫，不知道什么才是我人生最重要的事情"
    ]
    
    for message in test_messages:
        print(f"\n测试消息: {message}")
        intent_info = recognizer.recognize_intent(message)
        
        if intent_info:
            print("识别结果:")
            for intent_type, intent_data in intent_info.items():
                is_valid, description = intent_data
                print(f"- {intent_type}: {description}")
        else:
            print("未识别到特定意图")
        
        print("-" * 50)

if __name__ == "__main__":
    test_intent_recognition() 