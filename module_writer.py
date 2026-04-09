import pika
import json
import time
from pymongo import MongoClient
from datetime import datetime

RABBITMQ_HOST = "localhost"
MONGO_URI = "mongodb://localhost:27017/cat_health"

# 🌟 核心升级 1：配置 MongoDB 连接池 (最大允许 100 个并发连接)
client = MongoClient(MONGO_URI, maxPoolSize=100)
collection = client['cat_health']['water_logs']

# 🌟 核心升级 2：内存缓冲池参数设置
BUFFER_SIZE = 200      # 满 50 条消息执行一次批量写入
FLUSH_TIMEOUT = 1.0   # 或者最多等待 1 秒必须写入（防止数据一直留在内存）
buffer = []
last_flush_time = time.time()

def flush_buffer(ch, delivery_tag):
    """执行极速批量写入"""
    global buffer, last_flush_time
    if not buffer:
        return
    
    # 解析并转换时间戳
    records_to_insert = []
    for body in buffer:
        record = json.loads(body)
        record['timestamp'] = datetime.fromisoformat(record['timestamp'])
        records_to_insert.append(record)
        
    try:
        # 🚀 加特林模式：一次性将 50 条数据砸进底层硬盘！
        collection.insert_many(records_to_insert)
        print(f"🚀 [极速落盘] 成功批量写入 {len(records_to_insert)} 条数据到 MongoDB！")
        
        # 告诉 MQ 这批数据处理完了，可以从队列里删除了 (批量 Ack)
        ch.basic_ack(delivery_tag=delivery_tag, multiple=True)
    except Exception as e:
        print(f"🚨 [写入崩溃] 批量入库失败: {e}")
        # 如果写入失败，拒绝这些消息并让它们重回队列
        ch.basic_nack(delivery_tag=delivery_tag, multiple=True, requeue=True)
    finally:
        # 清空缓存池，重置倒计时
        buffer.clear()
        last_flush_time = time.time()

def callback(ch, method, properties, body):
    global buffer, last_flush_time
    buffer.append(body)
    
    current_time = time.time()
    # 触发条件：攒够50条，或者距离上次写入超过1秒
    if len(buffer) >= BUFFER_SIZE or (current_time - last_flush_time) >= FLUSH_TIMEOUT:
        flush_buffer(ch, method.delivery_tag)

connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
channel = connection.channel()

# 🌟 核心升级 3：QoS 限流！每次最多从 MQ 拿 100 条放内存，绝不贪多撑爆内存
channel.basic_qos(prefetch_count=1000) 

channel.exchange_declare(exchange='validated_exchange', exchange_type='fanout')
result = channel.queue_declare(queue='', exclusive=True)
queue_name = result.method.queue
channel.queue_bind(exchange='validated_exchange', queue=queue_name)

# auto_ack=False 表示我们需要手动发消息告诉 MQ 确认处理完毕
channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=False)
print("⏳ Writer 节点已启动，开启 [批量写入+连接池+QoS限流] 冠军压榨模式...")
channel.start_consuming()