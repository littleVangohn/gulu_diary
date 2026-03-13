
# 🐱 小猫饮水模拟器 (Cat Water Simulator)

这是一个模拟猫咪喝水行为的程序。

## Git 上传说明

如果您想通过 SSH 将此项目上传到 GitHub，请按照以下步骤操作：

1. 确保已生成 SSH 密钥并添加到 GitHub 账户
2. 在项目根目录执行以下命令：

```

# 🐱 小猫饮水模拟器 (Cat Water Simulator) 全流程测试指南

本项目通过 AI (通义千问) 与本地医学知识库结合，模拟不同品种猫咪的日常饮水行为。

## 1. 环境准备 (Environment Setup)

在开始任何测试之前，请确保您的环境已配置完毕。

```bash
# 1. 安装 Python 依赖（推荐使用 requirements.txt）
pip install -r requirements.txt

# 或手动安装核心依赖
pip install numpy requests dashscope

# 2. 检查项目结构 (确保核心文件到位)
# 目录应包含: gui_app.py, start_cats.sh, run_headless.py, requirements.txt, core/water_recommender.py

# 3. 构建 Docker 镜像 (用于容器测试)
docker build -t cat-simulator .
```

---

##  2. 四大测试模块命令

### 模式 A: 本地 GUI 交互测试 (GUI App)

**目的**：手动输入数据，观察单只猫咪的饮水时间轴。

```bash
# 执行此命令后将弹出窗口
python gui_app.py
```

* **测试步骤**：选择品种 -> 输入年龄 -> 点击“开始模拟”。
* **核心逻辑**：程序会模拟 4-8 次饮水事件，并实时刷新日志窗口。

---

### 模式 B: 本地多线程压测 (Multithread Simulation)

**目的**：快速生成 10 份模拟数据，并验证医学达标率。

```bash
# 1. 运行 10 线程并行模拟
python run_multithread.py

# 2. 验证结果分布 (可选)
python validate_distribution.py

# 3. 查看生成的结果文件
ls -lh C:/Users/ty/Desktop/cat_water_simulator/multithread_output
```

* **核心逻辑**：移除随机种子，确保每次生成的 `actual_total_ml` 具有真实的统计学差异。

---

### 模式 C: 容器独立运行测试 (Single Docker Container)

**目的**：验证 Docker 容器是否能正确调用 API 并将数据写回宿主机。

```bash
# 1. 创建输出目录
mkdir -p /root/cat-water-simulator/docker_output

# 2. 运行单个容器测试
docker run --rm \
  -e CAT_ID="test_api_cat" \
  -e CAT_BREED="缅因猫" \
  -e CAT_AGE="5" \
  -e DASHSCOPE_API_KEY="sk-83f11120c88f461c98c062e9afa4dbab" \
  -v "/root/cat-water-simulator/docker_output:/app/docker_output" \
  cat-simulator

# 3. 检查生成的 JSON 数据
cat /root/cat-water-simulator/docker_output/test_api_cat.json
```

* **核心逻辑**：容器内部将生成的 JSON 命名为 `test_api_cat.json` 以防覆盖。

---

### 模式 D: 批量脚本测试 (Shell Script)

**目的**：模拟大规模集群作业，测试 20 个并发容器的稳定性。

```bash
# 1. 确保脚本具有执行权限
chmod +x start_cats.sh

# 2. 运行批量模拟脚本
./start_cats.sh

# 3. 实时监控容器运行状态 (另开窗口运行)
docker ps

# 4. 确认最终生成的文件数量 (应为 20 个)
ls -1 /root/cat-water-simulator/docker_output | wc -l
```

* **核心逻辑**：脚本会自动为每个容器分配唯一的 `CAT_ID` (如 `cat_1`, `cat_2`)，防止数据写入冲突。

---

##  3. 结果验证要点 (Validation)

在测试完成后，请检查生成的 JSON 文件是否符合以下预期：

1. **`source` 字段**：若显示 `aliyun_api` 则代表成功接入 AI；若显示 `local_knowledge` 则代表 API 调用失败已回退到本地库。
2. **`status` 字段**：系统应根据 `actual_ml` 是否在 `recommended_range` 内自动标记为 `达标`、`未达标` 或 `超标`。
3. **文件名**：文件应严格按照 `cat_01.json` 格式排列，且内容不应被后续容器覆盖。

---

**建议**：测试完成后，您可以运行 `rm -rf /root/cat-water-simulator/docker_output/*.json` 来清理测试数据.