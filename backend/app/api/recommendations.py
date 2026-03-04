"""
每日推荐 API
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.database import engine, DailyRecommendation, Stock, StockIndicator, StockDaily
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime

router = APIRouter()

def get_db():
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()

class RecommendationResponse(BaseModel):
    id: int
    date: date
    stock_id: int
    rank: int
    score: int
    signal_count: int = 0
    signals: Optional[str] = None
    stock: Optional[dict] = None
    rsi: Optional[float] = None
    change_pct: Optional[float] = None
    
    class Config:
        from_attributes = True

def _enrich_recommendation(r, db) -> dict:
    """为推荐记录附加股票信息、指标和涨跌幅"""
    stock = db.query(Stock).filter(Stock.id == r.stock_id).first()
    indicator = db.query(StockIndicator).filter(
        StockIndicator.stock_id == r.stock_id
    ).order_by(StockIndicator.trade_date.desc()).first()
    latest = db.query(StockDaily).filter(
        StockDaily.stock_id == r.stock_id
    ).order_by(StockDaily.trade_date.desc()).first()
    
    change_pct = None
    if latest and latest.open and latest.close and latest.open > 0:
        change_pct = round((latest.close - latest.open) / latest.open * 100, 2)
    
    return {
        "id": r.id,
        "date": r.date,
        "stock_id": r.stock_id,
        "rank": r.rank,
        "score": r.score,
        "signal_count": r.signal_count or 0,
        "signals": r.signals,
        "stock": {"code": stock.code, "name": stock.name} if stock else None,
        "rsi": indicator.rsi if indicator else None,
        "change_pct": change_pct,
    }

@router.get("/recommendations/today", response_model=List[RecommendationResponse])
def get_today_recommendations(db: Session = Depends(get_db)):
    """获取今日推荐"""
    today = date.today()
    
    recommendations = db.query(DailyRecommendation).filter(
        DailyRecommendation.date == today
    ).order_by(DailyRecommendation.rank).all()
    
    return [_enrich_recommendation(r, db) for r in recommendations]

@router.get("/recommendations", response_model=List[RecommendationResponse])
def get_recommendations(db: Session = Depends(get_db), limit: int = 50):
    """获取推荐列表"""
    recommendations = db.query(DailyRecommendation).order_by(
        DailyRecommendation.date.desc(),
        DailyRecommendation.rank
    ).limit(limit).all()
    
    return [_enrich_recommendation(r, db) for r in recommendations]

@router.get("/recommendations/top", response_model=List[RecommendationResponse])
def get_top_recommendations(db: Session = Depends(get_db), limit: int = 10):
    """获取高分推荐股票"""
    latest_date = db.query(DailyRecommendation.date).order_by(
        desc(DailyRecommendation.date)
    ).first()
    
    if not latest_date:
        return []
    
    query = db.query(DailyRecommendation).filter(
        DailyRecommendation.date == latest_date[0],
        DailyRecommendation.score >= 8,
    )
    if hasattr(DailyRecommendation, 'signal_count'):
        query = query.filter(DailyRecommendation.signal_count >= 4)
    
    recommendations = query.order_by(
        DailyRecommendation.score.desc(),
        DailyRecommendation.rank
    ).limit(limit).all()
    
    return [_enrich_recommendation(r, db) for r in recommendations]
