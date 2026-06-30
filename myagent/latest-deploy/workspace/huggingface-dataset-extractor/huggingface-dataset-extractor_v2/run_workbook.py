# -*- coding: utf-8 -*-
"""
HuggingFace Dataset Metadata Extractor - Serial Version (v2)
串行版：逐条处理 + 配置外部化
无 LLM 调用版本，只提取 HuggingFace API 可直接获取的字段。
"""
import os, sys, time, re, requests, pandas as pd, yaml, json
from datetime import datetime


def load_config():
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config


config = load_config()
req_config = config['requests']


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


def check_content_warning(api_data, tags, readme_text, card_data):
    """检测内容警告"""
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


def extract_info(seq, url, dataset_id, api_data, readme_text):
    """提取完整信息（无 LLM）"""
    result = {
        '序号': seq, 'URL': url,
        '发布/更新时间': '/', '数据量级（条）': '/', '量级等级（条）': '/',
        '数据大小（GB）': '/', '下载量': '/', '点赞量': '/',
        'Tags': '/', 'Tasks': '/', 'License': '/',
        '数据类型（文件类型）': '/', '数据格式': '/', '语种': '/',
        '是否有论文': '/', '论文arXivURL': '/', '是否有测试集': '/',
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

    # 数据大小（直接用主 API 的 usedStorage）
    file_size = api_data.get('usedStorage')
    # fallback: cardData.download_size
    if not file_size or file_size <= 0:
        file_size = card_data.get('download_size')
    # fallback: dataset_info 中的 download_size
    if not file_size or file_size <= 0:
        total_ds = 0
        for di in dataset_info_list:
            ds = di.get('download_size')
            if ds:
                total_ds += ds
        if total_ds > 0:
            file_size = total_ds
    if file_size and file_size > 0:
        try:
            gb_val = file_size / (1024 ** 3)
            result['数据大小（GB）'] = round(gb_val, 6)
        except:
            pass

    # 数据量级
    num_examples_total = 0
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
        elif isinstance(splits_info, dict):
            for split_name in splits_info.keys():
                if 'test' in split_name.lower():
                    has_test = True
                    break
        if has_test:
            break
    result['是否有测试集'] = '是' if has_test else '/'

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

    # 支持完整路径或仅文件名
    if os.path.isabs(filename) or os.path.exists(filename):
        input_path = filename
    else:
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
    sleep_interval = req_config.get('sleep_between_items', 3)
    for idx, row in df.iterrows():
        seq = row.iloc[0]
        url = str(row.iloc[1]).strip()
        info, error = process_dataset(idx, total, seq, url)
        results.append(info)
        if error:
            errors.append(error)
        if idx < total - 1:
            time.sleep(sleep_interval)

    elapsed = time.time() - start_time

    output_df = pd.DataFrame(results)
    ts = datetime.now().strftime('%H%M%S')
    output_filename = f'dataset_result_{ts}.xlsx'
    # 输出到脚本所在目录的 output/ 文件夹
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_filename)
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
