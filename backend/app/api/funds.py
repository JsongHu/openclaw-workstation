"""
基金 API
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.models.database import engine, FundPortfolio
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

router = APIRouter()

def get_db():
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()

class FundBase(BaseModel):
    fund_code: str
    fund_name: Optional[str] = None
    nav: Optional[float] = None
    shares: float = 0
    avg_cost: Optional[float] = None

class FundCreate(FundBase):
    pass

class FundUpdate(BaseModel):
    fund_name: Optional[str] = None
    nav: Optional[float] = None
    shares: Optional[float] = None
    avg_cost: Optional[float] = None

class FundResponse(FundBase):
    id: int
    updated_at: datetime
    
    class Config:
        from_attributes = True

# API 端点
@router.get("/funds", response_model=List[FundResponse])
def list_funds(db: Session = Depends(get_db)):
    """获取基金持仓列表"""
    funds = db.query(FundPortfolio).all()
    return funds

@router.post("/funds", response_model=FundResponse)
def create_fund(fund: FundCreate, db: Session = Depends(get_db)):
    """添加基金持仓"""
    db_fund = FundPortfolio(**fund.dict())
    db.add(db_fund)
    db.commit()
    db.refresh(db_fund)
    return db_fund

@router.put("/funds/{fund_id}", response_model=FundResponse)
def update_fund(fund_id: int, fund: FundUpdate, db: Session = Depends(get_db)):
    """更新基金持仓"""
    db_fund = db.query(FundPortfolio).filter(FundPortfolio.id == fund_id).first()
    if not db_fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    
    for key, value in fund.dict(exclude_unset=True).items():
        setattr(db_fund, key, value)
    
    db_fund.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_fund)
    return db_fund

@router.delete("/funds/{fund_id}")
def delete_fund(fund_id: int, db: Session = Depends(get_db)):
    """删除基金持仓"""
    db_fund = db.query(FundPortfolio).filter(FundPortfolio.id == fund_id).first()
    if not db_fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    
    db.delete(db_fund)
    db.commit()
    return {"message": "Fund deleted successfully"}

@router.get("/funds/summary")
def get_funds_summary(db: Session = Depends(get_db)):
    """获取基金汇总"""
    funds = db.query(FundPortfolio).all()
    
    total_cost = 0
    total_value = 0
    
    for f in funds:
        cost = f.shares * f.avg_cost if f.avg_cost else 0
        value = f.shares * f.nav if f.nav else 0
        total_cost += cost
        total_value += value
    
    return {
        "total_cost": total_cost,
        "total_value": total_value,
        "total_profit": total_value - total_cost,
        "profit_pct": ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0,
        "funds": funds
    }
