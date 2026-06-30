# 工资计算工具 v2

从揽投人员数据总表中筛选平舆人员数据，自动填充到自有揽投员核算表和外包人员核算表中。

## 功能特性

- **两种运行模式**
  - 模式1：使用内置模板（人员无变动时）
  - 模式2：使用自定义文件（人员有变动时）

- **负责人-下属关系汇总**
  - 支持手动输入或从 Excel 导入
  - 自动将下属数据加总到负责人
  - 生成汇总明细表（含多级表头）

- **两种界面**
  - GUI 版本：图形界面，双击打开，适合不熟悉命令行的用户
  - 命令行版本：支持拖拽、管道输入，适合自动化场景

## 文件说明

- `generate_v2.py` — 命令行版本生成器（内嵌模板 base64）
- `generate_v2_gui.py` — GUI 版本生成器（内嵌模板 base64）
- `run_salary_v2.py` — 命令行版本运行脚本
- `run_salary_v2_gui.py` — GUI 版本运行脚本

## 打包

需要先生成内嵌 base64 模板文件（`own_template_b64.txt` 和 `outsource_template_b64.txt`），然后运行生成器：

```bash
python generate_v2.py
python generate_v2_gui.py
```

打包成 exe：

```bash
# 命令行版
pyinstaller --onefile --console --name "工资计算工具v2" run_salary_v2.py

# GUI 版
pyinstaller --onefile --windowed --name "工资计算工具v2-GUI" run_salary_v2_gui.py
```

## 使用方式

### GUI 版本（推荐）

1. 双击 `工资计算工具v2-GUI.exe`
2. 选择运行模式（内置模板 / 自定义文件）
3. 点击"浏览"按钮选择文件
4. 可选：配置负责人-下属关系
5. 点击"开始计算"
6. 计算完成后自动打开输出文件夹

### 命令行版本

```bash
# 模式1：使用内置模板
工资计算工具v2.exe <总文件.xlsx>

# 模式2：使用自定义文件
工资计算工具v2.exe <总文件.xlsx> <自有表.xlsx> <外包表.xlsx>

# 或拖拽总文件到 exe 上
```

## 输出文件

输出到桌面 `工资计算结果` 文件夹：

- 自有揽投员核算表标快.xlsx
- 外包人员标快计件薪酬核算表.xlsx
- 负责人汇总明细表.xlsx（配置了负责人关系时生成）

## 技术细节

- 总表筛选条件：单位列 = "平舆"
- 自有表列映射：总表第 7-42 列 → 模板数据列
- 外包表列映射：自定义规则（见 `COLUMN_MAPPING_RULES`）
- 负责人汇总明细表表头：自动从总文件第 2-5 行合并多级表头
- 表头行高 60，自动换行，居中对齐

## 依赖

- pandas
- openpyxl
- tkinter（GUI 版，Python 自带）
