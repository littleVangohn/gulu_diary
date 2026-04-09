from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from pymongo import MongoClient
import json
import aio_pika  # 替换掉同步的 pika
from datetime import datetime
from jinja2 import Template
from cipher_utils import decrypt_data  

app = FastAPI()

# --- 数据库配置（注意：如果压测也打到 dashboard 接口，这里也需要改成异步的 motor 库） ---
MONGO_URI = "mongodb://localhost:27017/cat_health"
client = MongoClient(MONGO_URI, maxPoolSize=50)
collection = client['cat_health']['water_logs']

VALID_API_KEY = "cat_secret_2026"
RABBITMQ_HOST = "amqp://guest:guest@localhost/" # 根据实际情况配置账号密码

# 全局 MQ 连接和 Channel
mq_connection = None
mq_channel = None

@app.on_event("startup")
async def startup_event():
    """在 FastAPI 启动时，建立【全局唯一的长连接】"""
    global mq_connection, mq_channel
    try:
        # 建立异步长连接
        mq_connection = await aio_pika.connect_robust(RABBITMQ_HOST)
        mq_channel = await mq_connection.channel()
        # 声明队列
        await mq_channel.declare_queue('cat_water_queue', durable=True)
        print("✅ RabbitMQ 异步长连接已就绪！")
    except Exception as e:
        print(f"🚨 RabbitMQ 连接失败: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """在应用关闭时，释放连接"""
    global mq_connection
    if mq_connection:
        await mq_connection.close()

@app.post('/upload_data')
async def receive_cat_data(request: Request):
    # 1. 鉴权
    if request.headers.get('X-Api-Key') != VALID_API_KEY:
        return JSONResponse(status_code=401, content={"status": "fail", "message": "鉴权失败"})
    
    # 2. 获取请求体
    try:
        req_json = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"status": "fail", "message": "非法的 JSON 格式"})

    # 3. 提取并解密 payload
    encrypted_payload = req_json.get('payload')
    if not encrypted_payload:
        return JSONResponse(status_code=400, content={"status": "fail", "message": "未找到加密报文"})

    try:
        decrypted_str = decrypt_data(encrypted_payload)
        original_data = json.loads(decrypted_str)
        
        # 4. 推入 MQ（使用已经建立好的全局通道，纯异步非阻塞！）
        message_body = json.dumps(original_data, ensure_ascii=False).encode()
        await mq_channel.default_exchange.publish(
            aio_pika.Message(body=message_body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
            routing_key='cat_water_queue'
        )
        
        return JSONResponse(status_code=200, content={"status": "success", "message": "密文解密成功并已进入处理队列"})
        
    except ValueError as ve:
        return JSONResponse(status_code=400, content={"status": "error", "message": f"JSON格式有误: {ve}"})
    except Exception as e:
        print(f"🚨 处理失败: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": f"服务端异常: {e}"})

# ... 后面的 dashboard 代码保持不变 ...
@app.get('/dashboard', response_class=HTMLResponse)
async def dashboard():
    cats_data = {}
    try:
        unique_cats = collection.distinct("cat_id")
        for cat_id in unique_cats:
            cursor = collection.find({"cat_id": cat_id}).sort("timestamp", -1).limit(15)
            records = list(cursor)
            records.reverse()
            if records:
                time_labels = []
                for r in records:
                    ts = r['timestamp']
                    if isinstance(ts, str):
                        try: ts = datetime.fromisoformat(ts)
                        except: ts = datetime.now()
                    time_labels.append(ts.strftime("%H:%M"))

                water_values = [r['actual_ml'] for r in records]
                latest_record = records[-1]
                cats_data[cat_id] = {
                    "labels": time_labels, "amounts": water_values,
                    "min": latest_record['min_ml'], "max": latest_record['max_ml']
                }
    except Exception as e:
        return HTMLResponse(content=f"数据库查询错误: {str(e)}", status_code=500)
    
    # 使用 Jinja2 渲染 HTML
    template = Template(HTML_TEMPLATE)
    return template.render(cats=cats_data)

# ==========================================
# 完整保留的 Paw Planet 前端看板模板
# ==========================================
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>咕噜日记 · Paw Planet</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Nunito', sans-serif; background-color: #FFF8F0; color: #4A4A4A; padding: 20px; margin: 0; }
        .header-section { text-align: center; margin-bottom: 40px; }
        .header-title { color: #FFA07A; font-size: 2.5em; margin: 10px 0; font-weight: 700; }
        .header-subtitle { color: #888; font-size: 1.1em; letter-spacing: 1px; }
        .hero-image { max-width: 100%; height: auto; border-radius: 20px; box-shadow: 0 8px 20px rgba(0,0,0,0.05); margin-bottom: 20px; }
        .card { background: #FFFFFF; border-radius: 24px; padding: 30px; margin: 0 auto 30px; max-width: 900px; box-shadow: 0 12px 30px rgba(255, 160, 122, 0.1); }
        .cat-title { color: #5C8D89; font-size: 1.5em; border-bottom: 2px dashed #eee; padding-bottom: 10px; margin-bottom: 20px; display: flex; align-items: center; }
        .cat-icon { width: 40px; height: 40px; margin-right: 15px; border-radius: 50%; }
        .empty-state { text-align: center; color: #FFA07A; padding: 50px; background: white; border-radius: 24px; max-width: 600px; margin: 0 auto; }
    </style>
</head>
<body>
    <div class="header-section">
        <h1 class="header-title">🐱 咕噜日记 · Paw Planet</h1>
        <div class="header-subtitle">连接每一次云端守护，共建宠物友好生态 (FastAPI 极速版)</div>
    </div>
    {% if not cats %}
        <div class="empty-state">
            <h2>🐾 星球还在沉睡中...</h2>
            <p>等待小猫咪喝水的数据上传唤醒它</p>
        </div>
    {% endif %}
    {% for cat_id, info in cats.items() %}
    <div class="card">
        <div class="cat-title">
            <img src="https://api.dicebear.com/7.x/notionists/svg?seed={{ cat_id }}" alt="猫咪图标" class="cat-icon">
            档案 ID: {{ cat_id }}
        </div>
        <div id="chart_{{ loop.index }}" style="width:100%;height:350px;"></div>
    </div>
    <script>
        (function() {
            var myChart = echarts.init(document.getElementById('chart_{{ loop.index }}'));
            var minVal = {{ info.min }};
            var maxVal = {{ info.max }};
            var option = {
                tooltip: { trigger: 'axis', backgroundColor: 'rgba(255, 255, 255, 0.9)', borderRadius: 12 },
                grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
                xAxis: { type: 'category', data: {{ info.labels|tojson }}, axisLine: { lineStyle: { color: '#ddd' } } },
                yAxis: { type: 'value', name: '饮水量(ml)', splitLine: { lineStyle: { type: 'dashed', color: '#eee' } } },
                visualMap: {
                    show: false,
                    pieces: [
                        {gt: 0, lt: minVal, color: '#FFA07A'},
                        {gte: minVal, lte: maxVal, color: '#74B49B'},
                        {gt: maxVal, color: '#FFA07A'}
                    ]
                },
                series: [{
                    name: '饮水量', data: {{ info.amounts|tojson }}, type: 'line', smooth: true, symbol: 'circle', symbolSize: 8, lineStyle: { width: 4 },
                    markLine: {
                        data: [
                            {yAxis: minVal, name: '最低标准', lineStyle: {color: '#F4A261'}}, 
                            {yAxis: maxVal, name: '最高警戒', lineStyle: {color: '#F4A261'}}
                        ]
                    },
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            {offset: 0, color: 'rgba(116, 180, 155, 0.4)'},
                            {offset: 1, color: 'rgba(116, 180, 155, 0.05)'}
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