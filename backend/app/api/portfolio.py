"""
持仓管理 API
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.models.database import engine, Portfolio, Stock, Account
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

# Pydantic 模型
class PortfolioBase(BaseModel):
    stock_id: int
    shares: float = 0
    avg_cost: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    notes: Optional[str] = None

class PortfolioCreate(PortfolioBase):
    pass

class PortfolioUpdate(BaseModel):
    shares: Optional[float] = None
    avg_cost: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    notes: Optional[str] = None

class PortfolioResponse(PortfolioBase):
    id: int
    created_at: datetime
    updated_at: datetime
    stock: Optional[dict] = None
    
    class Config:
        from_attributes = True

# API 端点
@router.get("/portfolio", response_model=List[PortfolioResponse])
def list_portfolio(db: Session = Depends(get_db)):
    """获取所有持仓"""
    positions = db.query(Portfolio).all()
    result = []
    for p in positions:
        stock = db.query(Stock).filter(Stock.id == p.stock_id).first()
        p_dict = {
            "id": p.id,
            "stock_id": p.stock_id,
            "shares": p.shares,
            "avg_cost": p.avg_cost,
            "target_price": p.target_price,
            "stop_loss": p.stop_loss,
            "notes": p.notes,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
            "stock": {"code": stock.code, "name": stock.name} if stock else None
        }
        result.append(p_dict)
    return result

@router.post("/portfolio", response_model=PortfolioResponse)
def create_portfolio(portfolio: PortfolioCreate, db: Session = Depends(get_db)):
    """添加持仓"""
    db_portfolio = Portfolio(**portfolio.dict())
    db.add(db_portfolio)
    db.commit()
    db.refresh(db_portfolio)
    
    # 构建返回字典（与list_portfolio一致）
    stock = db.query(Stock).filter(Stock.id == db_portfolio.stock_id).first()
    return {
        "id": db_portfolio.id,
        "stock_id": db_portfolio.stock_id,
        "shares": db_portfolio.shares,
        "avg_cost": db_portfolio.avg_cost,
        "target_price": db_portfolio.target_price,
        "stop_loss": db_portfolio.stop_loss,
        "notes": db_portfolio.notes,
        "created_at": db_portfolio.created_at,
        "updated_at": db_portfolio.updated_at,
        "stock": {"code": stock.code, "name": stock.name} if stock else None
    }

@router.put("/portfolio/{portfolio_id}", response_model=PortfolioResponse)
def update_portfolio(portfolio_id: int, portfolio: PortfolioUpdate, db: Session = Depends(get_db)):
    """更新持仓"""
    db_portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not db_portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    for key, value in portfolio.dict(exclude_unset=True).items():
        setattr(db_portfolio, key, value)
    
    db_portfolio.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio

@router.delete("/portfolio/{portfolio_id}")
def delete_portfolio(portfolio_id: int, db: Session = Depends(get_db)):
    """删除持仓"""
    db_portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not db_portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    db.delete(db_portfolio)
    db.commit()
    return {"message": "Portfolio deleted successfully"}

@router.get("/portfolio/summary")
def get_portfolio_summary(db: Session = Depends(get_db)):
    """获取持仓汇总"""
    positions = db.query(Portfolio).all()
    
    total_cost = 0
    total_value = 0
    positions_with_price = []
    
    for p in positions:
        stock = db.query(Stock).filter(Stock.id == p.stock_id).first()
        if stock:
            # 获取最新收盘价
            from app.models.database import StockDaily
            latest_price = db.query(StockDaily).filter(
                StockDaily.stock_id == p.stock_id
            ).order_by(StockDaily.trade_date.desc()).first()
            
            current_price = latest_price.close if latest_price else p.avg_cost
            cost = p.shares * p.avg_cost if p.avg_cost else 0
            value = p.shares * current_price if current_price else 0
            profit = value - cost if cost else 0
            profit_pct = (profit / cost * 100) if cost > 0 else 0
            
            total_cost += cost
            total_value += value
            
            positions_with_price.append({
                "stock_code": stock.code,
                "stock_name": stock.name,
                "shares": p.shares,
                "avg_cost": p.avg_cost,
                "current_price": current_price,
                "value": value,
                "profit": profit,
                "profit_pct": profit_pct,
                "stop_loss": p.stop_loss
            })
    
    return {
        "total_cost": total_cost,
        "total_value": total_value,
        "total_profit": total_value - total_cost,
        "profit_pct": ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0,
        "positions": positions_with_price
    }

# 账户相关API
class AccountCreate(BaseModel):
    owner: str
    balance: float = 0

class AccountUpdate(BaseModel):
    balance: float

class AccountResponse(BaseModel):
    id: int
    owner: str
    balance: float
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

@router.get("/account/{owner}")
def get_account(owner: str, db: Session = Depends(get_db)):
    """获取账户余额"""
    account = db.query(Account).filter(Account.owner == owner).first()
    if not account:
        # 如果账户不存在，创建默认账户
        account = Account(owner=owner, balance=0)
        db.add(account)
        db.commit()
        db.refresh(account)
    return account

@router.put("/account/{owner}")
def update_account(owner: str, account_data: AccountUpdate, db: Session = Depends(get_db)):
    """更新账户余额"""
    account = db.query(Account).filter(Account.owner == owner).first()
    if not account:
        # 如果账户不存在，创建新账户
        account = Account(owner=owner, balance=account_data.balance)
        db.add(account)
    else:
        account.balance = account_data.balance
        account.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(account)
    return account

@router.get("/account/{owner}/balance")
def get_account_balance(owner: str, db: Session = Depends(get_db)):
    """获取账户余额（简化版）"""
    account = db.query(Account).filter(Account.owner == owner).first()
    if not account:
        # 如果账户不存在，返回默认余额
        return {"owner": owner, "balance": 0}
    return {"owner": account.owner, "balance": account.balance}
