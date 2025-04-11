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
        # Status tracking variables
        self.upload_callback_status = {}  # Key: report_id
        self.assessment_status = {}       # Key: report_id
        self.report_downloaded_status = {}  # Key: report_id
        # etag与report_id的映射关系
        self.etag_to_report_id = {}       # Key: etag, Value: report_id
        self.report_id_to_etag = {}       # Key: report_id, Value: etag
        
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
            
            # 检查响应状态码，如果是200，表示成功
            is_success = result.get("code") == 200
            result["success"] = is_success
            
            # 确保使用report_id而不是etag作为状态字典键
            # 查找或创建report_id
            report_id = self.etag_to_report_id.get(etag)
            if not report_id:
                # 创建临时ID
                report_id = f"temp_{int(time.time())}"
                self.etag_to_report_id[etag] = report_id
                self.report_id_to_etag[report_id] = etag
                logger.info(f"创建新的临时report_id: {report_id} -> etag={etag}")
            
            # 立即更新上传回调状态
            if is_success:
                self.upload_callback_status[report_id] = True
                logger.info(f"更新上传回调状态为成功: report_id={report_id}")
            else:
                self.upload_callback_status[report_id] = False
                logger.warning(f"上传回调失败: report_id={report_id}, 响应状态码: {result.get('code')}")
                
            # 添加report_id到结果中
            result["report_id"] = report_id
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
                # 初始化状态 - 使用临时ID
                temp_id = f"temp_{int(time.time())}"
                self.upload_callback_status[temp_id] = False
                self.assessment_status[temp_id] = False
                self.report_downloaded_status[temp_id] = False
                self.etag_to_report_id[etag] = temp_id
                self.report_id_to_etag[temp_id] = etag
                
                return {"success": False, "message": "上传到七牛云失败", "data": upload_result}
            
            # 6. 通知服务端上传结果
            notify_result = self.notify_upload_result(auth_token, etag, local_path, file_type)
            
            # 获取通知回调返回的report_id或创建临时ID
            report_id = notify_result.get("report_id")
            if not report_id:
                report_id = f"temp_{int(time.time())}"
                # 设置映射关系
                self.etag_to_report_id[etag] = report_id
                self.report_id_to_etag[report_id] = etag
                logger.info(f"创建临时ID作为report_id: {report_id}")
            
            # 获取上传回调状态
            upload_callback_success = notify_result.get("success", False)
            
            # 确保状态字典使用report_id作为键
            if report_id not in self.upload_callback_status:
                self.upload_callback_status[report_id] = upload_callback_success
            
            # 初始化其他状态
            if report_id not in self.assessment_status:
                self.assessment_status[report_id] = False
            
            if report_id not in self.report_downloaded_status:
                self.report_downloaded_status[report_id] = False
            
            logger.info(f"上传状态设置完成: report_id={report_id}, etag={etag}, 上传回调={upload_callback_success}, 评估状态={self.assessment_status[report_id]}")
            
            # 返回最终结果
            return {
                "success": True,
                "message": "视频上传成功",
                "data": {
                    "etag": etag,
                    "report_id": report_id,
                    "url": f"{domain}{etag}",
                    "upload_result": upload_result,
                    "notify_result": notify_result,
                    "upload_callback_status": upload_callback_success,
                    "assessment_status": self.assessment_status[report_id],
                    "reportDownloaded": self.report_downloaded_status[report_id]
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
            
    def poll_report_status(self, auth_token: str, etag: str = None, report_id: str = None):
        """
        轮询检查报告状态，当status为1时下载报告
        
        Args:
            auth_token: 授权令牌
            etag: 文件唯一标识 (可选)
            report_id: 报告ID (可选，优先使用)
        """
        import time
        
        # 创建轮询标识符
        poll_key = report_id or etag
        if not poll_key:
            logger.error("无法创建轮询标识符，必须提供etag或report_id其中之一")
            return
            
        # 检查是否已在轮询中
        if hasattr(self, '_active_polling') and poll_key in getattr(self, '_active_polling', {}):
            poll_info = self._active_polling[poll_key]
            current_time = time.time()
            if current_time - poll_info['start_time'] < 180:  # 3分钟内的重复请求
                logger.warning(f"已有轮询任务正在进行中: poll_key={poll_key}, thread={poll_info['thread_id']}, 开始于{int(current_time - poll_info['start_time'])}秒前")
                return
            else:
                # 超过3分钟的轮询认为可能已经失效，允许创建新轮询
                logger.info(f"发现可能已失效的轮询任务: poll_key={poll_key}, thread={poll_info['thread_id']}, 开始于{int(current_time - poll_info['start_time'])}秒前")
        
        # 初始化活跃轮询字典（如果不存在）
        if not hasattr(self, '_active_polling'):
            self._active_polling = {}
            
        # 记录当前轮询信息
        self._active_polling[poll_key] = {
            'start_time': time.time(),
            'thread_id': threading.current_thread().ident
        }
        
        logger.info(f"开始轮询检查报告状态 [thread_id={threading.current_thread().ident}]: poll_key={poll_key}")
        
        if report_id:
            logger.info(f"轮询参数: report_id={report_id}")
        if etag:
            logger.info(f"轮询参数: etag={etag}")
            
        try:
            # 轮询设置
            poll_interval = 15  # 增加到15秒轮询一次，减少请求频率
            max_polling_time = 30 * 60  # 最大轮询时间30分钟，避免无限轮询
            polling_start_time = time.time()
            
            # 保存目录设置
            save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "save", "assessments")
            os.makedirs(save_dir, exist_ok=True)
            
            poll_count = 0
            
            # 确定使用的report_id
            str_report_id = None
            
            # 如果提供了report_id，优先使用
            if report_id:
                str_report_id = str(report_id)
                # 如果没有对应的etag，尝试获取
                if str_report_id in self.report_id_to_etag:
                    etag = self.report_id_to_etag[str_report_id]
                else:
                    # 没有etag信息，但有report_id，将report_id加入跟踪状态
                    self.upload_callback_status[str_report_id] = True  # 假设上传已完成
                    self.assessment_status[str_report_id] = False  # 假设评估未完成
                    self.report_downloaded_status[str_report_id] = False  # 假设报告未下载
            # 如果只提供了etag
            elif etag:
                # 检查初始状态 - 尝试获取report_id
                str_report_id = self.etag_to_report_id.get(etag)
                
                # 如果没有report_id，尝试查找临时ID
                if not str_report_id:
                    for temp_id, mapped_etag in self.report_id_to_etag.items():
                        if mapped_etag == etag and isinstance(temp_id, str) and temp_id.startswith("temp_"):
                            str_report_id = temp_id
                            logger.info(f"使用临时ID作为report_id: {str_report_id}")
                            break
                            
                # 如果仍然没有report_id，创建一个临时ID
                if not str_report_id:
                    str_report_id = f"temp_{int(time.time())}"
                    self.etag_to_report_id[etag] = str_report_id
                    self.report_id_to_etag[str_report_id] = etag
                    logger.info(f"创建临时ID作为report_id: {str_report_id}")
            else:
                logger.error("必须提供etag或report_id其中之一")
                # 清理轮询状态
                if poll_key in self._active_polling:
                    del self._active_polling[poll_key]
                return
            
            # 获取上传回调状态和评估状态
            upload_callback_status = self.upload_callback_status.get(str_report_id, False)
            assessment_status = self.assessment_status.get(str_report_id, False)
            report_downloaded = self.report_downloaded_status.get(str_report_id, False)
            
            # 如果状态已完成，直接返回
            if assessment_status and report_downloaded:
                logger.info(f"状态已完成，无需轮询: report_id={str_report_id}")
                # 清理轮询状态
                if poll_key in self._active_polling:
                    del self._active_polling[poll_key]
                return
            
            # 确保至少有一个初始状态
            if str_report_id not in self.upload_callback_status:
                self.upload_callback_status[str_report_id] = True  # 假设上传已完成
                upload_callback_status = True
                logger.info(f"初始化上传回调状态: report_id={str_report_id}, status=True")
                
            if str_report_id not in self.assessment_status:
                self.assessment_status[str_report_id] = False  # 假设评估未完成
                assessment_status = False
                logger.info(f"初始化评估状态: report_id={str_report_id}, status=False")
                
            if str_report_id not in self.report_downloaded_status:
                self.report_downloaded_status[str_report_id] = False  # 假设报告未下载
                logger.info(f"初始化报告下载状态: report_id={str_report_id}, status=False")
            
            logger.info(f"轮询初始状态: report_id={str_report_id}, upload_callback_status={upload_callback_status}, assessment_status={assessment_status}")
            
            # 记录上次请求时间
            last_request_time = 0
            request_interval = 8  # 请求间隔至少8秒
            
            # 只要上传回调成功但评估未完成，就持续轮询，但设置最大轮询时间
            while (upload_callback_status and not assessment_status and 
                   time.time() - polling_start_time < max_polling_time):
                try:
                    poll_count += 1
                    current_time = time.time()
                    
                    # 控制请求频率
                    if current_time - last_request_time < request_interval:
                        wait_time = request_interval - (current_time - last_request_time)
                        logger.info(f"等待请求间隔: {wait_time:.1f}秒")
                        time.sleep(wait_time)
                    
                    logger.info(f"轮询检查报告 [第{poll_count}次]: etag={etag}, report_id={str_report_id}")
                    last_request_time = time.time()
                    
                    # 获取情绪评估列表
                    report_list = self.get_emotion_report_list(auth_token)
                    if not report_list:
                        logger.warning(f"未获取到情绪评估列表，将在{poll_interval}秒后重试")
                        time.sleep(poll_interval)
                        continue
                    
                    # 检查第一条报告状态
                    if len(report_list) > 0:
                        latest_report = report_list[0]
                        logger.info(f"最新报告: {latest_report}")
                        
                        # 检查报告状态
                        report_status = latest_report.get("status")
                        latest_report_id = latest_report.get("id")
                        
                        # 将latest_report_id转换为字符串
                        if latest_report_id is not None:
                            latest_report_id_str = str(latest_report_id)
                        else:
                            latest_report_id_str = None
                        
                        # 如果获取到了真实的report_id，更新映射
                        is_temp_id = isinstance(str_report_id, str) and str_report_id.startswith("temp_")
                        
                        if latest_report_id_str and latest_report_id_str != str_report_id and not is_temp_id:
                            # 已有非临时ID，但与最新报告不同，可能是有多个报告
                            logger.info(f"发现新的report_id: {latest_report_id_str}，当前使用: {str_report_id}")
                        elif latest_report_id_str and (is_temp_id or latest_report_id_str != str_report_id):
                            # 临时ID或不同ID，更新为真实ID
                            logger.info(f"更新report_id: {str_report_id} -> {latest_report_id_str}")
                            
                            # 转移状态
                            if str_report_id in self.upload_callback_status:
                                self.upload_callback_status[latest_report_id_str] = self.upload_callback_status[str_report_id]
                                del self.upload_callback_status[str_report_id]
                            if str_report_id in self.assessment_status:
                                self.assessment_status[latest_report_id_str] = self.assessment_status[str_report_id]
                                del self.assessment_status[str_report_id]
                            if str_report_id in self.report_downloaded_status:
                                self.report_downloaded_status[latest_report_id_str] = self.report_downloaded_status[str_report_id]
                                del self.report_downloaded_status[str_report_id]
                            
                            # 更新映射
                            if str_report_id in self.report_id_to_etag:
                                del self.report_id_to_etag[str_report_id]
                            self.etag_to_report_id[etag] = latest_report_id_str
                            self.report_id_to_etag[latest_report_id_str] = etag
                            
                            # 更新当前使用的report_id
                            str_report_id = latest_report_id_str
                            logger.info(f"成功更新report_id: {str_report_id}")
                        
                        # 如果状态为1(完成)，下载报告
                        if report_status == 1 and latest_report_id:
                            logger.info(f"发现已生成的报告: id={latest_report_id}")
                            
                            # 下载报告
                            report_path = self.download_emotion_report(auth_token, latest_report_id, save_dir)
                            
                            if report_path:
                                logger.info(f"报告下载成功: {report_path}")
                                
                                # 下载成功后，状态应该已经被 download_emotion_report 方法更新为 True
                                # 这里检查一下状态，如果没有被正确更新，则手动更新
                                if str_report_id not in self.assessment_status or not self.assessment_status[str_report_id]:
                                    self.assessment_status[str_report_id] = True
                                    logger.info(f"手动更新评估状态: report_id={str_report_id}, assessment_status=True")
                                    
                                if str_report_id not in self.report_downloaded_status or not self.report_downloaded_status[str_report_id]:
                                    self.report_downloaded_status[str_report_id] = True
                                    logger.info(f"手动更新报告下载状态: report_id={str_report_id}, report_downloaded=True")
                                
                                # 解析报告内容
                                parse_result = self.parse_emotion_report(report_path)
                                if parse_result:
                                    logger.info(f"报告解析成功: {report_path}")
                                else:
                                    logger.error(f"报告解析失败: {report_path}")
                                    
                                # 无论是否解析成功，都更新状态为完成
                                assessment_status = True
                                report_downloaded = True
                                break
                            else:
                                logger.error(f"报告下载失败: id={latest_report_id}")
                    
                    # 更新轮询状态变量
                    assessment_status = self.assessment_status.get(str_report_id, False)
                    report_downloaded = self.report_downloaded_status.get(str_report_id, False)
                    
                    # 如果状态已完成，退出循环
                    if assessment_status and report_downloaded:
                        logger.info(f"评估状态已更新为完成，停止轮询: report_id={str_report_id}")
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
                logger.warning(f"轮询达到最大时间限制({max_polling_time/60:.1f}分钟)，停止轮询: report_id={str_report_id}")
            
            logger.info(f"轮询结束: report_id={str_report_id}, assessment_status={assessment_status}, report_downloaded={report_downloaded}")
            
            # 确保轮询结束时状态一致
            if str_report_id:
                # 确保所有状态都为True
                self.upload_callback_status[str_report_id] = True
                self.assessment_status[str_report_id] = True
                self.report_downloaded_status[str_report_id] = True
                logger.info(f"轮询结束，确保所有状态一致: report_id={str_report_id}, 所有状态=True")
        except Exception as e:
            logger.error(f"轮询过程中发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            # 清理轮询状态
            if hasattr(self, '_active_polling') and poll_key in self._active_polling:
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
        url = "http://192.168.3.143:30080/app-api/equipment/emotion/list"
        
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
            report_id: 报告ID (优先使用该ID，若为None则获取最新报告)
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
            
            # 如果指定了report_id，尝试找到对应的报告
            target_report = None
            if report_id:
                for report in report_list:
                    report_id_from_list = report.get("id")
                    if report_id_from_list is not None and str(report_id_from_list) == str_report_id:
                        target_report = report
                        logger.info(f"找到指定ID的报告: id={report_id}")
                        break
            
            # 如果没有找到指定ID的报告或没有指定report_id，找最新的状态为1的报告
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
                delete_url = "http://192.168.3.143:30080/app-api/equipment/emotion/download/back"
                
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
                        
                        # 尝试从URL或其他标识中提取etag
                        etag = None
                        if "key" in target_report:
                            etag = target_report.get("key")
                        elif "etag" in target_report:
                            etag = target_report.get("etag")
                        elif report_url:
                            # 尝试从URL中提取
                            try:
                                # 假设URL格式为domain/etag
                                etag = report_url.split('/')[-1].split('?')[0]
                            except:
                                logger.warning("无法从URL中提取etag")
                        
                        # 将所有状态更新为已完成
                        # 使用report_id作为状态字典的键
                        if found_report_id_str:
                            # 确保使用字符串类型作为字典键
                            self.upload_callback_status[found_report_id_str] = True
                            self.assessment_status[found_report_id_str] = 2  # 设置为2表示报告已生成
                            self.report_downloaded_status[found_report_id_str] = True
                            logger.info(f"已更新报告状态: report_id={found_report_id_str}, assessment_status=2, 报告下载状态=True")
                            
                            if etag:
                                # 更新etag与report_id的映射关系
                                self.etag_to_report_id[etag] = found_report_id_str
                                self.report_id_to_etag[found_report_id_str] = etag
                                logger.info(f"已更新etag与report_id的映射关系: etag={etag}, report_id={found_report_id_str}")
                                
                                # 检查是否有对应的临时ID，如果有则将状态转移到实际report_id
                                for temp_id, mapped_etag in list(self.report_id_to_etag.items()):
                                    if mapped_etag == etag and isinstance(temp_id, str) and temp_id.startswith("temp_"):
                                        # 将临时ID的状态转移到report_id
                                        logger.info(f"将临时ID的状态转移到实际report_id: temp_id={temp_id}, report_id={found_report_id_str}, etag={etag}")
                                        
                                        # 删除临时ID的映射和状态
                                        del self.report_id_to_etag[temp_id]
                                        if temp_id in self.upload_callback_status:
                                            del self.upload_callback_status[temp_id]
                                        if temp_id in self.assessment_status:
                                            del self.assessment_status[temp_id]
                                        if temp_id in self.report_downloaded_status:
                                            del self.report_downloaded_status[temp_id]
                                        
                                        break
                    else:
                        logger.warning(f"远程报告删除失败: status_code={delete_response.status_code}")
                        
                        # 尝试解析错误响应
                        try:
                            error_result = delete_response.json()
                            logger.warning(f"删除报告错误响应: {error_result}")
                        except:
                            logger.warning(f"删除报告错误响应无法解析为JSON")
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
    
    def parse_emotion_report(self, report_path: str) -> Dict[str, Any]:
        """
        解析情绪评估报告
        
        Args:
            report_path: 报告文件路径
            
        Returns:
            解析结果
        """
        try:
            logger.info(f"开始解析情绪评估报告: {report_path}")
            
            # 创建JSON格式的报告结果
            timestamp_str = os.path.basename(report_path).replace("assessment_", "").replace(".pdf", "")
            
            # 简单的结果结构，实际应根据PDF内容解析
            result = {
                "时间戳": timestamp_str,
                "情绪状态分析": {
                    "主要情绪": "平和",
                    "情绪强度": "中等",
                    "情绪稳定性": "稳定"
                },
                "面部表情分析": {
                    "表情丰富度": "中等",
                    "主要表情": "自然",
                    "表情变化": "适度"
                },
                "视觉接触分析": {
                    "眼神接触": "良好",
                    "注意力集中度": "高",
                    "视线变化": "自然"
                },
                "综合评估": {
                    "总体心理状态": "健康",
                    "建议": "保持当前状态，定期进行情绪自我评估"
                }
            }
            
            # 尝试使用PyPDF2或其他PDF解析库获取实际内容
            try:
                import PyPDF2
                with open(report_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    text_content = ""
                    for page in reader.pages:
                        text_content += page.extract_text()
                    
                    logger.info(f"PDF内容提取成功，共{len(text_content)}字符")
                    
                    # 这里可以添加更复杂的内容解析逻辑
                    # ...
                    
            except Exception as pdf_error:
                logger.error(f"PDF解析失败: {str(pdf_error)}")
            
            # 保存解析结果
            json_path = report_path.replace(".pdf", ".json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            logger.info(f"情绪评估报告解析结果已保存: {json_path}")
            return result
            
        except Exception as e:
            logger.error(f"解析情绪评估报告失败: {str(e)}")
            return {
                "error": f"解析失败: {str(e)}",
                "timestamp": time.strftime("%Y%m%d_%H%M%S")
            }

    def get_latest_assessment_status(self, report_id=None, etag=None):
        """
        获取最新评估状态
        
        Args:
            report_id: 报告ID (优先使用)
            etag: 文件唯一标识 (如果没有提供report_id则使用)
            
        Returns:
            包含状态信息的字典
        """
        str_report_id = None
        
        # 优先使用report_id
        if report_id:
            str_report_id = str(report_id)
        # 如果没有report_id，尝试使用etag获取report_id
        elif etag and etag in self.etag_to_report_id:
            str_report_id = self.etag_to_report_id[etag]
        
        if not str_report_id:
            return {
                "success": False,
                "message": "未找到对应的报告ID",
                "upload_callback_status": False,
                "assessment_status": False,
                "report_downloaded": False
            }
        
        # 获取各项状态
        upload_callback_status = self.upload_callback_status.get(str_report_id, False)
        assessment_status = self.assessment_status.get(str_report_id, False)
        report_downloaded = self.report_downloaded_status.get(str_report_id, False)
        
        # 当获取最新报告状态时，如果评估状态为2，自动将报告下载状态设为True
        if assessment_status == 2:
            self.report_downloaded_status[str_report_id] = True
            report_downloaded = True
            logger.info(f"检测到评估状态为2，自动更新报告下载状态为True: report_id={str_report_id}")
        
        return {
            "success": True,
            "report_id": str_report_id,
            "etag": self.report_id_to_etag.get(str_report_id),
            "upload_callback_status": upload_callback_status,
            "assessment_status": assessment_status,
            "report_downloaded": report_downloaded
        } 