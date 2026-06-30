# -*- coding: utf-8 -*-
"""
Kaggle Dataset Metadata Extractor
串行版：逐条处理 + 配置外部化
基于 Kaggle API 提取数据集元信息。
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

    # Kaggle API 返回结构（实测）
    
    # 更新时间: lastUpdated / createdDate
    last_updated = api_data.get('lastUpdated')
    if last_updated:
        result['发布/更新时间'] = last_updated[:10]
    else:
        created_date = api_data.get('createdDate')
        if created_date:
            result['发布/更新时间'] = created_date[:10]

    # 下载量: downloadCount
    downloads = api_data.get('downloadCount')
    if downloads is not None:
        result['下载量'] = downloads

    # 点赞量: voteCount
    votes = api_data.get('voteCount')
    if votes is not None:
        result['点赞量'] = votes

    # License: licenseNameNullable / licenseName
    license_name = api_data.get('licenseNameNullable') or api_data.get('licenseName')
    if license_name:
        result['License'] = license_name

    # 数据大小: totalBytesNullable / totalBytes
    total_bytes = api_data.get('totalBytesNullable') or api_data.get('totalBytes')
    if total_bytes and total_bytes > 0:
        try:
            gb_val = total_bytes / (1024 ** 3)
            result['数据大小（GB）'] = round(gb_val, 6)
        except:
            pass

    # Tags: tags 数组，每个元素有 name / nameNullable / fullPathNullable
    tags_list = api_data.get('tags', [])
    if tags_list:
        tag_names = []
        for t in tags_list:
            if isinstance(t, dict):
                name = t.get('nameNullable') or t.get('name', '')
                if name:
                    tag_names.append(name)
            elif isinstance(t, str):
                tag_names.append(t)
        if tag_names:
            result['Tags'] = ','.join(tag_names)

    # 数据格式 / 文件类型: 从 files 列表推断
    files_info = api_data.get('files', [])
    if files_info:
        extensions = set()
        for f in files_info:
            if isinstance(f, dict):
                fname = f.get('name', '')
            elif isinstance(f, str):
                fname = f
            else:
                continue
            if '.' in fname:
                ext = fname.rsplit('.', 1)[-1].lower()
                extensions.add(ext)
        if extensions:
            result['数据格式'] = ','.join(sorted(extensions))

    # 描述中提取论文信息
    description = api_data.get('descriptionNullable') or api_data.get('description') or ''
    if description:
        arxiv_match = re.findall(r'https?://arxiv\.org/abs/[\w.]+', description)
        paper_match = re.findall(r'https?://(?:papers\.nips|proceedings|aclanthology|openreview)[\w./\-]+', description)
        all_papers = arxiv_match + paper_match
        if all_papers:
            result['是否有论文'] = '是'
            result['论文URL'] = ','.join(all_papers[:3])
        else:
            result['是否有论文'] = '否'
    else:
        result['是否有论文'] = '/'

    return result


def process_dataset(idx, total, seq, url):
    """处理单个数据集"""
    # Kaggle URL 格式: https://www.kaggle.com/datasets/{user}/{dataset}
    # 或 https://kaggle.com/datasets/{user}/{dataset}
    match = re.search(r'kaggle\.com/datasets/(.+?)$', url)
    if not match:
        print(f'  [{idx+1}/{total}] {url} ERROR: Invalid URL format', flush=True)
        return extract_info(seq, url, '', None), f'{url}: Invalid URL format'
    
    dataset_id = match.group(1)
    print(f'  [{idx+1}/{total}] {dataset_id}', end='', flush=True)
    
    # Kaggle API endpoint (需要 API Key)
    # 格式: https://www.kaggle.com/api/v1/datasets/view/{user}/{dataset}
    api_url = f'https://www.kaggle.com/api/v1/datasets/view/{dataset_id}'
    
    # 如果有 Kaggle API Key，从环境变量读取
    kaggle_username = os.environ.get('KAGGLE_USERNAME')
    kaggle_key = os.environ.get('KAGGLE_KEY')
    
    try:
        if kaggle_username and kaggle_key:
            auth = (kaggle_username, kaggle_key)
            resp = requests.get(api_url, auth=auth, timeout=req_config['timeout'])
        else:
            # 无认证尝试（可能被拒绝）
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

    # 支持完整路径或仅文件名
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
    output_filename = f'kaggle_result_{ts}.xlsx'
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
