# Toolbox Scripts

个人自动化脚本和工具集合。

## 项目列表

### 1. HuggingFace Dataset Extractor

从 HuggingFace / ModelScope / Kaggle 批量提取数据集元信息。

- **位置**: `huggingface-dataset-extractor/`
- **版本**: v1（原始串行）、v2（配置外部化、无LLM）、v3（并发版，已废弃）
- **新增**: ModelScope 和 Kaggle 提取脚本
- **功能**: 提取 17 个元数据字段（时间、下载量、点赞、Tags、License、数据大小等）
- **详情**: [README](huggingface-dataset-extractor/README.md)

### 2. Salary Calculator

邮政揽投人员工资计算工具。

- **位置**: `salary-calculator/`
- **版本**: v1（基础版）、v2（双模式 + GUI + 负责人汇总）
- **功能**: 从数据总表筛选平舆地区人员，自动填充核算表，支持负责人-下属数据汇总

### 3. MyAgent Deploy

OpenClaw Agent 配置自动部署包。

- **位置**: `myagent/latest-deploy/`
- **功能**: 每天自动打包 workspace 核心配置（脱敏版），新电脑快速部署

---

## 工具结构

每个工具独立文件夹，多版本管理：

```
工具名/
  ├── 工具名_v1/      # 第一版
  ├── 工具名_v2/      # 第二版（改进）
  └── 工具名_v3/      # 第三版
```

---

## 环境

- Python 3.14+
- 依赖各工具独立管理（见各自 README）

---

_最后更新: 2026-06-30_
