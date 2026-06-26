# -*- coding: utf-8 -*-
"""
HuggingFace Dataset Metadata Extractor - Minimal Version
仅提取：榜单、Agent、警告相关字段
"""
import os, sys, time, re, requests, pandas as pd, yaml, asyncio
from datetime import datetime
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor
import threading


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

# LLM 客户端（线程安全）
llm_client = OpenAI(
    base_url=llm_config['base_url'],
    api_key=api_key
)

# 并发控制
CONCURRENCY = 5  # 并发度
print_lock = threading.Lock()


def extract_from_tags(tags, prefix):
    results = []
