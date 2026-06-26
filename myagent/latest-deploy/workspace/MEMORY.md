# MEMORY.md - 长期记忆

## 工作流程

### 每日工作日志
**触发时机：** 用户说"再见"、"晚安"、"今天就到这"等结束语时

**操作步骤：**
1. 回顾当天的对话和完成的任务
2. 整理成条目列表（包括完成的事项、讨论的主题、做出的决定）
3. 保存到 `daily-logs/YYYY-MM-DD.md`
4. 给用户一个简短的总结确认

**日志格式：**
```
# YYYY-MM-DD 工作日志

## 完成事项
1. **任务标题**
   - 详细描述
   - 相关文件或命令
```

**存储位置：** `workspace/daily-logs/`

---

## 工作流程规范

### 任务文件组织
**规则：** 每个独立任务创建专属文件夹，所有相关文件集中管理

**命名规范：**
- 文件夹名：小写英文+短横线，语义清晰（如 `huggingface-dataset-extractor`）
- 必须包含 `README.md` 说明文件

**标准结构：**
```
任务名称/
  ├── 任务名称_v1/      # 第一版
  │   ├── README.md
  │   └── 脚本/文档
  ├── 任务名称_v2/      # 第二版
  │   ├── README.md
  │   └── 脚本/文档
  └── 任务名称_v3/      # 第三版
      ├── README.md
      └── 脚本/文档
```

**规则：**
- 每个独立任务一个总文件夹
- 每个版本一个子文件夹（`任务名_v1`, `任务名_v2`, ...）
- 新版本不覆盖旧版本，保证安全性
- 子文件夹内脚本统一命名（如 `run_workbook.py`），不带版本号后缀
- 每个子文件夹必须有 `README.md`

**已建立的任务文件夹：**
- `huggingface-dataset-extractor/` - HuggingFace 数据集元信息提取工具
  - `v1/` - 原版（串行，双 LLM 调用，API Key 硬编码）
  - `v2/` - **优化版（推荐使用）** - 串行处理，合并 LLM 调用，配置外部化 config.yaml
  - `v3/` - 并发版（多线程并发，合并 LLM，配置外部化）**⚠️ 不推荐：并发易触发 API 速率限制**

**重要决定：v2 串行版优先使用**（2026-06-26）
- 原因：并发版（v3）网络请求容易触发 429 速率限制，稳定性差
- 规则：今后默认使用 v2，除非用户明确要求并发

---

## 安全删除机制（中转站）

**建立时间：** 2026-06-26

**背景：** 使用 Remove-Item 直接删除文件不可恢复（不进回收站），曾误删 v2 的"实现逻辑说明.md"导致无法恢复。

**规则：**
- 所有删除操作必须使用 `python scripts/safe_delete.py delete <path>`
- 禁止直接使用 Remove-Item / rm 删除工作文件
- 文件压缩后移入 `trash/YYYY-MM-DD/` 保留 3 天
- 3天内用户未要求还原则自动清理
- heartbeat 负责定期清理

**优势：**
- 可恢复：3天内可随时还原
- 节省空间：ZIP 压缩（文本文件约节省 60-80%）
- 有记录：每个文件附带 .meta 元数据（原路径、删除时间、大小）

**教训：** 即使文件看起来"没用了"也不要直接删，先进中转站。

---

## 每周自动部署包推送

**建立时间：** 2026-06-26
**Cron ID：** b8729b5d-86e0-4592-92ac-c0d5b4e32772

**机制：**
- 每周日凌晨3点自动运行
- 脚本：`scripts/auto_package_push.py`
- 打包当前 workspace 配置和记忆（脱敏版）
- 推送到 GitHub 仓库 `toolbox-scripts/myagent/latest-deploy/`
- 用户在新电脑 clone 仓库后即可部署

**脱敏规则：**
- 智谱 API Key → `${ZHIPU_API_KEY}`
- LiteLLM API Key → `${API_KEY}`
- GitHub Token → `${GITHUB_TOKEN}`
- Gateway Token → `${GATEWAY_TOKEN}`

**用户在新电脑部署后必须手动修改：**
1. `config/openclaw.json` 中的 apiKey 和 gateway token
2. HuggingFace 工具的 config.yaml 中的智谱 Key
3. 运行 `gh auth login` 配置 GitHub 认证
4. 配置 Git 代理（如需要）

---

## 个人偏好

_(待补充)_

## 重要决定

### HuggingFace 数据集提取工具优化记录

**2026-06-26: 数据量级(条)字段提取优化**
- **问题：** 原逻辑只处理 list 格式的 splits，漏掉 dict 格式（HF 常见：`{"train": {"num_examples": ...}}`）
- **优化内容：**
  1. 支持 dict 格式的 splits 提取
  2. 兼容 `num_rows` 字段（部分数据集用这个而非 `num_examples`）
  3. 添加 fallback：cardData 无数据时调用 datasets-server `/info` 接口
- **测试结果：**
  - `zeta0707/clean_desk`: 82,338 条 ✓
  - `plugnplai/plugins-dataset-sample`: 96 条 ✓
- **已同步：** v2 和 v3 都已更新并 push 到 `toolbox-scripts` 仓库
