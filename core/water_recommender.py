# core/water_recommender.py
import os
import json
import re
from typing import Optional, Tuple
import dashscope
from http import HTTPStatus

# 本地缓存文件
CACHE_FILE = os.path.join(os.path.dirname(__file__), "water_recommendations_cache.json")

def query_ai_for_water(breed: str, age: int, weight: float, diet: str) -> Optional[float]:
    """
    使用阿里云通义千问 API 查询推荐饮水量 (升级版科学 Prompt)
    """
    try:
        # 设置你的 API KEY
        dashscope.api_key = 'sk-83f11120c88f461c98c062e9afa4dbab' 
        
        prompt = (
            f"作为严谨的宠物临床营养专家，请根据 NRC 标准计算一只猫咪的【每日建议主动饮水量】。\n"
            f"档案：{age}岁的{breed}，体重 {weight}kg，日常饮食结构为：{diet}。\n"
            f"注意：如果是纯湿粮，猫咪从食物中已获取了大部分水分，请大幅扣除所需的主动饮水数值。\n"
            f"请直接给出一个具体的数字（单位：毫升），不要有任何解释文本、单位或区间，只返回纯数字。"
        )

        response = dashscope.Generation.call(
            model='qwen-turbo', 
            prompt=prompt
        )

        if response.status_code == HTTPStatus.OK:
            answer = response.output.text.strip()
            # 使用正则提取数字（支持浮点数提取）
            match = re.search(r'(\d+(\.\d+)?)', answer)
            if match:
                value = float(match.group(1))
                if 5 <= value <= 800:  # 放宽区间以适应湿粮极低饮水和大型猫极高饮水
                    return value
        else:
            print(f"⚠️ API 请求失败: {response.code} - {response.message}")
            
    except Exception as e:
        print(f"⚠️ 接入异常: {e}")
    return None

def calculate_local_water(breed: str, age: int, weight: float, diet: str) -> float:
    """
    本地生理目标计算器（基于调研报告公式）
    """
    # 1. 基础基准：45 ml/kg
    base_water = weight * 45.0

    # 2. 年龄干预
    if age <= 1:
        base_water *= 1.3  # 幼猫代谢高
    
    # 3. 品种干预 (可按需持续扩充)
    if "无毛" in breed or "斯芬克斯" in breed:
        base_water *= 1.15
        
    # 4. 饮食扣除 (极其重要)
    if "纯湿粮" in diet or diet == "湿粮":
        base_water *= 0.2  # 扣除80%水分
    elif "混合" in diet:
        base_water *= 0.5  # 扣除50%水分
        
    return round(base_water, 1)

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

def get_recommended_water(breed: str, age: int, weight: float = 4.5, diet: str = "纯干粮") -> float:
    """
    获取推荐饮水量逻辑：
    1. 查缓存 -> 2. AI 预测 -> 3. 本地硬核交叉校验 / 兜底
    保留了旧接口签名，新增参数通过默认值兼容旧调用。
    """
    cache_key = f"{breed}_{age}_{weight}_{diet}"
    cache = _load_cache()
    
    # 1. 优先检查缓存
    if cache_key in cache:
        return float(cache[cache_key])
    
    # 算出本地科学基准线
    local_baseline = calculate_local_water(breed, age, weight, diet)
    
    # 2. 尝试 AI 查询
    ai_result = query_ai_for_water(breed, age, weight, diet)
    
    final_value = local_baseline
    
    if ai_result is not None:
        # 交叉校验：如果 AI 输出与本地计算偏差超过 50%，判定 AI 产生幻觉（如忽略了湿粮），采用本地数据
        lower_bound = local_baseline * 0.5
        upper_bound = local_baseline * 1.5
        
        if lower_bound <= ai_result <= upper_bound:
            print(f"🤖 AI 推荐通过校验: {breed} {age}岁 ({diet}) → {ai_result:.1f} ml")
            final_value = ai_result
        else:
            print(f"⚖️ AI 数据 ({ai_result}ml) 偏差过大，降级使用本地计算: {local_baseline} ml")
            final_value = local_baseline
    else:
        print(f"📚 AI 离线，使用本地知识库计算: {local_baseline} ml")

    # 3. 存入缓存
    cache[cache_key] = final_value
    _save_cache(cache)
    return float(final_value)

def get_recommended_range(breed: str, age: int, weight: float = 4.5, diet: str = "纯干粮") -> Tuple[float, float]:
    """兼容旧接口：返回动态范围区间"""
    point = get_recommended_water(breed, age, weight, diet)
    # 取基准值的 80% - 120% 作为健康区间
    return (round(point * 0.8, 1), round(point * 1.2, 1))