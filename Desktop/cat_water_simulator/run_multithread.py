# run_multithread.py
import os
import json
import random
import threading
import numpy as np
from core.water_recommender import get_recommended_range

# ❌ 移除 np.random.seed(42) —— 让每次运行都不同！
# np.random.seed(42)  # ← 删除这一行

OUTPUT_DIR = r"C:\Users\ty\Desktop\cat_water_simulator\multithread_output"

BREEDS = [
    "英国短毛猫", "美国短毛猫", "布偶猫", "暹罗猫", "波斯猫",
    "缅因猫", "异国短毛猫", "俄罗斯蓝猫", "土耳其梵猫", "其他"
]

def simulate_one_cat(cat_id):
    breed = random.choice(BREEDS)
    age = random.randint(0, 20)
    min_ml, max_ml = get_recommended_range(breed, age)
    
    # ✅ 科学参数：80%置信区间（z=1.28）
    mu = (min_ml + max_ml) / 2.0
    sigma = max(5.0, (max_ml - min_ml) / 2.56)  # 2.56 = 2 * 1.28
    
    # ✅ 生成正态分布样本（无种子，真随机）
    total_ml = np.random.normal(loc=mu, scale=sigma)
    
    # ✅ 对称截断：使用相同相对比例（±20%）
    lower_bound = min_ml * 0.8   # 允许低至推荐最小值的 80%
    upper_bound = max_ml * 1.2   # 允许高至推荐最大值的 120%
    total_ml = max(lower_bound, min(total_ml, upper_bound))
    
    actual = round(max(10.0, total_ml), 1)

    # 分解饮水事件（略，保持不变）
    num_drinks = random.randint(4, 8)
    min_per = 5.0
    if actual < num_drinks * min_per:
        num_drinks = max(1, int(actual / min_per))
    
    amounts = []
    remaining = actual
    for i in range(num_drinks - 1):
        low = min_per
        high = remaining - (num_drinks - i - 1) * min_per
        if high <= low:
            amt = low
        else:
            amt = random.uniform(low, high)
        amt = round(amt, 1)
        amounts.append(amt)
        remaining -= amt
    amounts.append(round(remaining, 1))
    
    current_time = random.randint(0, 360)
    events = []
    for i, amt in enumerate(amounts):
        time_str = f"{current_time // 60:02d}:{current_time % 60:02d}"
        events.append({"time": time_str, "amount_ml": amt})
        if i < len(amounts) - 1:
            interval = random.randint(30, 150) if i < 2 else random.randint(120, 300)
            current_time = min(1439, current_time + interval)
    
    # 判断状态
    if actual < min_ml:
        status = "未达标"
    elif actual > max_ml:
        status = "超标"
    else:
        status = "达标"

    return {
        "cat_id": cat_id,
        "breed": breed,
        "age_years": age,
        "recommended_daily_ml": {"min": min_ml, "max": max_ml},
        "actual_total_ml": actual,
        "status": status,
        "drinking_events": events
    }

def save_to_json(data):
    filename = f"cat_{data['cat_id']:02d}.json"
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"📁 Output directory: {OUTPUT_DIR}")
    print("🐱 Simulating 10 cats with TRUE RANDOMNESS (WSAVA medical probability)")

    threads = []
    results = {}
    lock = threading.Lock()

    def thread_target(cid):
        data = simulate_one_cat(cid)
        save_to_json(data)
        with lock:
            results[cid] = data

    for i in range(1, 11):
        t = threading.Thread(target=thread_target, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    compliant = sum(1 for r in results.values() if r["status"] == "达标")
    insufficient = sum(1 for r in results.values() if r["status"] == "未达标")
    excessive = sum(1 for r in results.values() if r["status"] == "超标")

    print("\n" + "="*55)
    print("📊 Simulation complete! (True Medical Probability)")
    print(f"✅ Compliant (达标): {compliant} / 10  ({compliant*10:.1f}%)")
    print(f"❌ Insufficient (未达标): {insufficient}  (肾病高风险)")
    print(f"⚠️ Excessive (超标): {excessive}  (代谢疾病风险)")
    print("="*55)
    print(f"💾 JSON files saved to: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()