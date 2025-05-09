import os
import json
import time
import logging
import aiosqlite
import hashlib
import secrets
from typing import List, Dict, Any, Optional, Tuple

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
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    profile TEXT
);

CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    message_data TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (username) REFERENCES users(username)
);

CREATE TABLE IF NOT EXISTS user_sessions (
    session_id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    FOREIGN KEY (username) REFERENCES users(username)
);

CREATE TABLE IF NOT EXISTS password_reset (
    reset_token TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    used BOOLEAN DEFAULT 0,
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

def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """使用SHA-256哈希密码
    
    Args:
        password: 明文密码
        salt: 盐值，如果为None则生成新的盐值
        
    Returns:
        Tuple[str, str]: (密码哈希, 盐值)
    """
    if salt is None:
        salt = secrets.token_hex(16)
    
    # 使用密码和盐值创建哈希
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return password_hash, salt

async def register_user(username: str, email: str, password: str, profile: Optional[Dict] = None) -> Dict[str, Any]:
    """注册新用户
    
    Args:
        username: 用户名
        email: 电子邮箱
        password: 密码
        profile: 用户资料信息
        
    Returns:
        Dict[str, Any]: 包含操作结果的字典
    """
    try:
        # 确保数据库已初始化
        await init_db()
        
        async with aiosqlite.connect(DB_FILE) as db:
            # 检查用户名是否已存在
            async with db.execute("SELECT username FROM users WHERE username = ?", (username,)) as cursor:
                if await cursor.fetchone():
                    return {"success": False, "message": "用户名已存在"}
            
            # 检查邮箱是否已存在
            async with db.execute("SELECT email FROM users WHERE email = ?", (email,)) as cursor:
                if await cursor.fetchone():
                    return {"success": False, "message": "邮箱已被注册"}
            
            # 哈希密码
            password_hash, salt = hash_password(password)
            
            # 准备用户资料JSON
            profile_json = json.dumps(profile or {}, ensure_ascii=False)
            
            # 插入新用户
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            await db.execute(
                """INSERT INTO users 
                   (username, email, password_hash, salt, created_at, last_login, profile) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (username, email, password_hash, salt, current_time, current_time, profile_json)
            )
            await db.commit()
            
            logger.info(f"用户注册成功: {username}")
            return {"success": True, "message": "用户注册成功", "username": username}
    except Exception as e:
        logger.error(f"用户注册失败: {str(e)}")
        return {"success": False, "message": f"用户注册失败: {str(e)}"}

async def authenticate_user(username: str, password: str) -> Dict[str, Any]:
    """验证用户凭据
    
    Args:
        username: 用户名
        password: 密码
        
    Returns:
        Dict[str, Any]: 包含认证结果的字典
    """
    try:
        # 确保数据库已初始化
        await init_db()
        
        async with aiosqlite.connect(DB_FILE) as db:
            db.row_factory = aiosqlite.Row
            
            # 查询用户信息
            async with db.execute(
                """SELECT username, email, password_hash, salt, profile, is_active
                   FROM users WHERE username = ?""",
                (username,)
            ) as cursor:
                user = await cursor.fetchone()
                
                if not user:
                    return {"success": False, "message": "用户不存在"}
                
                if not user['is_active']:
                    return {"success": False, "message": "账户已被禁用"}
                
                # 验证密码
                stored_hash = user['password_hash']
                salt = user['salt']
                computed_hash, _ = hash_password(password, salt)
                
                if computed_hash != stored_hash:
                    return {"success": False, "message": "密码错误"}
                
                # 生成会话ID
                session_id = secrets.token_hex(32)
                
                # 更新用户最后登录时间
                current_time = time.strftime("%Y-%m-%d %H:%M:%S")
                await db.execute(
                    "UPDATE users SET last_login = ? WHERE username = ?",
                    (current_time, username)
                )
                
                # 创建会话记录
                expires_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() + 86400))  # 24小时后过期
                await db.execute(
                    "INSERT INTO user_sessions (session_id, username, created_at, expires_at) VALUES (?, ?, ?, ?)",
                    (session_id, username, current_time, expires_at)
                )
                
                await db.commit()
                
                # 解析用户资料
                try:
                    profile = json.loads(user['profile']) if user['profile'] else {}
                except json.JSONDecodeError:
                    profile = {}
                
                return {
                    "success": True,
                    "message": "登录成功",
                    "session_id": session_id,
                    "user": {
                        "username": user['username'],
                        "email": user['email'],
                        "profile": profile
                    }
                }
    except Exception as e:
        logger.error(f"用户认证失败: {str(e)}")
        return {"success": False, "message": f"用户认证失败: {str(e)}"}

async def verify_session(session_id: str) -> Dict[str, Any]:
    """验证会话有效性
    
    Args:
        session_id: 会话ID
        
    Returns:
        Dict[str, Any]: 包含验证结果的字典
    """
    try:
        # 确保数据库已初始化
        await init_db()
        
        async with aiosqlite.connect(DB_FILE) as db:
            db.row_factory = aiosqlite.Row
            
            # 查询会话信息
            async with db.execute(
                """SELECT s.username, s.expires_at, u.email, u.profile, u.is_active
                   FROM user_sessions s
                   JOIN users u ON s.username = u.username
                   WHERE s.session_id = ?""",
                (session_id,)
            ) as cursor:
                session = await cursor.fetchone()
                
                if not session:
                    return {"success": False, "message": "会话不存在"}
                
                if not session['is_active']:
                    return {"success": False, "message": "账户已被禁用"}
                
                # 检查会话是否过期
                current_time = time.strftime("%Y-%m-%d %H:%M:%S")
                if session['expires_at'] < current_time:
                    return {"success": False, "message": "会话已过期"}
                
                # 解析用户资料
                try:
                    profile = json.loads(session['profile']) if session['profile'] else {}
                except json.JSONDecodeError:
                    profile = {}
                
                return {
                    "success": True,
                    "message": "会话有效",
                    "user": {
                        "username": session['username'],
                        "email": session['email'],
                        "profile": profile
                    }
                }
    except Exception as e:
        logger.error(f"会话验证失败: {str(e)}")
        return {"success": False, "message": f"会话验证失败: {str(e)}"}

async def update_user_profile(username: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """更新用户资料
    
    Args:
        username: 用户名
        profile_data: 要更新的资料数据
        
    Returns:
        Dict[str, Any]: 包含操作结果的字典
    """
    try:
        # 确保数据库已初始化
        await init_db()
        
        async with aiosqlite.connect(DB_FILE) as db:
            db.row_factory = aiosqlite.Row
            
            # 检查用户是否存在
            async with db.execute("SELECT profile FROM users WHERE username = ?", (username,)) as cursor:
                user = await cursor.fetchone()
                
                if not user:
                    return {"success": False, "message": "用户不存在"}
                
                # 获取现有资料
                try:
                    current_profile = json.loads(user['profile']) if user['profile'] else {}
                except json.JSONDecodeError:
                    current_profile = {}
                
                # 更新资料
                current_profile.update(profile_data)
                profile_json = json.dumps(current_profile, ensure_ascii=False)
                
                # 保存到数据库
                await db.execute(
                    "UPDATE users SET profile = ? WHERE username = ?",
                    (profile_json, username)
                )
                await db.commit()
                
                return {
                    "success": True,
                    "message": "资料更新成功",
                    "profile": current_profile
                }
    except Exception as e:
        logger.error(f"更新用户资料失败: {str(e)}")
        return {"success": False, "message": f"更新用户资料失败: {str(e)}"}

async def change_password(username: str, current_password: str, new_password: str) -> Dict[str, Any]:
    """修改用户密码
    
    Args:
        username: 用户名
        current_password: 当前密码
        new_password: 新密码
        
    Returns:
        Dict[str, Any]: 包含操作结果的字典
    """
    try:
        # 确保数据库已初始化
        await init_db()
        
        # 验证当前密码
        auth_result = await authenticate_user(username, current_password)
        if not auth_result["success"]:
            return {"success": False, "message": "当前密码错误"}
        
        async with aiosqlite.connect(DB_FILE) as db:
            # 生成新的密码哈希
            password_hash, salt = hash_password(new_password)
            
            # 更新密码
            await db.execute(
                "UPDATE users SET password_hash = ?, salt = ? WHERE username = ?",
                (password_hash, salt, username)
            )
            
            # 删除所有现有会话，强制重新登录
            await db.execute("DELETE FROM user_sessions WHERE username = ?", (username,))
            
            await db.commit()
            
            return {"success": True, "message": "密码修改成功，请重新登录"}
    except Exception as e:
        logger.error(f"修改密码失败: {str(e)}")
        return {"success": False, "message": f"修改密码失败: {str(e)}"}

async def generate_password_reset_token(email: str) -> Dict[str, Any]:
    """生成密码重置令牌
    
    Args:
        email: 用户邮箱
        
    Returns:
        Dict[str, Any]: 包含操作结果的字典
    """
    try:
        # 确保数据库已初始化
        await init_db()
        
        async with aiosqlite.connect(DB_FILE) as db:
            db.row_factory = aiosqlite.Row
            
            # 查找用户
            async with db.execute("SELECT username FROM users WHERE email = ?", (email,)) as cursor:
                user = await cursor.fetchone()
                
                if not user:
                    return {"success": False, "message": "该邮箱未注册"}
                
                username = user['username']
                
                # 生成重置令牌
                reset_token = secrets.token_hex(32)
                current_time = time.strftime("%Y-%m-%d %H:%M:%S")
                
                # 令牌1小时内有效
                expires_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() + 3600))
                
                # 删除旧的重置请求
                await db.execute("DELETE FROM password_reset WHERE username = ?", (username,))
                
                # 插入新的重置请求
                await db.execute(
                    """INSERT INTO password_reset 
                       (reset_token, username, created_at, expires_at) 
                       VALUES (?, ?, ?, ?)""",
                    (reset_token, username, current_time, expires_at)
                )
                
                await db.commit()
                
                return {
                    "success": True,
                    "message": "密码重置令牌已生成",
                    "reset_token": reset_token,
                    "username": username,
                    "expires_at": expires_at
                }
    except Exception as e:
        logger.error(f"生成密码重置令牌失败: {str(e)}")
        return {"success": False, "message": f"生成密码重置令牌失败: {str(e)}"}

async def reset_password_with_token(reset_token: str, new_password: str) -> Dict[str, Any]:
    """使用令牌重置密码
    
    Args:
        reset_token: 重置令牌
        new_password: 新密码
        
    Returns:
        Dict[str, Any]: 包含操作结果的字典
    """
    try:
        # 确保数据库已初始化
        await init_db()
        
        async with aiosqlite.connect(DB_FILE) as db:
            db.row_factory = aiosqlite.Row
            
            # 查找令牌
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            async with db.execute(
                """SELECT username, expires_at, used 
                   FROM password_reset 
                   WHERE reset_token = ? AND expires_at > ? AND used = 0""",
                (reset_token, current_time)
            ) as cursor:
                token_info = await cursor.fetchone()
                
                if not token_info:
                    return {"success": False, "message": "无效或已过期的重置令牌"}
                
                username = token_info['username']
                
                # 生成新的密码哈希
                password_hash, salt = hash_password(new_password)
                
                # 更新密码
                await db.execute(
                    "UPDATE users SET password_hash = ?, salt = ? WHERE username = ?",
                    (password_hash, salt, username)
                )
                
                # 将令牌标记为已使用
                await db.execute(
                    "UPDATE password_reset SET used = 1 WHERE reset_token = ?",
                    (reset_token,)
                )
                
                # 删除所有现有会话，强制重新登录
                await db.execute("DELETE FROM user_sessions WHERE username = ?", (username,))
                
                await db.commit()
                
                return {"success": True, "message": "密码已重置，请使用新密码登录"}
    except Exception as e:
        logger.error(f"重置密码失败: {str(e)}")
        return {"success": False, "message": f"重置密码失败: {str(e)}"}

async def logout_user(session_id: str) -> Dict[str, Any]:
    """用户登出，删除会话
    
    Args:
        session_id: 会话ID
        
    Returns:
        Dict[str, Any]: 包含操作结果的字典
    """
    try:
        # 确保数据库已初始化
        await init_db()
        
        async with aiosqlite.connect(DB_FILE) as db:
            # 删除会话
            await db.execute("DELETE FROM user_sessions WHERE session_id = ?", (session_id,))
            await db.commit()
            
            return {"success": True, "message": "成功登出"}
    except Exception as e:
        logger.error(f"退出登录失败: {str(e)}")
        return {"success": False, "message": f"退出登录失败: {str(e)}"}

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
                """SELECT username, email, created_at, last_login, is_active, profile 
                   FROM users ORDER BY last_login DESC"""
            ) as cursor:
                rows = await cursor.fetchall()
                users = []
                
                for row in rows:
                    try:
                        profile = json.loads(row['profile']) if row['profile'] else {}
                    except json.JSONDecodeError:
                        profile = {}
                    
                    users.append({
                        "username": row['username'],
                        "email": row['email'],
                        "created_at": row['created_at'],
                        "last_login": row['last_login'],
                        "is_active": bool(row['is_active']),
                        "profile": profile
                    })
                
                return users
    except Exception as e:
        logger.error(f"获取所有用户信息失败: {str(e)}")
        return []

# 保持向后兼容的函数
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
            # 确保用户存在 - 现在我们有更完善的用户表，需要检查
            async with db.execute("SELECT username FROM users WHERE username = ?", (username,)) as cursor:
                user = await cursor.fetchone()
                
                # 如果用户不存在，使用最小信息创建一个
                if not user:
                    await db.execute(
                        """INSERT INTO users 
                           (username, email, password_hash, salt, last_login) 
                           VALUES (?, ?, ?, ?, ?)""",
                        (username, f"{username}@example.com", "", "", time.strftime("%Y-%m-%d %H:%M:%S"))
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