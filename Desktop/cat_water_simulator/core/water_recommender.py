# core/water_recommender.py
import os
import json
import requests
import re
from typing import Optional, Tuple
import dashscope
from http import HTTPStatus

def query_ai_for_water(breed: str, age: int) -> Optional[float]:
    """
    使用阿里云通义千问 API 查询推荐饮水量
    """
    try:
        # 设置你的 API KEY
        dashscope.api_key = 'sk-83f11120c88f461c98c062e9afa4dbab' # <--- 填入你刚才申请的 sk-xxxx
        
        prompt = (
            f"作为宠物专家，请告诉我在正常环境下，一只{age}岁的{breed}每天建议饮水量是多少毫升？"
            "请直接给出一个具体的数字，不要解释，只返回数字。"
        )

        response = dashscope.Generation.call(
            model='qwen-turbo', # 使用轻量级模型，速度快且免费额度多
            prompt=prompt
        )

        if response.status_code == HTTPStatus.OK:
            # 获取模型输出的文本
            answer = response.output.text.strip()
            
            # 使用正则提取数字
            import re
            match = re.search(r'(\d+)', answer)
            if match:
                value = float(match.group(1))
                # 合理区间校验
                if 50 <= value <= 600:
                    return value
        else:
            print(f"⚠️ API 请求失败: {response.code} - {response.message}")
            
    except Exception as e:
        print(f"⚠️ 接入异常: {e}")
    return None
# 本地缓存文件
CACHE_FILE = os.path.join(os.path.dirname(__file__), "water_recommendations_cache.json")

# 本地知识库（备用）
LOCAL_KNOWLEDGE = {
    ("英国短毛猫", 0): 120, ("英国短毛猫", 5): 180, ("英国短毛猫", 10): 200,
    ("美国短毛猫", 0): 130, ("美国短毛猫", 5): 190, ("美国短毛猫", 10): 210,
    ("布偶猫", 0): 140, ("布偶猫", 5): 220, ("布偶猫", 10): 240,
    ("暹罗猫", 0): 110, ("暹罗猫", 5): 170, ("暹罗猫", 10): 190,
    ("波斯猫", 0): 120, ("波斯猫", 5): 180, ("波斯猫", 10): 200,
    ("缅因猫", 0): 160, ("缅因猫", 5): 250, ("缅因猫", 10): 270,
    ("其他", 0): 120, ("其他", 5): 180, ("其他", 10): 200,
}

def _load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def _save_cache(cache: dict):
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except:
        pass


def get_recommended_water(breed: str, age: int) -> float:
    """
    获取推荐饮水量逻辑：
    1. 查缓存 -> 2. 调 AI -> 3. 兜底本地库
    """
    cache_key = f"{breed}_{age}"
    cache = _load_cache()
    
    # 1. 优先检查缓存
    if cache_key in cache:
        return float(cache[cache_key])
    
    # 2. 尝试 AI 查询
    ai_result = query_ai_for_water(breed, age)
    if ai_result is not None:
        cache[cache_key] = ai_result
        _save_cache(cache)
        print(f"🤖 AI 推荐: {breed} {age}岁 → {ai_result:.1f} ml")
        return ai_result

    # 3. 本地知识库插值（兜底）
    print(f"📚 使用本地知识库: {breed} {age}岁")
    ages = [0, 5, 10]
    base_age = min(ages, key=lambda x: abs(x - age))
    key_breed = breed if (breed, base_age) in LOCAL_KNOWLEDGE else "其他"
    
    base_value = LOCAL_KNOWLEDGE.get((key_breed, base_age), 150)
    # 简单的线性修正：年龄每大一岁增加少量水分需求
    adjustment = (age - base_age) * (2 if age > 10 else 1)
    value = max(80, base_value + adjustment)
    
    cache[cache_key] = value
    _save_cache(cache)
    return float(value)

def get_recommended_range(breed: str, age: int) -> Tuple[float, float]:
    """兼容旧接口：返回 ±20% 的区间"""
    point = get_recommended_water(breed, age)
    return (round(point * 0.8, 1), round(point * 1.2, 1))