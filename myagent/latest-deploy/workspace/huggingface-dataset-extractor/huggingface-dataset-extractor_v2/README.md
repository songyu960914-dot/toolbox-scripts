# HuggingFace Dataset Extractor v2

串行版：逐条处理 + 合并 LLM 调用 + 配置外部化。**推荐使用版本。**

## 文件说明

- `run_workbook.py` - 主脚本（完整字段提取 + 榜单/Agent/警告判断）
- `config.yaml` - 配置文件（API Key、请求参数、数据预览设置）

## 特性

- 串行处理，避免 API 速率限制（429错误）
- 榜单判断 + Agent判断合并为一次 LLM 调用，节省成本
- 配置外部化（config.yaml），API Key 与代码分离
- 双源字段提取（tags + cardData 去重合并）
- 内容警告检测（排除作者呼吁式语句）
- 数据预览辅助判断

## 使用方式

```bash
python run_workbook.py 工作簿1
```

输入文件放桌面，格式为 xlsx，第一列序号，第二列 URL。

## 输出字段

序号、URL、发布/更新时间、数据量级（条）、量级等级（条）、数据大小（GB）、
下载量、点赞量、Tags、Tasks、License、数据类型（文件类型）、数据格式、语种、
是否有论文、论文arXivURL、是否有测试集、榜单类型、榜单关键词原句、
Agent类型、混合说明、是否有警告、警告原因

## 配置

编辑 `config.yaml`：
- `llm.api_key`: 智谱 API Key（本地填真实值，GitHub 上用 `${ZHIPU_API_KEY}`）
- `requests.sleep_between_items`: 每条数据间隔秒数（默认 1.5s）
- `requests.timeout`: 请求超时秒数

## 性能

- 30条约 10-12 分钟（串行 + 间隔控制）
- LLM 成本约 ¥0.3-0.5/30条
