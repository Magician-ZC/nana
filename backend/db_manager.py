import os
import json
import time
import logging
import aiosqlite
from typing import List, Dict, Any, Optional

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 数据库文件路径
DB_FILE = os.path.join("data", "chat_history.db")

# 确保数据目录存在
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

# 创建表的SQL语句
CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    message_data TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (username) REFERENCES users(username)
);
"""

async def init_db():
    """初始化数据库，确保表存在"""
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            await db.executescript(CREATE_TABLES_SQL)
            await db.commit()
            logger.info("数据库初始化成功")
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")
        raise

async def save_user_chat_history(username: str, messages: List[Dict[str, Any]]) -> bool:
    """保存用户的聊天历史到数据库
    
    Args:
        username: 用户名
        messages: 消息列表
    
    Returns:
        bool: 是否保存成功
    """
    try:
        # 确保数据库已初始化
        await init_db()
        
        # 将消息转换为JSON字符串
        messages_json = json.dumps(messages, ensure_ascii=False)
        
        async with aiosqlite.connect(DB_FILE) as db:
            # 确保用户存在
            await db.execute(
                "INSERT OR IGNORE INTO users (username, last_login) VALUES (?, ?)",
                (username, time.strftime("%Y-%m-%d %H:%M:%S"))
            )
            
            # 更新用户的最后登录时间
            await db.execute(
                "UPDATE users SET last_login = ? WHERE username = ?",
                (time.strftime("%Y-%m-%d %H:%M:%S"), username)
            )
            
            # 清除现有的聊天历史
            await db.execute("DELETE FROM chat_history WHERE username = ?", (username,))
            
            # 插入新的聊天历史
            await db.execute(
                "INSERT INTO chat_history (username, message_data) VALUES (?, ?)",
                (username, messages_json)
            )
            
            await db.commit()
            logger.info(f"用户 {username} 的聊天历史保存成功")
            return True
    except Exception as e:
        logger.error(f"保存用户 {username} 的聊天历史失败: {str(e)}")
        return False

async def load_user_chat_history(username: str) -> Optional[List[Dict[str, Any]]]:
    """从数据库加载用户的聊天历史
    
    Args:
        username: 用户名
    
    Returns:
        Optional[List[Dict[str, Any]]]: 消息列表，如果没有找到则返回空列表
    """
    try:
        # 确保数据库已初始化
        await init_db()
        
        async with aiosqlite.connect(DB_FILE) as db:
            # 查询用户的聊天历史
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT message_data FROM chat_history WHERE username = ? ORDER BY created_at DESC LIMIT 1",
                (username,)
            ) as cursor:
                row = await cursor.fetchone()
                
                if row:
                    # 更新用户的最后登录时间
                    await db.execute(
                        "UPDATE users SET last_login = ? WHERE username = ?",
                        (time.strftime("%Y-%m-%d %H:%M:%S"), username)
                    )
                    await db.commit()
                    
                    # 解析JSON消息
                    messages = json.loads(row['message_data'])
                    logger.info(f"用户 {username} 的聊天历史加载成功，消息数量: {len(messages)}")
                    return messages
                else:
                    logger.info(f"用户 {username} 没有聊天历史")
                    return []
    except Exception as e:
        logger.error(f"加载用户 {username} 的聊天历史失败: {str(e)}")
        return []

async def clear_user_chat_history(username: str) -> bool:
    """清除用户的聊天历史
    
    Args:
        username: 用户名
    
    Returns:
        bool: 是否清除成功
    """
    try:
        # 确保数据库已初始化
        await init_db()
        
        async with aiosqlite.connect(DB_FILE) as db:
            # 删除用户的聊天历史
            await db.execute("DELETE FROM chat_history WHERE username = ?", (username,))
            await db.commit()
            logger.info(f"用户 {username} 的聊天历史清除成功")
            return True
    except Exception as e:
        logger.error(f"清除用户 {username} 的聊天历史失败: {str(e)}")
        return False

async def get_all_users() -> List[Dict[str, Any]]:
    """获取所有用户信息
    
    Returns:
        List[Dict[str, Any]]: 用户信息列表
    """
    try:
        # 确保数据库已初始化
        await init_db()
        
        async with aiosqlite.connect(DB_FILE) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT username, created_at, last_login FROM users ORDER BY last_login DESC"
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"获取所有用户信息失败: {str(e)}")
        return [] 