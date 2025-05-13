import json
import os
from datetime import datetime

class UserInfoManager:
    """用户信息管理器，负责存储和管理用户的个人信息"""
    
    def __init__(self, user_id="default_user", save_dir="save"):
        self.user_id = user_id
        self.save_dir = save_dir
        
        # 确保保存目录存在
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        # 创建用户专属的保存目录
        self.user_save_dir = os.path.join(save_dir, user_id)
        if not os.path.exists(self.user_save_dir):
            os.makedirs(self.user_save_dir)
        
        # 用户信息文件路径
        self.user_info_file = os.path.join(save_dir, f"{user_id}_info.json")
        
        # 用户me.txt文件路径
        self.user_me_file = os.path.join(self.user_save_dir, "me.txt")
        
        # 初始化用户信息
        self.user_info = self._load_user_info()
        
        # 确保me.txt文件存在
        self._ensure_me_file_exists()
    
    def _load_user_info(self):
        """加载用户信息，如果文件不存在则创建初始信息"""
        if os.path.exists(self.user_info_file):
            try:
                with open(self.user_info_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return self._create_initial_info()
        else:
            return self._create_initial_info()
    
    def _create_initial_info(self):
        """创建初始用户信息结构"""
        return {
            "user_id": self.user_id,
            "basic_info": {
                "姓名": "",
                "年龄": "",
                "性别": "",
                "学校": "",
                "专业": "",
                "职业": ""
            },
            "personal_info": {
                "心理状态": {
                    "描述": "",
                    "更新时间": ""
                },
                "学习状况": {
                    "描述": "",
                    "更新时间": ""
                },
                "人际关系": {
                    "描述": "",
                    "更新时间": ""
                },
                "价值观": {
                    "描述": "",
                    "更新时间": ""
                }
            },
            "history": []
        }
    
    def _ensure_me_file_exists(self):
        """确保用户的me.txt文件存在，如果不存在则创建空文件"""
        if not os.path.exists(self.user_me_file):
            with open(self.user_me_file, 'w', encoding='utf-8') as f:
                f.write(f"# {self.user_id}的个人信息记录\n\n")
    
    def _save_user_info(self):
        """保存用户信息到文件"""
        try:
            with open(self.user_info_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_info, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存用户信息时出错: {e}")
            return False
    
    def update_basic_info(self, basic_info):
        """更新用户基本信息"""
        if not basic_info:
            return False
        
        # 记录历史变更
        for key, value in basic_info.items():
            if key in self.user_info["basic_info"] and self.user_info["basic_info"][key] != value:
                self.user_info["history"].append({
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "type": "basic_info",
                    "field": key,
                    "old_value": self.user_info["basic_info"][key],
                    "new_value": value
                })
        
        # 更新信息
        self.user_info["basic_info"].update(basic_info)
        
        # 保存更新后的信息
        return self._save_user_info()
    
    def update_personal_info(self, intent_info):
        """更新用户个人信息"""
        if not intent_info:
            return False
        
        # 意图类型到个人信息类型的映射
        intent_to_info_type = {
            "mental_state": "心理状态",
            "learning_situation": "学习状况",
            "relationship": "人际关系",
            "values": "价值观"
        }
        
        # 记录变更并更新信息
        for intent_type, (_, description) in intent_info.items():
            if intent_type in intent_to_info_type:
                info_type = intent_to_info_type[intent_type]
                
                # 记录历史变更
                if info_type in self.user_info["personal_info"] and self.user_info["personal_info"][info_type]["描述"] != description:
                    self.user_info["history"].append({
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "type": "personal_info",
                        "field": info_type,
                        "old_value": self.user_info["personal_info"][info_type]["描述"],
                        "new_value": description
                    })
                
                # 更新信息
                self.user_info["personal_info"][info_type] = {
                    "描述": description,
                    "更新时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
        
        # 保存更新后的信息
        return self._save_user_info()
    
    def update_me_file(self, content):
        """更新用户的me.txt文件内容"""
        try:
            with open(self.user_me_file, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"更新用户me.txt文件时出错: {e}")
            return False
    
    def read_me_file(self):
        """读取用户的me.txt文件内容"""
        if os.path.exists(self.user_me_file):
            try:
                with open(self.user_me_file, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                print(f"读取用户me.txt文件时出错: {e}")
        return f"# {self.user_id}的个人信息记录\n\n"
    
    def get_user_info(self):
        """获取用户完整信息"""
        return self.user_info
    
    def get_basic_info(self):
        """获取用户基本信息"""
        return self.user_info["basic_info"]
    
    def get_personal_info(self):
        """获取用户个人信息"""
        return self.user_info["personal_info"]
    
    def get_history(self, limit=10):
        """获取用户信息变更历史"""
        return self.user_info["history"][-limit:] 