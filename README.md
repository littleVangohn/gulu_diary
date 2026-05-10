# Competition Race Server

这是数据服务器性能测试比赛用的冲分版本。

它做的事很简单：按比赛协议接收 PTS 请求，把 `/uploadData` 的数据同步写入 Redis，写成功后返回 `code=200`。赛后可以用 Redis 查询某个设备上传的数据。

## 技术方案

- HTTP 服务：Go + fasthttp
- 数据库：本机 Redis
- 数据存储：Redis List
- 监听端口：默认 `5000`
- 公网访问：`http://47.97.245.213:5000`

支持比赛接口：

- `GET /getTicket?deviceId=xxx`
- `POST /getToken`
- `POST /uploadData`
- `POST /refreshToken`
- `GET /healthz`

## 关键配置

配置文件：

```bash
configs/race.env
```

当前推荐冲分配置：

```env
PORT=5000
SECRET=comp2026
STRICT_SIGNATURE=1
STRICT_TOKEN=0
REDIS_ADDR=127.0.0.1:6379
REDIS_WRITE_MODE=list
```

说明：

- `STRICT_SIGNATURE=1`：取 token 时校验签名，符合比赛协议。
- `STRICT_TOKEN=0`：上传数据时不深度校验 token，减少性能损耗。
- `REDIS_WRITE_MODE=list`：用 Redis List 存数据，当前性能最好。

## 首次部署

在云服务器执行：

```bash
cd /root/competition-race
chmod +x scripts/*.sh
cp configs/race.env.example configs/race.env
./scripts/install_deps_ubuntu.sh
./scripts/tune_linux.sh
./scripts/build_linux.sh
./scripts/start_linux.sh
```

检查服务：

```bash
curl http://127.0.0.1:5000/healthz
curl http://47.97.245.213:5000/healthz
```

看到 `code:200` 就说明服务正常。

## 每轮比赛前

正式开打前只执行这一条：

```bash
cd /root/competition-race
PUBLIC_BASE_URL=http://47.97.245.213:5000 DO_BUILD=0 ./scripts/ready_round.sh
```

这个脚本会自动：

- 停掉旧服务
- 清空上一轮 Redis 数据
- 启动服务
- 检查本机和公网健康状态
- 跑一次完整协议冒烟
- 验证 Redis 能真实落库
- 最后再次清空 Redis，等待 PTS 正式压测

看到最后一行：

```text
ready for next round
```

就说明已经准备好，可以让 PTS 开始打。

## 本机 wrk 压测

在云服务器上压公网入口：

```bash
cd /root/competition-race
./scripts/cleanup_round.sh
BASE_URL=http://47.97.245.213:5000 THREADS=4 CONNECTIONS=200 DURATION=60s ./scripts/bench_local.sh
```

压完看结果里的：

```text
Requests/sec
```

这就是本次 wrk 测到的 RPS。

## 查数据库

查看某个设备写入了多少条：

```bash
redis-cli LLEN competition:bp:20845
```

查看前几条数据：

```bash
redis-cli LRANGE competition:bp:20845 0 2
```

或者用脚本：

```bash
./scripts/query_device.sh 20845 10
```

数据格式示例：

```json
{"deviceId":"20845","time":1776859860,"high":120,"low":90,"receivedTime":1776859861011}
```

## 常用维护命令

查看状态：

```bash
./scripts/status.sh
```

停止服务：

```bash
./scripts/stop_linux.sh
```

启动服务：

```bash
./scripts/start_linux.sh
```

清空比赛数据：

```bash
./scripts/cleanup_round.sh
```

重新编译：

```bash
./scripts/build_linux.sh
```

## 比赛当天流程

1. 登录云服务器。
2. 执行 `ready_round.sh`。
3. 看到 `ready for next round` 后不要再清库，不要关服务。
4. 让 PTS 打 `http://47.97.245.213:5000`。
5. 打完后用 `redis-cli` 或 `query_device.sh` 查询设备数据给老师看。

## 当前目标

当前公网 wrk 已测到约 `3500 RPS`，已经超过比赛起步 `1000 RPS`。下一步重点不是继续乱改代码，而是保证每轮前服务干净、端口通、Redis 能查到数据、PTS 成功率大于 `99%`。
