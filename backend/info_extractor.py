import re
from backend.intent_recognizer import IntentRecognizer

class InfoExtractor:
    """信息提取器，负责从用户输入中提取各类个人信息"""
    
    def __init__(self):
        # 初始化意图识别器
        self.intent_recognizer = IntentRecognizer()
        
        # 初始化基本信息提取模式
        self.basic_info_patterns = {
            "姓名": r"我(?:的名字|叫|是)(?:[\s]*)?([^\s，,。.、；;]{2,10})",
            "年龄": r"我(?:今年|现在)?(?:[\s]*)?((?:\d{1,2})(?:[\s]*)?(?:岁|周岁|年龄))",
            "性别": r"我(?:的性别)?(?:是|为)(?:[\s]*)?(男(?:生|性)?|女(?:生|性)?)",
            "学校": r"我(?:在|是|就读于|来自)(?:[\s]*)?([\w\u4e00-\u9fa5]{2,20}?(?:大学|学院|中学|小学|初中|高中|职业学校))",
            "专业": r"我(?:的专业(?:是|为)?|(?:在|正在)学习)(?:[\s]*)?([\w\u4e00-\u9fa5]{2,20}(?:专业|系)?)",
            "职业": r"我(?:的职业(?:是|为)?|(?:是|当)(?:一[名个]|一位)?)(?:[\s]*)?([\w\u4e00-\u9fa5]{2,10}(?:师|员|手|生|匠|师|医|人|官|兵|长|助理)?)"
        }
    
    def extract_basic_info(self, message):
        """提取用户基本信息"""
        basic_info = {}
        
        for info_type, pattern in self.basic_info_patterns.items():
            match = re.search(pattern, message)
            if match:
                if info_type == "年龄":
                    # 提取纯数字
                    age_text = match.group(1)
                    age_num = ''.join(filter(str.isdigit, age_text))
                    basic_info[info_type] = age_num
                else:
                    basic_info[info_type] = match.group(1)
        
        return basic_info
    
    def extract_personal_intents(self, message):
        """提取用户个人信息相关意图"""
        return self.intent_recognizer.recognize_intent(message)
    
    def extract_info(self, message):
        """从用户输入中提取所有类型的信息"""
        # 提取基本信息
        basic_info = self.extract_basic_info(message)
        
        # 提取个人相关意图
        intent_info = self.extract_personal_intents(message)
        
        # 汇总所有提取的信息
        extracted_info = {
            "basic_info": basic_info,
            "intent_info": intent_info
        }
        
        return extracted_info 