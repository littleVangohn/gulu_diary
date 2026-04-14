import os
import json
import time
import random
import numpy as np
import pika  
from datetime import datetime, timedelta

# 🌟 引入核心算法（来自阶段一优化）
from core.water_recommender import get_recommended_water
# 🌟 引入密码本
from cipher_utils import encrypt_data

# === 核心配置区 ===
RABBITMQ_HOST = "47.97.245.213"  
RABBITMQ_USER = "admin"          
RABBITMQ_PASS = "cat_mq_2026"    
MQ_QUEUE_NAME = "cat_water_queue" 
CACHE_FILE = "mq_pending_uploads.json" 

# === 丰满后的猫咪名录 (匹配科学计算的数据维度) ===
CAT_MODELS = [
    {"id": "a布偶_小白", "breed": "布偶猫", "age": 3, "weight": 5.0, "diet": "纯干粮", "social": "强势"},
    {"id": "b暹罗_小黑", "breed": "暹罗猫", "age": 2, "weight": 4.0, "diet": "纯湿粮", "social": "正常"},
    {"id": "c缅因_大壮", "breed": "缅因猫", "age": 5, "weight": 7.5, "diet": "纯干粮", "social": "强势"},
    {"id": "d美短_斑点", "breed": "美国短毛猫", "age": 4, "weight": 4.5, "diet": "混合喂养", "social": "弱势"}
]

# ==========================================
# 行为事件分配器 (Behavioral Engine)
# ==========================================

def get_random_time(base_date: datetime, hour_start: int, hour_end: int) -> datetime:
    """在指定的小时范围内生成一个随机时间戳"""
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return base_date.replace(hour=hour_start, minute=minute, second=second)

def split_water_volume(total_volume: float, num_splits: int) -> list:
    """将指定水量随机切分成 N 份，利用随机权重分配保证总和一致"""
    if num_splits <= 0: return []
    weights = [random.uniform(0.5, 1.5) for _ in range(num_splits)]
    total_weight = sum(weights)
    return [round(total_volume * (w / total_weight), 1) for w in weights]

def generate_daily_schedule(cat: dict) -> list:
    """生成猫咪一整天的饮水时间表（基于晨昏双峰与活水机特征）"""
    base_target = get_recommended_water(cat['breed'], cat['age'], cat['weight'], cat['diet'])
    daily_target = base_target * random.uniform(0.85, 1.15)
    
    total_freq = random.randint(5, 10)
    if cat.get('social') == "弱势":
        total_freq = max(3, total_freq - 2)
        
    distribution = [
        {"name": "清晨", "hours": (5, 7),  "vol_ratio": 0.30, "freq": max(1, int(total_freq * 0.3))},
        {"name": "傍晚", "hours": (17, 20), "vol_ratio": 0.40, "freq": max(1, int(total_freq * 0.4))},
        {"name": "夜间", "hours": (0, 2),   "vol_ratio": 0.20, "freq": max(1, int(total_freq * 0.2))},
        {"name": "白天", "hours": (9, 16),  "vol_ratio": 0.10, "freq": max(1, int(total_freq * 0.1))}
    ]
    
    today = datetime.now()
    schedule = []
    
    for period in distribution:
        period_volume = daily_target * period["vol_ratio"]
        volumes = split_water_volume(period_volume, period["freq"])
        
        for vol in volumes:
            if vol > 25.0:
                t1 = get_random_time(today, period["hours"][0], period["hours"][1])
                t2 = t1 + timedelta(minutes=random.randint(2, 5))
                schedule.append((t1, round(vol/2, 1), "补偿性牛饮"))
                schedule.append((t2, round(vol/2, 1), "补偿性牛饮"))
            else:
                t = get_random_time(today, period["hours"][0], period["hours"][1])
                schedule.append((t, vol, "正常饮水"))

    play_freq = random.randint(2, 4)
    for _ in range(play_freq):
        t = get_random_time(today, 10, 16)
        play_vol = round(random.uniform(0.5, 1.8), 1)
        schedule.append((t, play_vol, "活水机玩水/无效交互"))

    schedule.sort(key=lambda x: x[0])
    return schedule

# ==========================================
# 消息队列通信层 (MQ Layer)
# ==========================================

def send_to_mq(data):
    try:
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
        parameters = pika.ConnectionParameters(
            host=RABBITMQ_HOST, port=5672, credentials=credentials, socket_timeout=5
        )
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        channel.queue_declare(queue=MQ_QUEUE_NAME, durable=True)

        json_str = json.dumps(data, ensure_ascii=False)
        encrypted_body = encrypt_data(json_str)
        
        channel.basic_publish(
            exchange='',
            routing_key=MQ_QUEUE_NAME,
            body=encrypted_body,
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
            return True, info
        wait = (2 ** i) + random.random()
        time.sleep(wait)
    save_to_cache(data)
    return False, "投递失败已缓存"

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

# ==========================================
# 主程序：时间轴回放模拟
# ==========================================
if __name__ == "__main__":
    print("=== 🚀 智能猫咪模拟器 (MQ加密版 + 阶段二仿生时间轴) ===")
    process_offline_data()
    
    target_cat = random.choice(CAT_MODELS)
    print(f"\n🐾 设备已绑定猫咪: {target_cat['id']} ({target_cat['breed']}, {target_cat['weight']}kg, {target_cat['diet']})")
    
    print("⏳ 正在生成今日仿生行为时间轴...")
    daily_schedule = generate_daily_schedule(target_cat)
    total_sim_water = sum([event[1] for event in daily_schedule])
    print(f"✅ 时间轴生成完毕! 预计今日饮水 {len(daily_schedule)} 次，共计 {total_sim_water:.1f} ml\n")
    print("-" * 60)
    
    # 🌟 替换掉之前的 100 次狂暴循环，按时间轴顺序模拟发送
    for index, (timestamp, amount, event_type) in enumerate(daily_schedule, 1):
        iso_time = timestamp.isoformat()
        time_str = timestamp.strftime('%H:%M:%S')
        
        payload = {
            "cat_id": target_cat["id"],
            "cat_info": {"breed": target_cat["breed"], "age": target_cat["age"]},
            "actual_ml": amount,
            "timestamp": iso_time
        }
        
        # 控制台 UI 输出格式化
        print(f"[{time_str}] 💧 {event_type:<10} | {amount:>4.1f} ml ", end="", flush=True)
        
        success, server_msg = upload_logic(payload)
        
        if success:
            print(f"-> 📡 MQ 状态: {server_msg}")
        else:
            print("-> ❌ 连接 MQ 失败，已转入本地缓存")
            
        # 每次发送间隔 0.5 秒，模拟一天的时光飞逝
        if index < len(daily_schedule):
            time.sleep(0.5) 
            
    print("-" * 60)
    print(f"🎉 模拟结束！【{target_cat['id']}】的完整一日加密特征数据已全部推送到 RabbitMQ。")