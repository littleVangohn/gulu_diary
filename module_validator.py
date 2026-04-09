import pika
import json
from datetime import datetime
from core.water_recommender import get_recommended_range

# 引入密码本
from cipher_utils import decrypt_data

RABBITMQ_HOST = "localhost"

def callback(ch, method, properties, body):
    raw_msg = body.decode('utf-8').strip('"').strip("'")
    
    # 🌟 核心升级：智能解析模块 (兼容双链路)
    try:
        # 第一步：先尝试直接把它当做明文 JSON 解析（如果是 FastAPI 大门传来的）
        data = json.loads(raw_msg)
        # 如果能运行到这里，说明已经是明文了，不需要解密
    except json.JSONDecodeError:
        # 第二步：如果报错，说明它是乱码，那就执行 AES 解密（针对脚本直连 MQ 的情况）
        try:
            decrypted_str = decrypt_data(raw_msg)
            data = json.loads(decrypted_str)
        except Exception as e:
            print(f"🚨 [安全拦截] 非法密文: {e}")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

    # --- 下面是验证逻辑，完全不变 ---
    cat_id = data.get('cat_id', 'Unknown')
    breed = data.get('cat_info', {}).get('breed', '其他')
    age = data.get('cat_info', {}).get('age', 3)
    actual_ml = float(data.get('actual_ml', 0.0))

    min_ml, max_ml = get_recommended_range(breed, age)
    judgment = "达标"
    if actual_ml < min_ml: judgment = "未达标"
    elif actual_ml > max_ml: judgment = "超标"

    processed_data = {
        "cat_id": cat_id, "breed": breed, "age": age,
        "actual_ml": actual_ml, "min_ml": min_ml, "max_ml": max_ml,
        "judgment": judgment, "timestamp": datetime.now().isoformat()
    }

    ch.basic_publish(
        exchange='validated_exchange',
        routing_key='',
        body=json.dumps(processed_data, ensure_ascii=False)
    )
    # 为了防止 JMeter 压测时日志刷屏太快导致服务器卡顿，建议把下面这行打印注释掉或保留
    # print(f"🧠 [验证完毕] {cat_id} -> {judgment}，已广播。") 
    
    ch.basic_ack(delivery_tag=method.delivery_tag)

connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
channel = connection.channel()

channel.queue_declare(queue='cat_water_queue', durable=True)
channel.exchange_declare(exchange='validated_exchange', exchange_type='fanout')

channel.basic_consume(queue='cat_water_queue', on_message_callback=callback)
print("⏳ Validator 节点已启动，开启双重兼容智能解析...")
channel.start_consuming()