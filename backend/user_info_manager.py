import json
import os
import aiosqlite
import logging
from datetime import datetime
import db_manager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        
        # 用户me.txt文件路径
        self.user_me_file = os.path.join(self.user_save_dir, "me.txt")
        
        # 初始化用户信息
        self.user_info = self._load_user_info()
        
        # 初始化用户配置
        self.user_config = self._load_user_config()
        
        # 确保me.txt文件存在
        self._ensure_me_file_exists()
    
    async def _get_user_profile_from_db(self):
        """从数据库获取用户配置文件"""
        try:
            # 从数据库获取用户的profile信息
            async with aiosqlite.connect(db_manager.DB_FILE) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT profile FROM users WHERE username = ?",
                    (self.user_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    
                    if row and row['profile']:
                        try:
                            # 解析JSON格式的profile字段
                            profile_data = json.loads(row['profile'])
                            # 如果profile中有ui_settings，则返回它
                            if 'ui_settings' in profile_data:
                                logger.info(f"从数据库获取到用户 {self.user_id} 的UI设置: {profile_data['ui_settings']}")
                                return profile_data['ui_settings']
                            return profile_data
                        except json.JSONDecodeError:
                            logger.error(f"解析用户 {self.user_id} 的profile时出错")
                            return {}
            
            # 如果没有找到或发生其他错误，返回空字典
            return {}
        except Exception as e:
            logger.error(f"从数据库获取用户 {self.user_id} 的profile时出错: {e}")
            return {}
    
    async def _save_user_profile_to_db(self, profile_data):
        """保存用户配置到数据库"""
        try:
            # 首先获取完整的profile
            current_profile = await self._get_user_profile_from_db()
            
            # 创建一个包含ui_settings的结构
            full_profile = {}
            
            # 如果当前profile是一个包含ui_settings的结构，保留其他字段
            if isinstance(current_profile, dict):
                if 'ui_settings' in current_profile:
                    # 如果是旧格式(有ui_settings字段)，保留其他字段
                    full_profile = current_profile
                else:
                    # 如果是旧版本的profile(没有ui_settings字段)，将其整体放入ui_settings
                    full_profile['ui_settings'] = current_profile
            
            # 更新ui_settings
            full_profile['ui_settings'] = profile_data
            
            logger.info(f"准备保存用户 {self.user_id} 的配置到数据库: {full_profile}")
            
            # 将更新后的profile保存回数据库
            async with aiosqlite.connect(db_manager.DB_FILE) as db:
                # 检查用户是否存在
                async with db.execute(
                    "SELECT COUNT(*) FROM users WHERE username = ?",
                    (self.user_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    user_exists = row and row[0] > 0
                
                profile_json = json.dumps(full_profile, ensure_ascii=False)
                
                if user_exists:
                    # 更新现有用户
                    await db.execute(
                        "UPDATE users SET profile = ? WHERE username = ?",
                        (profile_json, self.user_id)
                    )
                    await db.commit()
                    logger.info(f"用户 {self.user_id} 的配置已保存到数据库")
                    return True
                else:
                    # 用户不存在，记录日志但不插入
                    # 注: 实际应用中应先通过正常注册流程创建用户
                    logger.warning(f"用户 {self.user_id} 不存在于数据库中，无法保存配置")
                    return False
                
        except Exception as e:
            logger.error(f"保存用户 {self.user_id} 的配置到数据库时出错: {e}")
            return False
    
    def _load_user_info(self):
        """加载用户信息，如果文件不存在则创建初始信息"""
        return self._create_initial_info()
    
    def _load_user_config(self):
        """加载用户配置"""
        return self._create_initial_config()
    
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
    
    def _create_initial_config(self):
        """创建初始用户配置结构"""
        from config import Config
        
        return {
            "enable_tts": Config.ENABLE_TTS,
            "enable_super_tts": Config.ENABLE_SUPER_TTS,
            "enable_tts_global": Config.ENABLE_TTS_GLOBAL,
            "tts_voice": Config.TTS_VCN,
            "super_tts_voice": Config.SUPER_TTS_VCN,
            "tts_speed": Config.TTS_SPEED,
            "typing_speed": Config.TYPING_SPEED,
            "voice_input_mode": Config.VOICE_INPUT_MODE,
            "voice_timeout": Config.VOICE_TIMEOUT
        }
    
    def _ensure_me_file_exists(self):
        """确保用户的me.txt文件存在，如果不存在则创建空文件"""
        if not os.path.exists(self.user_me_file):
            with open(self.user_me_file, 'w', encoding='utf-8') as f:
                f.write(f"# {self.user_id}的个人信息记录\n\n")
    
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
        return True
    
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
        
        return True
    
    async def update_ui_settings(self, settings):
        """更新用户界面设置
        
        Args:
            settings: 用户界面设置字典
            
        Returns:
            bool: 是否成功更新
        """
        if not settings:
            logger.error(f"更新用户设置失败: 设置数据为空")
            return False
        
        try:
            # 先获取当前的设置
            current_settings = await self.get_ui_settings()
            
            # 合并现有设置和新设置
            updated_settings = {**current_settings, **settings}
            logger.info(f"更新用户设置: 当前={current_settings}, 新设置={settings}, 合并结果={updated_settings}")
            
            # 更新本地配置
            self.user_config = updated_settings
            
            # 保存到数据库
            result = await self._save_user_profile_to_db(self.user_config)
            return result
        except Exception as e:
            logger.error(f"更新用户 {self.user_id} 的UI设置时出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def get_ui_settings(self):
        """获取用户界面设置
        
        Returns:
            dict: 用户界面设置
        """
        try:
            # 先尝试从数据库获取
            db_settings = await self._get_user_profile_from_db()
            
            if db_settings:
                # 如果数据库中有配置，使用它
                self.user_config = db_settings
                logger.info(f"从数据库获取到用户 {self.user_id} 的UI设置")
            else:
                # 如果数据库中没有配置，使用默认配置并保存回数据库
                from config import Config
                self.user_config = {
                    "enable_tts": Config.ENABLE_TTS,
                    "enable_super_tts": Config.ENABLE_SUPER_TTS,
                    "enable_tts_global": Config.ENABLE_TTS_GLOBAL,
                    "tts_voice": Config.TTS_VCN,
                    "super_tts_voice": Config.SUPER_TTS_VCN,
                    "tts_speed": Config.TTS_SPEED,
                    "typing_speed": Config.TYPING_SPEED,
                    "voice_input_mode": Config.VOICE_INPUT_MODE,
                    "voice_timeout": Config.VOICE_TIMEOUT
                }
                logger.info(f"用户 {self.user_id} 未找到配置，使用默认配置")
                
                # 保存默认配置到数据库
                await self._save_user_profile_to_db(self.user_config)
            
            return self.user_config
        except Exception as e:
            logger.error(f"获取用户 {self.user_id} 的UI设置时出错: {e}")
            import traceback
            traceback.print_exc()
            # 出错时返回本地配置
            return self.user_config
    
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