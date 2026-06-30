# -*- coding: utf-8 -*-
"""
ModelScope Dataset Metadata Extractor
串行版：逐条处理 + 配置外部化
基于 ModelScope API 提取数据集元信息。
"""
import os, sys, time, re, requests, pandas as pd, yaml
from datetime import datetime


def load_config():
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config


config = load_config()
req_config = config['requests']


def extract_info(seq, url, dataset_id, api_data):
    """提取完整信息"""
    result = {
        '序号': seq, 'URL': url,
        '发布/更新时间': '/', '数据量级（条）': '/', '量级等级（条）': '/',
        '数据大小（GB）': '/', '下载量': '/', '点赞量': '/',
        'Tags': '/', 'Tasks': '/', 'License': '/',
        '数据类型（文件类型）': '/', '数据格式': '/', '语种': '/',
        '是否有论文': '/', '论文URL': '/', '是否有测试集': '/',
        '是否有警告': '/', '警告原因': '/',
    }
    if not api_data:
        return result

    # ModelScope API 返回结构：{"Code": 200, "Data": {...}}
    data = api_data.get('Data', {})
    
    # 基本信息
    # GmtCreate: "2024-09-24"
    gmt_create = data.get('GmtCreate')
    if gmt_create:
        result['发布/更新时间'] = gmt_create[:10] if len(gmt_create) >= 10 else gmt_create
    
    # LastUpdatedTime: "179947258"（时间戳）或 GmtModified
    last_updated = data.get('GmtModified') or data.get('LastUpdatedTime')
    if last_updated and not gmt_create:
        try:
            if isinstance(last_updated, (int, str)) and str(last_updated).isdigit():
                dt = datetime.fromtimestamp(int(last_updated) / 1000)
                result['发布/更新时间'] = dt.strftime('%Y-%m-%d')
            else:
                result['发布/更新时间'] = str(last_updated)[:10]
        except:
            pass

    # Downloads: 7256
    downloads = data.get('Downloads')
    if downloads is not None:
        result['下载量'] = downloads

    # Likes: 2
    likes = data.get('Likes')
    if likes is not None:
        result['点赞量'] = likes

    # UserDefineTags: "evaluation, code, java, code-translation, agentic, benchmark"
    user_tags = data.get('UserDefineTags', '')
    if user_tags:
        result['Tags'] = user_tags

    # License: "apache-2.0"
    license_info = data.get('License')
    if license_info:
        result['License'] = license_info

    # StorageSize: 151947644 (bytes)
    storage_size = data.get('StorageSize')
    if storage_size and storage_size > 0:
        try:
            gb_val = storage_size / (1024 ** 3)
            result['数据大小（GB）'] = round(gb_val, 6)
        except:
            pass

    # DatasetCount: null (可能表示数据量级)
    dataset_count = data.get('DatasetCount')
    if dataset_count:
        result['数据量级（条）'] = dataset_count

    return result


def process_dataset(idx, total, seq, url):
    """处理单个数据集"""
    # ModelScope URL 格式: https://modelscope.cn/datasets/{user}/{dataset}
    # 或 https://www.modelscope.cn/datasets/{user}/{dataset}
    match = re.search(r'modelscope\.cn/datasets/(.+?)$', url)
    if not match:
        print(f'  [{idx+1}/{total}] {url} ERROR: Invalid URL format', flush=True)
        return extract_info(seq, url, '', None), f'{url}: Invalid URL format'
    
    dataset_id = match.group(1)
    print(f'  [{idx+1}/{total}] {dataset_id}', end='', flush=True)
    
    # ModelScope API endpoint (根据实际文档调整)
    api_url = f'https://modelscope.cn/api/v1/datasets/{dataset_id}'
    
    try:
        resp = requests.get(api_url, timeout=req_config['timeout'])
        if resp.status_code == 200:
            api_data = resp.json()
            info = extract_info(seq, url, dataset_id, api_data)
            print(' OK', flush=True)
            return info, None
        else:
            print(f' ERROR: HTTP {resp.status_code}', flush=True)
            return extract_info(seq, url, dataset_id, None), f'{dataset_id}: HTTP {resp.status_code}'
    except Exception as e:
        print(f' ERROR: {e}', flush=True)
        return extract_info(seq, url, dataset_id, None), f'{dataset_id}: {e}'


if __name__ == '__main__':
    if len(sys.argv) > 1:
        filename = sys.argv[1].strip()
    else:
        print('请输入 Excel 文件路径（或文件名）')
        filename = input('> ').strip()

    if not filename.endswith('.xlsx'):
        filename = filename + '.xlsx'

    # 支持完整路径或仅文件名（仅文件名时假设在桌面）
    if os.path.isabs(filename) or os.path.exists(filename):
        input_path = filename
    else:
        desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
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
    output_filename = f'modelscope_result_{ts}.xlsx'
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_filename)
    output_df.to_excel(output_path, index=False, engine='openpyxl')
    
    print(f'\n{"="*60}')
    print(f'Done! Saved to: {output_path}')
    print(f'Total: {len(results)} rows, {len(errors)} errors')
    print(f'Time: {elapsed:.1f}s (avg {elapsed/total:.1f}s/item)')
    if errors:
        print(f'\nErrors:')
        for e in errors:
            print(f'  - {e}')
    print(f'{"="*60}')
