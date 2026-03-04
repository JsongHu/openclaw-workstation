"""
量化分析引擎 - 升级版（pandas 精确指标）
评分标准（满分15分）：
  必须条件: RSI < 75, -3% < 涨跌幅 < 5%
  均线多头排列 +2, 站上MA20 +1
  MACD金叉(3日内) +2, MACD零轴上 +1
  KDJ金叉(3日内) +2, KDJ健康 +1
  RSI健康 +1, 布林支撑 +1, 温和放量 +2
  筛选门槛: 得分 >= 8, 信号数 >= 4
"""
import json
import logging
import pandas as pd
import numpy as np
from datetime import date
from sqlalchemy.orm import Session
from app.models.database import engine, Stock, StockDaily, StockIndicator, DailyRecommendation

logger = logging.getLogger(__name__)


class QuantitativeAnalyzer:
    """量化分析引擎"""

    def __init__(self):
        self.db = Session(engine)
        self._df_cache = {}  # stock_id -> (df_raw, df_with_indicators) 缓存

    def _load_df(self, stock_id: int, limit: int = 80):
        """从数据库加载 OHLCV 数据，返回 pandas DataFrame（带缓存）"""
        if stock_id in self._df_cache:
            return self._df_cache[stock_id][0]

        rows = (
            self.db.query(StockDaily)
            .filter(StockDaily.stock_id == stock_id)
            .order_by(StockDaily.trade_date.asc())
            .limit(limit)
            .all()
        )
        if len(rows) < 20:
            return None

        df = pd.DataFrame([{
            "date": r.trade_date,
            "open": r.open,
            "high": r.high,
            "low": r.low,
            "close": r.close,
            "volume": r.volume,
        } for r in rows])
        df = df.dropna(subset=["close"])
        if len(df) < 20:
            return None

        self._df_cache[stock_id] = (df.copy(), None)
        return df

    def _load_and_compute(self, stock_id: int):
        """加载数据并计算指标（带缓存，避免重复计算）"""
        if stock_id in self._df_cache and self._df_cache[stock_id][1] is not None:
            return self._df_cache[stock_id][1]

        df = self._load_df(stock_id)
        if df is None:
            return None
        df = self._compute_indicators(df)
        self._df_cache[stock_id] = (self._df_cache[stock_id][0], df)
        return df

    def clear_cache(self):
        """清除缓存（批量分析完成后调用）"""
        self._df_cache.clear()

    def _compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算全部技术指标序列"""
        # 均线
        for p in [5, 10, 20, 60]:
            df[f"MA{p}"] = df["close"].rolling(p).mean()

        # MACD
        ema12 = df["close"].ewm(span=12, adjust=False).mean()
        ema26 = df["close"].ewm(span=26, adjust=False).mean()
        df["DIF"] = ema12 - ema26
        df["DEA"] = df["DIF"].ewm(span=9, adjust=False).mean()
        df["MACD"] = (df["DIF"] - df["DEA"]) * 2

        # KDJ（使用 high/low 的 RSV，EWM 迭代）
        low9 = df["low"].rolling(9, min_periods=9).min()
        high9 = df["high"].rolling(9, min_periods=9).max()
        rsv = (df["close"] - low9) / (high9 - low9 + 1e-9) * 100
        df["K"] = rsv.ewm(com=2, adjust=False).mean()
        df["D"] = df["K"].ewm(com=2, adjust=False).mean()
        df["J"] = 3 * df["K"] - 2 * df["D"]

        # RSI
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df["RSI"] = 100 - 100 / (1 + gain / (loss + 1e-9))

        # 布林带
        df["BOLL_MID"] = df["close"].rolling(20).mean()
        std20 = df["close"].rolling(20).std()
        df["BOLL_UPPER"] = df["BOLL_MID"] + 2 * std20
        df["BOLL_LOWER"] = df["BOLL_MID"] - 2 * std20

        # 量比（当日 / 5日均量）
        df["VOL_MA5"] = df["volume"].rolling(5).mean()
        df["VOL_RATIO"] = df["volume"] / (df["VOL_MA5"] + 1e-9)

        # 涨跌幅（用前收盘价，更准确）
        df["PCT_CHANGE"] = df["close"].pct_change() * 100

        return df

    def _detect_crossover(self, fast: pd.Series, slow: pd.Series, lookback: int = 3) -> bool:
        """检测最近 lookback 根 K 线内是否发生金叉（fast 上穿 slow）"""
        combined = pd.concat([fast, slow], axis=1).dropna()
        if len(combined) < 2:
            return False
        tail = combined.tail(lookback + 1)
        f, s = tail.iloc[:, 0], tail.iloc[:, 1]
        for i in range(1, len(tail)):
            if f.iloc[i] > s.iloc[i] and f.iloc[i - 1] <= s.iloc[i - 1]:
                return True
        return False

    def _fv(self, series_val, default=0.0):
        """安全取浮点值"""
        if series_val is None:
            return default
        try:
            v = float(series_val)
            return default if np.isnan(v) else v
        except Exception:
            return default

    def calculate_indicators(self, stock_id: int):
        """返回最新一日的指标标量字典（供存库用）"""
        df = self._load_and_compute(stock_id)
        if df is None:
            return None
        last = df.iloc[-1]
        fv = self._fv

        return {
            "ma5": fv(last.get("MA5")), "ma10": fv(last.get("MA10")),
            "ma20": fv(last.get("MA20")), "ma60": fv(last.get("MA60")),
            "dif": fv(last.get("DIF")), "dea": fv(last.get("DEA")), "macd": fv(last.get("MACD")),
            "k": fv(last.get("K")), "d": fv(last.get("D")), "j": fv(last.get("J")),
            "rsi": fv(last.get("RSI")),
            "boll_upper": fv(last.get("BOLL_UPPER")), "boll_mid": fv(last.get("BOLL_MID")),
            "boll_lower": fv(last.get("BOLL_LOWER")),
            "volume_ratio": fv(last.get("VOL_RATIO")),
        }

    def score_stock(self, stock_id: int) -> dict:
        """评分（满分15分），返回 score / signals / signal_count"""
        df = self._load_and_compute(stock_id)
        if df is None:
            return {"score": 0, "signals": [], "signal_count": 0}
        last = df.iloc[-1]
        fv = self._fv

        rsi = fv(last.get("RSI"), 50)
        pct = fv(last.get("PCT_CHANGE"), 0)
        close = fv(last.get("close"), 0)

        # 一票否决
        if rsi >= 75:
            return {"score": 0, "signals": ["RSI追高"], "signal_count": 0}
        if not (-3 < pct < 5):
            return {"score": 0, "signals": ["涨跌幅过大"], "signal_count": 0}

        score = 0
        signals = []

        # 均线多头排列 +2
        ma5, ma10, ma20, ma60 = fv(last.get("MA5")), fv(last.get("MA10")), fv(last.get("MA20")), fv(last.get("MA60"))
        if ma5 and ma10 and ma20 and ma60 and ma5 > ma10 > ma20 > ma60:
            score += 2
            signals.append("均线多头排列")

        # 站上MA20 +1
        if close and ma20 and close > ma20:
            score += 1
            signals.append("站上MA20")

        # MACD金叉（3日内上穿）+2
        if self._detect_crossover(df["DIF"], df["DEA"]):
            score += 2
            signals.append("MACD金叉")

        # MACD零轴上 +1
        if fv(last.get("DIF")) > 0 and fv(last.get("DEA")) > 0:
            score += 1
            signals.append("MACD零轴上")

        # KDJ金叉（3日内上穿）+2
        if self._detect_crossover(df["K"], df["D"]):
            score += 2
            signals.append("KDJ金叉")

        # KDJ健康 +1
        k = fv(last.get("K"), 50)
        if 20 < k < 80:
            score += 1
            signals.append("KDJ健康")

        # RSI健康 +1
        if 40 < rsi < 70:
            score += 1
            signals.append("RSI健康")

        # 布林支撑 +1
        boll_mid = fv(last.get("BOLL_MID"))
        if boll_mid and close and close >= boll_mid * 0.98:
            score += 1
            signals.append("布林支撑")

        # 温和放量 +2
        vol_ratio = fv(last.get("VOL_RATIO"))
        if 1.2 < vol_ratio < 3.0:
            score += 2
            signals.append("温和放量")

        return {
            "score": score,
            "signals": signals,
            "signal_count": len(signals),
            "rsi": rsi,
            "pct_change": pct,
        }

    def run_daily_analysis(self):
        """每日定时分析：计算所有股票指标 + 生成推荐（15:30 由调度器调用）"""
        MIN_SCORE = 8
        MIN_SIGNALS = 4
        today = date.today()

        all_stocks = self.db.query(Stock).all()
        logger.info(f"开始每日指标分析，共 {len(all_stocks)} 只股票...")

        scored = []
        indicator_objects = []

        # 清除当日已有指标（重新计算）
        self.db.query(StockIndicator).filter(StockIndicator.trade_date == today).delete()
        self.db.commit()

        for i, stock in enumerate(all_stocks):
            if i % 500 == 0 and i > 0:
                logger.info(f"  分析进度: {i}/{len(all_stocks)}")
                # 定期清缓存释放内存
                self.clear_cache()

            result = self.score_stock(stock.id)
            indicators = self.calculate_indicators(stock.id)

            if not indicators:
                continue

            # 所有有数据的股票都保存指标（含 score 和 signal_count）
            indicator_objects.append(StockIndicator(
                stock_id=stock.id, trade_date=today,
                score=result.get("score", 0),
                signal_count=result.get("signal_count", 0),
                signals_json=json.dumps(result.get("signals", []), ensure_ascii=False),
                rsi=indicators.get("rsi"), ma5=indicators.get("ma5"),
                ma10=indicators.get("ma10"), ma20=indicators.get("ma20"),
                ma60=indicators.get("ma60"), dif=indicators.get("dif"),
                dea=indicators.get("dea"), macd=indicators.get("macd"),
                k=indicators.get("k"), d=indicators.get("d"), j=indicators.get("j"),
                boll_upper=indicators.get("boll_upper"), boll_mid=indicators.get("boll_mid"),
                boll_lower=indicators.get("boll_lower"),
                volume_ratio=indicators.get("volume_ratio"),
            ))

            # 达标的加入推荐候选
            if result["score"] >= MIN_SCORE and result["signal_count"] >= MIN_SIGNALS:
                scored.append((stock, result))

            # 每1000条批量写入一次
            if len(indicator_objects) >= 1000:
                self.db.bulk_save_objects(indicator_objects)
                self.db.commit()
                indicator_objects = []

        # 写入剩余指标
        if indicator_objects:
            self.db.bulk_save_objects(indicator_objects)
            self.db.commit()

        self.clear_cache()
        logger.info(f"指标计算完成，达到推荐门槛: {len(scored)} 只")

        # 生成 Top 30 推荐
        scored.sort(key=lambda x: (x[1]["score"], x[1]["signal_count"]), reverse=True)
        top = scored[:30]

        self.db.query(DailyRecommendation).filter(DailyRecommendation.date == today).delete()
        self.db.commit()

        for rank, (stock, result) in enumerate(top, 1):
            self.db.add(DailyRecommendation(
                date=today, stock_id=stock.id, rank=rank,
                score=result["score"], signal_count=result["signal_count"],
                signals=json.dumps(result["signals"], ensure_ascii=False),
            ))

        self.db.commit()
        logger.info(f"每日分析完成: 保存指标, 生成 {len(top)} 条推荐")
        return len(top)

    def close(self):
        self.clear_cache()
        self.db.close()


if __name__ == "__main__":
    analyzer = QuantitativeAnalyzer()
    result = analyzer.score_stock(1)
    print(result)
    analyzer.close()
