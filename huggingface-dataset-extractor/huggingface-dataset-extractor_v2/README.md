# HuggingFace 数据集信息提取工具

本文件夹包含从 HuggingFace 批量提取数据集元信息的脚本和文档。

## 文件说明

- **run_workbook.py** - 主脚本，提取17个元数据字段 + 榜单类型 + Agent类型
- **run_agent_type.py** - 单独的 Agent 类型判断脚本（包含数据预览功能）
- **实现逻辑说明.md** - 详细的实现逻辑和字段判断规则

## 使用方式

```bash
# 完整提取（所有字段）
python run_workbook.py 工作簿1

# 仅提取 Agent 类型
python run_agent_type.py 工作簿1
```

## 功能特性

- 17个元信息字段：发布时间、下载量、点赞量、License、Tasks、数据大小、语种等
- 榜单类型判断：benchmark榜单、名字含bench类、其他榜单、非榜单
- Agent类型判断：代码/机器人、多模态、通用、通用混合、混合不可用
  - **使用 GLM-5-turbo LLM 推理**
  - **整合数据预览**（列名 + 前5行样本）提升准确率
- 内容安全检测：gated dataset、NSFW、敏感内容警告（已记录在文档，待实现）

## 依赖

- Python 3.8+
- pandas, openpyxl, requests, openai

## 成本与性能

- **成本**: 每25条数据集约 ¥0.3-0.4（智谱 GLM-5-turbo API）
- **速度**: 约5-6秒/条，25条约2.5-3分钟

## 版本历史

- **v2.1** (2026-06-25)
  - 主脚本整合数据预览功能，与专项脚本逻辑统一
  - 新增"其他榜单"英文关键词支持
  - LLM 判断优先考虑实际数据内容（category列等）
