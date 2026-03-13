from flask import Flask, request, jsonify, render_template_string
from pymongo import MongoClient
from datetime import datetime
import os
# 引入核心算法 (保持不变)
from core.water_recommender import get_recommended_range

app = Flask(__name__)

# ==========================================
# 1. 数据库配置区 (根据 PPT 第326-327页)
# ==========================================
# 格式: mongodb://用户名:密码@地址:端口/数据库名
# 注意: 密码中有特殊字符需要URL编码，但你的密码 'cat_password_2026' 很安全，无需编码
MONGO_URI = "mongodb://cat_user:cat_password_2026@localhost:27017/cat_health"

# 创建数据库客户端 (配置连接池，参考 PPT截图 image_7930a3.jpg)
client = MongoClient(
    MONGO_URI,
    maxPoolSize=50,             # 最大连接池数量
    connectTimeoutMS=20000,     # 连接超时 20s
    socketTimeoutMS=20000       # 读写超时 20s
)

# 获取数据库和集合对象
db = client['cat_health']       # 数据库: cat_health
collection = db['water_logs']   # 集合(表): water_logs
collection.create_index([("cat_id", 1)]) 
print("cat_id 索引已就绪")
# 鉴权密钥 (保持不变)
VALID_API_KEY = "cat_secret_2026"

# ==========================================
# 2. 数据上报接口 (改写为 MongoDB 写入)
# ==========================================
@app.route('/upload_data', methods=['POST'])
def receive_cat_data():
    try:
        # API 鉴权
        if request.headers.get('X-Api-Key') != VALID_API_KEY:
            return jsonify({"status": "fail", "message": "鉴权失败"}), 401

        # 解析请求数据
        data = request.get_json()
        cat_id = data.get('cat_id', 'Unknown_Cat')
        cat_info = data.get('cat_info', {})
        breed = cat_info.get('breed', '其他')
        age = cat_info.get('age', 3)
        actual_ml = float(data.get('actual_ml', 0.0))

        # 核心业务逻辑: 判定饮水量
        min_ml, max_ml = get_recommended_range(breed, age)
        judgment = "达标"
        if actual_ml < min_ml: judgment = "未达标"
        elif actual_ml > max_ml: judgment = "超标"

        # 【核心修改】构造 MongoDB 文档对象 (BSON)
        # 移除了文件操作，改为直接构造字典
        record = {
            "cat_id": cat_id,          # 用于索引查询
            "breed": breed,
            "age": age,
            "actual_ml": actual_ml,
            "min_ml": min_ml,
            "max_ml": max_ml,
            "judgment": judgment,
            "timestamp": datetime.now() # MongoDB 原生支持时间类型，比字符串更科学
        }
        
        # 【核心修改】写入数据库 (PPT 第329页)
        # 对应 insert_one 操作
        result = collection.insert_one(record)
        
        print(f"数据已存入 MongoDB, ID: {result.inserted_id}") # 打印日志方便调试

        return jsonify({"status": "success", "judgment": judgment}), 200

    except Exception as e:
        print(f"Database Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ==========================================
# 3. 可视化看板 (改写为 MongoDB 查询)
# ==========================================
@app.route('/dashboard')
def dashboard():
    cats_data = {}
    
    try:
        # 【核心修改】获取所有不重复的猫咪 ID (相当于 SQL 的 SELECT DISTINCT)
        unique_cats = collection.distinct("cat_id")

        for cat_id in unique_cats:
            # 【核心修改】查询逻辑 (PPT 第330-331页)
            # 1. filter: {"cat_id": cat_id} 筛选特定猫咪
            # 2. sort: ("timestamp", -1) 按时间倒序(最新的在前面)
            # 3. limit: 15 只取最近15条
            cursor = collection.find({"cat_id": cat_id}).sort("timestamp", -1).limit(15)
            
            # 将游标转换为列表
            records = list(cursor)
            
            # 因为是倒序查出的，为了图表从左到右显示(旧->新)，需要反转列表
            records.reverse()

            if records:
                # 提取数据用于前端渲染
                #strftime将datetime对象转为易读字符串
                time_labels = [r['timestamp'].strftime("%H:%M:%S") for r in records]
                water_values = [r['actual_ml'] for r in records]
                
                # 取最新的一条记录作为当前阈值参考
                latest_record = records[-1]
                
                cats_data[cat_id] = {
                    "labels": time_labels,
                    "amounts": water_values,
                    "min": latest_record['min_ml'],
                    "max": latest_record['max_ml']
                }
    except Exception as e:
        return f"数据库连接或查询错误: {str(e)}"

    # 渲染 HTML (保持原有 ECharts 逻辑不变)
    return render_template_string(HTML_TEMPLATE, cats=cats_data)

# ==========================================
# 4. 前端模板 (保持 ECharts 样式，无需改动)
# ==========================================
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>猫咪多档案监控 (MongoDB版)</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f4f7f6; padding: 20px; }
        .card { background: white; border-radius: 15px; padding: 25px; margin: 0 auto 30px; max-width: 900px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); }
        h1 { color: #2c3e50; text-align: center; margin-bottom: 40px; }
        h2 { color: #34495e; border-left: 5px solid #3498db; padding-left: 15px; margin-bottom: 20px;}
    </style>
</head>
<body>
    <h1>🐱 猫咪智能饮水监控中心 <span style="font-size:0.5em; color:green;">(MongoDB Connected)</span></h1>
    
    {% if not cats %}
        <div class="card" style="text-align:center; color:#888;">
            <h3>暂无数据</h3>
            <p>请运行 run_headless_pro.py 上报数据...</p>
        </div>
    {% endif %}

    {% for cat_id, info in cats.items() %}
    <div class="card">
        <h2>档案 ID: {{ cat_id }}</h2>
        <div id="chart_{{ loop.index }}" style="width:100%;height:400px;"></div>
    </div>
    <script>
        (function() {
            var myChart = echarts.init(document.getElementById('chart_{{ loop.index }}'));
            var minVal = {{ info.min }};
            var maxVal = {{ info.max }};
            var option = {
                tooltip: { trigger: 'axis' },
                grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
                xAxis: { type: 'category', data: {{ info.labels|tojson }} },
                yAxis: { type: 'value', name: '饮水量(ml)' },
                visualMap: {
                    show: false,
                    pieces: [
                        {gt: 0, lt: minVal, color: '#ff7875'}, // 低于下限-红
                        {gte: minVal, lte: maxVal, color: '#52c41a'}, // 正常-绿
                        {gt: maxVal, color: '#ff7875'} // 高于上限-红
                    ]
                },
                series: [{
                    name: '饮水量',
                    data: {{ info.amounts|tojson }},
                    type: 'line',
                    smooth: true,
                    lineStyle: { width: 3 },
                    markLine: {
                        data: [
                            {yAxis: minVal, name: '最低标准', lineStyle: {color: '#faad14'}}, 
                            {yAxis: maxVal, name: '最高警戒', lineStyle: {color: '#faad14'}}
                        ]
                    },
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            {offset: 0, color: 'rgba(82, 196, 26, 0.3)'},
                            {offset: 1, color: 'rgba(82, 196, 26, 0.01)'}
                        ])
                    }
                }]
            };
            myChart.setOption(option);
        })();
    </script>
    {% endfor %}
</body>
</html>
'''

if __name__ == '__main__':
    # 启动 Flask 服务
    print("正在连接 MongoDB 并启动服务...")
    app.run(debug=True, port=5000)

# from flask import Flask, request, jsonify, render_template_string
# import json
# import os
# import re
# from datetime import datetime
# from core.water_recommender import get_recommended_range

# app = Flask(__name__)

# # 配置区
# VALID_API_KEY = "cat_secret_2026"
# DATA_DIR = "server_data"

# if not os.path.exists(DATA_DIR):
#     os.makedirs(DATA_DIR)

# def sanitize_filename(name):
#     return re.sub(r'[\\/*?Source:"<>|]', "", str(name))

# @app.route('/upload_data', methods=['POST'])
# def receive_cat_data():
#     try:
#         if request.headers.get('X-Api-Key') != VALID_API_KEY:
#             return jsonify({"status": "fail", "message": "鉴权失败"}), 401

#         data = request.get_json()
#         cat_id = data.get('cat_id', 'Unknown_Cat')
#         cat_info = data.get('cat_info', {})
#         breed = cat_info.get('breed', '其他')
#         age = cat_info.get('age', 3)
#         actual_ml = float(data.get('actual_ml', 0.0))

#         min_ml, max_ml = get_recommended_range(breed, age)
#         judgment = "达标"
#         if actual_ml < min_ml: judgment = "未达标"
#         elif actual_ml > max_ml: judgment = "超标"

#         record = {
#             "time_str": datetime.now().strftime("%H:%M:%S"), # 改名避开 time 关键词
#             "actual_ml": actual_ml,
#             "min_ml": min_ml,
#             "max_ml": max_ml,
#             "status": judgment
#         }
        
#         file_path = os.path.join(DATA_DIR, f"{sanitize_filename(cat_id)}.json")
#         with open(file_path, "a", encoding="utf-8") as f:
#             f.write(json.dumps(record, ensure_ascii=False) + "\n")

#         return jsonify({"status": "success", "judgment": judgment}), 200
#     except Exception as e:
#         return jsonify({"status": "error", "message": str(e)}), 500

# @app.route('/dashboard')
# def dashboard():
#     cats_data = {}
#     if not os.path.exists(DATA_DIR):
#         return "尚未创建数据目录"

#     for filename in os.listdir(DATA_DIR):
#         if filename.endswith(".json"):
#             cat_id = filename.replace(".json", "")
#             filepath = os.path.join(DATA_DIR, filename)
            
#             time_labels, water_values = [], [] # 使用更明确的变量名
#             l_min, l_max = 0, 0
            
#             with open(filepath, "r", encoding="utf-8") as f:
#                 for line in f:
#                     try:
#                         r = json.loads(line.strip())
#                         # 重点：确保从 JSON 读取的是字符串和数字，而不是函数
#                         time_labels.append(str(r.get("time_str", r.get("time", "Unknown"))))
#                         water_values.append(float(r.get("actual_ml", 0)))
#                         l_min = float(r.get("min_ml", 0))
#                         l_max = float(r.get("max_ml", 0))
#                     except:
#                         continue
            
#             if time_labels:
#                 cats_data[cat_id] = {
#                     "labels": time_labels[-15:], # 只取最后15条
#                     "amounts": water_values[-15:],
#                     "min": l_min,
#                     "max": l_max
#                 }

#     # 渲染网页
#     html_content = '''
#     <!DOCTYPE html>
#     <html>
#     <head>
#         <meta charset="UTF-8">
#         <title>猫咪多档案监控</title>
#         <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
#         <style>
#             body { font-family: sans-serif; background: #f0f2f5; padding: 20px; }
#             .card { background: white; border-radius: 12px; padding: 20px; margin: 0 auto 30px; max-width: 800px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
#             h2 { color: #333; border-left: 5px solid #4facfe; padding-left: 10px; }
#         </style>
#     </head>
#     <body>
#         <h1 style="text-align:center"> 猫咪健康监控看板</h1>
#         {% for cat_id, info in cats.items() %}
#         <div class="card">
#             <h2>猫咪档案: {{ cat_id }}</h2>
#             <div id="chart_{{ loop.index }}" style="width:100%;height:350px;"></div>
#         </div>
#         <script>
#             (function() {
#                 var myChart = echarts.init(document.getElementById('chart_{{ loop.index }}'));
#                 var minVal = {{ info.min }};
#                 var maxVal = {{ info.max }};
#                 var option = {
#                     tooltip: { trigger: 'axis' },
#                     xAxis: { type: 'category', data: {{ info.labels|tojson }} },
#                     yAxis: { type: 'value', name: 'ml' },
#                     visualMap: {
#                         show: false,
#                         pieces: [
#                             {gt: 0, lt: minVal, color: '#ff4d4f'},
#                             {gte: minVal, lte: maxVal, color: '#52c41a'},
#                             {gt: maxVal, color: '#ff4d4f'}
#                         ]
#                     },
#                     series: [{
#                         data: {{ info.amounts|tojson }},
#                         type: 'line',
#                         smooth: true,
#                         markLine: {
#                             data: [{yAxis: minVal, name: '下限'}, {yAxis: maxVal, name: '上限'}],
#                             lineStyle: { color: '#aaa', type: 'dashed' }
#                         }
#                     }]
#                 };
#                 myChart.setOption(option);
#             })();
#         </script>
#         {% endfor %}
#     </body>
#     </html>
#     '''
#     return render_template_string(html_content, cats=cats_data)

# if __name__ == '__main__':
#     app.run(debug=True, port=5000)