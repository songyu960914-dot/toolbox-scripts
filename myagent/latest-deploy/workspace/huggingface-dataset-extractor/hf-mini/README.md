# HuggingFace 数据集提取工具 - Mini 版本

本地使用版本，不纳入 Git 仓库。

## 特性

- **配置内嵌**：无需外部 config.yaml
- **无 LLM 调用**：只提取 HF API 直接可获取的字段
- **输出到本地**：`output/hf_result_HHMMSS.xlsx`

## 使用

```bash
python run_hf_mini.py 工作簿1.xlsx
```

或直接运行（交互输入文件名）：

```bash
python run_hf_mini.py
```

## 配置

脚本内嵌配置（可直接修改代码中的 CONFIG 字典）：

```python
CONFIG = {
    'requests': {
        'timeout': 15,
        'retry_max': 3,
        'retry_interval': 2,
        'sleep_between_items': 3,  # 请求间隔（秒）
    },
    'readme': {
        'max_length': 10000,
    }
}
```

## 输出字段

- 序号、URL
- 发布/更新时间、数据量级、量级等级、数据大小
- 下载量、点赞量
- Tags、Tasks、License
- 数据类型、数据格式、语种
- 是否有论文、论文URL
- 是否有测试集
- 是否有警告、警告原因

## 注意

- 此版本为本地快速使用，不推送到 GitHub
- 推送到仓库的是 v2 版本（带 config.yaml）
