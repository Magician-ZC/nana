import sys
import os

# 添加当前目录到系统路径，确保能够导入自定义模块
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from backend.info_extractor import InfoExtractor
from backend.user_info_manager import UserInfoManager

def test_info_processing():
    """测试用户信息处理流程"""
    # 初始化信息提取器和用户信息管理器
    extractor = InfoExtractor()
    manager = UserInfoManager(user_id="test_user")
    
    # 测试案例
    test_messages = [
        "我叫张三，今年25岁，是一名大学生",
        "我是男生，在北京大学学习计算机科学专业",
        "我不认为我会是一个好老师，但是我又不想做其他工作",
        "我想调整自己的心理状态，感觉最近压力很大",
        "我和我的室友关系很紧张，不知道怎么解决",
        "我希望提高自己的学习成绩，但总是记不住知识点",
        "我对未来感到迷茫，不知道什么才是我人生最重要的事情"
    ]
    
    # 处理每条测试消息
    for message in test_messages:
        print(f"\n正在处理消息: {message}")
        
        # 提取信息
        extracted_info = extractor.extract_info(message)
        
        # 输出提取结果
        print("\n提取的基本信息:")
        for key, value in extracted_info["basic_info"].items():
            if value:
                print(f"- {key}: {value}")
        
        # 输出识别的意图
        if extracted_info["intent_info"]:
            print("\n识别的意图信息:")
            for intent_type, (_, description) in extracted_info["intent_info"].items():
                print(f"- {intent_type}: {description}")
        
        # 更新用户信息
        manager.update_basic_info(extracted_info["basic_info"])
        if extracted_info["intent_info"]:
            manager.update_personal_info(extracted_info["intent_info"])
        
        print("\n" + "-" * 50)
    
    # 输出最终的用户信息
    print("\n最终的用户信息:")
    user_info = manager.get_user_info()
    
    print("\n基本信息:")
    for key, value in user_info["basic_info"].items():
        print(f"- {key}: {value}")
    
    print("\n个人信息:")
    for key, value in user_info["personal_info"].items():
        if value["描述"]:
            print(f"- {key}: {value['描述']} (更新时间: {value['更新时间']})")
    
    print("\n信息变更历史:")
    for history_item in user_info["history"]:
        print(f"- {history_item['time']} - {history_item['type']} - {history_item['field']}: {history_item['old_value']} -> {history_item['new_value']}")

if __name__ == "__main__":
    test_info_processing() 