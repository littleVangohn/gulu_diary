# core/cat_water.py
import random

def estimate_weight(breed: str, age: int) -> float:
    """
    根据品种和年龄估算猫的体重（kg）
    数据参考常见家猫平均体重（简化模型）
    """
    breed_base = {
        "英国短毛猫": 5.0,
        "美国短毛猫": 4.5,
        "布偶猫": 6.0,
        "暹罗猫": 4.0,
        "波斯猫": 4.5,
        "缅因猫": 8.0,
        "其他": 4.0
    }
    
    base_weight = breed_base.get(breed, 4.0)
    
    if age < 1:
        return base_weight * 0.3
    elif 1 <= age <= 10:
        return base_weight
    else:  # age > 10
        return base_weight * 0.9

def calculate_recommended_range(breed: str, age: int) -> tuple[int, int]:
    """
    计算每日推荐饮水量区间 [min, max]（单位：ml）
    公式：体重 × (40 ~ 60 ml/kg)
    """
    weight = estimate_weight(breed, age)
    min_ml = max(50, int(weight * 40))  # 至少 50ml
    max_ml = int(weight * 60)
    return min_ml, max_ml