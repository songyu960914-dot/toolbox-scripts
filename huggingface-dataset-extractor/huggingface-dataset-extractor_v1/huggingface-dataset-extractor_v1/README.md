# HuggingFace Dataset Extractor v1

原始版本：串行处理 + 双 LLM 调用 + 硬编码配置

## 文件说明

- `run_workbook.py` - 主脚本（完整17字段提取）
- `run_agent_type.py` - Agent 类型专项脚本
- `实现逻辑说明.md` - 详细设计文档

## 特性

- 串行处理（单线程）
- 榜单判断 + Agent 判断各一次 LLM 调用
- API Key 硬编码在脚本中

## 使用方式

```bash
python run_workbook.py 工作簿1
```

## 性能

- 25条约 3-4 分钟
- 成本约 ¥0.4-0.6
