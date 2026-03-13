import requests
import time
import json
import os
import random
import numpy as np
from datetime import datetime
from core.water_recommender import get_recommended_range

# === 全局配置 ===
#API_URL = "https://mock.apipost.net/mock/5ced3c80a451000/upload_data?apipost_id=ed3eaf4fcf003"#mock测试用的
API_URL = "http://127.0.0.1:5000/upload_data"#本地测试
API_KEY = "cat_secret_2026"
CACHE_FILE = "pending_uploads.json"

# === 模拟猫咪名录 (用于产生多样性数据) ===
CAT_MODELS = [
    {"id": "a布偶_小白", "breed": "布偶猫", "age": 3},
    {"id": "b暹罗_小黑", "breed": "暹罗猫", "age": 2},
    {"id": "c缅因_大壮", "breed": "缅因猫", "age": 5},
    {"id": "d美短_斑点", "breed": "美国短毛猫", "age": 4}
]

def get_single_reading(cat_dict):
    """
    针对特定猫咪生成一次科学随机饮水数据
    """
    min_ml, max_ml = get_recommended_range(cat_dict["breed"], cat_dict["age"])
    
    # 增强随机性逻辑 (15%异常低, 15%异常高, 70%正态分布)
    dice = random.random()
    if dice < 0.15:
        actual = random.uniform(min_ml * 0.3, min_ml * 0.9)
    elif dice > 0.85:
        actual = random.uniform(max_ml * 1.1, max_ml * 1.5)
    else:
        mu = (min_ml + max_ml) / 2
        sigma = (max_ml - min_ml) / 6
        actual = np.random.normal(mu, sigma)
        actual = max(min_ml * 0.8, min(actual, max_ml * 1.2))

    return {
        "cat_id": cat_dict["id"],
        "cat_info": {"breed": cat_dict["breed"], "age": cat_dict["age"]},
        "actual_ml": round(actual, 1),
        "timestamp": datetime.now().isoformat()
    }

def send_request(data):
    """底层 HTTP 发送逻辑"""
    headers = {"X-Api-Key": API_KEY, "Content-Type": "application/json"}
    try:
        response = requests.post(API_URL, json=data, headers=headers, timeout=5)
        if response.status_code == 200:
            return True, response.json().get("judgment")
        return False, f"HTTP_{response.status_code}"
    except Exception as e:
        return False, str(e)

def upload_logic(data):
    """带有指数退避重试的上传封装"""
    for i in range(3):
        success, info = send_request(data)
        if success:
            print(f"✅ [{data['cat_id']}] 采样成功: {data['actual_ml']}ml -> 服务器判定: {info}")
            return True
        
        wait = (2 ** i) + random.random()
        print(f"❌ 尝试 {i+1} 失败 ({info})，{wait:.1f}s 后重试...")
        time.sleep(wait)
    
    print(f" [{data['cat_id']}] 连续失败，存入本地缓存")
    save_to_cache(data)
    return False

def save_to_cache(data):
    """持久化缓存"""
    cache = []
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            try: cache = json.load(f)
            except: cache = []
    cache.append(data)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def process_offline_data():
    """断网续传逻辑"""
    if not os.path.exists(CACHE_FILE): return
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        try: items = json.load(f)
        except: items = []
    
    if not items: return
    
    print(f"🔍 发现 {len(items)} 条本地积压数据，正在尝试补传...")
    still_failed = []
    for item in items:
        success, _ = send_request(item)
        if not success: still_failed.append(item)
    
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(still_failed, f, ensure_ascii=False, indent=2)
    print(f" 补传处理完成。")

# === 主程序 ===
if __name__ == "__main__":
    print("===  猫咪智能饮水模拟器===")
    
    # 1. 启动先处理历史遗留数据
    process_offline_data()
    
    # 2. 核心要求：随机选定一只猫，本次运行仅代表这只猫
    target_cat = random.choice(CAT_MODELS)
    print(f"\n 设备已绑定猫咪: {target_cat['id']} [{target_cat['breed']}]")
    print("-" * 50)
    
    # 3. 连续采集 5 次数据并上传
    for i in range(1, 6):
        print(f"🕒 进度: {i}/5")
        current_data = get_single_reading(target_cat)
        upload_logic(current_data)
        
        if i < 5:
            # 模拟采集间隔，最后一次不需要等待
            time.sleep(1.5)
            
    print("-" * 50)
    print(f"=== 模拟结束：{target_cat['id']} 的 5 次数据已同步完成 ===")