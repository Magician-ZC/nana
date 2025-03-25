from typing import Tuple, Dict, List
import re
from intent_recognizer import IntentRecognizer

class IntentExtractor:
    """意图提取器，负责从用户消息中提取各种意图"""
    
    def __init__(self):
        """初始化意图提取器"""
        self.recognizer = IntentRecognizer()
    
    def check_for_new_user_info(self, message: str) -> Tuple[bool, str, str, str]:
        """检查用户消息是否包含新的个人信息
        
        Args:
            message: 用户消息
            
        Returns:
            Tuple[bool, str, str, str]: (是否包含新信息, 信息类型, 信息内容, 关联信息)
        """
        # 检查爱好信息
        has_hobby, hobby_content = self.recognizer.check_for_new_hobby(message)
        if has_hobby:
            return True, "爱好", hobby_content, ""
            
        # 检查消息是否包含各类个人信息 (基本信息)
        basic_info_result = self._check_basic_info(message)
        if basic_info_result[0]:
            return basic_info_result
            
        # 检查消息是否包含各类状态信息
        status_info_result = self._check_status_info(message)
        if status_info_result[0]:
            return status_info_result
            
        # 检查职业规划意图
        career_result = self._check_career_intent(message)
        if career_result[0]:
            return career_result
            
        # 检查学习情况意图
        study_result = self._check_study_intent(message)
        if study_result[0]:
            return study_result
            
        # 检查心理状态意图
        mental_result = self._check_mental_intent(message)
        if mental_result[0]:
            return mental_result
            
        # 检查价值观意图
        value_result = self._check_value_intent(message)
        if value_result[0]:
            return value_result
            
        # 检查人际关系意图
        relationship_result = self._check_relationship_intent(message)
        if relationship_result[0]:
            return relationship_result
            
        # 检查情感状况意图
        emotion_result = self._check_emotion_intent(message)
        if emotion_result[0]:
            return emotion_result
            
        # 检查关键生活状态更新
        status_update_result = self._check_status_updates(message)
        if status_update_result[0]:
            return status_update_result
            
        return False, "", "", ""
        
    def _check_basic_info(self, message: str) -> Tuple[bool, str, str, str]:
        """检查用户消息是否包含基本个人信息
        
        Args:
            message: 用户消息
            
        Returns:
            Tuple[bool, str, str, str]: (是否包含新信息, 信息类型, 信息内容, 关联信息)
        """
        # 检查消息是否包含各类个人信息
        for info_type, patterns in self.recognizer.info_patterns.items():
            for pattern in patterns:
                matches = re.search(pattern, message)
                if matches:
                    # 提取信息内容
                    # 根据模式的不同，选择合适的捕获组
                    if info_type == "姓名":
                        if len(matches.groups()) >= 4 and matches.group(3):  # 第一种模式
                            info = matches.group(3).strip()
                        elif len(matches.groups()) >= 2 and matches.group(2):  # 第三种模式
                            info = matches.group(2).strip()
                        elif len(matches.groups()) >= 4 and matches.group(4):  # 第二种模式
                            info = matches.group(4).strip()
                        else:
                            continue
                    elif info_type == "年龄":
                        if len(matches.groups()) >= 2 and matches.group(2):  # 第一种模式
                            info = matches.group(2).strip() + "岁"
                        elif len(matches.groups()) >= 1 and matches.group(1):  # 第二和第三种模式
                            info = matches.group(1).strip() + "岁"
                        else:
                            continue
                    elif info_type == "性别":
                        if len(matches.groups()) >= 1 and matches.group(1):
                            gender = matches.group(1).strip()
                            # 标准化性别表示
                            if gender in ["男生", "男孩", "男"]:
                                info = "男"
                            elif gender in ["女生", "女孩", "女"]:
                                info = "女"
                            else:
                                continue
                    elif info_type == "学校":
                        # 避免将职业意向误识别为学校信息
                        if len(matches.groups()) >= 4 and matches.group(3) and matches.group(4):
                            info = matches.group(3).strip() + matches.group(4).strip()
                            # 检查是否包含职业相关关键词，如果有则跳过
                            career_keywords = ["当", "成为", "做", "从事", "职业", "工作", "规划"]
                            if any(keyword in info for keyword in career_keywords):
                                # 尝试提取职业意向并更新相应字段
                                has_career, career_info = self.recognizer.extract_career_intent(info)
                                if has_career:
                                    # 返回职业规划信息而不是学校信息
                                    return True, "职业规划", career_info, ""
                                continue
                        elif len(matches.groups()) >= 1 and matches.group(1):
                            info = matches.group(1).strip()
                            # 同样检查职业关键词
                            career_keywords = ["当", "成为", "做", "从事", "职业", "工作", "规划"]
                            if any(keyword in info for keyword in career_keywords):
                                has_career, career_info = self.recognizer.extract_career_intent(info)
                                if has_career:
                                    return True, "职业规划", career_info, ""
                                continue
                        else:
                            continue
                    else:  # 专业和年级
                        # 为简化处理，选择最后一个非空捕获组
                        for i in range(len(matches.groups()), 0, -1):
                            if matches.group(i) and not matches.group(i).strip() in ["是", "为", "方面", "情况", "状况"]:
                                info = matches.group(i).strip()
                                break
                        else:
                            continue
                    
                    # 简单验证信息是否合理
                    if info and len(info) <= 50:  # 限制信息长度，避免误匹配
                        # 关联更新机制：如果更新了学校信息且包含小学/中学/教师等关键词，同时检查是否需要更新职业规划
                        if info_type == "学校" and any(kw in info for kw in ["小学", "中学", "高中", "教师", "老师"]):
                            career_intent = self.recognizer.infer_career_from_school(info)
                            if career_intent:
                                # 先返回学校信息
                                return True, info_type, info, career_intent  # 返回推断的职业意向作为第四个参数
                        return True, info_type, info, ""
        
        return False, "", "", ""
    
    def _check_status_info(self, message: str) -> Tuple[bool, str, str, str]:
        """检查用户消息是否包含状态信息
        
        Args:
            message: 用户消息
            
        Returns:
            Tuple[bool, str, str, str]: (是否包含新信息, 信息类型, 信息内容, 关联信息)
        """
        # 检查消息是否包含各种状态信息
        for info_type, patterns in self.recognizer.status_patterns.items():
            for pattern in patterns:
                matches = re.search(pattern, message)
                if matches:
                    # 为简化处理，选择最后一个非空捕获组
                    for i in range(len(matches.groups()), 0, -1):
                        if matches.group(i) and not matches.group(i).strip() in ["是", "为", "方面", "情况", "状况"]:
                            # 特殊处理心理状态，确保完整捕获
                            if info_type == "心理状态" and i == 4 and len(matches.groups()) >= 5:
                                info = matches.group(4).strip()
                                # 补充额外的描述，如果存在
                                if matches.group(5) and matches.group(5).strip():
                                    info += matches.group(5).strip()
                            else:
                                info = matches.group(i).strip()
                            break
                    else:
                        continue
                    
                    # 排除挖掘到的否定表达，例如"不xx"
                    if "不" in info and len(info) <= 3:
                        continue
                        
                    # 排除心理状态识别中仅包含"不"的情况
                    if info_type == "心理状态" and info == "不":
                        continue
                        
                    # 简单验证信息是否合理
                    if info and len(info) <= 50:  # 限制信息长度，避免误匹配
                        return True, info_type, info, ""
        
        return False, "", "", ""
    
    def _check_career_intent(self, message: str) -> Tuple[bool, str, str, str]:
        """检查职业规划意图
        
        Args:
            message: 用户消息
            
        Returns:
            Tuple[bool, str, str, str]: (是否包含新信息, 信息类型, 信息内容, 关联信息)
        """
        for pattern in self.recognizer.career_patterns:
            matches = re.search(pattern, message)
            if matches:
                for i in range(len(matches.groups()), 0, -1):
                    if matches.group(i) and len(matches.group(i).strip()) > 1:
                        career_info = matches.group(i).strip()
                        # 验证是否是职业相关词汇
                        if any(kw in career_info for kw in ["老师", "教师", "工程师", "医生", "律师", "会计", "设计师", "研究员", "教授"]):
                            return True, "职业规划", career_info, ""
                        else:
                            # 尝试构建完整的职业描述
                            full_match = matches.group(0)
                            if "老师" in full_match or "教师" in full_match or "工程师" in full_match:
                                return True, "职业规划", full_match, ""
        
        # 处理特殊情况：用户表达对某职业的怀疑或不确定
        career_doubt_pattern = r"我(不认为|不觉得)(自己)?(会|能)(成为|当|做)(一个)?(好)?(的)?([^，,。.、]+)"
        matches = re.search(career_doubt_pattern, message)
        if matches:
            for i in range(len(matches.groups()), 0, -1):
                if matches.group(i) and len(matches.group(i).strip()) > 1:
                    career = matches.group(i).strip()
                    if any(kw in career for kw in ["老师", "教师", "工程师", "医生", "律师", "会计", "设计师"]):
                        doubt_info = f"对自己能否成为一名好{career}有疑虑和担忧"
                        return True, "职业规划", doubt_info, ""
            
            # 即使没有具体职业关键词，也可能表达对职业的困惑
            if "职业" in message or "工作" in message:
                return True, "职业规划", "对自己的职业选择和发展道路感到迷茫", ""
        
        return False, "", "", ""
    
    def _check_study_intent(self, message: str) -> Tuple[bool, str, str, str]:
        """检查学习情况意图
        
        Args:
            message: 用户消息
            
        Returns:
            Tuple[bool, str, str, str]: (是否包含新信息, 信息类型, 信息内容, 关联信息)
        """
        for pattern in self.recognizer.study_patterns:
            matches = re.search(pattern, message)
            if matches:
                full_match = matches.group(0)
                # 构建完整的学习描述
                if "学习" in full_match or "成绩" in full_match or "考试" in full_match:
                    study_info = f"准备{full_match}，希望能取得好成绩"
                    return True, "学习情况", study_info, ""
        
        return False, "", "", ""
    
    def _check_mental_intent(self, message: str) -> Tuple[bool, str, str, str]:
        """检查心理状态意图
        
        Args:
            message: 用户消息
            
        Returns:
            Tuple[bool, str, str, str]: (是否包含新信息, 信息类型, 信息内容, 关联信息)
        """
        for pattern in self.recognizer.mental_patterns:
            matches = re.search(pattern, message)
            if matches:
                full_match = matches.group(0)
                
                # 特殊处理：识别职业怀疑情况
                career_doubt_pattern = r"我(不认为|不觉得)(自己)?(会|能)(成为|当|做)(一个)?(好)?(的)?([^，,。.、]+)"
                if re.search(career_doubt_pattern, full_match):
                    for i in range(len(matches.groups()), 0, -1):
                        if matches.group(i) and len(matches.group(i).strip()) > 1:
                            career = matches.group(i).strip()
                            if any(kw in career for kw in ["老师", "教师", "工程师", "医生", "律师", "会计", "设计师"]):
                                mental_info = f"对自己的能力和未来感到不确定，尤其在成为{career}方面"
                                return True, "心理状态", mental_info, ""
                    
                    # 处理职业和工作的复杂表达
                    if "职业" in full_match or "工作" in full_match:
                        parts = full_match.split("，")
                        if len(parts) > 1 and "不想" in parts[1]:
                            mental_info = "对职业选择感到迷茫和焦虑，无法确定自己想要的方向"
                        else:
                            mental_info = "对自己的职业能力感到怀疑和不自信"
                        return True, "心理状态", mental_info, ""
                
                # 构建完整的心理状态描述
                if "压力" in full_match or "焦虑" in full_match or "抑郁" in full_match:
                    mental_info = f"正在{full_match}，寻求更好的心理状态"
                    return True, "心理状态", mental_info, ""
                else:
                    mental_info = f"希望保持积极心态，{full_match}"
                    return True, "心理状态", mental_info, ""
        
        return False, "", "", ""
    
    def _check_value_intent(self, message: str) -> Tuple[bool, str, str, str]:
        """检查价值观意图
        
        Args:
            message: 用户消息
            
        Returns:
            Tuple[bool, str, str, str]: (是否包含新信息, 信息类型, 信息内容, 关联信息)
        """
        for pattern in self.recognizer.value_patterns:
            matches = re.search(pattern, message)
            if matches:
                for i in range(len(matches.groups()), 0, -1):
                    if matches.group(i) and len(matches.group(i).strip()) > 1 and not matches.group(i).strip() in ["是", "的是"]:
                        value_info = matches.group(i).strip()
                        return True, "价值观", f"认为{value_info}是非常重要的", ""
                
                full_match = matches.group(0)
                if "价值观" in full_match or "人生观" in full_match or "世界观" in full_match:
                    return True, "价值观", full_match, ""
        
        return False, "", "", ""
    
    def _check_relationship_intent(self, message: str) -> Tuple[bool, str, str, str]:
        """检查人际关系意图
        
        Args:
            message: 用户消息
            
        Returns:
            Tuple[bool, str, str, str]: (是否包含新信息, 信息类型, 信息内容, 关联信息)
        """
        for pattern in self.recognizer.relationship_patterns:
            matches = re.search(pattern, message)
            if matches:
                full_match = matches.group(0)
                # 尝试提取关系对象
                relation_object = ""
                for i in range(len(matches.groups()), 0, -1):
                    if matches.group(i) and "关系" not in matches.group(i) and "沟通" not in matches.group(i):
                        potential_object = matches.group(i).strip()
                        if len(potential_object) <= 15 and any(kw in potential_object for kw in ["同学", "朋友", "室友", "家人", "父母", "老师"]):
                            relation_object = potential_object
                            break
                
                if relation_object:
                    if "道歉" in full_match or "和解" in full_match:
                        relationship_info = f"打算与{relation_object}和解，改善关系"
                    else:
                        relationship_info = f"希望与{relation_object}建立更好的关系"
                    return True, "人际关系", relationship_info, ""
                else:
                    return True, "人际关系", full_match, ""
        
        return False, "", "", ""
    
    def _check_emotion_intent(self, message: str) -> Tuple[bool, str, str, str]:
        """检查情感状况意图
        
        Args:
            message: 用户消息
            
        Returns:
            Tuple[bool, str, str, str]: (是否包含新信息, 信息类型, 信息内容, 关联信息)
        """
        for pattern in self.recognizer.emotion_patterns:
            matches = re.search(pattern, message)
            if matches:
                full_match = matches.group(0)
                # 尝试提取情感对象
                emotion_object = ""
                for i in range(len(matches.groups()), 0, -1):
                    if matches.group(i) and not any(kw in matches.group(i) for kw in ["感情", "喜欢", "爱意", "关系", "情"]):
                        potential_object = matches.group(i).strip()
                        if len(potential_object) <= 15:
                            emotion_object = potential_object
                            break
                
                if emotion_object:
                    if "表白" in full_match or "告诉" in full_match or "表达" in full_match:
                        emotion_info = f"准备向{emotion_object}表达自己的感情"
                    elif "放弃" in full_match or "忘记" in full_match or "放下" in full_match:
                        emotion_info = f"决定放下对{emotion_object}的感情"
                    elif "暗恋" in full_match or "喜欢" in full_match or "爱" in full_match:
                        emotion_info = f"喜欢{emotion_object}，但还没有表白"
                    else:
                        emotion_info = f"对{emotion_object}有好感，想发展关系"
                    return True, "情感状况", emotion_info, ""
                else:
                    if "表白" in full_match:
                        return True, "情感状况", "准备向喜欢的人表白", ""
                    elif "放弃" in full_match or "忘记" in full_match:
                        return True, "情感状况", "决定放下感情", ""
                    else:
                        return True, "情感状况", full_match, ""
        
        return False, "", "", ""
    
    def _check_status_updates(self, message: str) -> Tuple[bool, str, str, str]:
        """检查关键生活状态更新
        
        Args:
            message: 用户消息
            
        Returns:
            Tuple[bool, str, str, str]: (是否包含新信息, 信息类型, 信息内容, 关联信息)
        """
        for status_type, patterns in self.recognizer.status_updates.items():
            for pattern in patterns:
                matches = re.search(pattern, message)
                if matches:
                    # 选择最有意义的捕获组作为状态更新内容
                    status_info = message  # 默认使用整个消息
                    for i in range(len(matches.groups()), 0, -1):
                        if matches.group(i) and len(matches.group(i).strip()) > 2:
                            status_info = matches.group(i).strip()
                            break
                    
                    if status_info and len(status_info) <= 100:
                        return True, f"最近状况_{status_type}", status_info, ""
        
        return False, "", "", "" 