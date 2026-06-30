# 数据集元信息提取工具

从 HuggingFace / ModelScope / Kaggle 批量抓取数据集元信息，保存到 Excel。

## 目录结构

- `huggingface-dataset-extractor_v2/` - HuggingFace 版本（推荐，无 LLM）
- `modelscope/` - ModelScope 版本
- `kaggle/` - Kaggle 版本

## 使用方式

### HuggingFace

```bash
cd huggingface-dataset-extractor_v2
python run_workbook.py 工作簿1.xlsx
```

### ModelScope

```bash
cd modelscope
python run_modelscope.py 工作簿1.xlsx
```

### Kaggle

需要配置 API Key（可选，无认证可能被拒绝）：

```bash
export KAGGLE_USERNAME=your_username
export KAGGLE_KEY=your_api_key

cd kaggle
python run_kaggle.py 工作簿1.xlsx
```

## 输出

所有结果保存在各自的 `output/` 目录下，文件名格式：`{platform}_result_{HHMMSS}.xlsx`

## 配置

`config.yaml` 控制：
- 请求超时和重试
- Sleep 间隔（避免速率限制）
- README 最大长度

## 字段说明

- 发布/更新时间
- 数据量级（条）
- 数据大小（GB）
- 下载量、点赞量
- Tags、Tasks、License
- 数据类型、数据格式、语种
- 是否有论文、论文URL
- 是否有测试集
- 是否有警告、警告原因

## 注意事项

- HuggingFace: 无需 API Key，直接调用公开 API
- ModelScope: API 结构需根据实际文档调整（脚本为框架）
- Kaggle: 建议配置 API Key，否则可能被拒绝访问
- 所有版本均为串行处理，避免触发速率限制
