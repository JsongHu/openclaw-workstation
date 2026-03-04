"""
日记聚合 API - 获取各 agent 的日记
"""
import os
import json
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

# 各 agent 的 workspace 路径和日记子目录
# 格式: agent -> (基础路径, [日记子目录列表])
AGENT_DIARY_CONFIG = {
    "main": ("/Users/hjsclaw/.openclaw/workspace/memory/", ["diary", "finance-diary", "work_diary", ""]),
    "finance": ("/Users/hjsclaw/.openclaw/workspace-finance/memory/", ["diary", "finance-diary", "work_diary", ""]),
    "social": ("/Users/hjsclaw/.openclaw/workspace-social/memory/", ["diary"]),
}

class DiaryEntry(BaseModel):
    date: str
    content: str
    source: Optional[str] = None

def scan_diary_files(agent: str) -> List[DiaryEntry]:
    """扫描 agent 的日记文件"""
    entries = []
    
    config = AGENT_DIARY_CONFIG.get(agent)
    if not config:
        return entries
    
    base_path, diary_dirs = config
    if not os.path.exists(base_path):
        return entries
    
    # 扫描指定的日记目录
    for diary_dir in diary_dirs:
        dir_path = os.path.join(base_path, diary_dir) if diary_dir else base_path
        if not os.path.isdir(dir_path):
            continue
        
        for filename in os.listdir(dir_path):
            if filename.endswith(".md"):
                filepath = os.path.join(dir_path, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    # 尝试从文件名提取日期
                    date_str = filename.replace(".md", "")
                    # 尝试从内容提取日期
                    if "# " in content:
                        first_line = content.split("\n")[0]
                        if "20" in first_line:
                            # 可能是日期
                            import re
                            dates = re.findall(r"20\d{2}-\d{2}-\d{2}", first_line)
                            if dates:
                                date_str = dates[0]
                    
                    entries.append(DiaryEntry(
                        date=date_str,
                        content=content[:500],  # 截取前500字符作为摘要
                        source=diary_dir or "root"
                    ))
                except Exception as e:
                    print(f"读取日记失败 {filepath}: {e}")
    
    # 按日期排序
    entries.sort(key=lambda x: x.date, reverse=True)
    return entries

@router.get("/{agent}")
def get_agent_diary(agent: str):
    """获取指定 agent 的日记"""
    if agent not in AGENT_DIARY_CONFIG:
        return {"error": "Unknown agent"}
    
    entries = scan_diary_files(agent)
    return entries

@router.get("/")
def get_all_agents():
    """获取所有有日记的 agent 列表"""
    result = []
    for agent, (base_path, diary_dirs) in AGENT_DIARY_CONFIG.items():
        if not os.path.exists(base_path):
            continue
        
        # 统计日记文件数量
        count = 0
        for diary_dir in diary_dirs:
            dir_path = os.path.join(base_path, diary_dir) if diary_dir else base_path
            if os.path.isdir(dir_path):
                count += len([f for f in os.listdir(dir_path) if f.endswith(".md")])
        
        if count > 0:
            result.append({
                "agent": agent,
                "diary_count": count,
                "path": base_path
            })
    return result
