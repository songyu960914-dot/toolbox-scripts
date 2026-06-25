# Toolbox Scripts

我的个人自动化脚本和工具集合。

## 项目列表

### 1. HuggingFace Dataset Extractor
从 HuggingFace 批量提取数据集元信息的工具。

- **位置**: `huggingface-dataset-extractor/`
- **版本**: v1, v2, v3
- **功能**: 提取17个元数据字段 + 榜单类型判断 + Agent类型判断（LLM推理）
- **详情**: [README](huggingface-dataset-extractor/README.md)

---

## 工具结构

每个工具独立文件夹，多版本管理：

```
工具名/
  ├── 工具名_v1/      # 第一版
  ├── 工具名_v2/      # 第二版（改进）
  └── 工具名_v3/      # 第三版（进一步优化）
```

---

## 环境

- Python 3.8+
- 依赖各工具独立管理（见各自 README）

---

_持续更新中..._
