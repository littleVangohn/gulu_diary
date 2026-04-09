from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64

# 🔑 必须是 16 位字符串
SECRET_KEY = b'pawsplanet2026mq' 
BLOCK_SIZE = 16

def encrypt_data(plain_text):
    """加密：JSON字符串 -> Base64密文"""
    cipher = AES.new(SECRET_KEY, AES.MODE_CBC)
    iv = cipher.iv # 生成初始向量
    ct_bytes = cipher.encrypt(pad(plain_text.encode('utf-8'), BLOCK_SIZE))
    # 将 IV 和 密文拼接后转为 Base64 方便传输
    return base64.b64encode(iv + ct_bytes).decode('utf-8')


def decrypt_data(cipher_text):
    """解密：增加对非 ASCII 字符的容错处理"""
    try:
        # 如果输入是字符串，先尝试编码为纯 ASCII 字节流
        # 如果包含中文导致报错，先忽略掉非 ASCII 字符
        if isinstance(cipher_text, str):
            cipher_text = cipher_text.encode('ascii', 'ignore')
            
        raw_data = base64.b64decode(cipher_text)
        iv = raw_data[:16]
        ct = raw_data[16:]
        cipher = AES.new(SECRET_KEY, AES.MODE_CBC, iv)
        pt = unpad(cipher.decrypt(ct), 16)
        return pt.decode('utf-8')
    except Exception as e:
        raise ValueError(f"Base64解码或解密失败: {e}")