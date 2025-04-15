import requests
import os
import sys
import argparse
import json
import time
from hashlib import md5
import binascii
from Crypto.Cipher import DES, AES
from Crypto.Util.Padding import pad, unpad
import base64

# 加密相关常量
DES_KEY = "12345678"
DES_IV = "12345678"
AES_KEY = "1234567890123456"
AES_IV = "1234567890123456"

def generate_md5(data):
    return md5(data.encode()).hexdigest()

def encrypt_des(data, key, iv):
    """DES加密数据"""
    if isinstance(data, str):
        data = data.encode('utf-8')
    if isinstance(key, str):
        key = key.encode('utf-8')
    if isinstance(iv, str):
        iv = iv.encode('utf-8')
    
    # 使用PKCS7填充
    padded_data = pad(data, DES.block_size)
    cipher = DES.new(key, DES.MODE_CBC, iv)
    encrypted = cipher.encrypt(padded_data)
    # 转为base64编码的字符串
    return base64.b64encode(encrypted).decode('utf-8')

def decrypt_des(encrypted, key, iv):
    """DES解密数据"""
    if isinstance(encrypted, str):
        encrypted = base64.b64decode(encrypted)
    if isinstance(key, str):
        key = key.encode('utf-8')
    if isinstance(iv, str):
        iv = iv.encode('utf-8')
    
    cipher = DES.new(key, DES.MODE_CBC, iv)
    decrypted = cipher.decrypt(encrypted)
    unpadded = unpad(decrypted, DES.block_size)
    return unpadded.decode('utf-8')

def encrypt_aes(data, key, iv):
    """AES加密数据"""
    if isinstance(data, str):
        data = data.encode('utf-8')
    if isinstance(key, str):
        key = key.encode('utf-8')
    if isinstance(iv, str):
        iv = iv.encode('utf-8')
    
    # 使用PKCS7填充
    padded_data = pad(data, AES.block_size)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(padded_data)
    # 转为base64编码的字符串
    return base64.b64encode(encrypted).decode('utf-8')

def decrypt_aes(encrypted, key, iv):
    """AES解密数据"""
    if isinstance(encrypted, str):
        encrypted = base64.b64decode(encrypted)
    if isinstance(key, str):
        key = key.encode('utf-8')
    if isinstance(iv, str):
        iv = iv.encode('utf-8')
    
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(encrypted)
    unpadded = unpad(decrypted, AES.block_size)
    return unpadded.decode('utf-8')

def decrypt_response(response):
    """尝试解密响应数据"""
    try:
        # 检查是否存在加密的data字段
        if "data" in response and isinstance(response["data"], str):
            # 尝试使用DES解密
            try:
                decrypted_data = decrypt_des(response["data"], DES_KEY, DES_IV)
                # 转换为Python对象
                decrypted_json = json.loads(decrypted_data)
                # 返回解密后的结果，保留其他字段
                response["data"] = decrypted_json
                return response
            except Exception as e:
                print(f"DES解密失败，尝试AES解密: {str(e)}")
                
                # 尝试使用AES解密
                try:
                    decrypted_data = decrypt_aes(response["data"], AES_KEY, AES_IV)
                    # 转换为Python对象
                    decrypted_json = json.loads(decrypted_data)
                    # 返回解密后的结果，保留其他字段
                    response["data"] = decrypted_json
                    return response
                except Exception as e:
                    print(f"AES解密也失败: {str(e)}")
        
        # 如果解密失败或没有加密字段，返回原始响应
        return response
    except Exception as e:
        print(f"响应解密过程中发生异常: {str(e)}")
        return response

def get_qiniu_upload_info(auth_token):
    """
    获取七牛云上传配置信息
    """
    url = "http://192.168.3.143:30080/app-api/system/family-and-manage/oss/common/get-oss-upload-info"
    
    # 当前时间戳
    timestamp = int(time.time() * 1000)
    # 签名 - 使用时间戳的MD5
    sign = generate_md5(str(timestamp))
    
    # 请求参数
    query_params = {
        "platform": 1,
        "type": 1,
        "orgId": 0
    }
    
    # 加密请求参数 - 转为JSON字符串后DES加密
    json_query = json.dumps(query_params)
    encrypted_content = encrypt_des(json_query, DES_KEY, DES_IV)
    
    # 构建最终请求参数 - 使用字符串格式
    final_data = f"sign={sign}&content={encrypted_content}&timestamp={timestamp}"
    
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    try:
        print("正在获取七牛云配置信息...")
        print(f"发送请求: URL={url}, data={final_data[:100]}...")
        response = requests.post(url, headers=headers, data=final_data)
        response.raise_for_status()
        result = response.json()
        
        # 输出完整的响应结果，帮助调试
        print(f"API响应结果: {json.dumps(result, ensure_ascii=False)}")
        
        # 尝试解密响应内容
        result = decrypt_response(result)
        
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
                        print(f"七牛云配置获取成功!")
                        print(f"上传类型: {upload_type}")
                        print(f"域名: {domain}")
                        print(f"Token: {upload_token[:20]}..." if upload_token else "Token: 未获取到")
                        
                        return {
                            "success": True,
                            "token": upload_token,
                            "domain": domain,
                            "upload_type": upload_type
                        }
            
            # 如果上面的尝试都失败了，提取错误信息
            error_msg = (
                result.get("message") or 
                result.get("msg") or 
                result.get("error") or
                "未知错误"
            )
            
            print(f"获取七牛云配置失败: {error_msg}")
            return {
                "success": False,
                "message": error_msg
            }
        else:
            print(f"获取七牛云配置失败: 响应格式不正确，预期字典，得到 {type(result)}")
            return {
                "success": False,
                "message": "响应格式不正确"
            }
    except Exception as e:
        print(f"获取七牛云配置异常: {str(e)}")
        return {
            "success": False,
            "message": f"请求异常: {str(e)}"
        }

def test_upload_video(video_path, auth_token, file_type="avi", use_local_api=True):
    """
    测试视频上传到七牛云
    
    Args:
        video_path: 视频文件路径
        auth_token: 授权令牌
        file_type: 文件类型
        use_local_api: 是否使用本地API，False则直接使用七牛SDK上传
    """
    if not os.path.exists(video_path):
        print(f"错误: 文件不存在 - {video_path}")
        return False
    
    if use_local_api:
        # 使用本地API上传
        url = "https://localhost:8666/api/upload-video"
        headers = {
            "Authorization": f"Bearer {auth_token}"
        }
        
        with open(video_path, "rb") as f:
            files = {
                "file": (os.path.basename(video_path), f, f"video/{file_type}")
            }
            
            params = {
                "file_type": file_type
            }
            
            print(f"正在通过本地API上传视频: {video_path}")
            response = requests.post(url, headers=headers, files=files, params=params)
            
            if response.status_code == 200:
                result = response.json()
                print("上传成功!")
                print(f"eTag: {result.get('data', {}).get('etag', '')}")
                print(f"URL: {result.get('data', {}).get('url', '')}")
                return True
            else:
                print(f"上传失败! 状态码: {response.status_code}")
                print(response.text)
                return False
    else:
        # 直接获取七牛配置并使用七牛SDK上传
        # 第1步：获取七牛云配置
        qiniu_info = get_qiniu_upload_info(auth_token)
        if not qiniu_info.get("success", False):
            return False
        
        # 第2步：从QiniuUploader导入需要的功能
        try:
            # 可以选择手动导入或者直接使用QiniuUploader
            from qiniu_uploader import QiniuUploader
            uploader = QiniuUploader()
            
            # 第3步：缓存文件并计算eTag
            with open(video_path, "rb") as f:
                file_data = f.read()
            
            # 保存临时文件
            file_name = os.path.basename(video_path)
            local_path = uploader.save_temp_file(file_data, file_name)
            
            # 计算eTag
            etag = uploader.calculate_file_etag(local_path)
            
            # 第4步：上传文件到七牛云
            upload_result = uploader.upload_to_qiniu(
                local_path=local_path,
                upload_token=qiniu_info.get("token", ""),
                etag=etag,
                domain=qiniu_info.get("domain", "")
            )
            
            if upload_result.get("status") == 1:
                print("直接上传七牛云成功!")
                print(f"eTag: {upload_result.get('etag', '')}")
                print(f"URL: {upload_result.get('remote_path', '')}")
                
                # 第5步：通知服务端上传结果
                notify_result = uploader.notify_upload_result(
                    auth_token=auth_token,
                    etag=etag,
                    file_path=local_path,
                    file_type=file_type
                )
                
                print(f"通知服务端结果: {json.dumps(notify_result, ensure_ascii=False)}")
                return True
            else:
                print(f"直接上传七牛云失败!")
                print(f"错误信息: {upload_result.get('error', '未知错误')}")
                return False
                
        except Exception as e:
            print(f"直接上传七牛云异常: {str(e)}")
            return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="测试视频上传到七牛云")
    parser.add_argument("video_path", help="要上传的视频文件路径")
    parser.add_argument("auth_token", help="认证令牌，示例: 0035f0043dac4be4ba8db607b1c948c5")
    parser.add_argument("--file-type", default="avi", help="文件类型，默认为avi")
    parser.add_argument("--direct", action="store_true", help="直接使用七牛SDK上传，不经过本地API")
    
    args = parser.parse_args()
    
    # 如果只需要测试获取配置
    if args.video_path.lower() == "config":
        qiniu_info = get_qiniu_upload_info(args.auth_token)
        sys.exit(0 if qiniu_info.get("success", False) else 1)
    else:
        # 测试视频上传
        success = test_upload_video(
            args.video_path, 
            args.auth_token, 
            args.file_type,
            not args.direct
        )
        
        sys.exit(0 if success else 1) 