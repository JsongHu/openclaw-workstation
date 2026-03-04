"""
理财日记 API
"""
import json
import os
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

DIARY_DIR = "/Users/hjsclaw/.openclaw/workspace/OpenClaw-workstation/memory/diary"

class DiaryEntry(BaseModel):
    date: str
    content: str
    portfolio: Optional[dict] = None

def load_diary() -> List[dict]:
    """加载日记 - 从MD文件读取"""
    entries = []
    if os.path.exists(DIARY_DIR):
        for filename in os.listdir(DIARY_DIR):
            if filename.endswith('.md'):
                filepath = os.path.join(DIARY_DIR, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                    # 从文件名提取日期 (格式: 2026-03-04.md)
                    date = filename.replace('.md', '')
                    entries.append({
                        "date": date,
                        "content": content,
                        "portfolio": None
                    })
                except:
                    pass
    # 按日期倒序排列
    entries.sort(key=lambda x: x.get("date", ""), reverse=True)
    return entries

def save_diary(entries: List[dict]):
    """保存日记 - 写入MD文件"""
    os.makedirs(DIARY_DIR, exist_ok=True)
    for entry in entries:
        date = entry.get("date", "unknown")
        filename = f"{date}.md"
        filepath = os.path.join(DIARY_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(entry.get("content", ""))

@router.get("/entries")
def get_entries():
    """获取所有日记"""
    return load_diary()

@router.post("/entries")
def add_entry(entry: DiaryEntry):
    """添加日记"""
    entries = load_diary()
    # 检查是否已存在相同日期的日记
    existing_index = None
    for i, e in enumerate(entries):
        if e.get("date") == entry.date:
            existing_index = i
            break
    
    if existing_index is not None:
        entries[existing_index] = entry.dict()
    else:
        entries.insert(0, entry.dict())
    
    save_diary(entries)
    return {"success": True}
