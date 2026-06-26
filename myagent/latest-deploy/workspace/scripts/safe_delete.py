# -*- coding: utf-8 -*-
"""
安全删除工具：文件移到中转站保留3天，压缩存储节省空间
"""
import os
import shutil
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).parent.parent
TRASH_ROOT = WORKSPACE_ROOT / 'trash'


def safe_delete(path, reason=''):
    """
    安全删除：移到中转站并压缩
    
    Args:
        path: 文件或目录路径（相对/绝对均可）
        reason: 删除原因（可选，会记录在元数据中）
    
    Returns:
        压缩包路径
    """
    path = Path(path).resolve()
    if not path.exists():
        print(f'路径不存在: {path}')
        return None
    
    # 按日期组织中转站目录
    today = datetime.now().strftime('%Y-%m-%d')
    trash_dir = TRASH_ROOT / today
    trash_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成压缩包名（避免重复）
    base_name = path.name
    zip_name = f'{base_name}.zip'
    zip_path = trash_dir / zip_name
    counter = 1
    while zip_path.exists():
        zip_name = f'{base_name}_{counter}.zip'
        zip_path = trash_dir / zip_name
        counter += 1
    
    # 压缩
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            if path.is_file():
                zf.write(path, path.name)
            else:
                for root, dirs, files in os.walk(path):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(path.parent)
                        zf.write(file_path, arcname)
        
        # 写元数据
        meta_path = zip_path.with_suffix('.meta')
        with open(meta_path, 'w', encoding='utf-8') as f:
            f.write(f'原路径: {path}\n')
            f.write(f'删除时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
            f.write(f'原始大小: {get_size(path)} bytes\n')
            f.write(f'压缩后: {zip_path.stat().st_size} bytes\n')
            if reason:
                f.write(f'原因: {reason}\n')
        
        # 删除原文件
        if path.is_file():
            path.unlink()
        else:
            shutil.rmtree(path)
        
        print(f'已移至中转站（压缩）: {zip_path.relative_to(WORKSPACE_ROOT)}')
        print(f'  原始: {get_size_human(get_size(None))} → 压缩后: {get_size_human(zip_path.stat().st_size)}')
        return zip_path
    
    except Exception as e:
        print(f'删除失败: {e}')
        return None


def get_size(path):
    """获取文件/目录大小（bytes）"""
    if path is None:
        return 0
    path = Path(path)
    if path.is_file():
        return path.stat().st_size
    total = 0
    for root, dirs, files in os.walk(path):
        for file in files:
            total += (Path(root) / file).stat().st_size
    return total


def get_size_human(size_bytes):
    """字节转人类可读格式"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f'{size_bytes:.1f}{unit}'
        size_bytes /= 1024
    return f'{size_bytes:.1f}TB'


def restore(zip_name, target_path=None):
    """
    还原文件
    
    Args:
        zip_name: 压缩包名称（在 trash/ 目录中搜索）
        target_path: 还原目标路径（可选，默认还原到原位置）
    """
    # 在所有日期目录中搜索
    found = None
    for date_dir in TRASH_ROOT.iterdir():
        if not date_dir.is_dir():
            continue
        zip_path = date_dir / zip_name
        if zip_path.exists():
            found = zip_path
            break
    
    if not found:
        print(f'未找到: {zip_name}')
        return False
    
    # 读取元数据获取原路径
    meta_path = found.with_suffix('.meta')
    original_path = None
    if meta_path.exists():
        with open(meta_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('原路径:'):
                    original_path = Path(line.split(':', 1)[1].strip())
                    break
    
    target = Path(target_path) if target_path else original_path
    if not target:
        print('无法确定还原路径')
        return False
    
    # 解压
    try:
        with zipfile.ZipFile(found, 'r') as zf:
            zf.extractall(target.parent)
        
        print(f'已还原: {target}')
        
        # 删除中转站中的压缩包和元数据
        found.unlink()
        if meta_path.exists():
            meta_path.unlink()
        
        return True
    
    except Exception as e:
        print(f'还原失败: {e}')
        return False


def cleanup_trash(days=3):
    """
    清理中转站中超过指定天数的文件
    
    Args:
        days: 保留天数（默认3天）
    
    Returns:
        清理的文件数量
    """
    if not TRASH_ROOT.exists():
        return 0
    
    cutoff_date = datetime.now() - timedelta(days=days)
    deleted_count = 0
    freed_space = 0
    
    for date_dir in TRASH_ROOT.iterdir():
        if not date_dir.is_dir():
            continue
        
        # 解析目录日期
        try:
            dir_date = datetime.strptime(date_dir.name, '%Y-%m-%d')
        except:
            continue
        
        if dir_date < cutoff_date:
            # 统计空间
            for file in date_dir.iterdir():
                freed_space += file.stat().st_size
                deleted_count += 1
            
            # 删除整个日期目录
            shutil.rmtree(date_dir)
            print(f'清理: {date_dir.name} ({deleted_count} 文件, {get_size_human(freed_space)} 释放)')
    
    return deleted_count


def list_trash():
    """列出中转站中的所有文件"""
    if not TRASH_ROOT.exists():
        print('中转站为空')
        return
    
    items = []
    for date_dir in sorted(TRASH_ROOT.iterdir(), reverse=True):
        if not date_dir.is_dir():
            continue
        for zip_file in date_dir.glob('*.zip'):
            meta_file = zip_file.with_suffix('.meta')
            original_path = '(未知)'
            delete_time = date_dir.name
            
            if meta_file.exists():
                with open(meta_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('原路径:'):
                            original_path = line.split(':', 1)[1].strip()
                        elif line.startswith('删除时间:'):
                            delete_time = line.split(':', 1)[1].strip()
            
            items.append({
                'zip': zip_file.name,
                'date': delete_time,
                'original': original_path,
                'size': get_size_human(zip_file.stat().st_size)
            })
    
    if not items:
        print('中转站为空')
        return
    
    print(f'\n中转站内容（共 {len(items)} 项）：')
    print(f'{"压缩包":<30} {"删除时间":<20} {"原路径":<40} {"大小":<10}')
    print('-' * 100)
    for item in items:
        print(f'{item["zip"]:<30} {item["date"]:<20} {item["original"]:<40} {item["size"]:<10}')


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print('用法:')
        print('  删除: python safe_delete.py delete <path> [reason]')
        print('  还原: python safe_delete.py restore <zip_name> [target_path]')
        print('  列表: python safe_delete.py list')
        print('  清理: python safe_delete.py cleanup [days]')
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == 'delete':
        path = sys.argv[2]
        reason = sys.argv[3] if len(sys.argv) > 3 else ''
        safe_delete(path, reason)
    
    elif action == 'restore':
        zip_name = sys.argv[2]
        target = sys.argv[3] if len(sys.argv) > 3 else None
        restore(zip_name, target)
    
    elif action == 'list':
        list_trash()
    
    elif action == 'cleanup':
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        cleanup_trash(days)
    
    else:
        print(f'未知操作: {action}')
