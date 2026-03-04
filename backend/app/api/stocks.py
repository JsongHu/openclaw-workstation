"""
股票 API 接口
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from app.models.database import engine, Stock, StockDaily, StockIndicator, init_db
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime

router = APIRouter()

# 初始化数据库
init_db()

def get_db():
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()

# Pydantic 模型
class StockBase(BaseModel):
    code: str
    name: Optional[str] = None
    market: Optional[str] = None
    sector: Optional[str] = None

class StockCreate(StockBase):
    pass

class StockResponse(StockBase):
    id: int
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class StockDailyBase(BaseModel):
    stock_id: int
    trade_date: date
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None
    amount: Optional[float] = None

class StockDailyResponse(StockDailyBase):
    id: int
    
    class Config:
        from_attributes = True

class IndicatorBase(BaseModel):
    stock_id: int
    trade_date: date
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    ma60: Optional[float] = None
    dif: Optional[float] = None
    dea: Optional[float] = None
    macd: Optional[float] = None
    k: Optional[float] = None
    d: Optional[float] = None
    j: Optional[float] = None
    rsi: Optional[float] = None
    boll_upper: Optional[float] = None
    boll_mid: Optional[float] = None
    boll_lower: Optional[float] = None
    volume_ratio: Optional[float] = None
    score: Optional[int] = 0
    signal_count: Optional[int] = 0
    signals_json: Optional[str] = None

# API 端点
@router.get("/stocks/count")
def count_stocks(db: Session = Depends(get_db)):
    """返回股票总数"""
    total = db.query(Stock).count()
    return {"total": total}

def stock_to_dict(stock: Stock, latest_daily: StockDaily = None, prev_daily: StockDaily = None) -> dict:
    """将股票转换为字典，包含最新行情"""
    # 计算涨跌幅（优先用昨日收盘价，其次用今日开盘价）
    change_pct = None
    change = None
    
    if latest_daily:
        # 方法1：用昨日收盘价计算
        if prev_daily and prev_daily.close and latest_daily.close:
            change = latest_daily.close - prev_daily.close
            if prev_daily.close > 0:
                change_pct = (change / prev_daily.close) * 100
        # 方法2：用今日开盘价计算（日内涨跌幅）
        elif latest_daily.open and latest_daily.close:
            change = latest_daily.close - latest_daily.open
            if latest_daily.open > 0:
                change_pct = (change / latest_daily.open) * 100
    
    result = {
        "id": stock.id,
        "code": stock.code,
        "name": stock.name,
        "market": stock.market,
        "sector": stock.sector,
        "pe": stock.pe,
        "pb": stock.pb,
        "total_market_cap": stock.total_market_cap,
        "circulating_market_cap": stock.circulating_market_cap,
        "created_at": stock.created_at.isoformat() if stock.created_at else None,
    }
    # 添加最新行情数据
    if latest_daily:
        result["price"] = latest_daily.close  # 使用收盘价作为现价
        result["change"] = change
        result["change_pct"] = change_pct
        result["volume"] = latest_daily.volume
        result["amount"] = latest_daily.amount
    return result

@router.get("/stocks")
def list_stocks(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    sector: Optional[str] = None,
):
    """获取股票列表（支持按行业筛选），包含最新行情 - 优化版：批量查询替代N+1"""
    query = db.query(Stock)

    if sector:
        query = query.filter(Stock.sector.contains(sector))

    stocks = query.offset(skip).limit(limit).all()
    if not stocks:
        return []

    stock_ids = [s.id for s in stocks]

    # 子查询：每只股票最新的两条日线记录（用于计算涨跌幅）
    # 先获取每只股票最新交易日
    latest_date_sub = (
        db.query(
            StockDaily.stock_id,
            func.max(StockDaily.trade_date).label('max_date')
        )
        .filter(StockDaily.stock_id.in_(stock_ids))
        .group_by(StockDaily.stock_id)
        .subquery()
    )

    # 批量获取最新日线
    latest_rows = (
        db.query(StockDaily)
        .join(latest_date_sub, and_(
            StockDaily.stock_id == latest_date_sub.c.stock_id,
            StockDaily.trade_date == latest_date_sub.c.max_date
        ))
        .all()
    )
    latest_map = {row.stock_id: row for row in latest_rows}

    # 批量获取次新日线（用于涨跌幅计算）
    prev_date_sub = (
        db.query(
            StockDaily.stock_id,
            func.max(StockDaily.trade_date).label('prev_date')
        )
        .filter(StockDaily.stock_id.in_(stock_ids))
        .join(latest_date_sub, and_(
            StockDaily.stock_id == latest_date_sub.c.stock_id,
            StockDaily.trade_date < latest_date_sub.c.max_date
        ))
        .group_by(StockDaily.stock_id)
        .subquery()
    )

    prev_rows = (
        db.query(StockDaily)
        .join(prev_date_sub, and_(
            StockDaily.stock_id == prev_date_sub.c.stock_id,
            StockDaily.trade_date == prev_date_sub.c.prev_date
        ))
        .all()
    )
    prev_map = {row.stock_id: row for row in prev_rows}

    # 批量获取最新指标（score, signal_count）
    ind_date_sub = (
        db.query(
            StockIndicator.stock_id,
            func.max(StockIndicator.trade_date).label('max_date')
        )
        .filter(StockIndicator.stock_id.in_(stock_ids))
        .group_by(StockIndicator.stock_id)
        .subquery()
    )
    ind_rows = (
        db.query(StockIndicator.stock_id, StockIndicator.score, StockIndicator.signal_count)
        .join(ind_date_sub, and_(
            StockIndicator.stock_id == ind_date_sub.c.stock_id,
            StockIndicator.trade_date == ind_date_sub.c.max_date
        ))
        .all()
    )
    ind_map = {row[0]: {"score": row[1], "signal_count": row[2]} for row in ind_rows}

    result = []
    for stock in stocks:
        latest = latest_map.get(stock.id)
        prev = prev_map.get(stock.id)
        d = stock_to_dict(stock, latest, prev)
        ind = ind_map.get(stock.id)
        if ind:
            d["score"] = ind["score"]
            d["signal_count"] = ind["signal_count"]
        result.append(d)

    return result

@router.get("/stocks/{stock_id}", response_model=StockResponse)
def get_stock(stock_id: int, db: Session = Depends(get_db)):
    stock = db.query(Stock).filter(Stock.id == stock_id).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    return stock

@router.post("/stocks", response_model=StockResponse)
def create_stock(stock: StockCreate, db: Session = Depends(get_db)):
    db_stock = Stock(**stock.dict())
    db.add(db_stock)
    db.commit()
    db.refresh(db_stock)
    return db_stock

@router.get("/stocks/{stock_id}/daily", response_model=List[StockDailyResponse])
def get_stock_daily(stock_id: int, db: Session = Depends(get_db), limit: int = 30):
    daily_data = db.query(StockDaily).filter(
        StockDaily.stock_id == stock_id
    ).order_by(StockDaily.trade_date.desc()).limit(limit).all()
    return daily_data

@router.get("/stocks/{stock_id}/indicators")
def get_stock_indicators(stock_id: int, db: Session = Depends(get_db), limit: int = 30):
    indicators = db.query(StockIndicator).filter(
        StockIndicator.stock_id == stock_id
    ).order_by(StockIndicator.trade_date.desc()).limit(limit).all()
    return indicators

@router.get("/by-code/{code}/daily")
def get_stock_daily_by_code(code: str, db: Session = Depends(get_db), days: int = 30):
    """通过股票代码获取日线数据（近N天）"""
    stock = db.query(Stock).filter(Stock.code == code).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    daily_data = (
        db.query(StockDaily)
        .filter(StockDaily.stock_id == stock.id)
        .order_by(StockDaily.trade_date.desc())
        .limit(days)
        .all()
    )

    return {
        "stock": {"id": stock.id, "code": stock.code, "name": stock.name, "market": stock.market},
        "daily": [{
            "trade_date": d.trade_date.isoformat(),
            "open": d.open,
            "high": d.high,
            "low": d.low,
            "close": d.close,
            "volume": d.volume,
            "amount": d.amount,
            "change": d.change,
            "change_pct": d.change_pct,
        } for d in reversed(daily_data)]  # 按时间正序返回
    }

@router.get("/search")
def search_stocks(q: str, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """搜索股票（支持分页）"""
    base = db.query(Stock).filter(
        (Stock.code.contains(q)) | (Stock.name.contains(q))
    )
    total = base.count()
    items = base.offset(skip).limit(limit).all()
    return {"items": items, "total": total}
