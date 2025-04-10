import os
import hashlib
import base64
import requests
import json
import time
from typing import Dict, Any, Optional
import logging
from Crypto.Cipher import DES, AES
from Crypto.Util.Padding import pad, unpad
import binascii

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("QiniuUploader")

# 加密密钥和IV值，与Flutter代码保持一致
DES_KEY = "Ic20a32M"  # 8字节DES密钥
DES_IV = "2w3IoN2Y"   # 8字节DES IV
AES_KEY = "wKnqXvKi3tVMJkbg"  # 16字节AES密钥
AES_IV = "YpNsuo66V8DkFZyb"   # 16字节AES IV

def encrypt_des(plain_text: str, key: str = DES_KEY, iv: str = DES_IV) -> str:
    """
    使用DES CBC模式加密，与Flutter代码保持一致
    """
    try:
        # 确保key和iv正确长度
        key_bytes = key.encode('utf-8')
        iv_bytes = iv.encode('utf-8')
        
        # 创建DES加密器，使用CBC模式
        cipher = DES.new(key_bytes, DES.MODE_CBC, iv_bytes)
        
        # 填充并加密
        padded_data = pad(plain_text.encode('utf-8'), DES.block_size)
        encrypted_bytes = cipher.encrypt(padded_data)
        
        # 转换为十六进制字符串
        encrypted_hex = binascii.hexlify(encrypted_bytes).decode('utf-8')
        
        logger.info(f"DES加密成功: {plain_text[:20]}... -> {encrypted_hex[:20]}...")
        return encrypted_hex
    except Exception as e:
        logger.error(f"DES加密错误: {str(e)}")
        return ""

def decrypt_des(cipher_hex: str, key: str = DES_KEY, iv: str = DES_IV) -> str:
    """
    使用DES CBC模式解密，与Flutter代码保持一致
    """
    try:
        # 确保key和iv正确长度
        key_bytes = key.encode('utf-8')
        iv_bytes = iv.encode('utf-8')
        
        # 创建DES解密器，使用CBC模式
        cipher = DES.new(key_bytes, DES.MODE_CBC, iv_bytes)
        
        # 解码十六进制并解密
        encrypted_bytes = binascii.unhexlify(cipher_hex)
        decrypted_padded = cipher.decrypt(encrypted_bytes)
        
        # 去除填充
        decrypted_bytes = unpad(decrypted_padded, DES.block_size)
        plain_text = decrypted_bytes.decode('utf-8')
        
        logger.info(f"DES解密成功: {cipher_hex[:20]}... -> {plain_text[:20]}...")
        return plain_text
    except Exception as e:
        logger.error(f"DES解密错误: {str(e)}")
        return ""

def encrypt_aes(plain_text: str, key: str = AES_KEY, iv: str = AES_IV) -> str:
    """
    使用AES CBC模式加密，与Flutter代码保持一致
    """
    try:
        # 确保key和iv正确长度
        key_bytes = key.encode('utf-8')
        iv_bytes = iv.encode('utf-8')
        
        # 创建AES加密器，使用CBC模式
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
        
        # 填充并加密
        padded_data = pad(plain_text.encode('utf-8'), AES.block_size)
        encrypted_bytes = cipher.encrypt(padded_data)
        
        # 转换为Base64编码
        encrypted_b64 = base64.b64encode(encrypted_bytes).decode('utf-8')
        
        logger.info(f"AES加密成功: {plain_text[:20]}... -> {encrypted_b64[:20]}...")
        return encrypted_b64
    except Exception as e:
        logger.error(f"AES加密错误: {str(e)}")
        return ""

def decrypt_aes(cipher_b64: str, key: str = AES_KEY, iv: str = AES_IV) -> str:
    """
    使用AES CBC模式解密，与Flutter代码保持一致
    """
    try:
        # 确保key和iv正确长度
        key_bytes = key.encode('utf-8')
        iv_bytes = iv.encode('utf-8')
        
        # 创建AES解密器，使用CBC模式
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
        
        # 解码Base64并解密
        encrypted_bytes = base64.b64decode(cipher_b64)
        decrypted_padded = cipher.decrypt(encrypted_bytes)
        
        # 去除填充
        decrypted_bytes = unpad(decrypted_padded, AES.block_size)
        plain_text = decrypted_bytes.decode('utf-8')
        
        logger.info(f"AES解密成功: {cipher_b64[:20]}... -> {plain_text[:20]}...")
        return plain_text
    except Exception as e:
        logger.error(f"AES解密错误: {str(e)}")
        return ""

def generate_md5(text: str) -> str:
    """
    生成MD5哈希，与Flutter代码中的toMd5()保持一致
    """
    return hashlib.md5(text.encode('utf-8')).hexdigest()

class QiniuUploader:
    def __init__(self):
        self.temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_uploads")
        os.makedirs(self.temp_dir, exist_ok=True)
        
    def get_upload_info(self, auth_token: str) -> Dict[str, Any]:
        """
        获取七牛云上传配置信息，使用加密方式请求
        """
        url = "http://192.168.3.143:30080/app-api/system/family-and-manage/oss/common/get-oss-upload-info"
        
        # 当前时间戳
        timestamp = int(time.time() * 1000)
        # 签名 - 与Flutter代码一致，使用时间戳的MD5
        sign = generate_md5(str(timestamp))
        
        # 请求参数
        query_params = {
            "platform": 1,
            "type": 1,
            "orgId": 0
        }
        
        # 加密请求参数 - 转为JSON字符串后DES加密
        json_query = json.dumps(query_params)
        encrypted_content = encrypt_des(json_query)
        
        # 构建最终请求参数 - 使用字符串格式
        final_data = f"sign={sign}&content={encrypted_content}&timestamp={timestamp}"
        
        # 构建请求头
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        try:
            logger.info(f"发送加密请求: URL={url}, data={final_data[:100]}...")
            response = requests.post(url, headers=headers, data=final_data)
            response.raise_for_status()
            
            # 获取响应内容
            encrypted_response = response.json()
            logger.info(f"收到加密响应: {encrypted_response}")
            
            # 尝试解密响应内容
            result = self.decrypt_response(encrypted_response)
            
            logger.info(f"获取到上传配置原始响应: {result}")
            
            # 修改判断逻辑，适应不同的响应结构
            if isinstance(result, dict):
                # 尝试不同的成功标志
                is_success = (
                    result.get("success") == True or 
                    result.get("code") == 200 or 
                    result.get("status") == 200 or
                    (isinstance(result.get("msg"), str) and "成功" in result.get("msg", ""))
                )
                
                if is_success:
                    # 尝试不同的数据路径
                    data_paths = [
                        result.get("data", {}),
                        result.get("result", {}),
                        result
                    ]
                    
                    for data_path in data_paths:
                        if not isinstance(data_path, dict):
                            continue
                            
                        upload_token = (
                            data_path.get("token") or 
                            data_path.get("uploadToken") or 
                            data_path.get("upload_token") or
                            ""
                        )
                        
                        domain = (
                            data_path.get("domain") or 
                            data_path.get("domainUrl") or 
                            data_path.get("domain_url") or
                            ""
                        )
                        
                        upload_type = (
                            data_path.get("uploadType") or 
                            data_path.get("type") or 
                            ""
                        )
                        
                        if upload_token and domain:
                            logger.info(f"七牛云配置获取成功!")
                            logger.info(f"上传类型: {upload_type}")
                            logger.info(f"域名: {domain}")
                            logger.info(f"Token: {upload_token[:20]}..." if upload_token else "Token: 未获取到")
                            
                            # 返回原始响应格式，但添加解析后的数据
                            result["data"] = {
                                "token": upload_token,
                                "domain": domain,
                                "uploadType": upload_type
                            }
                            result["success"] = True
                            return result
                
                # 如果上面的尝试都失败了
                error_msg = (
                    result.get("message") or 
                    result.get("msg") or 
                    result.get("error") or
                    "未知错误"
                )
                
                logger.error(f"获取七牛云配置失败: {error_msg}")
                result["success"] = False
                return result
            else:
                logger.error(f"获取七牛云配置失败: 响应格式不正确")
                return {
                    "success": False,
                    "message": "响应格式不正确",
                    "data": None
                }
        except Exception as e:
            logger.error(f"获取上传配置失败: {str(e)}")
            return {
                "success": False,
                "message": f"获取上传配置失败: {str(e)}",
                "data": None
            }
    
    def decrypt_response(self, encrypted_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        解密服务器返回的加密响应
        """
        try:
            # 检查响应结构
            if not isinstance(encrypted_response, dict):
                logger.error("解密失败: 响应不是字典格式")
                return encrypted_response
                
            # 检查是否包含必要的加密字段
            if "data" in encrypted_response and isinstance(encrypted_response["data"], dict):
                # 处理data中可能的加密内容
                data = encrypted_response["data"]
                if "content" in data and data["content"]:
                    try:
                        # 尝试DES解密
                        decrypted_content = decrypt_des(data["content"])
                        if decrypted_content:
                            # 尝试解析JSON
                            decrypted_data = json.loads(decrypted_content)
                            # 替换原始data
                            encrypted_response["data"] = decrypted_data
                    except Exception as e:
                        logger.error(f"解密data.content失败: {str(e)}")
            
            # 处理响应根级别可能的加密内容
            if "content" in encrypted_response and encrypted_response["content"]:
                try:
                    # 尝试DES解密
                    decrypted_content = decrypt_des(encrypted_response["content"])
                    if decrypted_content:
                        # 尝试解析JSON
                        decrypted_data = json.loads(decrypted_content)
                        # 合并解密后的数据
                        if isinstance(decrypted_data, dict):
                            # 保留原始的code和message等字段
                            decrypted_data["code"] = encrypted_response.get("code", decrypted_data.get("code"))
                            decrypted_data["message"] = encrypted_response.get("message", decrypted_data.get("message"))
                            decrypted_data["msg"] = encrypted_response.get("msg", decrypted_data.get("msg"))
                            return decrypted_data
                except Exception as e:
                    logger.error(f"解密根级别content失败: {str(e)}")
                
            return encrypted_response
        except Exception as e:
            logger.error(f"响应解密处理异常: {str(e)}")
            return encrypted_response
    
    def save_temp_file(self, file_data: bytes, file_name: str) -> str:
        """
        将文件暂存到本地
        """
        local_path = os.path.join(self.temp_dir, file_name)
        with open(local_path, "wb") as f:
            f.write(file_data)
        logger.info(f"文件已保存到本地: {local_path}")
        return local_path
    
    def convert_to_avi(self, input_path: str) -> str:
        """
        将视频转换为AVI格式，并确保与手机录制的视频属性相同
        
        Args:
            input_path: 输入视频路径
            
        Returns:
            转换后的AVI视频路径
        """
        try:
            import subprocess
            import cv2
            output_path = os.path.splitext(input_path)[0] + "_converted.avi"
            
            # 使用ffmpeg强制设置为标准手机录制参数
            # 视频分辨率720x1280，帧率25fps，降低码率以减小文件大小
            cmd = [
                'ffmpeg', '-y', '-i', input_path,
                '-vf', 'scale=720:1280', # 强制设置分辨率为720x1280
                '-r', '25',              # 强制设置帧率为25fps
                '-vcodec', 'mjpeg',      # 使用MJPEG编码器，OpenCV兼容性最好
                '-pix_fmt', 'yuvj420p',  # 确保像素格式兼容
                '-q:v', '20',            # 降低质量参数 (2-31,越大质量越低，文件越小)
                '-b:v', '800k',          # 降低视频码率至800kbps
                '-maxrate', '1000k',     # 最大码率
                '-bufsize', '1000k',     # 缓冲区大小
                '-acodec', 'pcm_s16le',  # 标准音频编码
                '-ar', '22050',          # 降低音频采样率
                '-ac', '1',              # 单声道音频
                '-vsync', '1',           # 确保帧同步
                output_path
            ]
            
            # 输出命令用于调试
            logger.info(f"执行ffmpeg命令: {' '.join(cmd)}")
            
            # 执行转换
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info(f"ffmpeg输出: {result.stdout}")
            if result.stderr:
                logger.warning(f"ffmpeg警告: {result.stderr}")
            
            # 验证转换后的视频能被OpenCV正确读取
            cap = cv2.VideoCapture(output_path)
            if not cap.isOpened():
                logger.error("转换后的视频无法被OpenCV打开，回退到原始文件")
                return input_path
            
            # 检查视频属性是否正确
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            logger.info(f"转换后视频属性: 宽={width}, 高={height}, FPS={fps}, 总帧数={frame_count}")
            
            # 检查帧数是否正确
            if frame_count <= 0:
                logger.error(f"转换后的视频帧数仍然有问题: {frame_count}")
                return input_path
            
            # 手动验证帧数
            actual_frames = 0
            while True:
                ret, _ = cap.read()
                if not ret:
                    break
                actual_frames += 1
                # 只检查前100帧，避免太慢
                if actual_frames >= 100:
                    break
            
            logger.info(f"实际读取帧数(前100帧): {actual_frames}")
            cap.release()
            
            # 检查文件大小
            original_size = os.path.getsize(input_path)
            converted_size = os.path.getsize(output_path)
            
            logger.info(f"原始文件大小: {original_size/1024/1024:.2f}MB, 转换后文件大小: {converted_size/1024/1024:.2f}MB")
            logger.info(f"压缩率: {(1 - converted_size/original_size) * 100:.2f}%")
            
            if actual_frames > 0:
                logger.info(f"视频转换成功: {output_path}")
                return output_path
            else:
                logger.error("转换后的视频无法读取帧，回退到原始文件")
                return input_path
            
        except Exception as e:
            logger.error(f"视频转换失败: {str(e)}")
            import traceback
            traceback.print_exc()
            # 转换失败时返回原始文件路径
            return input_path
            
    def calculate_file_etag(self, file_path: str) -> str:
        """
        计算文件的七牛云eTag
        根据提供的Java代码实现的Python版本
        """
        if not os.path.exists(file_path):
            return 'Fto5o-5ea0sNMlW_75VgGJCv2AcJ'  # 默认值
            
        prefix = 0x16
        block_size = 4 * 1024 * 1024  # 4MB
        
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
            
        buffer_size = len(file_bytes)
        
        if buffer_size > block_size:
            # 大文件处理
            block_count = buffer_size // block_size
            if buffer_size % block_size > 0:
                block_count += 1
                
            sha1_bytes = bytearray()
            
            for i in range(block_count):
                length = block_size
                if i == block_count - 1 and buffer_size % block_size > 0:
                    length = buffer_size % block_size
                    
                block_data = file_bytes[i * block_size:i * block_size + length]
                sha1_hash = hashlib.sha1(block_data).digest()
                sha1_bytes.extend(sha1_hash)
                
            final_sha1 = hashlib.sha1(sha1_bytes).digest()
            prefix = 0x96
        else:
            # 小文件处理
            final_sha1 = hashlib.sha1(file_bytes).digest()
            
        # 添加前缀
        etag_bytes = bytearray([prefix]) + bytearray(final_sha1)
        etag = base64.urlsafe_b64encode(etag_bytes).decode('utf-8')
        
        logger.info(f"计算的eTag: {etag}")
        return etag
    
    def upload_to_qiniu(self, local_path: str, upload_token: str, etag: str, domain: str) -> Dict[str, Any]:
        """
        上传文件到七牛云
        使用Python SDK上传
        """
        try:
            # 引入七牛SDK
            from qiniu import put_file, etag as qiniu_etag
            
            ret, info = put_file(upload_token, etag, local_path, version='v2')
            
            if info.status_code == 200:
                logger.info(f"上传成功: {ret}")
                return {
                    "status": 1,
                    "etag": ret.get("hash", etag),
                    "local_path": local_path,
                    "remote_path": f"{domain}{etag}"
                }
            else:
                logger.error(f"上传失败: {info}")
                return {
                    "status": 2,
                    "etag": etag,
                    "local_path": local_path,
                    "remote_path": f"{domain}{etag}",
                    "error": str(info)
                }
        except Exception as e:
            logger.error(f"上传异常: {str(e)}")
            return {
                "status": 2,
                "etag": etag,
                "local_path": local_path,
                "remote_path": f"{domain}{etag}",
                "error": str(e)
            }
    
    def notify_upload_result(self, auth_token: str, etag: str, file_path: str, file_type: str) -> Dict[str, Any]:
        """
        通知服务端上传结果
        """
        url = "http://192.168.3.143:30080/app-api/equipment/emotion/video-upload-back"
        
        # 当前时间戳
        timestamp = int(time.time() * 1000)
        # 签名 - 与Flutter代码一致，使用时间戳的MD5
        sign = generate_md5(str(timestamp))
        
        # 获取文件大小
        file_size = os.path.getsize(file_path)
        
        # 构建请求数据
        data = {
            "userName": "启智宝管理7627",
            "userSex": 1,
            "userBirthday": "1970-01-01",
            "key": etag,
            "fileSize": file_size,
            "fileType": file_type
        }
        
        # 加密数据
        json_data = json.dumps(data)
        encrypted_content = encrypt_des(json_data)
        
        # 构建最终请求数据 - 使用字符串格式
        final_data = f"sign={sign}&content={encrypted_content}&timestamp={timestamp}"
        
        # 构建请求头
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        try:
            logger.info(f"发送通知请求: URL={url}, data={data}")
            response = requests.post(url, headers=headers, data=final_data)
            response.raise_for_status()
            
            # 获取响应内容
            encrypted_response = response.json()
            logger.info(f"收到通知响应: {encrypted_response}")
            
            # 尝试解密响应内容
            result = self.decrypt_response(encrypted_response)
            logger.info(f"上传回调成功: {result}")
            
            return result
        except Exception as e:
            logger.error(f"上传回调失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def process_video_upload(self, auth_token: str, video_data: bytes, file_name: str, file_type: str = "avi") -> Dict[str, Any]:
        """
        处理视频上传的完整流程
        """
        try:
            # 确保file_type是avi
            if file_type.lower() != "avi":
                logger.warning(f"指定的文件类型 '{file_type}' 不是AVI，已自动修正为AVI")
                file_type = "avi"
                
            # 确保文件名以.avi结尾
            if not file_name.lower().endswith('.avi'):
                file_name = os.path.splitext(file_name)[0] + '.avi'
                logger.info(f"文件名修正为: {file_name}")

            # 1. 获取上传配置
            upload_info = self.get_upload_info(auth_token)
            if not upload_info.get("success", False):
                return {"success": False, "message": "获取上传配置失败", "data": upload_info}
            
            # 获取上传参数
            upload_data = upload_info.get("data", {})
            if not upload_data:
                return {"success": False, "message": "上传配置数据为空", "data": upload_info}
                
            upload_token = upload_data.get("token", "")
            domain = upload_data.get("domain", "")
            
            if not upload_token or not domain:
                return {
                    "success": False, 
                    "message": "上传配置缺少必要参数", 
                    "data": {
                        "has_token": bool(upload_token),
                        "has_domain": bool(domain)
                    }
                }
            
            # 2. 保存临时文件
            local_path = self.save_temp_file(video_data, file_name)
            
            # 3. 转换视频为标准AVI格式
            logger.info("开始转换视频为标准AVI格式...")
            converted_path = self.convert_to_avi(local_path)
            if converted_path != local_path:
                logger.info(f"视频转换成功: {converted_path}")
                local_path = converted_path
            
            # 4. 计算eTag
            etag = self.calculate_file_etag(local_path)
            
            # 5. 上传文件到七牛云
            upload_result = self.upload_to_qiniu(local_path, upload_token, etag, domain)
            
            if upload_result["status"] != 1:
                return {"success": False, "message": "上传到七牛云失败", "data": upload_result}
            
            # 6. 通知服务端上传结果
            notify_result = self.notify_upload_result(auth_token, etag, local_path, file_type)
            
            # 7. 返回最终结果
            return {
                "success": True,
                "message": "视频上传成功",
                "data": {
                    "etag": etag,
                    "url": f"{domain}{etag}",
                    "upload_result": upload_result,
                    "notify_result": notify_result
                }
            }
            
        except Exception as e:
            logger.error(f"视频上传处理失败: {str(e)}")
            return {
                "success": False,
                "message": f"视频上传处理失败: {str(e)}",
                "data": None
            } 