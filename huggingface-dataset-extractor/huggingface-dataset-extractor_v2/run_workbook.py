# -*- coding: utf-8 -*-
"""
HuggingFace Dataset Metadata Extractor - Serial Version (v2)
串行版：逐条处理 + 合并 LLM 调用 + 配置外部化
推荐使用版本，避免并发导致的 API 速率限制问题。
"""
import os, sys, time, re, requests, pandas as pd, yaml, json
from datetime import datetime
from openai import OpenAI


def load_config():
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    api_key = config['llm']['api_key']
    if api_key.startswith('${') and api_key.endswith('}'):
        env_var = api_key[2:-1]
        api_key = os.environ.get(env_var, api_key)
    
    return config, api_key


config, api_key = load_config()
llm_config = config['llm']
req_config = config['requests']

# LLM 客户端
llm_client = OpenAI(
    base_url=llm_config['base_url'],
    api_key=api_key
)


def extract_from_tags(tags, prefix):
    """从 tags 数组中提取指定前缀的值"""
    results = []
    if not tags:
        return results
    for tag in tags:
        if tag.startswith(prefix + ':'):
            results.append(tag[len(prefix)+1:])
    return results


def safe_list(val):
    """确保返回列表"""
    if val is None:
        return []
    if isinstance(val, list):
        return val
    return [val]


def merge_unique(*lists):
    """合并多个列表并去重，保持顺序"""
    seen = set()
    result = []
    for lst in lists:
        for item in lst:
            item_str = str(item).strip()
            if item_str and item_str.lower() not in seen:
                seen.add(item_str.lower())
                result.append(item_str)
    return result


def fetch_readme(dataset_id):
    """获取 README（带重试）"""
    url = f'https://huggingface.co/datasets/{dataset_id}/raw/main/README.md'
    max_retries = req_config['retry_max']
    
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=req_config['timeout'])
            if resp.status_code == 200:
                return resp.text[:config['readme']['max_length']]
            break
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            if attempt < max_retries - 1:
                time.sleep(req_config['retry_interval'] * (attempt + 1))
            continue
        except:
            break
    return ''


def fetch_data_preview(dataset_id):
    """获取数据集前几行预览，包括列名和样本值"""
    base_url = 'https://datasets-server.huggingface.co'
    max_retries = req_config['retry_max']
    
    for attempt in range(max_retries):
        try:
            resp = requests.get(
                f'{base_url}/first-rows',
                params={'dataset': dataset_id, 'config': 'default', 'split': 'train'},
                timeout=req_config['timeout']
            )
            if resp.status_code != 200:
                # 尝试获取正确的 config/split
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
                        first_config, first_split = 'default', 'train'
                else:
                    first_config, first_split = 'default', 'train'
                
                resp = requests.get(
                    f'{base_url}/first-rows',
                    params={'dataset': dataset_id, 'config': first_config, 'split': first_split},
                    timeout=req_config['timeout']
                )
            
            if resp.status_code == 200:
                data = resp.json()
                rows = data.get('rows', [])
                features = data.get('features', [])
                
                col_names = [f.get('name', '') for f in features]
                sample_rows = []
                max_cols = config['data_preview']['max_columns']
                max_len = config['data_preview']['max_cell_length']
                max_rows = config['data_preview']['max_rows']
                
                for row_data in rows[:max_rows]:
                    row = row_data.get('row', {})
                    row_summary = {}
                    for col in col_names[:max_cols]:
                        val = row.get(col, '')
                        val_str = str(val)
                        if len(val_str) > max_len:
                            val_str = val_str[:max_len] + '...'
                        row_summary[col] = val_str
                    sample_rows.append(row_summary)
                
                return {'columns': col_names, 'samples': sample_rows}
            break
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            if attempt < max_retries - 1:
                time.sleep(req_config['retry_interval'] * (attempt + 1))
            continue
        except:
            break
    return None


def check_content_warning(api_data, tags, readme_text, card_data):
    """检测内容警告（排除作者呼吁式语句）"""
    all_text = readme_text if readme_text else ''
    if isinstance(card_data, dict):
        desc = card_data.get('description', '') or ''
        all_text += ' ' + desc
    
    warning_patterns = [
        (r'(contain|include|有|包含).{0,30}(harmful|offensive|有害|冒犯)', 'contains_harmful'),
        (r'(pornograph|sexually explicit|nsfw|色情|成人内容)', 'adult_content'),
        (r'benchmark.{0,50}(harmful|offensive|有害|冒犯)', 'harmful_in_benchmark'),
    ]
    
    exclude_patterns = [
        r'(should not|must not|do not|请勿|不应|禁止).{0,30}(use|使用|用于)',
        r'(responsibility|负责|responsible)',
        r'(recommend|建议|suggest)',
    ]
    
    all_text_lower = all_text.lower()
    nsfw_tags = {'not-for-all-audiences', 'nsfw', 'adult', '18+'}
    has_nsfw_tag = any(tag.lower() in nsfw_tags for tag in tags)
    
    found_sentences = []
    if has_nsfw_tag:
        found_sentences.append(f'标签含: {", ".join(t for t in tags if t.lower() in nsfw_tags)}')
    
    sentences = re.split(r'[.。\n]', all_text)
    for pattern, pattern_type in warning_patterns:
        if re.search(pattern, all_text_lower):
            for sent in sentences:
                sent_lower = sent.lower()
                if re.search(pattern, sent_lower):
                    is_excluded = any(re.search(excl, sent_lower) for excl in exclude_patterns)
                    if not is_excluded and len(sent.strip()) > 10:
                        found_sentences.append(sent.strip()[:250])
                        break
    
    if found_sentences:
        unique = list(dict.fromkeys(found_sentences))
        return '是', '; '.join(unique[:3])
    return '否', '/'


def llm_classify_combined(dataset_id, readme_text, tags, card_data, task_categories, modalities, data_preview):
    """合并 LLM 调用：同时判断榜单类型和 Agent 类型"""
    readme_empty = not readme_text or len(readme_text.strip().replace('---', '').strip()) < 50
    preview_empty = data_preview is None or len(data_preview.get('samples', [])) == 0
    
    if readme_empty and preview_empty:
        return '非榜单', '/', '/', '/'
    
    tags_lower = [str(t).lower() for t in tags]
    has_robotics = any('robot' in t for t in tags_lower)
    has_multimodal_tag = any(t in ['multimodal', 'image', 'audio', 'video'] for t in tags_lower) or \
                          any(t.startswith('modality:') and any(m in t for m in ['image', 'audio', 'video']) for t in tags_lower)
    
    readme_snippet = readme_text[:1500] if readme_text else '(无 README)'
    tags_str = ', '.join(tags[:30]) if tags else '(无)'
    tasks_str = ', '.join(task_categories) if task_categories else '(无)'
    modalities_str = ', '.join(modalities) if modalities else '(无)'
    
    card_desc = ''
    if isinstance(card_data, dict):
        card_desc = card_data.get('description', '') or ''
        card_desc = card_desc[:500]

    preview_text = '(无法获取)'
    if data_preview:
        cols = data_preview['columns']
        preview_text = f"列名: {', '.join(cols[:15])}\n"
        for i, sample in enumerate(data_preview['samples'][:3]):
            preview_text += f"  Row {i+1}: {sample}\n"

    prompt = f"""根据以下HuggingFace数据集信息，同时判断两个分类，只返回JSON：

数据集: {dataset_id}
Tasks: {tasks_str}
Modalities: {modalities_str}
Tags: {tags_str}
描述: {card_desc}

README摘要:
{readme_snippet}

数据预览:
{preview_text}

---
请判断：

1. **榜单类型**（四选一）：
- benchmark榜单: 数据集本身是benchmark/测评基准
- 名字含bench类: 仓库名含bench但README为空
- 其他榜单: 包含评测内容但不是标准benchmark
- 非榜单: 训练数据

2. **Agent类型**（六选一）：
- 代码/机器人: 输出代码或控制机器人（代码+机器人算一个标签）
- 多模态: 每条数据都包含图片/音频/视频
- 通用: 纯文本任务
- 混合可用: 包含两种或以上不同类别
- 混合不可用: 代码/机器人 + 多模态，缺乏通用数据
- 其他: 信息不足
- /: 无法获取信息

返回JSON格式：
{{
  "榜单类型": "...",
  "榜单原句": "...",
  "Agent类型": "...",
  "混合说明": "..."
}}

榜单原句：如果是benchmark/其他榜单，提取关键词原句（最多200字符）；否则填"/"
混合说明：非混合类型填"/"，混合类型注明具体组合"""

    try:
        resp = llm_client.chat.completions.create(
            model=llm_config['model'],
            messages=[{"role": "user", "content": prompt}],
            max_tokens=llm_config['max_tokens'],
            temperature=llm_config['temperature']
        )
        msg = resp.choices[0].message
        content = msg.content or ''
        reasoning = getattr(msg, 'reasoning_content', '') or ''
        
        result = None
        for text in [content, reasoning]:
            matches = [
                re.search(r'\{[^{}]*榜单[^{}]*Agent[^{}]*\}', text),
                re.search(r'\{.*?"榜单类型".*?"Agent类型".*?\}', text, re.DOTALL),
            ]
            for match in matches:
                if match:
                    try:
                        result = json.loads(match.group())
                        break
                    except:
                        continue
            if result:
                break
        
        if not result:
            if has_robotics and has_multimodal_tag:
                return '非榜单', '/', '混合不可用', '代码/机器人+多模态'
            return '非榜单', '/', '其他', '/'
        
        benchmark_type = result.get('榜单类型', '')
        benchmark_sentence = result.get('榜单原句', '') or '/'
        agent_type = result.get('Agent类型', '')
        mix_detail = result.get('混合说明', '') or '/'
        
        valid_benchmark = ['benchmark榜单', '名字含bench类', '其他榜单', '非榜单']
        valid_agent = ['代码/机器人', '多模态', '通用', '混合可用', '混合不可用', '其他', '/']
        
        matched_benchmark = '非榜单'
        for std in valid_benchmark:
            if std in benchmark_type:
                matched_benchmark = std
                break
        
        matched_agent = '其他'
        for std in valid_agent:
            if std in agent_type:
                matched_agent = std
                break
        
        if has_robotics and has_multimodal_tag:
            matched_agent = '混合不可用'
            mix_detail = '代码/机器人+多模态'
        
        if matched_agent not in ['混合可用', '混合不可用']:
            mix_detail = '/'
        
        return matched_benchmark, benchmark_sentence, matched_agent, mix_detail
        
    except Exception as e:
        print(f' [LLM error: {e}]', end='')
        if has_robotics and has_multimodal_tag:
            return '非榜单', '/', '混合不可用', '代码/机器人+多模态'
        return '非榜单', '/', '其他', '/'


def extract_info(seq, url, dataset_id, api_data, readme_text):
    """提取完整信息"""
    result = {
        '序号': seq, 'URL': url,
        '发布/更新时间': '/', '数据量级（条）': '/', '量级等级（条）': '/',
        '数据大小（GB）': '/', '下载量': '/', '点赞量': '/',
        'Tags': '/', 'Tasks': '/', 'License': '/',
        '数据类型（文件类型）': '/', '数据格式': '/', '语种': '/',
        '是否有论文': '/', '论文arXivURL': '/', '是否有测试集': '/',
        '榜单类型': '/', '榜单关键词原句': '/',
        'Agent类型': '/', '混合说明': '/',
        '是否有警告': '/', '警告原因': '/',
    }
    if not api_data:
        return result

    # 基本信息
    last_modified = api_data.get('lastModified', '')
    if last_modified:
        try:
            dt = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
            result['发布/更新时间'] = dt.strftime('%Y-%m-%d')
        except:
            result['发布/更新时间'] = last_modified[:10] if len(last_modified) >= 10 else '/'

    downloads = api_data.get('downloads')
    if downloads is not None:
        result['下载量'] = downloads

    likes = api_data.get('likes')
    if likes is not None:
        result['点赞量'] = likes

    tags = api_data.get('tags', []) or []
    card_data = api_data.get('cardData')
    if not isinstance(card_data, dict):
        card_data = {}

    dataset_info = card_data.get('dataset_info', {})
    if isinstance(dataset_info, dict):
        dataset_info_list = [dataset_info]
    elif isinstance(dataset_info, list):
        dataset_info_list = [di for di in dataset_info if isinstance(di, dict)]
    else:
        dataset_info_list = []

    # 双源字段提取（tags + cardData 去重合并）
    from_tags = extract_from_tags(tags, 'license')
    from_card = safe_list(card_data.get('license'))
    merged = merge_unique(from_tags, from_card)
    if merged:
        result['License'] = ','.join(merged)

    from_tags = extract_from_tags(tags, 'task_categories')
    from_card = safe_list(card_data.get('task_categories'))
    task_categories = merge_unique(from_tags, from_card)
    if task_categories:
        result['Tasks'] = ','.join(task_categories)

    from_tags = extract_from_tags(tags, 'size_categories')
    from_card = safe_list(card_data.get('size_categories'))
    merged = merge_unique(from_tags, from_card)
    if merged:
        result['量级等级（条）'] = ','.join(merged)

    from_tags = extract_from_tags(tags, 'modality')
    from_card = safe_list(card_data.get('modality'))
    modalities = merge_unique(from_tags, from_card)
    if modalities:
        result['数据类型（文件类型）'] = ','.join(modalities)

    from_tags = extract_from_tags(tags, 'format')
    from_card = safe_list(card_data.get('format'))
    merged = merge_unique(from_tags, from_card)
    if merged:
        result['数据格式'] = ','.join(merged)

    from_tags = extract_from_tags(tags, 'language')
    from_card = safe_list(card_data.get('language'))
    merged = merge_unique(from_tags, from_card)
    if merged:
        result['语种'] = ','.join(merged)

    custom_from_tags = [t for t in tags if ':' not in t]
    custom_from_card = safe_list(card_data.get('tags'))
    merged = merge_unique(custom_from_tags, custom_from_card)
    if merged:
        result['Tags'] = ','.join(merged)

    # 数据大小
    download_size = card_data.get('download_size')
    if download_size is None:
        for di in dataset_info_list:
            ds = di.get('download_size')
            if ds:
                download_size = (download_size or 0) + ds
    if download_size is not None and download_size > 0:
        try:
            result['数据大小（GB）'] = round(download_size / (1024 ** 3), 4)
        except:
            pass

    # 数据量级
    num_examples_total = 0
    # 来源1: cardData.dataset_info.splits（支持 list 和 dict 两种格式）
    for di in dataset_info_list:
        splits_info = di.get('splits', {})
        if isinstance(splits_info, list):
            for s in splits_info:
                if isinstance(s, dict):
                    n = s.get('num_examples') or s.get('num_rows') or 0
                    num_examples_total += int(n)
        elif isinstance(splits_info, dict):
            for split_name, split_val in splits_info.items():
                if isinstance(split_val, dict):
                    n = split_val.get('num_examples') or split_val.get('num_rows') or 0
                    num_examples_total += int(n)
                elif isinstance(split_val, (int, float)):
                    num_examples_total += int(split_val)

    # 来源2: datasets-server /info 接口（cardData 拿不到时 fallback）
    if num_examples_total == 0:
        try:
            info_resp = requests.get(
                'https://datasets-server.huggingface.co/info',
                params={'dataset': dataset_id},
                timeout=15
            )
            if info_resp.status_code == 200:
                server_info = info_resp.json().get('dataset_info', {})
                for config_name, config_val in server_info.items():
                    if not isinstance(config_val, dict):
                        continue
                    splits_dict = config_val.get('splits', {})
                    if isinstance(splits_dict, dict):
                        for sp_name, sp_val in splits_dict.items():
                            if isinstance(sp_val, dict):
                                n = sp_val.get('num_examples') or sp_val.get('num_rows') or 0
                                num_examples_total += int(n)
        except:
            pass

    if num_examples_total > 0:
        result['数据量级（条）'] = num_examples_total

    # 论文
    arxiv_ids = extract_from_tags(tags, 'arxiv')
    card_arxiv = safe_list(card_data.get('arxiv'))
    all_arxiv = merge_unique(arxiv_ids, card_arxiv)
    if all_arxiv:
        result['是否有论文'] = '是'
        urls = [f'https://arxiv.org/abs/{aid}' for aid in all_arxiv]
        result['论文arXivURL'] = ','.join(urls)
    else:
        result['是否有论文'] = '否'

    # 测试集
    has_test = False
    for di in dataset_info_list:
        splits_info = di.get('splits', [])
        if isinstance(splits_info, list):
            for s in splits_info:
                if isinstance(s, dict) and 'test' in s.get('name', '').lower():
                    has_test = True
                    break
        if has_test:
            break
    result['是否有测试集'] = '是' if has_test else '/'

    # 榜单 + Agent（合并 LLM 调用）
    data_preview = fetch_data_preview(dataset_id)
    benchmark_type, benchmark_sentence, agent_type, mix_detail = llm_classify_combined(
        dataset_id, readme_text, tags, card_data, task_categories, modalities, data_preview
    )
    result['榜单类型'] = benchmark_type
    result['榜单关键词原句'] = benchmark_sentence
    result['Agent类型'] = agent_type
    result['混合说明'] = mix_detail

    # 内容安全
    has_warning, warning_reason = check_content_warning(api_data, tags, readme_text, card_data)
    result['是否有警告'] = has_warning
    result['警告原因'] = warning_reason

    return result


def process_dataset(idx, total, seq, url):
    """处理单个数据集"""
    dataset_id = url.replace('https://huggingface.co/datasets/', '')
    
    print(f'  [{idx+1}/{total}] {dataset_id}', end='', flush=True)
    
    api_url = f'https://huggingface.co/api/datasets/{dataset_id}'
    try:
        resp = requests.get(api_url, timeout=req_config['timeout'])
        if resp.status_code == 200:
            api_data = resp.json()
            readme_text = fetch_readme(dataset_id)
            info = extract_info(seq, url, dataset_id, api_data, readme_text)
            print(' OK', flush=True)
            return info, None
        else:
            print(f' ERROR: HTTP {resp.status_code}', flush=True)
            return extract_info(seq, url, dataset_id, None, ''), f'{dataset_id}: HTTP {resp.status_code}'
    except Exception as e:
        print(f' ERROR: {e}', flush=True)
        return extract_info(seq, url, dataset_id, None, ''), f'{dataset_id}: {e}'


if __name__ == '__main__':
    desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')

    if len(sys.argv) > 1:
        filename = sys.argv[1].strip()
    else:
        print('请输入桌面上的 Excel 文件名（含 .xlsx 后缀）')
        filename = input('> ').strip()

    if not filename.endswith('.xlsx'):
        filename = filename + '.xlsx'

    input_path = os.path.join(desktop, filename)
    if not os.path.exists(input_path):
        print(f'错误: 文件不存在 - {input_path}')
        exit(1)

    df = pd.read_excel(input_path, engine='openpyxl')
    total = len(df)
    print(f'Loaded {total} rows')

    start_time = time.time()
    results = []
    errors = []

    # 串行处理
    sleep_interval = req_config.get('sleep_between_items', 1.5)
    for idx, row in df.iterrows():
        seq = row.iloc[0]
        url = str(row.iloc[1]).strip()
        info, error = process_dataset(idx, total, seq, url)
        results.append(info)
        if error:
            errors.append(error)
        # 间隔控制，避免触发速率限制
        if idx < total - 1:
            time.sleep(sleep_interval)

    elapsed = time.time() - start_time

    output_df = pd.DataFrame(results)
    ts = datetime.now().strftime('%H%M%S')
    output_filename = f'dataset_result_{ts}.xlsx'
    output_path = os.path.join(desktop, output_filename)
    output_df.to_excel(output_path, index=False, engine='openpyxl')
    
    print(f'\n{"="*60}')
    print(f'Done! Saved to: {output_filename}')
    print(f'Total: {len(results)} rows, {len(errors)} errors')
    print(f'Time: {elapsed:.1f}s (avg {elapsed/total:.1f}s/item)')
    if errors:
        print(f'\nErrors:')
        for e in errors:
            print(f'  - {e}')
    print(f'{"="*60}')
