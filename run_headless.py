import os
import json
import time
import random
import numpy as np
import pika  
from datetime import datetime
from core.water_recommender import get_recommended_range

# 🌟 引入密码本
from cipher_utils import encrypt_data

# === 核心配置区 ===
RABBITMQ_HOST = "121.43.99.176"  
RABBITMQ_USER = "admin"          
RABBITMQ_PASS = "cat_mq_2026"    
MQ_QUEUE_NAME = "cat_water_queue" 
CACHE_FILE = "mq_pending_uploads.json" 

CAT_MODELS = [
    {"id": "a布偶_小白", "breed": "布偶猫", "age": 3},
    {"id": "b暹罗_小黑", "breed": "暹罗猫", "age": 2},
    {"id": "c缅因_大壮", "breed": "缅因猫", "age": 5},
    {"id": "d美短_斑点", "breed": "美国短毛猫", "age": 4}
]

def get_single_reading(cat_dict):
    min_ml, max_ml = get_recommended_range(cat_dict["breed"], cat_dict["age"])
    mu = (min_ml + max_ml) / 2
    sigma = (max_ml - min_ml) / 6
    actual = np.random.normal(mu, sigma)
    if random.random() < 0.1:
        actual = actual * random.choice([0.5, 1.5])
    return {
        "cat_id": cat_dict["id"],
        "cat_info": {"breed": cat_dict["breed"], "age": cat_dict["age"]},
        "actual_ml": round(max(0, actual), 1),
        "timestamp": datetime.now().isoformat()
    }

def send_to_mq(data):
    try:
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
        parameters = pika.ConnectionParameters(
            host=RABBITMQ_HOST, port=5672, credentials=credentials, socket_timeout=5
        )
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        channel.queue_declare(queue=MQ_QUEUE_NAME, durable=True)

        # 🌟 核心修改点：将 JSON 转成字符串，并进行 AES 加密
        json_str = json.dumps(data, ensure_ascii=False)
        encrypted_body = encrypt_data(json_str)
        
        channel.basic_publish(
            exchange='',
            routing_key=MQ_QUEUE_NAME,
            body=encrypted_body,  # 发送的不再是明文，而是加密后的乱码
            properties=pika.BasicProperties(delivery_mode=2) 
        )
        connection.close()
        return True, "密文投递成功"
    except Exception as e:
        return False, str(e)

def upload_logic(data):
    for i in range(3):
        success, info = send_to_mq(data)
        if success:
            print(f"✅ [{data['cat_id']}] {data['actual_ml']}ml -> MQ 状态: {info}")
            return True
        wait = (2 ** i) + random.random()
        print(f"❌ 连接 MQ 失败 ({info})，{wait:.1f}s 后重试...")
        time.sleep(wait)
    save_to_cache(data)
    return False

def save_to_cache(data):
    cache = []
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            try: cache = json.load(f)
            except: cache = []
    cache.append(data)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def process_offline_data():
    if not os.path.exists(CACHE_FILE): return
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        try: items = json.load(f)
        except: items = []
    if not items: return
    still_failed = []
    for item in items:
        success, _ = send_to_mq(item)
        if not success: still_failed.append(item)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(still_failed, f, ensure_ascii=False, indent=2)

# === 主程序 ===
if __name__ == "__main__":
    print("=== 🚀 智能猫咪模拟器 (极限狂暴火力测试) ===")
    process_offline_data()
    target_cat = random.choice(CAT_MODELS)
    print(f"\n🐾 设备已绑定猫咪: {target_cat['id']}")
    
    # 🌟 修改点：一次性连发 100 条，并且去掉 time.sleep！
    for i in range(1, 101):
        # 提示：为了不让终端刷屏太快，我们就不打印进度了
        current_data = get_single_reading(target_cat)
        upload_logic(current_data)
        
    print(f"=== 100 条狂暴火力发送完毕 ===")