from typing import Tuple, Dict, List
import re

class IntentRecognizer:
    """意图识别器，负责从用户消息中识别各种意图"""
    
    def __init__(self):
        """初始化意图识别器"""
        # 初始化各种意图的模式
        self._init_decision_keywords()
        self._init_hobby_keywords()
        self._init_patterns()
    
    def _init_decision_keywords(self):
        """初始化决策关键词"""
        # 决策相关的关键词映射
        self.decision_keywords = {
            "人际关系": ["原谅", "接纳", "和解", "沟通", "交流", "理解", "宽容", "谅解", "道歉", "解决冲突"],
            "学习情况": ["努力", "复习", "学习", "备考", "提高", "专注", "坚持", "计划", "安排时间", "求助"],
            "情感状况": ["表白", "表达", "关系", "喜欢", "爱", "追求", "告白", "放下", "珍惜", "维持"],
            "心理状态": ["放松", "减压", "调整", "正面", "积极", "接受", "面对", "放下", "忘记", "调节"],
            "职业规划": ["规划", "学习技术", "实习", "提升", "准备", "面试", "简历", "技能", "培训", "经验"],
            "家庭情况": ["沟通", "理解", "接纳", "支持", "独立", "减轻负担", "表达", "感谢", "孝顺"],
            "价值观": ["探索", "思考", "寻找", "定义", "明确", "坚持", "调整", "改变", "确立"]
        }
        
        # 判断词组，表示用户正在做决策
        self.decision_indicators = [
            "我决定", "我会尝试", "我准备", "我想", "我选择", "我接受", 
            "我同意", "我打算", "我应该", "我要", "准备", "决定",
            "我会", "我愿意", "我可以", "我打算", "我认为应该", "我觉得可以"
        ]
        
        # 引导决策的关键词
        self.guidance_keywords = [
            "打算怎么做", "会选择", "想尝试", "打算如何", "如何选择", 
            "准备怎么做", "决定", "计划", "怎么办", "什么方法", 
            "怎么想", "接下来", "怎么处理", "如何应对", "怎么样", 
            "要不要", "是否要", "是否愿意", "是不是想", "打算", "选择"
        ]
        
        # 强烈决策表达
        self.strong_decision = ["我已经决定", "我一定会", "我下定决心", "我坚决", "我肯定会"]
    
    def _init_hobby_keywords(self):
        """初始化爱好关键词"""
        # 常见爱好关键词，用于验证提取的内容是否可能是爱好
        self.hobby_keywords = [
            "游泳", "跑步", "健身", "阅读", "看书", "绘画", "画画", "音乐", "唱歌", "弹琴", 
            "钢琴", "吉他", "跳舞", "摄影", "旅行", "电影", "写作", "烹饪", "做饭", "烘焙", 
            "瑜伽", "冥想", "篮球", "足球", "网球", "羽毛球", "乒乓球", "滑板", "滑雪", 
            "攀岩", "徒步", "骑行", "骑车", "园艺", "种花", "手工", "编程", "游戏", 
            "下棋", "象棋", "围棋", "收藏", "钓鱼", "养宠物", "志愿者", "登山", "潜水", 
            "舞蹈", "书法", "雕刻", "DIY", "动漫", "尤克里里", "小提琴", "戏剧"
        ]
    
    def _init_patterns(self):
        """初始化各种意图识别的正则表达式模式"""
        # 基本信息字段及其可能的表达方式
        self.info_patterns = {
            "姓名": [
                r"我(的)?名字(是|叫)([^，,。.、]+)",
                r"我(应该)?(可以)?叫(做)?([^，,。.、]+)",
                r"(我是|我叫)([^，,。.、]+)"
            ],
            "年龄": [
                r"我(今年|现在)?([0-9]+)岁",
                r"我的年龄是([0-9]+)",
                r"([0-9]+)(岁|周岁)"
            ],
            "性别": [
                r"我是(男生|女生|男孩|女孩|男|女)",
                r"我的性别是(男|女)"
            ],
            "学校": [
                r"我(在|是|现在|目前)?(就读于|读|在)?([^，,。.、]+)(大学|学院|中学|小学)",
                r"我的学校是([^，,。.、]+)"
            ],
            "专业": [
                r"我(在读|学的|现在学的|目前学的|选择的|读的)?专业(是)?([^，,。.、]+)",
                r"我学(的是)?([^，,。.、]+)(专业)?"
            ],
            "年级": [
                r"我(是|现在是|目前是)?([大小][一二三四五六1-6]|研[一二三1-3]|博[一二三四五1-5])",
                r"我(现在|目前)?(在|读|上)([大小][一二三四五六1-6]|研[一二三1-3]|博[一二三四五1-5])"
            ]
        }
        
        # 状态信息模式
        self.status_patterns = {
            "学习情况": [
                r"我(最近|近期)?(的)?学习(情况|状况)(是)?([^。.]+)[。.]",
                r"我在(学习|课程|考试)方面([^。.]+)[。.]",
                r"我的成绩(是|为|大概是)?([^，,。.]+)"
            ],
            "人际关系": [
                r"我(和)?(同学|朋友|室友|舍友|同宿舍)(的关系|相处|处得)([^。.]+)[。.]",
                r"我(最近|近期)?(在)?(交友|社交|人际关系)(方面)?([^。.]+)[。.]"
            ],
            "情感状况": [
                r"我(现在|目前)?(喜欢|爱|暗恋)([^，,。.、]+)",
                r"我(和)?([^，,。.、]+)(在一起|是男女朋友|是情侣|谈恋爱)"
            ],
            "心理状态": [
                r"我(最近|近期|现在|总是|经常)?(感到|感觉|觉得)?(很|非常)?(焦虑|抑郁|不安|紧张|开心|难过|悲伤|压力大)([^,，。.]*)",
                r"我(的)?心理状态(是|为)?([^。.]+)[。.]"
            ],
            "职业规划": [
                r"我(未来|将来)?(想|希望|计划|准备)(成为|做|从事)([^，,。.、]+)",
                r"我的(职业|就业|工作)(目标|规划|方向)(是)?([^。.]+)[。.]"
            ],
            "家庭情况": [
                r"我的家庭(情况|状况)(是)?([^。.]+)[。.]",
                r"我(的)?父母(都是|是|在)?([^，,。.、]+)"
            ],
            "价值观": [
                r"我(认为|觉得|相信|追求|重视)([^。.]+)[。.]",
                r"我的(人生观|价值观|世界观)(是)?([^。.]+)[。.]"
            ]
        }
        
        # 生活状态更新模式
        self.status_updates = {
            "学习情况": [
                r"我(最近)?(通过|考过|得了|取得|拿到)(了)?([^，,。.、]+)(考试|证书|资格)",
                r"我(最近|刚|刚刚)?(参加了|考了|完成了)([^，,。.、]+)"
            ],
            "人际关系": [
                r"我(和|跟)([^，,。.、]+)(和好了|道歉了|解决了问题|解决了矛盾)",
                r"我(和|跟)([^，,。.、]+)(成为了朋友|关系变好了|处得很好)"
            ],
            "心理状态": [
                r"我(最近|现在|目前)(觉得|感到|感觉)(很|非常)?(开心|高兴|快乐|放松|舒服)",
                r"我(的)?(心情|状态|情绪)(最近|现在|这段时间)(变得|变|是)(很|非常)?(好|积极|正面|乐观)"
            ]
        }
        
        # 新增：表示爱好的模式
        self.hobby_patterns = [
            r"我(最近)?(有了)?(新的)?爱好[是为，,。.、]([^，,。.、]+)",
            r"我(最近)?(开始)?(喜欢|热爱|迷上了|爱上了)([^，,。.、]+)",
            r"我(现在)?(很)?(喜欢|热爱|迷上|爱上)([^，,。.、]+)",
            r"(最近)?(开始)?(对)?([^，,。.、]+)(很)?感兴趣",
            r"新(爱好|兴趣|喜好)[是为:：]?([^，,。.、]+)"
        ]
        
        # 新增：专门检测职业规划的意图表达
        self.career_patterns = [
            r"我(想|希望|准备|计划|要)(毕业后|以后|未来)?(当|成为|做|从事)([^，,。.、]+)",
            r"我(毕业后|以后|未来)(想|希望|准备|计划|要)(当|成为|做|从事)([^，,。.、]+)",
            r"(准备|计划|想)(毕业后|以后|将来|未来)?(当|成为|做|从事)([^，,。.、]+)"
        ]
        
        # 新增：学习情况意图识别
        self.study_patterns = [
            r"我(最近|近期|现在)?(打算|计划|准备|决定|想)(努力|认真|好好)(学习|复习|备考|准备)([^，,。.、]*)",
            r"我(想|希望|准备|计划|要)(提高|改善|加强)(自己)?(的)?(学习|成绩|绩点|能力)([^，,。.、]*)",
            r"我(决定|打算|要)(参加|报名|考取)([^，,。.、]+)(证书|考试|资格)",
        ]
        
        # 新增：心理状态意图识别
        self.mental_patterns = [
            r"我(想|希望|准备|计划|要)(调整|改善|缓解|解决)(自己)?(的)?(心理|情绪|压力|焦虑|抑郁)([^，,。.、]*)",
            r"我(决定|打算|要)(积极|乐观|正面|平静|放松)(地)?(面对|处理|应对)([^，,。.、]*)",
            r"我(需要|想要|希望)(寻找|获得|得到)(心理|精神|情绪)(上的)?(帮助|支持|咨询)([^，,。.、]*)",
            r"我(不认为|不觉得)(自己)?(会|能)(成为|当|做|是)([^，,。.、]+)"
        ]
        
        # 新增：价值观意图识别
        self.value_patterns = [
            r"我(想|希望|准备|计划|要)(探索|寻找|确立|明确|坚定)(自己)?(的)?(价值观|人生观|世界观|目标|方向)([^，,。.、]*)",
            r"我(决定|打算|要)(追求|重视|看重|关注)(更多)?(的)?(是)?([^，,。.、]+)",
            r"对我(来说|而言)?(最|更|非常)?(重要|有价值|有意义)(的)?(是)?([^，,。.、]+)",
        ]
        
        # 新增：人际关系意图识别
        self.relationship_patterns = [
            r"我(想|希望|准备|计划|要)(改善|调整|修复|增进)(自己)?(和|与)?([^，,。.、]+)(的)?(关系|友谊)",
            r"我(决定|打算|要)(多|积极|主动)(和|与)?([^，,。.、]+)(交流|沟通|相处|接触)",
            r"我(准备|打算|要)(道歉|和解|原谅|谅解|理解)(自己)?(的)?([^，,。.、]*)",
        ]
        
        # 新增：情感状况意图识别
        self.emotion_patterns = [
            r"我(想|希望|准备|计划|要)(向|告诉|表白|追求)([^，,。.、]+)(表达|表白|说出|告白|告诉)(自己)?(的)?(感情|喜欢|爱意)",
            r"我(决定|打算|要)(放弃|忘记|放下)(对)?([^，,。.、]+)(的)?(感情|喜欢|爱)",
            r"我(准备|打算|要)(珍惜|维持|发展)(和|与)?([^，,。.、]+)(的)?(感情|关系|爱情)",
            r"我(喜欢|爱|暗恋)([^，,。.、]+)(很久|很长时间)(了)?",
            r"我(想|打算|准备|决定|要)(追求|接近|了解)([^，,。.、]+)",
        ]
        
        # 职业意向关键词
        self.career_keywords = {
            "老师": ["小学老师", "中学老师", "高中老师", "数学老师", "语文老师", "英语老师", "教师"],
            "工程师": ["软件工程师", "开发工程师", "算法工程师", "硬件工程师"],
            "医生": ["医生", "医师", "外科医生", "内科医生"],
            "设计师": ["设计师", "UI设计", "产品设计"]
        }
        
        # 职业意向匹配模式
        self.career_intent_patterns = [
            r"(当|成为|做)([^，,。.、]+)(老师|工程师|医生|律师|会计师|设计师)",
            r"(准备|计划|想)(当|成为|做)([^，,。.、]+)"
        ]
    
    def check_if_user_decision(self, message: str, context: str) -> Tuple[bool, str, str]:
        """判断用户消息是否是对之前建议的决策回复
        
        Args:
            message: 用户消息
            context: 对话上下文
            
        Returns:
            Tuple[bool, str, str]: (是否是决策回复, 决策类型, 决策内容)
        """
        # 检查用户消息是否包含决策指示词
        for indicator in self.decision_indicators:
            if indicator in message:
                # 确定决策类型和内容
                decision_type = "一般决策"
                decision_content = message
                
                # 进一步识别是哪种类型的决策
                for type_key, keywords in self.decision_keywords.items():
                    if any(keyword in message for keyword in keywords):
                        decision_type = type_key
                        break
                
                # 检查上下文中的最后一条助手消息是否包含引导决策的内容
                context_lines = context.split('\n')
                for i in range(len(context_lines) - 1, -1, -1):
                    if "助手:" in context_lines[i]:
                        last_assistant_msg = context_lines[i].split("助手:", 1)[1].strip()
                        # 如果上一条消息包含引导决策关键词，或者消息超过50个字（可能是详细建议）
                        if any(keyword in last_assistant_msg for keyword in self.guidance_keywords) or len(last_assistant_msg) > 50:
                            return True, decision_type, decision_content
                        break
                
                # 即使上下文中没有明确引导，但用户消息本身非常明确表达了决策意图，也视为决策
                if any(sd in message for sd in self.strong_decision):
                    return True, decision_type, decision_content
        
        return False, "", ""
    
    def check_for_new_hobby(self, message: str) -> Tuple[bool, str]:
        """检查用户消息是否包含新的爱好信息
        
        Args:
            message: 用户消息
            
        Returns:
            Tuple[bool, str]: (是否包含新爱好, 爱好内容)
        """
        # 检查每个模式
        for pattern in self.hobby_patterns:
            matches = re.search(pattern, message)
            if matches:
                # 提取爱好内容，根据不同的正则表达式模式选择合适的组
                if len(matches.groups()) >= 4 and matches.group(4):  # 第一种和第二种模式
                    hobby = matches.group(4).strip()
                elif len(matches.groups()) >= 2 and matches.group(2):  # 最后一种模式
                    hobby = matches.group(2).strip()
                else:  # 可能是其他模式或捕获组不匹配预期
                    continue
                    
                # 验证提取的内容是否包含常见爱好关键词
                if any(keyword in hobby for keyword in self.hobby_keywords) or len(hobby) <= 10:
                    return True, hobby
        
        # 简单的肯定回答检查，如果前面有关于爱好的提问
        if "是的" in message or "对" in message or "没错" in message or "喜欢" in message:
            # 这里需要通过上下文检查是否是对爱好的确认，但简化处理
            for keyword in self.hobby_keywords:
                if keyword in message:
                    return True, keyword
        
        return False, ""
        
    def extract_career_intent(self, text: str) -> Tuple[bool, str]:
        """从文本中提取职业意向
        
        Args:
            text: 包含可能的职业意向的文本
            
        Returns:
            Tuple[bool, str]: (是否找到职业意向, 职业内容)
        """
        # 尝试直接匹配职业关键词
        for career, variations in self.career_keywords.items():
            if any(var in text for var in variations):
                # 构建合适的职业描述
                if "老师" in career or "教师" in career:
                    for var in variations:
                        if var in text:
                            context = text.split(var)[0][-10:] if len(text.split(var)[0]) > 10 else text.split(var)[0]
                            return True, f"想毕业后成为一名{var}，喜欢教书育人"
                    return True, f"想毕业后成为一名{career}，喜欢教书育人"
                else:
                    return True, f"想毕业后成为一名{career}"
        
        # 使用正则表达式模式匹配
        for pattern in self.career_intent_patterns:
            matches = re.search(pattern, text)
            if matches:
                if len(matches.groups()) >= 3 and matches.group(3) in ["老师", "工程师", "医生", "律师", "会计师", "设计师"]:
                    career = (matches.group(2) + matches.group(3)).strip()
                    return True, f"想毕业后成为一名{career}"
                elif len(matches.groups()) >= 3 and "老师" in text:
                    return True, "想毕业后成为一名老师，喜欢教书育人"
        
        return False, ""
    
    def infer_career_from_school(self, school_info: str) -> str:
        """根据学校信息推断可能的职业意向
        
        Args:
            school_info: 学校信息文本
            
        Returns:
            str: 推断的职业意向，如果无法推断则返回空字符串
        """
        # 根据学校信息中的关键词推断职业
        if "小学" in school_info and any(kw in school_info for kw in ["当", "成为", "准备"]):
            return "想毕业后成为一名小学老师，喜欢教书育人"
        elif "中学" in school_info and any(kw in school_info for kw in ["当", "成为", "准备"]):
            return "想毕业后成为一名中学老师，喜欢教书育人"
        elif "高中" in school_info and any(kw in school_info for kw in ["当", "成为", "准备"]):
            return "想毕业后成为一名高中老师，喜欢教书育人"
        elif "教师" in school_info or "老师" in school_info:
            if "小学" in school_info:
                return "想毕业后成为一名小学老师，喜欢教书育人"
            elif "中学" in school_info:
                return "想毕业后成为一名中学老师，喜欢教书育人"
            else:
                return "想毕业后成为一名老师，喜欢教书育人"
        
        return ""

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