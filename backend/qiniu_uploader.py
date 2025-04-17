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
import threading

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
        
        # 统一状态管理字典 - 键为report_id
        self.report_status = {}  # {report_id: {"upload_callback": bool, "assessment": bool/int, "downloaded": bool}}
        
        # 记录正在轮询的任务
        self._active_polling = {}
    
    def get_upload_info(self, auth_token: str) -> Dict[str, Any]:
        """
        获取七牛云上传配置信息，使用加密方式请求
        """
        url = "http://qzb.oamicnet.com/app-api/system/family-and-manage/oss/common/get-oss-upload-info"
        
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
            logger.info(f"发送加密请求: URL={url}, data={final_data[:]}...")
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
        url = "http://qzb.oamicnet.com/app-api/equipment/emotion/video-upload-back"
        
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
            
            # 检查响应状态码，如果是200，表示成功
            is_success = result.get("code") == 200
            result["success"] = is_success
            
        
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
                # 上传失败，不设置状态
                return {"success": False, "message": "上传到七牛云失败", "data": upload_result}
            
            # 6. 通知服务端上传结果
            notify_result = self.notify_upload_result(auth_token, etag, local_path, file_type)
            
            # 获取上传回调状态
            upload_callback_success = notify_result.get("success", False)
            
            # 初始化状态 - 但不设置report_id，因为此时还没有
            # 前端需要在获取报告列表后设置report_id
            initial_status = {
                "upload_callback": upload_callback_success,
                "assessment": False,
                "downloaded": False,
                "etag": etag  # 保存etag用于调试
            }
            
            logger.info(f"上传状态设置完成: 上传回调={upload_callback_success}, 评估状态=False, 报告下载状态=False")
            
            # 返回最终结果
            return {
                "success": True,
                "message": "视频上传成功",
                "data": {
                    "url": f"{domain}{etag}",
                    "upload_result": upload_result,
                    "notify_result": notify_result,
                    "upload_callback_status": upload_callback_success,
                    "assessment_status": False,
                    "reportDownloaded": False,
                    "initial_status": initial_status
                }
            }
            
        except Exception as e:
            logger.error(f"视频上传处理失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "message": f"视频上传处理失败: {str(e)}",
                "data": None
            }
            
    def poll_report_status(self, auth_token: str, report_id: str = None):
        """
        轮询检查报告状态，当status为1时下载报告
        
        Args:
            auth_token: 授权令牌
            report_id: 报告ID
        """
        import time
        
        # 如果没有提供report_id，无法轮询
        if not report_id:
            logger.error("轮询需要提供report_id参数")
            return
        
        # 创建轮询标识符
        poll_key = report_id
            
        # 检查是否已在轮询中
        if poll_key in self._active_polling:
            poll_info = self._active_polling[poll_key]
            current_time = time.time()
            if current_time - poll_info['start_time'] < 180:  # 3分钟内的重复请求
                logger.warning(f"已有轮询任务正在进行中: poll_key={poll_key}, thread={poll_info['thread_id']}, 开始于{int(current_time - poll_info['start_time'])}秒前")
                return
            else:
                # 超过3分钟的轮询认为可能已经失效，允许创建新轮询
                logger.info(f"发现可能已失效的轮询任务: poll_key={poll_key}, thread={poll_info['thread_id']}, 开始于{int(current_time - poll_info['start_time'])}秒前")
        
        # 记录当前轮询信息
        self._active_polling[poll_key] = {
            'start_time': time.time(),
            'thread_id': threading.current_thread().ident
        }
        
        logger.info(f"开始轮询检查报告状态 [thread_id={threading.current_thread().ident}]: report_id={report_id}")
            
        try:
            # 轮询设置
            poll_interval = 15  # 增加到15秒轮询一次，减少请求频率
            max_polling_time = 30 * 60  # 最大轮询时间30分钟，避免无限轮询
            polling_start_time = time.time()
            
            # 保存目录设置
            save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "save", "assessments")
            os.makedirs(save_dir, exist_ok=True)
            
            poll_count = 0
            
            # 获取当前状态
            if report_id in self.report_status:
                upload_callback_status = self.report_status[report_id].get("upload_callback", False)
                assessment_status = self.report_status[report_id].get("assessment", False)
                report_downloaded = self.report_status[report_id].get("downloaded", False)
            else:
                # 初始化状态
                self.report_status[report_id] = {
                    "upload_callback": True,
                    "assessment": False,
                    "downloaded": False
                }
                upload_callback_status = True
                assessment_status = False
                report_downloaded = False
            
            # 如果状态已完成，直接返回
            if assessment_status and report_downloaded:
                logger.info(f"状态已完成，无需轮询: report_id={report_id}")
                # 清理轮询状态
                if poll_key in self._active_polling:
                    del self._active_polling[poll_key]
                return
                
            # 如果上传回调为False，直接退出轮询，不需要请求情绪评估列表
            if not upload_callback_status:
                logger.info(f"上传回调为False，停止轮询: report_id={report_id}")
                if poll_key in self._active_polling:
                    del self._active_polling[poll_key]
                return
            
            logger.info(f"轮询初始状态: report_id={report_id}, upload_callback_status={upload_callback_status}, assessment_status={assessment_status}")
            
            # 记录上次请求时间
            last_request_time = 0
            request_interval = 8  # 请求间隔至少8秒
            
            # 只要上传回调成功但评估未完成，就持续轮询，但设置最大轮询时间
            while (upload_callback_status and not assessment_status and 
                   time.time() - polling_start_time < max_polling_time):
                
                # 每次循环开始时检查是否应该停止轮询
                # 检查1: 线程已被标记为停止（从全局POLLING_THREADS中移除）
                import inspect
                frame = inspect.currentframe()
                frame_locals = frame.f_back.f_locals if frame.f_back else {}
                global_polling_threads = frame_locals.get('POLLING_THREADS', {})
                
                if (poll_key not in self._active_polling) or (poll_key not in global_polling_threads):
                    logger.info(f"检测到轮询停止请求，中止轮询: report_id={report_id}")
                    break
                
                # 检查2: 报告状态已更新为下载完成
                if report_id in self.report_status:
                    current_status = self.report_status[report_id]
                    if current_status.get("downloaded", False) or current_status.get("assessment", False):
                        logger.info(f"检测到报告已处理完成，停止轮询: report_id={report_id}, downloaded={current_status.get('downloaded')}, assessment={current_status.get('assessment')}")
                        break
                
                try:
                    poll_count += 1
                    current_time = time.time()
                    
                    # 控制请求频率
                    if current_time - last_request_time < request_interval:
                        wait_time = request_interval - (current_time - last_request_time)
                        logger.info(f"等待请求间隔: {wait_time:.1f}秒")
                        time.sleep(wait_time)
                    
                    logger.info(f"轮询检查报告 [第{poll_count}次]: report_id={report_id}")
                    last_request_time = time.time()
                    
                    # 再次检查轮询是否应该停止
                    if poll_key not in self._active_polling:
                        logger.info(f"轮询过程中检测到停止请求，中止轮询: report_id={report_id}")
                        break
                    
                    # 获取情绪评估列表
                    report_list = self.get_emotion_report_list(auth_token)
                    if not report_list:
                        logger.warning(f"未获取到情绪评估列表，将在{poll_interval}秒后重试")
                        time.sleep(poll_interval)
                        continue
                    
                    # 检查报告列表中是否有匹配的report_id
                    found_report = None
                    for report in report_list:
                        if str(report.get("id", "")) == str(report_id):
                            found_report = report
                            break
                    
                    # 如果找到了匹配的报告
                    if found_report:
                        report_status = found_report.get("status")
                        
                        # 如果状态为1(完成)，下载报告
                        if report_status == 1:
                            logger.info(f"发现已生成的报告: id={report_id}")
                            
                            # 下载报告
                            report_path = self.download_emotion_report(auth_token, report_id, save_dir)
                            
                            if report_path:
                                logger.info(f"报告下载成功: {report_path}")
                                
                                # 更新状态
                                self.report_status[report_id] = {
                                    "upload_callback": True,
                                    "assessment": True,  # True表示报告已生成
                                    "downloaded": True
                                }
                                
                                # 下载成功，只记录日志而不做其他操作
                                logger.info(f"报告下载完成，轮询即将终止: {report_path}")
                                
                                # 无论是否解析成功，都更新状态为完成
                                assessment_status = True
                                report_downloaded = True
                                break
                            else:
                                logger.error(f"报告下载失败: id={report_id}")
                    else:
                        logger.warning(f"在报告列表中未找到匹配的报告ID: {report_id}")
                    
                    # 更新轮询状态变量
                    if report_id in self.report_status:
                        assessment_status = self.report_status[report_id].get("assessment", False)
                        report_downloaded = self.report_status[report_id].get("downloaded", False)
                    
                    # 如果状态已完成，退出循环
                    if assessment_status and report_downloaded:
                        logger.info(f"评估状态已更新为完成，停止轮询: report_id={report_id}")
                        break
                    
                    # 等待下一次轮询
                    logger.info(f"等待{poll_interval}秒后进行下一次轮询")
                    time.sleep(poll_interval)
                    
                except Exception as e:
                    logger.error(f"轮询检查报告出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    time.sleep(poll_interval)  # 出错后依然继续轮询
                
            # 检查轮询退出的原因
            if time.time() - polling_start_time >= max_polling_time:
                logger.warning(f"轮询达到最大时间限制({max_polling_time/60:.1f}分钟)，停止轮询: report_id={report_id}")
            
            logger.info(f"轮询结束: report_id={report_id}, assessment_status={assessment_status}, report_downloaded={report_downloaded}")
            
            # 确保轮询结束时状态一致
            if report_id:
                # 确保所有状态都为True
                self.report_status[report_id] = {
                    "upload_callback": True,
                    "assessment": True,
                    "downloaded": True
                }
                logger.info(f"轮询结束，确保所有状态一致: report_id={report_id}, 所有状态=True")
        except Exception as e:
            logger.error(f"轮询过程中发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            # 清理轮询状态
            if poll_key in self._active_polling:
                del self._active_polling[poll_key]
            logger.info(f"轮询任务结束: poll_key={poll_key}")
    
    def get_emotion_report_list(self, auth_token: str) -> list:
        """
        获取情绪评估报告列表
        
        Args:
            auth_token: 授权令牌
            
        Returns:
            报告列表
        """
        url = "http://qzb.oamicnet.com/app-api/equipment/emotion/list"
        
        # 当前时间戳
        timestamp = int(time.time() * 1000)
        # 签名 - 使用时间戳的MD5
        sign = generate_md5(str(timestamp))
        
        # 请求参数
        query_params = {
            "pageNo": 1,
            "pageSize": 10
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
            logger.info(f"请求情绪评估列表: URL={url}")
            response = requests.post(url, headers=headers, data=final_data)
            response.raise_for_status()
            
            # 解析响应
            encrypted_response = response.json()
            logger.info(f"收到情绪评估列表响应: {encrypted_response}")
            
            # 解密响应
            result = self.decrypt_response(encrypted_response)
            
            # 检查响应状态
            if result.get("code") == 200 and "data" in result and "list" in result.get("data", {}):
                report_list = result["data"]["list"]
                logger.info(f"获取到{len(report_list)}条情绪评估记录")
                return report_list
            else:
                logger.warning(f"情绪评估列表响应格式异常或状态码错误: {result}")
                return []
                
        except Exception as e:
            logger.error(f"获取情绪评估列表失败: {str(e)}")
            return []
    
    def download_emotion_report(self, auth_token: str, report_id: int, save_dir: str) -> Optional[str]:
        """
        下载情绪评估报告
        
        Args:
            auth_token: 授权令牌
            report_id: 报告ID
            save_dir: 保存目录
            
        Returns:
            报告保存路径，下载失败则返回None
        """
        try:
            # 确保保存目录存在
            os.makedirs(save_dir, exist_ok=True)
            
            # 确保report_id是字符串类型
            str_report_id = str(report_id) if report_id is not None else None
            logger.info(f"下载情绪评估报告，初始report_id: {report_id}, 转换为字符串: {str_report_id}")
            
            # 获取最新报告列表
            report_list = self.get_emotion_report_list(auth_token)
            
            # 检查是否有报告
            if not report_list or len(report_list) == 0:
                logger.error("未获取到任何报告")
                return None
            
            # 尝试找到对应的报告
            target_report = None
            if report_id:
                for report in report_list:
                    report_id_from_list = report.get("id")
                    if report_id_from_list is not None and str(report_id_from_list) == str_report_id:
                        target_report = report
                        logger.info(f"找到指定ID的报告: id={report_id}")
                        break
            
            # 如果没有找到指定ID的报告，找最新的状态为1的报告
            if not target_report:
                for report in report_list:
                    if report.get("status") == 1:
                        target_report = report
                        logger.info(f"找到最新完成的报告: id={report.get('id')}")
                        break
            
            if not target_report:
                logger.error("未找到状态为完成的报告")
                return None
            
            # 使用找到的报告
            found_report_id = target_report.get("id")
            found_report_id_str = str(found_report_id) if found_report_id is not None else None
            report_url = target_report.get("url")
            
            if not report_url:
                logger.error(f"报告URL为空: id={found_report_id}")
                return None
            
            # 使用报告URL直接下载
            logger.info(f"使用URL下载报告: URL={report_url}")
            headers = {
                "Authorization": f"Bearer {auth_token}"
            }
            response = requests.get(report_url, headers=headers)
            response.raise_for_status()
            
            # 检查内容类型
            content_type = response.headers.get("Content-Type", "")
            
            # 判断是否为PDF文件
            if "application/pdf" in content_type or response.content.startswith(b"%PDF"):
                # 保存PDF文件
                timestamp_str = time.strftime("%Y%m%d_%H%M%S")
                file_name = f"assessment_{timestamp_str}.pdf"
                file_path = os.path.join(save_dir, file_name)
                
                with open(file_path, "wb") as f:
                    f.write(response.content)
                
                logger.info(f"情绪评估报告已保存: {file_path}")
                
                # 下载成功后，调用API删除远程报告
                delete_url = "http://qzb.oamicnet.com/app-api/equipment/emotion/download/back"
                
                # 当前时间戳
                timestamp = int(time.time() * 1000)
                # 签名 - 使用时间戳的MD5
                sign = generate_md5(str(timestamp))
                
                # 请求参数
                query_params = {
                    "id": found_report_id
                }
                
                # 加密请求参数
                json_query = json.dumps(query_params)
                encrypted_content = encrypt_des(json_query)
                
                # 构建最终请求数据
                final_data = f"sign={sign}&content={encrypted_content}&timestamp={timestamp}"
                
                # 发送删除请求
                try:
                    logger.info(f"请求删除远程报告: URL={delete_url}, id={found_report_id}")
                    delete_headers = {
                        "Authorization": f"Bearer {auth_token}",
                        "Content-Type": "application/json"
                    }
                    delete_response = requests.post(delete_url, headers=delete_headers, data=final_data)
                    
                    if delete_response.status_code == 200:
                        logger.info(f"远程报告删除成功: id={found_report_id}")
                        
                        # 更新状态
                        if found_report_id_str:
                            self.report_status[found_report_id_str] = {
                                "upload_callback": True,
                                "assessment": 2,  # 2表示报告已生成
                                "downloaded": True
                            }
                            logger.info(f"已更新报告状态: report_id={found_report_id_str}, assessment_status=2, 报告下载状态=True")
                    else:
                        logger.warning(f"远程报告删除失败: status_code={delete_response.status_code}")
                        
                except Exception as delete_error:
                    logger.error(f"删除远程报告出错: {str(delete_error)}")
                    import traceback
                    traceback.print_exc()
                
                return file_path
            else:
                # 尝试解析非PDF响应
                try:
                    result = response.json()
                    logger.warning(f"下载情绪评估报告返回非PDF数据: {result}")
                    
                    # 检查是否有错误信息
                    error_msg = (
                        result.get("message") or 
                        result.get("msg") or 
                        result.get("error") or
                        "下载报告失败: 返回非PDF数据"
                    )
                    logger.error(error_msg)
                except:
                    logger.warning(f"下载情绪评估报告返回未知格式数据")
                
                return None
                
        except Exception as e:
            logger.error(f"下载情绪评估报告失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_latest_assessment_status(self, report_id=None):
        """
        获取最新评估状态
        
        Args:
            report_id: 报告ID
            
        Returns:
            包含状态信息的字典
        """
        if not report_id:
            return {
                "success": False,
                "message": "未提供报告ID",
                "upload_callback_status": False,
                "assessment_status": False,
                "report_downloaded": False
            }
        
        # 从状态字典中获取状态
        if report_id in self.report_status:
            status = self.report_status[report_id]
            upload_callback_status = status.get("upload_callback", False)
            assessment_status = status.get("assessment", False)
            report_downloaded = status.get("downloaded", False)
            
            # 当获取最新报告状态时，如果评估状态为2，自动将报告下载状态设为True
            if assessment_status == 2:
                self.report_status[report_id]["downloaded"] = True
                report_downloaded = True
                logger.info(f"检测到评估状态为2，自动更新报告下载状态为True: report_id={report_id}")
        else:
            # 如果没有找到对应状态，初始化一个新状态
            self.report_status[report_id] = {
                "upload_callback": True,  # 默认假设上传回调已完成
                "assessment": False,
                "downloaded": False
            }
            upload_callback_status = True
            assessment_status = False
            report_downloaded = False
            logger.info(f"为report_id={report_id}创建新状态")
        
        return {
            "success": True,
            "report_id": report_id,
            "upload_callback_status": upload_callback_status,
            "assessment_status": assessment_status,
            "report_downloaded": report_downloaded
        }
        
    def check_and_download_report(self, auth_token: str):
        """
        检查最新报告并下载
        
        此方法用于video_status端点，不需要传入report_id
        会自动获取报告列表，找到第一条数据作为report_id
        如果报告下载成功，应当由调用方调用情绪评估文档分析接口
        
        Args:
            auth_token: 授权令牌
            
        Returns:
            包含状态信息的字典，如果下载了报告，会包含report_path字段
        """
        try:
            # 获取报告列表
            report_list = self.get_emotion_report_list(auth_token)
            
            if not report_list or len(report_list) == 0:
                logger.warning("未获取到报告列表")
                return {
                    "success": False,
                    "message": "未获取到报告列表",
                    "data": None
                }
            
            # 获取第一条报告数据
            latest_report = report_list[0]
            report_id = latest_report.get("id")
            status = latest_report.get("status")
            
            if not report_id:
                logger.warning("报告ID为空")
                return {
                    "success": False,
                    "message": "报告ID为空",
                    "data": None
                }
            
            # 将report_id转为字符串
            str_report_id = str(report_id)
            
            # 获取当前状态
            if str_report_id in self.report_status:
                current_status = self.report_status[str_report_id]
            else:
                # 初始化状态
                current_status = {
                    "upload_callback": True,
                    "assessment": False if status != 1 else 2,
                    "downloaded": False
                }
                self.report_status[str_report_id] = current_status
            
            # 报告下载路径
            report_path = None
            # 标记该次调用是否下载了新报告
            downloaded_now = False
            
            # 如果报告状态为1(已完成)且未下载，则下载报告
            if status == 1 and not current_status.get("downloaded", False):
                logger.info(f"发现已生成的报告: id={str_report_id}")
                
                # 设置保存目录
                save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "save", "assessments")
                os.makedirs(save_dir, exist_ok=True)
                
                # 下载报告
                report_path = self.download_emotion_report(auth_token, report_id, save_dir)
                
                if report_path:
                    logger.info(f"报告下载成功: {report_path}")
                    
                    # 标记为本次下载
                    downloaded_now = True
                    
                    # 更新状态 - 只设置状态，不进行额外操作
                    self.report_status[str_report_id] = {
                        "upload_callback": True,
                        "assessment": True,  # 使用布尔值表示报告已生成
                        "downloaded": True
                    }
                    
                    logger.info(f"报告下载成功，已完成评估流程: {report_path}")
                    # 注意：报告下载成功后，应由调用方决定是否调用情绪评估文档分析接口
            
            # 返回最新状态
            result = {
                "success": True,
                "report_id": str_report_id,
                "status": status,
                "upload_callback_status": self.report_status[str_report_id].get("upload_callback", False),
                "assessment_status": self.report_status[str_report_id].get("assessment", False),
                "report_downloaded": self.report_status[str_report_id].get("downloaded", False),
                "downloaded_now": downloaded_now  # 添加下载标记
            }
            
            # 如果下载了报告，添加报告路径
            if report_path:
                result["report_path"] = report_path
            
            return result
            
        except Exception as e:
            logger.error(f"检查报告状态出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "message": f"检查报告状态出错: {str(e)}",
                "data": None
            } 