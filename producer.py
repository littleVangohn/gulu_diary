import redis
import json
import random

r = redis.Redis(host='localhost', port=6379, db=0)

breeds = ["英国短毛猫", "美国短毛猫", "布偶猫", "暹罗猫", "波斯猫", "缅因猫"]
NUM = 50 # 一次性派发 50 个任务

print(f"🚀 准备下发 {NUM} 个猫咪饮水任务...")

for i in range(1, NUM + 1):
    cat_id = f"cat_{i}"
    breed = random.choice(breeds)
    age = random.randint(1, 15)
    
    # 构造任务数据字典
    task_data = {
        "CAT_ID": cat_id,
        "CAT_BREED": breed,
        "CAT_AGE": str(age)
    }
    
    r.rpush('cat_task_queue', json.dumps(task_data))
    
print("✅ 任务已全部推送至 Redis 队列！")