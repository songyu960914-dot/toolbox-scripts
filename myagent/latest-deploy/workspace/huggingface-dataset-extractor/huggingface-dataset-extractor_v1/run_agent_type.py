# -*- coding: utf-8 -*-
"""
HuggingFace Dataset Agent Type Classifier
通过 API metadata + README + 数据预览样本 综合判断 Agent 类型
"""
import os, sys, time, re, requests, pandas as pd
from datetime import datetime
from openai import OpenAI

# 智谱 GLM API
llm_client = OpenAI(
    base_url="https://open.bigmodel.cn/api/paas/v4",
    api_key="0f69e84c9f484b77b8c2df48967245ea.WDa8YSYqxEqKD5Ch"
)


def fetch_readme(dataset_id, max_retries=3):
    """获取数据�?README"""
    url = f'https://huggingface.co/datasets/{dataset_id}/raw/main/README.md'
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                return resp.text[:3000]
            break
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
            continue
        except:
            break
    return ''


def fetch_data_preview(dataset_id, max_retries=3):
    """获取数据集前几行预览，包括列名和样本�?""
    # 先获取可用的 config/split
    base_url = f'https://datasets-server.huggingface.co'
    
    for attempt in range(max_retries):
        try:
            # 获取第一页数�?            resp = requests.get(
                f'{base_url}/first-rows',
                params={'dataset': dataset_id, 'config': 'default', 'split': 'train'},
                timeout=30
            )
            if resp.status_code != 200:
                # 尝试获取可用配置
                info_resp = requests.get(
                    f'{base_url}/info',
                    params={'dataset': dataset_id},
                    timeout=15
                )
                if info_resp.status_code == 200:
                    info = info_resp.json()
                    dataset_info = info.get('dataset_info', {})
                    if dataset_info:
                        first_config = list(dataset_info.keys())[0]
                        splits = dataset_info[first_config].get('splits', {})
                        first_split = list(splits.keys())[0] if splits else 'train'
                    else:
                        first_config = 'default'
                        first_split = 'train'
                else:
                    first_config = 'default'
                    first_split = 'train'
                
                resp = requests.get(
                    f'{base_url}/first-rows',
                    params={'dataset': dataset_id, 'config': first_config, 'split': first_split},
                    timeout=30
                )
            
            if resp.status_code == 200:
                data = resp.json()
                rows = data.get('rows', [])
                features = data.get('features', [])
                
                # 提取列名
                col_names = [f.get('name', '') for f in features]
                
                # 提取�?行的关键字段值（截断长文本）
                sample_rows = []
                for row_data in rows[:5]:
                    row = row_data.get('row', {})
                    row_summary = {}
                    for col in col_names[:10]:  # 最多取10�?                        val = row.get(col, '')
                        val_str = str(val)
                        if len(val_str) > 200:
                            val_str = val_str[:200] + '...'
                        row_summary[col] = val_str
                    sample_rows.append(row_summary)
                
                return {
                    'columns': col_names,
                    'samples': sample_rows
                }
            break
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
            continue
        except:
            break
    return None


def llm_classify(dataset_id, readme_text, tags, card_data, task_categories, modalities, data_preview):
    """�?LLM 综合判断 Agent 类型"""
    readme_snippet = readme_text[:2000] if readme_text else '(�?README)'
    tags_str = ', '.join(tags[:30]) if tags else '(�?'
    tasks_str = ', '.join(task_categories) if task_categories else '(�?'
    modalities_str = ', '.join(modalities) if modalities else '(�?'
    
    card_desc = ''
    if isinstance(card_data, dict):
        card_desc = card_data.get('description', '') or ''
        card_desc = card_desc[:500]

    # 构建数据预览文本
    preview_text = '(无法获取)'
    if data_preview:
        cols = data_preview['columns']
        preview_text = f"列名: {', '.join(cols[:15])}\n"
        for i, sample in enumerate(data_preview['samples'][:3]):
            preview_text += f"  Row {i+1}: {sample}\n"

    prompt = f"""根据以下HuggingFace数据集的所有信息综合判断Agent类型，只返回JSON�?
数据�? {dataset_id}
Tasks: {tasks_str}
Modalities: {modalities_str}
Tags: {tags_str}
描述: {card_desc}

README摘要:
{readme_snippet[:1500]}

数据预览（实际数据内容）:
{preview_text}

---
Agent类型（五选一，严格使用以下值）�?- 代码/机器人：任务目标要求输出代码（代码生成、补全、终端操作等）或控制物理/虚拟机器�?- 多模态：数据包含图片、音频、视频等多模态内�?- 通用：纯文本任务（对话、问答、推理、搜索、浏览器操作等），不要求输出代码
- 通用混合：同时包含代码类任务和通用文本任务（如数据集中有多种category涵盖代码和非代码�?- 混合不可用：同时含代�?机器人和多模态但不含通用文本

关键判断依据�?1. 优先看数据预览中的实际内容（如category/subcategory/task列的值）
2. 看任务目标是否要求输出代�?3. 工具调用、浏览器操作等如果输出自然语言指令而非代码，归通用
4. 如果数据集同时包含代码类和通用类任务（如category有Coding也有其他），归通用混合

严格只返回JSON，值必须是上面五个之一�?{{"Agent类型":"..."}}"""

    try:
        resp = llm_client.chat.completions.create(
            model="glm-5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.1
        )
        msg = resp.choices[0].message
        content = msg.content or ''
        reasoning = getattr(msg, 'reasoning_content', '') or ''
        
        import json as json_mod
        result = None
        for text in [content, reasoning]:
            match = re.search(r'\{[^{}]*Agent[^{}]*\}', text)
            if match:
                try:
                    result = json_mod.loads(match.group())
                    break
                except:
                    continue
        
        if not result:
            try:
                result = json_mod.loads(content)
            except:
                return None
        
        agent_type = result.get('Agent\u7c7b\u578b', '') or result.get('Agent类型', '')
        
        valid_agent = ['代码/机器�?, '多模�?, '通用', '通用混合', '混合不可�?]
        for std_val in valid_agent:
            if std_val in agent_type:
                return std_val
        return '通用'
    except Exception as e:
        print(f' [LLM error: {e}]', end='')
        return None


def extract_basic(tags, card_data):
    """从tags和cardData提取基本分类信息"""
    if not isinstance(card_data, dict):
        card_data = {}
    
    # task_categories
    from_tags = [t.split(':')[1] for t in (tags or []) if t.startswith('task_categories:')]
    from_card = card_data.get('task_categories', []) or []
    if isinstance(from_card, str):
        from_card = [from_card]
    task_categories = list(set(from_tags + from_card))
    
    # modalities
    from_tags = [t.split(':')[1] for t in (tags or []) if t.startswith('modality:')]
    from_card = card_data.get('modality', []) or []
    if isinstance(from_card, str):
        from_card = [from_card]
    modalities = list(set(from_tags + from_card))
    
    return task_categories, modalities


if __name__ == '__main__':
    desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')

    if len(sys.argv) > 1:
        filename = sys.argv[1].strip()
    else:
        print('请输入桌面上�?Excel 文件名（�?.xlsx 后缀�?)
        filename = input('> ').strip()

    if not filename.endswith('.xlsx'):
        filename = filename + '.xlsx'

    input_path = os.path.join(desktop, filename)
    if not os.path.exists(input_path):
        print(f'错误: 文件不存�?- {input_path}')
        exit(1)

    df = pd.read_excel(input_path, engine='openpyxl')
    print(f'Loaded {len(df)} rows')

    results = []
    errors = []
    for idx, row in df.iterrows():
        seq = row.iloc[0]
        url = str(row.iloc[1]).strip()
        dataset_id = url.replace('https://huggingface.co/datasets/', '')
        print(f'  [{idx+1}/{len(df)}] {dataset_id}', end='')
        
        api_url = f'https://huggingface.co/api/datasets/{dataset_id}'
        try:
            # 1. 获取 API 元数�?            resp = requests.get(api_url, timeout=30)
            if resp.status_code != 200:
                print(f' ERROR: HTTP {resp.status_code}')
                errors.append(f'{dataset_id}: HTTP {resp.status_code}')
                results.append({'序号': seq, 'URL': url, 'Agent类型': '/'})
                time.sleep(1.0)
                continue
            
            api_data = resp.json()
            tags = api_data.get('tags', []) or []
            card_data = api_data.get('cardData', {})
            if not isinstance(card_data, dict):
                card_data = {}
            
            task_categories, modalities = extract_basic(tags, card_data)
            
            # 2. 获取 README
            readme_text = fetch_readme(dataset_id)
            
            # 3. 获取数据预览
            data_preview = fetch_data_preview(dataset_id)
            
            # 4. LLM 判断
            agent_type = llm_classify(
                dataset_id, readme_text, tags, card_data,
                task_categories, modalities, data_preview
            )
            if agent_type is None:
                agent_type = '通用'
            
            results.append({'序号': seq, 'URL': url, 'Agent类型': agent_type})
            print(f' -> {agent_type}')
            
        except Exception as e:
            print(f' ERROR: {e}')
            errors.append(f'{dataset_id}: {e}')
            results.append({'序号': seq, 'URL': url, 'Agent类型': '/'})
        
        time.sleep(1.0)

    output_df = pd.DataFrame(results)
    ts = datetime.now().strftime('%H%M%S')
    output_filename = f'agent_type_{ts}.xlsx'
    output_path = os.path.join(desktop, output_filename)
    output_df.to_excel(output_path, index=False, engine='openpyxl')
    print(f'\n{"="*60}')
    print(f'Done! Saved to: {output_filename}')
    print(f'Total: {len(results)} rows, {len(errors)} errors')
    if errors:
        print(f'\nErrors:')
        for e in errors:
            print(f'  - {e}')
    print(f'{"="*60}')

