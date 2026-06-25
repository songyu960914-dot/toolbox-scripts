# -*- coding: utf-8 -*-
"""
HuggingFace Dataset Metadata Extractor
从 tags 和 cardData 两处全面提取所有字段，去重合并
新增：榜单类型判断 + Agent类型判断
"""
import os, sys, time, re, requests, pandas as pd
from datetime import datetime
from openai import OpenAI

# 智谱 GLM API 用于分类判断
llm_client = OpenAI(
    base_url="https://open.bigmodel.cn/api/paas/v4",
    api_key="0ae785e691cc4159a99a7f60f869a9bb.0eis0htIzPx6i8y3"
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
    """将值统一转为列表"""
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


def fetch_readme(dataset_id, max_retries=3):
    """获取数据集 README 内容用于关键词判断，带重试"""
    url = f'https://huggingface.co/datasets/{dataset_id}/raw/main/README.md'
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                return resp.text.lower()
            break  # 非 200 不重试
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
            continue
        except:
            break
    return ''


def fetch_data_preview(dataset_id, max_retries=3):
    """获取数据集前几行预览，包括列名和样本值"""
    base_url = 'https://datasets-server.huggingface.co'
    
    for attempt in range(max_retries):
        try:
            # 获取第一页数据
            resp = requests.get(
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
                
                # 提取前5行的关键字段值（截断长文本）
                sample_rows = []
                for row_data in rows[:5]:
                    row = row_data.get('row', {})
                    row_summary = {}
                    for col in col_names[:10]:  # 最多取10列
                        val = row.get(col, '')
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


def check_content_warning(api_data, tags, readme_text, card_data):
    """
    只检测数据集中确实可能存在的有害、色情内容警告。
    忽略作者的呼吁式警告（如"请勿用于..."、"不应用于..."等）。
    返回: (是否有警告, 警告原文)
    """
    all_text = readme_text if readme_text else ''
    if isinstance(card_data, dict):
        desc = card_data.get('description', '') or ''
        all_text += ' ' + desc
    
    # 数据集包含有害内容的关键模式（排除呼吁式）
    warning_patterns = [
        (r'(contain|include|有|包含).{0,30}(harmful|offensive|有害|冒犯)', 'contains_harmful'),
        (r'(pornograph|sexually explicit|nsfw|色情|成人内容)', 'adult_content'),
        (r'benchmark.{0,50}(harmful|offensive|有害|冒犯)', 'harmful_in_benchmark'),
    ]
    
    # 排除模式：呼吁式语句
    exclude_patterns = [
        r'(should not|must not|do not|请勿|不应|禁止).{0,30}(use|使用|用于)',
        r'(responsibility|负责|responsible)',
        r'(recommend|建议|suggest)',
    ]
    
    all_text_lower = all_text.lower()
    
    # 检查 tags
    nsfw_tags = {'not-for-all-audiences', 'nsfw', 'adult', '18+'}
    has_nsfw_tag = any(tag.lower() in nsfw_tags for tag in tags)
    
    found_sentences = []
    
    if has_nsfw_tag:
        found_sentences.append(f'标签含: {", ".join(t for t in tags if t.lower() in nsfw_tags)}')
    
    # 在正文中查找警告模式并提取原句
    sentences = re.split(r'[.。\n]', all_text)
    for pattern, pattern_type in warning_patterns:
        if re.search(pattern, all_text_lower):
            # 找到匹配的原句
            for sent in sentences:
                sent_lower = sent.lower()
                if re.search(pattern, sent_lower):
                    # 检查是否是呼吁式语句（需要排除）
                    is_excluded = any(re.search(excl, sent_lower) for excl in exclude_patterns)
                    if not is_excluded and len(sent.strip()) > 10:
                        found_sentences.append(sent.strip()[:250])
                        break
    
    if found_sentences:
        unique = list(dict.fromkeys(found_sentences))
        return '是', '; '.join(unique[:3])
    return '否', '/'


def judge_benchmark(dataset_id, readme_text, tags, card_data):
    """
    榜单判断（仅关注 README 关键词，不看数据预览）：
    1. benchmark榜单：README 含 bench/benchmark/longbench
    2. 名字含bench类：仓库名含 bench 但 README 为空
    3. 其他榜单：README 含 测试/测评/评估/评价/基准/evaluation/eval 等
    4. 非榜单：以上都不符合
    
    当初步判断为 benchmark榜单 或 其他榜单 时，提取关键词原句并交 LLM 二次确认。
    """
    # 仅使用 README + tags + description（不含数据预览）
    readme_lower = readme_text.lower() if readme_text else ''
    all_text = readme_lower
    if tags:
        all_text += ' ' + ' '.join(str(t).lower() for t in tags)
    if isinstance(card_data, dict):
        desc = card_data.get('description', '') or ''
        all_text += ' ' + desc.lower()

    # 判断仓库名是否含 bench
    repo_name = dataset_id.lower()
    name_has_bench = any(kw in repo_name for kw in ['bench', 'benchmark'])
    
    # README 是否为空
    readme_empty = not readme_text or len(readme_text.strip().replace('---', '').strip()) < 50

    # --- 关键词匹配 ---
    preliminary_type = None
    matched_keyword = None
    
    # 优先级1：benchmark 关键词
    benchmark_keywords = ['benchmark', 'longbench', 'bench']
    for kw in benchmark_keywords:
        if kw in all_text:
            preliminary_type = 'benchmark榜单'
            matched_keyword = kw
            break

    # 优先级2：仓库名含 bench 但 README 为空
    if not preliminary_type and name_has_bench and readme_empty:
        return '名字含bench类', '(README为空，仅仓库名含bench)'

    # 优先级3：评测相关关键词
    if not preliminary_type:
        eval_keywords = [
            '测试', '测评', '评估', '评价', '基准',
            'evaluation', 'evaluate', 'eval', 'assessment', 'test set',
            'leaderboard', 'scoring', 'metric'
        ]
        for kw in eval_keywords:
            if kw in all_text:
                preliminary_type = '其他榜单'
                matched_keyword = kw
                break

    # 如果没有匹配任何关键词
    if not preliminary_type:
        return '非榜单', '/'

    # --- 提取关键词所在原句 ---
    source_text = readme_text if readme_text else ''
    if isinstance(card_data, dict):
        source_text += ' ' + (card_data.get('description', '') or '')
    
    keyword_sentence = ''
    sentences = re.split(r'[.。\n]', source_text)
    for sent in sentences:
        if matched_keyword in sent.lower() and len(sent.strip()) > 10:
            keyword_sentence = sent.strip()[:300]
            break
    
    # --- LLM 二次确认 ---
    confirmed_type = llm_confirm_benchmark(
        dataset_id, preliminary_type, matched_keyword, keyword_sentence, readme_text
    )
    
    return confirmed_type, keyword_sentence if keyword_sentence else f'(含关键词: {matched_keyword})'


def llm_confirm_benchmark(dataset_id, preliminary_type, keyword, keyword_sentence, readme_text):
    """
    LLM 二次确认榜单判断：结合语句情景分析是否真的表示该数据集有测评/评估用途
    """
    readme_snippet = readme_text[:1000] if readme_text else '(无)'
    
    prompt = f"""根据以下信息判断该数据集是否真的属于"{preliminary_type}"类型。

数据集: {dataset_id}
初步判断: {preliminary_type}（因为包含关键词 "{keyword}"）
关键词所在原句: {keyword_sentence}

README摘要:
{readme_snippet}

---
判断规则：
- 如果关键词在语境中确实表达了"该数据集用于测评/评估模型性能"的含义 → 确认为 {preliminary_type}
- 如果关键词只是顺带提及（如"我们在benchmark上测试了效果"、"eval split"等描述，但数据集本身是训练数据）→ 改判为 非榜单
- benchmark榜单：数据集本身就是benchmark，用于评测模型
- 其他榜单：数据集有评估/测试用途，但不是标准benchmark

只返回JSON：
{{"榜单类型":"benchmark榜单"}} 或 {{"榜单类型":"其他榜单"}} 或 {{"榜单类型":"非榜单"}}"""

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
        for text in [content, reasoning]:
            match = re.search(r'\{[^{}]*榜单[^{}]*\}', text)
            if not match:
                match = re.search(r'\{[^{}]*\u699c\u5355[^{}]*\}', text)
            if match:
                try:
                    result = json_mod.loads(match.group())
                    val = result.get('榜单类型', '') or result.get('\u699c\u5355\u7c7b\u578b', '')
                    for std in ['benchmark榜单', '其他榜单', '非榜单']:
                        if std in val:
                            return std
                except:
                    continue
        return preliminary_type  # LLM 解析失败时保留初步判断
    except:
        return preliminary_type


def judge_agent_type(readme_text, tags, card_data, task_categories, modalities):
    """fallback：信息不足时返回'其他'"""
    return '其他'


def llm_classify(dataset_id, readme_text, tags, card_data, task_categories, modalities, data_preview):
    """
    用 LLM 综合判断 Agent 类型（包含数据预览）。
    返回: (Agent类型, 混合说明)
    - 当 README 和数据预览都为空时，返回 ('/', '/')
    - 特殊规则：tags 含 robotics + multimodal → ('混合不可用', '代码/机器人+多模态')
    - 混合分类需要注明具体类别组合
    - 代码和机器人算一个标签，单独或一起不算混合
    """
    # 判断信息是否足够
    readme_empty = not readme_text or len(readme_text.strip().replace('---', '').strip()) < 50
    preview_empty = data_preview is None or len(data_preview.get('samples', [])) == 0
    
    if readme_empty and preview_empty:
        return '/', '/'
    
    # 特殊规则：tags 直接显示 robotics + multimodal → 混合不可用
    tags_lower = [str(t).lower() for t in tags]
    has_robotics = any('robot' in t for t in tags_lower)
    has_multimodal_tag = any(t in ['multimodal', 'image', 'audio', 'video'] for t in tags_lower) or \
                          any(t.startswith('modality:') and any(m in t for m in ['image', 'audio', 'video']) for t in tags_lower)
    if has_robotics and has_multimodal_tag:
        return '混合不可用', '代码/机器人+多模态'

    readme_snippet = readme_text[:2000] if readme_text else '(无 README)'
    tags_str = ', '.join(tags[:30]) if tags else '(无)'
    tasks_str = ', '.join(task_categories) if task_categories else '(无)'
    modalities_str = ', '.join(modalities) if modalities else '(无)'
    
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

    prompt = f"""根据以下HuggingFace数据集的所有信息综合判断Agent类型，只返回JSON：

数据集: {dataset_id}
Tasks: {tasks_str}
Modalities: {modalities_str}
Tags: {tags_str}
描述: {card_desc}

README摘要:
{readme_snippet[:1500]}

数据预览（实际数据内容）:
{preview_text}

---
Agent类型（六选一，严格使用以下值）：
- 代码/机器人：任务目标要求输出代码（代码生成、补全、终端操作等）或控制物理/虚拟机器人。注意：代码和机器人算一个标签，单独出现或一起出现都不算混合
- 多模态：**每条数据都包含**图片、音频、视频等多模态内容（如每行都有screenshot/image/audio列）
- 通用：纯文本任务（对话、问答、推理、搜索、浏览器操作等），不要求输出代码
- 混合可用：数据集包含**两种或以上不同类别**（代码/机器人、多模态、通用中至少两种），且有可用的数据
- 混合不可用：代码/机器人 + 多模态的组合，缺乏纯文本通用数据
- 其他：信息不足以判断具体类别
- /：完全无法获取任何信息

混合判断规则：
1. 代码类 + 机器人类 → **不算混合**，归为"代码/机器人"
2. 通用 + 多模态 → 混合可用
3. 通用 + 代码/机器人 → 混合可用
4. 代码/机器人 + 多模态 + 通用 → 混合可用
5. 代码/机器人 + 多模态（无通用） → 混合不可用

关键判断依据：
1. **优先看数据预览**中每行的列结构
2. 如果**每行都有** screenshot/image 列 → 多模态（不是混合）
3. 如果数据集同时包含不同类型的数据（如部分是对话、部分是图像任务） → 判断是哪些类别的混合

返回JSON格式：
{{"Agent类型":"...", "混合说明":"..."}}

混合说明填写规则：
- 非混合类型：填 "/"
- 混合可用：注明具体组合，如"通用+多模态"、"通用+代码/机器人"、"通用+代码/机器人+多模态"
- 混合不可用：填"代码/机器人+多模态"

严格只返回JSON。"""

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
                return '其他', '/'
        
        agent_type = result.get('Agent\u7c7b\u578b', '') or result.get('Agent类型', '')
        mix_detail = result.get('\u6df7\u5408\u8bf4\u660e', '') or result.get('混合说明', '') or '/'
        
        # 模糊匹配标准值
        valid_agent = ['代码/机器人', '多模态', '通用', '混合可用', '混合不可用', '其他', '/']
        matched_type = None
        for std_val in valid_agent:
            if std_val in agent_type:
                matched_type = std_val
                break
        
        if not matched_type:
            matched_type = '其他'
        
        # 非混合类型，混合说明填 /
        if matched_type not in ['混合可用', '混合不可用']:
            mix_detail = '/'
        
        return matched_type, mix_detail
    except Exception as e:
        print(f' [LLM error: {e}]', end='')
        return '其他', '/'


def extract_info(seq, url, dataset_id, api_data, readme_text):
    result = {
        '序号': seq,
        'URL': url,
        '发布/更新时间': '/',
        '数据量级（条）': '/',
        '量级等级（条）': '/',
        '数据大小（GB）': '/',
        '下载量': '/',
        '点赞量': '/',
        'Tags': '/',
        'Tasks': '/',
        'License': '/',
        '数据类型（文件类型）': '/',
        '数据格式': '/',
        '语种': '/',
        '是否有论文': '/',
        '论文arXivURL': '/',
        '是否有测试集': '/',
        '榜单类型': '/',
        '榜单关键词原句': '/',
        'Agent类型': '/',
        '混合说明': '/',
        '是否有警告': '/',
        '警告原因': '/',
    }
    if not api_data:
        return result

    # === 基本信息 ===
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

    # === 准备数据源 ===
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

    # === License ===
    from_tags = extract_from_tags(tags, 'license')
    from_card = safe_list(card_data.get('license'))
    merged = merge_unique(from_tags, from_card)
    if merged:
        result['License'] = ','.join(merged)

    # === Tasks ===
    from_tags = extract_from_tags(tags, 'task_categories')
    from_card = safe_list(card_data.get('task_categories'))
    task_categories = merge_unique(from_tags, from_card)
    if task_categories:
        result['Tasks'] = ','.join(task_categories)

    # === 量级等级 ===
    from_tags = extract_from_tags(tags, 'size_categories')
    from_card = safe_list(card_data.get('size_categories'))
    merged = merge_unique(from_tags, from_card)
    if merged:
        result['量级等级（条）'] = ','.join(merged)

    # === 数据类型（modality） ===
    from_tags = extract_from_tags(tags, 'modality')
    from_card = safe_list(card_data.get('modality'))
    modalities = merge_unique(from_tags, from_card)
    if modalities:
        result['数据类型（文件类型）'] = ','.join(modalities)

    # === 数据格式 ===
    from_tags = extract_from_tags(tags, 'format')
    from_card = safe_list(card_data.get('format'))
    merged = merge_unique(from_tags, from_card)
    if merged:
        result['数据格式'] = ','.join(merged)

    # === 语种 ===
    from_tags = extract_from_tags(tags, 'language')
    from_card = safe_list(card_data.get('language'))
    merged = merge_unique(from_tags, from_card)
    if merged:
        result['语种'] = ','.join(merged)

    # === Tags ===
    custom_from_tags = [t for t in tags if ':' not in t]
    custom_from_card = safe_list(card_data.get('tags'))
    merged = merge_unique(custom_from_tags, custom_from_card)
    if merged:
        result['Tags'] = ','.join(merged)

    # === 数据大小（GB） ===
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

    # === 数据量级（条） ===
    num_examples_total = 0
    for di in dataset_info_list:
        splits_info = di.get('splits', [])
        if isinstance(splits_info, list):
            for s in splits_info:
                if isinstance(s, dict) and s.get('num_examples'):
                    num_examples_total += s['num_examples']
    if num_examples_total > 0:
        result['数据量级（条）'] = num_examples_total

    # === 是否有论文 ===
    arxiv_ids = extract_from_tags(tags, 'arxiv')
    card_arxiv = safe_list(card_data.get('arxiv'))
    all_arxiv = merge_unique(arxiv_ids, card_arxiv)
    if all_arxiv:
        result['是否有论文'] = '是'
        urls = [f'https://arxiv.org/abs/{aid}' for aid in all_arxiv]
        result['论文arXivURL'] = ','.join(urls)
    else:
        result['是否有论文'] = '否'

    # === 是否有测试集 ===
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
    if not has_test:
        configs = card_data.get('configs', [])
        if isinstance(configs, list):
            for cfg in configs:
                if isinstance(cfg, dict):
                    data_files = cfg.get('data_files', [])
                    if isinstance(data_files, list):
                        for df_item in data_files:
                            if isinstance(df_item, dict) and 'test' in str(df_item.get('split', '')).lower():
                                has_test = True
                                break
    result['是否有测试集'] = '是' if has_test else '/'

    # === 榜单类型（关键词判断 + LLM二次确认） ===
    benchmark_type, benchmark_sentence = judge_benchmark(dataset_id, readme_text, tags, card_data)
    result['榜单类型'] = benchmark_type
    result['榜单关键词原句'] = benchmark_sentence

    # === Agent类型（LLM 判断，包含数据预览） ===
    # 获取数据预览
    data_preview = fetch_data_preview(dataset_id)
    agent_type, mix_detail = llm_classify(dataset_id, readme_text, tags, card_data, task_categories, modalities, data_preview)
    result['Agent类型'] = agent_type
    result['混合说明'] = mix_detail

    # === 内容安全警告 ===
    has_warning, warning_reason = check_content_warning(api_data, tags, readme_text, card_data)
    result['是否有警告'] = has_warning
    result['警告原因'] = warning_reason

    return result


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
            resp = requests.get(api_url, timeout=30)
            if resp.status_code == 200:
                api_data = resp.json()
                # 获取 README 用于关键词判断
                readme_text = fetch_readme(dataset_id)
                info = extract_info(seq, url, dataset_id, api_data, readme_text)
                print(' OK')
            else:
                print(f' ERROR: HTTP {resp.status_code}')
                errors.append(f'{dataset_id}: HTTP {resp.status_code}')
                info = extract_info(seq, url, dataset_id, None, '')
        except Exception as e:
            print(f' ERROR: {e}')
            errors.append(f'{dataset_id}: {e}')
            info = extract_info(seq, url, dataset_id, None, '')
        results.append(info)
        time.sleep(1.5)

    output_df = pd.DataFrame(results)
    # 使用时间戳避免文件名冲突
    ts = datetime.now().strftime('%H%M%S')
    output_filename = f'dataset_result_{ts}.xlsx'
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
