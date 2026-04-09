import pika
import json
import os

RABBITMQ_HOST = "localhost"
LOG_FILE = "system_audit.log"

def callback(ch, method, properties, body):
    record = json.loads(body)
    log_line = f"[{record['timestamp']}] ACTION: IOT_UPLOAD | CAT: {record['cat_id']} | ML: {record['actual_ml']} | RESULT: {record['judgment']}\n"
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line)
        
    print(f"📝 [日志记录] 已追加至 {LOG_FILE}")
    ch.basic_ack(delivery_tag=method.delivery_tag)

connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
channel = connection.channel()

# 声明广播交换机，并绑定专属的日志队列
channel.exchange_declare(exchange='validated_exchange', exchange_type='fanout')
result = channel.queue_declare(queue='', exclusive=True)
queue_name = result.method.queue
channel.queue_bind(exchange='validated_exchange', queue=queue_name)

channel.basic_consume(queue=queue_name, on_message_callback=callback)
print("⏳ Logger 节点已启动，正在监听系统日志...")
channel.start_consuming()