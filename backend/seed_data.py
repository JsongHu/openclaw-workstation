"""
数据初始化脚本 — 从全量 A 股代码文件扫描并生成推荐
读取 all_stock_codes_no_gem.txt → 批量验证有效股票 → 并发采集K线 → 量化分析 → 生成推荐
"""
import sys
import os
import json
import time
import logging
import requests
from datetime import date, datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.orm import Session

sys.path.insert(0, ".")
from app.models.database import (
    engine, init_db, Stock, StockDaily, StockIndicator, DailyRecommendation
)
from app.services.analyzer import QuantitativeAnalyzer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

# 全量代码文件（可通过环境变量覆盖）
CODES_FILE = os.environ.get(
    "STOCK_CODES_FILE",
    "/Users/hjsclaw/.openclaw/workspace-finance/stock_analysis/all_stock_codes_no_gem.txt",
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://finance.sina.com.cn",
}

MIN_SCORE = 8
MIN_SIGNALS = 4


# ──────────────────────────────────────────────
# Step 1: 读取代码文件
# ──────────────────────────────────────────────
def load_codes_from_file(filepath: str) -> list:
    """从文件读取股票代码列表（每行第一列为代码）"""
    codes = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split()
            if parts:
                codes.append(parts[0])
    log.info(f"从文件读取 {len(codes)} 个代码: {filepath}")
    return codes


# ──────────────────────────────────────────────
# Step 2: 批量验证有效股票，获取名称
# ──────────────────────────────────────────────
def batch_validate_stocks(codes: list, batch_size: int = 100) -> dict:
    """
    调用新浪实时行情 API 批量检查代码是否有效，并获取股票中文名。
    返回 {code: name}，只包含有效（正常上市）股票。
    """
    valid = {}

    def fetch_batch(batch):
        url = f"https://hq.sinajs.cn/list={','.join(batch)}"
        result = {}
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                return result
            for line in resp.text.split("\n"):
                line = line.strip()
                if "hq_str_" not in line or "=" not in line:
                    continue
                try:
                    code_key = line.split("=")[0].replace("var hq_str_", "").strip()
                    data_part = line.split("=", 1)[1].strip().strip('"').rstrip('";').strip('"')
                    if not data_part or "," not in data_part:
                        continue
                    name = data_part.split(",")[0].strip()
                    # 过滤无效：名称为空、纯数字、或与代码相同
                    if name and not name.replace(".", "").isdigit() and name != code_key:
                        result[code_key] = name
                except Exception:
                    continue
        except Exception:
            pass
        return result

    batches = [codes[i : i + batch_size] for i in range(0, len(codes), batch_size)]
    log.info(f"分 {len(batches)} 批（每批 {batch_size} 个）验证有效股票...")

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_batch, b) for b in batches]
        for i, future in enumerate(as_completed(futures), 1):
            valid.update(future.result())
            if i % 20 == 0 or i == len(batches):
                log.info(f"  验证进度: {i}/{len(batches)} 批，已找到 {len(valid)} 只有效股票")

    log.info(f"有效股票共 {len(valid)} 只（原始 {len(codes)} 个代码）")
    return valid


# ──────────────────────────────────────────────
# Step 3: K线采集（并发）
# ──────────────────────────────────────────────
def fetch_kline(code: str, days: int = 80) -> list:
    """从新浪 JSONP 接口获取日线K线数据"""
    url = (
        f"https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_{code}="
        f"/CN_MarketDataService.getKLineData"
    )
    params = {"symbol": code, "scale": "240", "ma": "no", "datalen": days}
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=5)
        text = resp.text
        start = text.find("(")
        end = text.rfind(")")
        if start == -1 or end == -1:
            return []
        data = json.loads(text[start + 1 : end])
        return data if data and len(data) >= 20 else []
    except Exception:
        return []


def parallel_fetch_klines(stocks_to_fetch: list, workers: int = 15) -> dict:
    """
    并发采集K线，返回 {stock_id: [bar, ...]}
    stocks_to_fetch: list of Stock ORM 对象
    """
    results = {}

    def do_fetch(stock):
        bars = fetch_kline(stock.code, 80)
        return stock.id, bars

    total = len(stocks_to_fetch)
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(do_fetch, s): s for s in stocks_to_fetch}
        for future in as_completed(futures):
            done += 1
            if done % 200 == 0:
                log.info(f"  K线采集进度: {done}/{total}")
            sid, bars = future.result()
            if bars:
                results[sid] = bars

    log.info(f"K线采集完成: {len(results)}/{total} 只有数据")
    return results


# ──────────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────────
def seed():
    init_db()
    db = Session(engine)
    log.info("=== 开始全量数据初始化 ===")

    # ── 1. 读取代码文件 ──
    if os.path.exists(CODES_FILE):
        all_codes = load_codes_from_file(CODES_FILE)
    else:
        log.error(f"代码文件不存在: {CODES_FILE}")
        db.close()
        return

    # ── 2. 批量验证，获取有效股票名称 ──
    valid_stocks = batch_validate_stocks(all_codes)
    if not valid_stocks:
        log.error("未获取到有效股票，退出")
        db.close()
        return

    # ── 3. 写入股票基础信息（只插入新增的）──
    log.info("写入股票基础信息...")
    new_count = 0
    for code, name in valid_stocks.items():
        existing = db.query(Stock).filter(Stock.code == code).first()
        if not existing:
            db.add(Stock(code=code, name=name, market=code[:2], sector=""))
            new_count += 1
        elif existing.name != name:
            # 更新名称（防止旧数据名称有误）
            existing.name = name
    db.commit()
    total_in_db = db.query(Stock).count()
    log.info(f"股票总数: {total_in_db} 只（本次新增 {new_count} 只）")

    # ── 4. 并发采集 K 线 ──
    all_stocks = db.query(Stock).all()
    # 只采集 K 线不足的股票
    to_fetch = [
        s for s in all_stocks
        if db.query(StockDaily).filter(StockDaily.stock_id == s.id).count() < 60
    ]
    log.info(f"需要采集K线: {len(to_fetch)} 只，跳过已有数据: {len(all_stocks) - len(to_fetch)} 只")

    kline_data = parallel_fetch_klines(to_fetch, workers=15)

    # 批量写入K线（每只股票用独立 Session 避免锁竞争）
    saved_bars = 0
    for stock_id, bars in kline_data.items():
        s_db = Session(engine)
        try:
            added = 0
            for bar in bars:
                try:
                    trade_date = datetime.strptime(bar["day"], "%Y-%m-%d").date()
                    exists = s_db.query(StockDaily).filter(
                        StockDaily.stock_id == stock_id,
                        StockDaily.trade_date == trade_date,
                    ).first()
                    if not exists:
                        s_db.add(StockDaily(
                            stock_id=stock_id,
                            trade_date=trade_date,
                            open=float(bar["open"]),
                            high=float(bar["high"]),
                            low=float(bar["low"]),
                            close=float(bar["close"]),
                            volume=float(bar["volume"]),
                            amount=0,
                        ))
                        added += 1
                except Exception:
                    continue
            s_db.commit()
            saved_bars += added
        except Exception:
            s_db.rollback()
        finally:
            s_db.close()

    log.info(f"K线写入完成，新增 {saved_bars} 条日线记录")

    # ── 5. 量化分析 ──
    log.info("=== 开始量化分析 ===")
    analyzer = QuantitativeAnalyzer()
    today = date.today()
    scored = []

    all_stocks = db.query(Stock).all()
    for i, stock in enumerate(all_stocks):
        if i % 500 == 0:
            log.info(f"  分析进度: {i}/{len(all_stocks)}")
        result = analyzer.score_stock(stock.id)
        if not result or result["score"] < MIN_SCORE or result["signal_count"] < MIN_SIGNALS:
            continue

        indicators = analyzer.calculate_indicators(stock.id)
        if indicators:
            existing_ind = db.query(StockIndicator).filter(
                StockIndicator.stock_id == stock.id,
                StockIndicator.trade_date == today,
            ).first()
            if not existing_ind:
                db.add(StockIndicator(
                    stock_id=stock.id, trade_date=today,
                    score=result["score"], signal_count=result["signal_count"],
                    signals_json=json.dumps(result["signals"], ensure_ascii=False),
                    rsi=indicators.get("rsi"), ma5=indicators.get("ma5"),
                    ma10=indicators.get("ma10"), ma20=indicators.get("ma20"),
                    ma60=indicators.get("ma60"), dif=indicators.get("dif"),
                    dea=indicators.get("dea"), macd=indicators.get("macd"),
                    k=indicators.get("k"), d=indicators.get("d"), j=indicators.get("j"),
                    boll_upper=indicators.get("boll_upper"), boll_mid=indicators.get("boll_mid"),
                    boll_lower=indicators.get("boll_lower"),
                    volume_ratio=indicators.get("volume_ratio"),
                ))
                db.commit()

        scored.append((stock, result))

    analyzer.close()
    log.info(f"达到推荐门槛（≥{MIN_SCORE}分且≥{MIN_SIGNALS}信号）: {len(scored)} 只")

    # ── 6. 生成 Top 30 推荐 ──
    scored.sort(key=lambda x: (x[1]["score"], x[1]["signal_count"]), reverse=True)
    top = scored[:30]

    db.query(DailyRecommendation).filter(DailyRecommendation.date == today).delete()
    db.commit()

    for rank, (stock, result) in enumerate(top, 1):
        db.add(DailyRecommendation(
            date=today, stock_id=stock.id, rank=rank,
            score=result["score"], signal_count=result["signal_count"],
            signals=json.dumps(result["signals"], ensure_ascii=False),
        ))
        log.info(f"  #{rank} {stock.code} {stock.name}: {result['score']}分 | {result['signals']}")

    db.commit()
    log.info(f"=== 生成 {len(top)} 条推荐，初始化完成 ===")
    db.close()


if __name__ == "__main__":
    seed()
