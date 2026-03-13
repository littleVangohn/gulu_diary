#!/bin/bash
# start_cats.sh

IMAGE="cat-simulator"
NUM=20
PROJECT_DIR="/root/cat-water-simulator"
OUTPUT_DIR="$PROJECT_DIR/docker_output"

# 创建并清理旧数据
mkdir -p "$OUTPUT_DIR"
rm -f "$OUTPUT_DIR"/*.json

breeds=("英国短毛猫" "美国短毛猫" "布偶猫" "暹罗猫" "波斯猫" "缅因猫")

echo "🚀 启动 $NUM 个猫咪饮水模拟容器..."

for i in $(seq 1 $NUM); do
    # 随机属性
    breed=${breeds[$((RANDOM % ${#breeds[@]}))]}
    age=$((RANDOM % 15 + 1))
    
    # 为每个容器分配唯一的 ID
    cat_id="cat_$i"
    
    # 启动 Docker
    # 注意：这里 -v 必须使用绝对路径
    docker run --rm \
        -e CAT_ID="$cat_id" \
        -e CAT_BREED="$breed" \
        -e CAT_AGE="$age" \
        -v "$OUTPUT_DIR:/app/docker_output" \
        "$IMAGE" &
        
    echo "  >> 容器 $cat_id 已派发 (品种: $breed, 年龄: $age)"
done

# 等待所有后台容器执行完毕
wait

echo "-----------------------------------------------"
echo "✅ 模拟全部完成！"
echo "📂 结果存储在: $OUTPUT_DIR"
echo "📄 文件列表:"
ls -1 "$OUTPUT_DIR"