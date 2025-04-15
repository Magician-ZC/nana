import os
from OpenSSL import crypto
import socket

def get_local_ip():
    # 获取本地IP地址
    try:
        # 通过创建一个UDP连接来获取本机IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        # 如果无法获取，返回默认IP
        return "192.168.3.51"

def generate_self_signed_cert(cert_file, key_file):
    # 创建自签名证书
    # 创建key pair
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 2048)

    # 创建自签名证书
    cert = crypto.X509()
    cert.get_subject().C = "CN"
    cert.get_subject().ST = "Beijing"
    cert.get_subject().L = "Beijing"
    cert.get_subject().O = "Nana AI"
    cert.get_subject().OU = "Development"
    cert.get_subject().CN = "localhost"
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(365*24*60*60)  # 1年有效期
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    
    # 添加证书扩展 - 支持多个域名和IP地址
    local_ip = get_local_ip()
    sans = [
        f"DNS:localhost",
        f"DNS:127.0.0.1",
        f"IP:127.0.0.1", 
        f"IP:{local_ip}"
    ]
    
    # 打印IP地址提示
    print(f"证书将包含以下IP地址: localhost, 127.0.0.1, {local_ip}")
    
    # 特别添加前端访问的IP
    if local_ip != "192.168.3.51":
        sans.append(f"IP:192.168.3.51")
        print(f"添加额外IP地址: 192.168.3.51")
    
    # 添加SAN扩展
    san_extension = crypto.X509Extension(
        b"subjectAltName", 
        False, 
        ", ".join(sans).encode()
    )
    cert.add_extensions([san_extension])
    
    # 签名证书
    cert.sign(k, 'sha256')

    # 保存证书和私钥
    if not os.path.exists(os.path.dirname(cert_file)):
        os.makedirs(os.path.dirname(cert_file))
    
    with open(cert_file, "wb") as cf:
        cf.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    
    with open(key_file, "wb") as kf:
        kf.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))
    
    print(f"证书已生成:\n证书文件: {cert_file}\n私钥文件: {key_file}")

if __name__ == "__main__":
    ssl_dir = "ssl"
    if not os.path.exists(ssl_dir):
        os.makedirs(ssl_dir)
    
    cert_file = os.path.join(ssl_dir, "server.crt")
    key_file = os.path.join(ssl_dir, "server.key")
    
    generate_self_signed_cert(cert_file, key_file) 