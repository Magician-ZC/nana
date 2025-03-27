from typing import Tuple, Dict, List
import re
import os

class UserInfoProcessor:
    """用户信息处理类，负责用户信息的提取、解析、更新等操作"""
    
    def __init__(self, user_info_file='save/me.txt'):
        """初始化用户信息处理器
        
        Args:
            user_info_file: 用户信息文件路径
        """
        self.user_info_file = user_info_file
        os.makedirs(os.path.dirname(user_info_file), exist_ok=True)
        self.user_info = self._load_user_info()
        
    def _load_user_info(self) -> str:
        """加载用户个人信息"""
        try:
            if os.path.exists(self.user_info_file):
                with open(self.user_info_file, 'r', encoding='utf-8') as f:
                    return f.read().strip()
        except Exception as e:
            print(f"读取个人信息文件出错: {e}")
        return ""
        
    def save_user_info(self, new_info: str) -> None:
        """保存用户个人信息，合并新旧信息而不是覆盖"""
        try:
            # 获取现有信息
            existing_info = self._load_user_info()
            
            # 如果没有现有信息，直接保存新信息
            if not existing_info:
                with open(self.user_info_file, 'w', encoding='utf-8') as f:
                    f.write(new_info)
                return
                
            # 解析新旧信息
            existing_dict = self.parse_user_info(existing_info)
            new_dict = self.parse_user_info(new_info)
            
            # 合并信息，优先保留原有格式
            # 1. 首先检查并合并基本信息部分
            basic_info_keys = ["姓名", "年龄", "性别", "学校", "专业", "年级", "爱好"]
            for key in basic_info_keys:
                if key in new_dict and new_dict[key]:
                    existing_dict[key] = new_dict[key]
            
            # 2. 检查并合并其他部分(除了"最近状况"和"心理状态"之外的部分)
            for key in new_dict:
                if key not in basic_info_keys and key not in ["最近状况", "心理状态"] and new_dict[key]:
                    existing_dict[key] = new_dict[key]
            
            # 3. 特殊处理"最近状况"，保持原有结构
            if "最近状况" in new_dict and new_dict["最近状况"]:
                # 保存现有状况但可能会更新内容
                status_dict = {}
                if "最近状况" in existing_dict:
                    status_lines = existing_dict["最近状况"].split("\n")
                    for line in status_lines:
                        if ":" in line or "：" in line:
                            parts = line.replace("：", ":").split(":", 1)
                            if len(parts) == 2:
                                key = parts[0].strip().rstrip("0123456789.").strip()
                                status_dict[key] = parts[1].strip()
                
                # 更新来自新信息的状况
                new_status_lines = new_dict["最近状况"].split("\n")
                for line in new_status_lines:
                    if ":" in line or "：" in line:
                        parts = line.replace("：", ":").split(":", 1)
                        if len(parts) == 2:
                            key = parts[0].strip().rstrip("0123456789.").strip()
                            if key and parts[1].strip():
                                status_dict[key] = parts[1].strip()
                
                # 如果是原来的格式化结构，保持原有结构
                if "最近状况" in existing_dict and existing_dict["最近状况"].startswith("1."):
                    status_text = []
                    index = 1
                    for key, value in status_dict.items():
                        status_text.append(f"{index}. {key}: {value}")
                        index += 1
                    existing_dict["最近状况"] = "\n".join(status_text)
                else:
                    # 否则使用新格式
                    status_text = []
                    for key, value in status_dict.items():
                        status_text.append(f"{key}: {value}")
                    existing_dict["最近状况"] = "\n".join(status_text)

            # 4. 特殊处理"心理状态"
            if "心理状态" in new_dict and new_dict["心理状态"]:
                # 直接替换心理状态，因为这是情绪评估的结果
                existing_dict["心理状态"] = new_dict["心理状态"]
            
            # 构建合并后的信息文本
            merged_info = ""
            # 基本信息部分
            for key in basic_info_keys:
                if key in existing_dict and existing_dict[key]:
                    merged_info += f"{key}: {existing_dict[key]}\n"
            
            merged_info += "\n"
            
            # 最近状况部分
            if "最近状况" in existing_dict:
                merged_info += "最近状况: \n" + existing_dict["最近状况"] + "\n\n"
            
            # 心理状态部分
            if "心理状态" in existing_dict:
                merged_info += "心理状态: \n" + existing_dict["心理状态"] + "\n\n"
            
            # 其他信息
            for key in existing_dict:
                if key not in basic_info_keys and key not in ["最近状况", "心理状态"] and existing_dict[key]:
                    merged_info += f"{key}: {existing_dict[key]}\n"
            
            # 保存合并后的信息
            with open(self.user_info_file, 'w', encoding='utf-8') as f:
                f.write(merged_info.strip())
            
            # 更新内存中的用户信息
            self.user_info = self._load_user_info()
                
        except Exception as e:
            print(f"保存个人信息文件出错: {e}")
            
    def has_substantial_changes(self, old_info: str, new_info: str) -> bool:
        """判断新旧用户信息是否有实质性变化"""
        if not old_info or not new_info:
            return True
            
        # 解析信息为字典形式
        old_dict = self.parse_user_info(old_info)
        new_dict = self.parse_user_info(new_info)
        
        # 检查是否有新的键
        for key in new_dict:
            if key not in old_dict:
                return True
        
        # 检查值是否有变化
        for key in new_dict:
            if key in old_dict:
                # 忽略空格和大小写的差异
                old_value = old_dict[key].lower().strip()
                new_value = new_dict[key].lower().strip()
                if old_value != new_value:
                    # 进一步检查是否只是格式变化
                    if not self._is_format_change_only(old_value, new_value):
                        return True
        
        return False
    
    def _is_format_change_only(self, old_text: str, new_text: str) -> bool:
        """判断两段文本是否只有格式上的差异"""
        # 移除所有空格、换行和标点
        def normalize(text):
            # 移除所有空格、换行和标点符号
            return re.sub(r'[\s\r\n,.;，。；、！？!?]+', '', text)
        
        normalized_old = normalize(old_text)
        normalized_new = normalize(new_text)
        
        # 如果处理后的文本基本相同，认为只有格式变化
        return normalized_old == normalized_new
    
    def parse_user_info(self, info_text: str) -> dict:
        """解析用户信息文本为字典结构"""
        info_dict = {}
        current_key = None
        current_value = []
        
        lines = info_text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 检查是否是新的键值对
            if ":" in line or "：" in line:
                # 如果已有键，先保存之前的
                if current_key:
                    info_dict[current_key] = "\n".join(current_value)
                    current_value = []
                
                # 解析新的键值对
                parts = line.replace("：", ":").split(":", 1)
                if len(parts) == 2:
                    current_key = parts[0].strip()
                    value = parts[1].strip()
                    if value:  # 如果值不为空，直接保存
                        current_value.append(value)
                    else:  # 否则可能是多行值的开始
                        current_key = parts[0].strip()
            else:
                # 继续添加到当前值
                if current_key:
                    current_value.append(line)
        
        # 保存最后一个键值对
        if current_key and current_value:
            info_dict[current_key] = "\n".join(current_value)
        
        return info_dict
        
    def manually_update_user_info(self, info_type: str, info_content: str, career_intent: str = "") -> str:
        """手动更新用户信息
        
        Args:
            info_type: 信息类型
            info_content: 信息内容
            career_intent: 可选的职业意向信息，当更新学校信息关联到职业规划时使用
            
        Returns:
            str: 更新后的用户信息
        """
        if not self.user_info:
            return ""
        
        # 解析当前用户信息
        info_dict = self.parse_user_info(self.user_info)
        
        # 特殊处理爱好字段
        if info_type == "爱好":
            if "爱好" in info_dict:
                current_hobbies = info_dict["爱好"].split("、")
                # 检查新爱好是否已存在
                if info_content not in current_hobbies:
                    current_hobbies.append(info_content)
                    info_dict["爱好"] = "、".join(current_hobbies)
            else:
                info_dict["爱好"] = info_content
        
        # 处理最近状况特殊字段
        elif info_type.startswith("最近状况_"):
            status_type = info_type.split("_")[1]
            
            if "最近状况" in info_dict:
                status_text = info_dict["最近状况"]
                status_lines = status_text.split("\n")
                updated = False
                
                # 检查是否已有相应类型的状况，如果有则更新
                for i, line in enumerate(status_lines):
                    if status_type in line:
                        # 替换现有内容
                        key_part = line.split(":", 1)[0] if ":" in line else line
                        status_lines[i] = f"{key_part}: {info_content}"
                        updated = True
                        break
                
                # 如果没有找到对应类型，添加新行
                if not updated:
                    # 尝试按编号格式添加
                    if any(line.strip().startswith(str(i) + ".") for i in range(1, 10) for line in status_lines):
                        next_num = max([int(line.strip().split(".")[0]) 
                                      for line in status_lines 
                                      if line.strip() and line.strip()[0].isdigit() and "." in line.strip()], default=0) + 1
                        status_lines.append(f"{next_num}. {status_type}: {info_content}")
                    else:
                        status_lines.append(f"{status_type}: {info_content}")
                
                info_dict["最近状况"] = "\n".join(status_lines)
            else:
                # 如果没有最近状况字段，创建新的
                info_dict["最近状况"] = f"{status_type}: {info_content}"
        
        # 处理普通字段
        else:
            info_dict[info_type] = info_content
            
            # 关联更新机制：如果更新了学校信息，且提供了职业意向信息，同时更新职业规划
            if info_type == "学校" and career_intent and info_dict.get("职业规划", "") != career_intent:
                print(f"检测到学校信息变更，关联更新职业规划: {career_intent}")
                info_dict["职业规划"] = career_intent
        
        # 重构用户信息
        basic_info_keys = ["姓名", "年龄", "性别", "学校", "专业", "年级", "爱好"]
        merged_info = ""
        
        # 基本信息部分
        for key in basic_info_keys:
            if key in info_dict and info_dict[key]:
                merged_info += f"{key}: {info_dict[key]}\n"
        
        merged_info += "\n"
        
        # 最近状况部分
        if "最近状况" in info_dict:
            merged_info += "最近状况: \n" + info_dict["最近状况"] + "\n"
        
        # 其他信息
        for key in info_dict:
            if key not in basic_info_keys and key != "最近状况" and info_dict[key]:
                merged_info += f"{key}: {info_dict[key]}\n"
        
        return merged_info.strip() 