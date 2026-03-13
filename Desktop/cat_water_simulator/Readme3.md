

# 🐱 猫咪健康监测系统 - 数据库开发手册 (MongoDB 版)

本项目已完成从“本地 JSON 文件存储”到“**MongoDB 工业级数据库**”的全面升级，符合《软件系统架构技术》课程关于数据持久化、安全性及系统性能的工程要求。

##  环境准备

在开始运行系统前，请确保已安装 Python 环境及 MongoDB 8.2+ 数据库。

### 1. 安装 Python 依赖库

在项目根目录下运行以下命令，安装 MongoDB 官方驱动：

```cmd
pip install pymongo
```

---

## 数据库部署流程 (核心步骤)

### 1. 第一步：创建管理员与业务用户

**必须先在“无鉴权模式”下进入数据库创建钥匙。**

1. **启动临时数据库窗口**：
```cmd
"D:\MongoDB\bin\mongosh.exe" 
```


2. **执行创建指令**（新开一个 CMD 运行 `mongosh`）：
```javascript
use admin
// 创建系统管理员
db.createUser({user: "superAdmin", pwd: "Password123", roles: [{role: "root", db: "admin"}]})

use cat_health
// 创建项目业务账号 (对应代码中的配置)
db.createUser({user: "cat_user", pwd: "cat_password_2026", roles: [{role: "readWrite", db: "cat_health"}]})

```



### 2. 第二步：开启账户认证与系统服务化

为了安全性及开机自启，需将数据库注册为 Windows 服务。

1. **注册服务**（管理员权限）：
```cmd
"D:\MongoDB\bin\mongod.exe" --config "D:\MongoDB\bin\mongod.cfg" --install --serviceName "MongoDB"

```


2. **管理命令**：
* **启动服务**：`net start MongoDB`
* **停止服务**：`net stop MongoDB`



---

## 数据库配置与架构

### 1. 配置文件 (`mongod.cfg`)

确保配置文件中开启了认证，并指定了正确路径：

```yaml
storage:
  dbPath: D:\MongoDB\data
systemLog:
  destination: file
  path: D:\MongoDB\log\mongod.log
security:
  authorization: enabled  # 核心：开启账户验证
net:
  bindIp: 0.0.0.0         # 允许局域网访问

```



### 创建查询索引

在 `mongosh` 或代码启动时执行，让 `cat_id` 的检索速度提升 100 倍：

```javascript
db.water_logs.createIndex({ "cat_id": 1 })
```

---

##  运行说明

1. **启动后端服务器**：运行 `python server.py`，系统将自动连接至 MongoDB。
2. **运行模拟器**：运行 `python run_headless.py`，数据将实时写入数据库。
3. **查看结果**：
* **图形化**：通过浏览器访问 `http://127.0.0.1:5000/dashboard`。
* **数据库管理**：使用 **MongoDB Compass** 登录 `cat_user` 账号查看原始 BSON 文档，本机已经完成所有配置，可放心使用，无需在cmd设置。



---
