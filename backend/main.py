"""
股票系统后端 - 主应用入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import stocks, portfolio, recommendations, funds, diary, diary_agents
from app.services.collector import StockCollector, FundCollector
from app.services.analyzer import QuantitativeAnalyzer
from app.services.scheduler import start_scheduler
from contextlib import asynccontextmanager

# 全局实例
stock_collector = StockCollector()
fund_collector = FundCollector()
analyzer = QuantitativeAnalyzer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    start_scheduler(stock_collector, fund_collector, analyzer)
    yield
    # 关闭时
    analyzer.close()


app = FastAPI(title="股票分析系统", version="1.0.0", lifespan=lifespan)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(stocks.router, prefix="/api/stocks", tags=["股票"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["持仓"])
app.include_router(recommendations.router, prefix="/api/recommendations", tags=["推荐"])
app.include_router(funds.router, prefix="/api/funds", tags=["基金"])
app.include_router(diary.router, prefix="/api/diary", tags=["日记"])
app.include_router(diary_agents.router, prefix="/api/diary-agents", tags=["日记聚合"])

@app.get("/")
def root():
    return {"message": "股票分析系统 API", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "ok"}
