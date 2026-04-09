#!/bin/bash
# start_cats_safe.sh

IMAGE="cat-simulator"
NUM=20
PROJECT_DIR="/root/cat-water-simulator"
OUTPUT_DIR="$PROJECT_DIR/docker_output"

# 创建并清理旧数据
mkdir -p "$OUTPUT_DIR"
rm -f "$OUTPUT_DIR"/*.json

breeds=("英国短毛猫" "美国短毛猫" "布偶猫" "暹罗猫" "波斯猫" "缅因猫")

echo "🚀 开始串行启动 $NUM 个猫咪饮水模拟容器..."

for i in $(seq 1 $NUM); do
    # 随机属性
    breed=${breeds[$((RANDOM % ${#breeds[@]}))]}
    age=$((RANDOM % 15 + 1))
    
    cat_id="cat_$i"
    
    echo "  >> 正在启动容器 $cat_id (品种: $breed, 年龄: $age)..."
    
    # 【关键修改】去掉了 "&"，改为前台运行
    # 这样每次只跑一个，跑完再跑下一个，内存不会爆炸
    docker run --rm \
        -e CAT_ID="$cat_id" \
        -e CAT_BREED="$breed" \
        -e CAT_AGE="$age" \
        -v "$OUTPUT_DIR:/app/docker_output" \
        "$IMAGE"
        
    # 可选：如果容器运行时间极短，可以加个微小延迟防止磁盘IO拥堵
    # sleep 0.5 
done

echo "-----------------------------------------------"
echo "✅ 所有模拟任务依次执行完毕！"
echo "📂 结果存储在: $OUTPUT_DIR"
ls -1 "$OUTPUT_DIR"