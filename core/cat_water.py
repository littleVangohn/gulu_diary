# core/cat_water.py

def estimate_weight(breed: str, age: int) -> float:
    """
    根据品种和年龄估算猫的体重（kg）
    数据参考常见家猫平均体重（简化模型）
    """
    # 品种基础体重（成年，单位：kg）
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
    
    # 年龄调整：幼猫（<1岁）较轻，老年猫（>10岁）略轻
    if age < 1:
        return base_weight * 0.3
    elif age >= 1 and age <= 10:
        return base_weight
    else:  # age > 10
        return base_weight * 0.9

def calculate_recommended_water(breed: str, age: int) -> int:
    """
    计算每日推荐饮水量（ml）
    公式：体重(kg) × 50 ml/kg（取中间值）
    返回整数（ml）
    """
    weight = estimate_weight(breed, age)
    water_ml = weight * 50
    return int(water_ml)