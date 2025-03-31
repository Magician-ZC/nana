from OpenSSL import crypto
import socket

def generate_self_signed_cert(cert_file, key_file):
    # 创建密钥对
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 2048)
    
    # 创建自签名证书
    cert = crypto.X509()
    cert.get_subject().C = "CN"
    cert.get_subject().ST = "State"
    cert.get_subject().L = "City"
    cert.get_subject().O = "Organization"
    cert.get_subject().OU = "Organizational Unit"
    cert.get_subject().CN = socket.gethostname()
    
    # 添加备用名称
    alt_names = [
        f"DNS:localhost",
        f"DNS:{socket.gethostname()}",
        f"DNS:192.168.3.51"  # 添加你的内网IP
    ]
    cert.add_extensions([
        crypto.X509Extension(b"subjectAltName", False, ", ".join(alt_names).encode())
    ])
    
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(10*365*24*60*60)  # 10年有效期
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(k, 'sha256')
    
    # 写入文件
    with open(cert_file, "wb") as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    
    with open(key_file, "wb") as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))
    
    print(f"已生成自签名证书: {cert_file} 和私钥: {key_file}")

if __name__ == "__main__":
    generate_self_signed_cert("server.crt", "server.key") 