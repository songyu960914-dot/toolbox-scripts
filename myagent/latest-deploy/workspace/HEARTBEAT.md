# HEARTBEAT.md

## 定期任务

### 清理 temp/ 文件夹
检查 `workspace/temp/` 目录，删除超过 3 天的文件。

### 清理中转站
检查 `workspace/trash/` 目录，彻底删除超过 3 天的压缩文件。
命令：`python scripts/safe_delete.py cleanup`
