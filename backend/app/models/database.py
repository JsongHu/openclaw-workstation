"""
数据库模型
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, Text, UniqueConstraint, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Stock(Base):
    __tablename__ = "stocks"
    
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(100))
    market = Column(String(10))
    sector = Column(String(100))
    # 基本面指标
    pe = Column(Float)  # 市盈率
    pb = Column(Float)  # 市净率
    total_market_cap = Column(Float)  # 总市值
    circulating_market_cap = Column(Float)  # 流通市值
    created_at = Column(DateTime, default=datetime.utcnow)
    
    daily_data = relationship("StockDaily", back_populates="stock")
    indicators = relationship("StockIndicator", back_populates="stock")
    portfolio = relationship("Portfolio", back_populates="stock")

class StockDaily(Base):
    __tablename__ = "stock_daily"
    
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"))
    trade_date = Column(Date, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    amount = Column(Float)
    # 扩展行情字段
    price = Column(Float)  # 现价
    change = Column(Float)  # 涨跌额
    change_pct = Column(Float)  # 涨跌幅
    
    stock = relationship("Stock", back_populates="daily_data")

    __table_args__ = (
        UniqueConstraint('stock_id', 'trade_date', name='uix_stock_date'),
        Index('ix_stock_daily_trade_date', 'trade_date'),
        Index('ix_stock_daily_stock_id_date_desc', 'stock_id', 'trade_date'),
    )

class StockIndicator(Base):
    __tablename__ = "stock_indicators"
    
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"))
    trade_date = Column(Date, nullable=False)
    ma5 = Column(Float)
    ma10 = Column(Float)
    ma20 = Column(Float)
    ma60 = Column(Float)
    dif = Column(Float)
    dea = Column(Float)
    macd = Column(Float)
    k = Column(Float)
    d = Column(Float)
    j = Column(Float)
    rsi = Column(Float)
    boll_upper = Column(Float)
    boll_mid = Column(Float)
    boll_lower = Column(Float)
    volume_ratio = Column(Float)
    score = Column(Integer, default=0)
    signal_count = Column(Integer, default=0)
    signals_json = Column(Text)

    stock = relationship("Stock", back_populates="indicators")

    __table_args__ = (
        Index('ix_stock_indicators_stock_date', 'stock_id', 'trade_date'),
    )

class Portfolio(Base):
    __tablename__ = "portfolio"
    
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"))
    owner = Column(String(50), nullable=False, default="小猫")  # 持仓人：小猫、松
    shares = Column(Float, default=0)
    avg_cost = Column(Float)
    target_price = Column(Float)
    stop_loss = Column(Float)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    stock = relationship("Stock", back_populates="portfolio")

    __table_args__ = (
        Index('ix_portfolio_owner', 'owner'),
    )

class FundPortfolio(Base):
    __tablename__ = "fund_portfolio"
    
    id = Column(Integer, primary_key=True)
    fund_code = Column(String(20))
    fund_name = Column(String(100))
    nav = Column(Float)
    shares = Column(Float)
    avg_cost = Column(Float)
    updated_at = Column(DateTime, default=datetime.utcnow)

class DailyRecommendation(Base):
    __tablename__ = "daily_recommendations"
    
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    stock_id = Column(Integer, ForeignKey("stocks.id"))
    rank = Column(Integer)
    score = Column(Integer)
    signal_count = Column(Integer, default=0)
    signals = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Account(Base):
    """账户余额表"""
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True)
    owner = Column(String(50), nullable=False)  # 账户持有人：小猫、松
    balance = Column(Float, default=0)  # 账户余额
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('owner', name='uix_account_owner'),
    )

# 数据库引擎
DATABASE_URL = "sqlite:///./stock_system.db"
engine = create_engine(DATABASE_URL, echo=False)

def init_db():
    Base.metadata.create_all(bind=engine)
