"""
回填近90天日线数据脚本
使用 baostock 采集所有股票近90个自然日（约60个交易日）的 OHLCV 数据，
满足 MA60 等技术指标计算需求，然后运行量化分析生成指标和推荐。

用法: cd backend && python backfill_30d.py
"""
import sys
import logging

sys.path.insert(0, ".")

from app.services.collector import StockCollector
from app.services.analyzer import QuantitativeAnalyzer
from app.models.database import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def main():
    init_db()

    # 1. 回填近90天日线数据（约60个交易日，满足MA60计算需求）
    log.info("=== 开始回填近90天日线数据 ===")
    collector = StockCollector()
    saved = collector.backfill_history(days=90)
    log.info(f"=== 日线回填完成: {saved} 条记录 ===")

    if saved == 0:
        log.warning("未采集到任何数据，请检查 baostock 是否安装以及网络连接")
        return

    # 2. 计算技术指标和推荐
    log.info("=== 开始计算技术指标 ===")
    analyzer = QuantitativeAnalyzer()
    try:
        analyzer.run_daily_analysis()
        log.info("=== 指标计算完成 ===")
    except Exception as e:
        log.error(f"指标计算失败: {e}")
    finally:
        analyzer.close()


if __name__ == "__main__":
    main()
