import requests
import json
import sys
import argparse
import hashlib
import time
import binascii
from Crypto.Cipher import DES
from Crypto.Util.Padding import pad

# 加密密钥和IV值
DES_KEY = "wKnqXvKi"  # 8字节DES密钥
DES_IV = "YpNsuo66"   # 8字节DES IV

def generate_md5(text: str) -> str:
    """生成MD5哈希"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def encrypt_des(plain_text: str, key: str = DES_KEY, iv: str = DES_IV) -> str:
    """使用DES CBC模式加密"""
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
        
        print(f"DES加密成功: {plain_text[:20]}... -> {encrypted_hex[:20]}...")
        return encrypted_hex
    except Exception as e:
        print(f"DES加密错误: {str(e)}")
        return ""

def test_api_response(auth_token):
    """
    直接测试API响应格式
    """
    print("======= 测试获取七牛云配置接口 =======")
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
    encrypted_content = encrypt_des(json_query)
    
    # 构建最终请求参数 - 使用字符串格式
    final_data = f"sign={sign}&content={encrypted_content}&timestamp={timestamp}"
    
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    try:
        print(f"发送请求: URL={url}")
        print(f"请求头: {headers}")
        print(f"请求体: {final_data}")
        
        response = requests.post(url, headers=headers, data=final_data)
        print(f"响应状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        try:
            result = response.json()
            print(f"响应体(原始JSON):\n{json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # 检查响应结构
            print("\n======= 响应结构分析 =======")
            print(f"响应类型: {type(result)}")
            
            if isinstance(result, dict):
                # 检查常见的成功标志
                success_keys = ["success", "code", "status", "msg"]
                found_keys = [key for key in success_keys if key in result]
                print(f"找到的状态键: {found_keys}")
                
                for key in found_keys:
                    print(f"- {key}: {result.get(key)}")
                
                # 检查数据结构
                data_keys = ["data", "result"]
                for key in data_keys:
                    if key in result:
                        data = result.get(key)
                        print(f"\n'{key}'字段内容:")
                        print(f"- 类型: {type(data)}")
                        if isinstance(data, dict):
                            print(f"- 键: {list(data.keys())}")
                            # 检查关键值
                            for data_key in ["token", "uploadToken", "domain", "domainUrl", "content"]:
                                if data_key in data:
                                    value = data.get(data_key)
                                    # 如果是token，只显示部分
                                    if "token" in data_key.lower() and isinstance(value, str) and len(value) > 20:
                                        print(f"- {data_key}: {value[:20]}...")
                                    else:
                                        print(f"- {data_key}: {value}")
                
                # 检查整个结构中是否有token和domain
                all_keys = []
                
                def collect_keys(obj, prefix=""):
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            full_key = f"{prefix}.{k}" if prefix else k
                            all_keys.append(full_key)
                            collect_keys(v, full_key)
                    elif isinstance(obj, list) and len(obj) > 0:
                        collect_keys(obj[0], f"{prefix}[0]")
                
                collect_keys(result)
                print(f"\n所有键路径: {all_keys}")
                
                # 查找可能的token和domain
                token_keys = [k for k in all_keys if "token" in k.lower()]
                domain_keys = [k for k in all_keys if "domain" in k.lower()]
                content_keys = [k for k in all_keys if "content" in k.lower()]
                print(f"可能的token键: {token_keys}")
                print(f"可能的domain键: {domain_keys}")
                print(f"可能的content键: {content_keys}")
                
            else:
                print("响应不是字典格式，无法进一步分析")
            
        except json.JSONDecodeError:
            print(f"响应不是有效的JSON: {response.text}")
            
    except Exception as e:
        print(f"请求出错: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="测试API响应格式")
    parser.add_argument("auth_token", help="认证令牌，示例: 0035f0043dac4be4ba8db607b1c948c5")
    
    args = parser.parse_args()
    test_api_response(args.auth_token) 