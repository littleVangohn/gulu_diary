# validate_distribution.py
import os
import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

OUTPUT_DIR = r"C:\Users\ty\Desktop\cat_water_simulator\multithread_output"

def validate_against_literature():
    """验证模拟数据是否符合医学文献分布"""
    actuals = []
    recommended_mins = []
    recommended_maxs = []
    
    for file in Path(OUTPUT_DIR).glob("*.json"):
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            actuals.append(data['actual_total_ml'])
            recommended_mins.append(data['recommended_daily_ml']['min'])
            recommended_maxs.append(data['recommended_daily_ml']['max'])
    
    if not actuals:
        print("❌ 无数据，请先运行 run_multithread.py")
        return
    
    actuals = np.array(actuals)
    mins = np.array(recommended_mins)
    maxs = np.array(recommended_maxs)
    
    # 计算达标率
    compliant = np.sum((actuals >= mins) & (actuals <= maxs))
    rate = compliant / len(actuals)
    
    print(f"📊 模拟达标率: {rate:.1%}")
    print("📚 医学期望达标率: 75% ~ 85%")
    
    # 绘制直方图
    plt.figure(figsize=(10, 6))
    
    # 推荐范围（背景）
    all_mins = np.min(mins)
    all_maxs = np.max(maxs)
    plt.axvspan(all_mins, all_maxs, alpha=0.2, color='green', label='推荐范围')
    
    # 实际分布
    plt.hist(actuals, bins=12, alpha=0.7, color='skyblue', edgecolor='black', label='实际饮水量')
    
    plt.axvline(np.mean(actuals), color='red', linestyle='--', label=f'平均值: {np.mean(actuals):.1f}ml')
    plt.xlabel('每日饮水量 (ml)')
    plt.ylabel('频次')
    plt.title('饮水量分布 vs 医学推荐范围')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 保存
    plt.savefig('validation_histogram.png', dpi=150, bbox_inches='tight')
    plt.show()
    
    if 0.75 <= rate <= 0.85:
        print("✅ 达标率符合医学标准！")
    else:
        print("⚠️ 达标率偏离医学标准，请检查算法参数")

if __name__ == "__main__":
    validate_against_literature()