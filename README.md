# GRUMon - GPU Remote Usage Monitor

通过 SSH 远程监控服务器 GPU 显存占用情况，支持等待显存释放后自动执行后续命令。

## 功能特性

- **远程监控**：通过 SSH 连接远程服务器，实时查看所有 GPU 的显存使用情况
- **双模式运行**：
  - **Monitor 模式**：定时查询并显示 GPU 状态
  - **Wait 模式**：等待所有 GPU 显存空闲达到指定阈值后退出（exit 0），可用于命令链
- **配置文件支持**：服务器信息存储在 `config.json` 中，避免硬编码密码
- **可视化展示**：以表格和进度条形式展示显存使用率

## 环境要求

- Python 3.6+
- 依赖库：`paramiko`

```bash
pip install paramiko
```

## 快速开始

### 1. 配置服务器信息

复制示例配置文件并填入你的服务器信息：

```bash
cp config.example.json config.json
```

编辑 `config.json`：

```json
{
    "host": "YOUR_SERVER_IP",
    "port": 2222,
    "user": "YOUR_USERNAME",
    "password": "YOUR_PASSWORD"
}
```

> **注意**：`config.json` 已被添加到 `.gitignore`，不会被提交到仓库。

### 2. 运行监控

#### Monitor 模式 - 定时查看 GPU 状态

```bash
# 默认每 20 秒查询一次
python gpu_monitor.py

# 自定义查询间隔（每 5 秒）
python gpu_monitor.py --interval 5

# 查询 10 次后停止
python gpu_monitor.py --count 10
```

#### Wait 模式 - 等待显存释放

```bash
# 等待每张卡都有 16GB 空闲后退出
python gpu_monitor.py --wait 16

# 等待每张卡都有 12GB 空闲，每 10 秒检查一次
python gpu_monitor.py --wait 12 --interval 10
```

### 3. 命令链示例

等待 GPU 显存释放后自动运行训练脚本：

```bash
python gpu_monitor.py --wait 16 && bash run.sh
```

- 如果显存足够，脚本 exit(0)，`run.sh` 会被执行
- 如果显存不足，脚本会持续等待直到满足条件
- 按 `Ctrl+C` 中止，脚本 exit(1)，`run.sh` 不会被执行

## 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--host` | 从 config.json 读取 | 服务器 IP 地址 |
| `--port` | 从 config.json 读取 (22) | SSH 端口 |
| `--user` | 从 config.json 读取 | SSH 用户名 |
| `--password` | 从 config.json 读取 | SSH 密码 |
| `--interval` | 20 | 查询间隔（秒） |
| `--count` | 0 | 查询次数，0 表示无限（Monitor 模式） |
| `--wait` | 0 | Wait 模式：等待每张卡空闲 N GB |

> 命令行参数优先级高于配置文件。

## 输出示例

```
Connecting to user@192.168.1.100:2222 ...
Connected.

======================================================================
  GPU Status @ 2024-01-15 14:30:25
======================================================================
  GPU  Name                          Used /    Total      Free   Util
  ---  ------------------------- --------   --------  --------  -----
    0  NVIDIA GeForce RTX 4090 D 20315 MiB / 24564 MiB   4249 MiB    98% <-- NEED
    1  NVIDIA GeForce RTX 4090 D 20315 MiB / 24564 MiB   4249 MiB    97% <-- NEED
======================================================================
  -> Not enough, waiting 20s ...

======================================================================
  GPU Status @ 2024-01-15 14:30:45
======================================================================
  GPU  Name                          Used /    Total      Free   Util
  ---  ------------------------- --------   --------  --------  -----
    0  NVIDIA GeForce RTX 4090 D  2048 MiB / 24564 MiB  22516 MiB     5%
    1  NVIDIA GeForce RTX 4090 D  2048 MiB / 24564 MiB  22516 MiB     3%
======================================================================

*** GPU memory sufficient! (16 GB free on each card) ***
*** Checked 2 times, total wait ~40s ***
```

## 文件结构

```
GRUMon/
├── gpu_monitor.py        # 主程序
├── config.json           # 服务器配置（不提交）
├── config.example.json   # 配置示例
├── .gitignore
└── README.md
```

## 注意事项

1. 确保远程服务器已安装 `nvidia-smi`
2. SSH 连接需要密码认证（暂不支持密钥认证）
3. 请勿将 `config.json` 提交到公开仓库，其中包含敏感信息
4. 如果使用 WSL，请确保网络连通性

## License

MIT
