"""
定时任务调度器
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime

logger = logging.getLogger(__name__)

# 全局调度器实例
scheduler = BackgroundScheduler()


def setup_scheduler(stock_collector=None, fund_collector=None, analyzer=None):
    """配置定时任务"""

    # 每日收盘后更新基金净值 (22:00 执行)
    if fund_collector:
        scheduler.add_job(
            func=fund_collector.update_all_funds_nav,
            trigger=CronTrigger(hour=22, minute=0),
            id='update_fund_nav',
            name='更新基金净值',
            replace_existing=True
        )

    if stock_collector:
        # 主力任务：每日用 baostock 采集当日完整日线 (18:30 执行，确保数据已入库)
        scheduler.add_job(
            func=stock_collector.collect_with_baostock,
            trigger=CronTrigger(hour=18, minute=30),
            id='baostock_daily_collect',
            name='baostock每日行情采集',
            replace_existing=True
        )

        # 辅助任务：盘中每30分钟用东方财富更新实时行情（交易时间 9:30-15:00）
        scheduler.add_job(
            func=stock_collector.collect_stock_list_basic,
            trigger=CronTrigger(
                day_of_week='mon-fri',
                hour='9-14',
                minute='0,30'
            ),
            id='update_stock_basic',
            name='盘中实时行情更新',
            replace_existing=True
        )

        # 每日清理超过90天的旧数据 (17:00 执行)
        scheduler.add_job(
            func=lambda: stock_collector.cleanup_old_daily_data(days=90),
            trigger=CronTrigger(hour=17, minute=0),
            id='cleanup_old_data',
            name='清理旧数据',
            replace_existing=True
        )

    # 每日 19:00 计算所有股票技术指标和推荐（在 baostock 采集完成后）
    if analyzer:
        scheduler.add_job(
            func=analyzer.run_daily_analysis,
            trigger=CronTrigger(hour=19, minute=0),
            id='daily_indicator_calc',
            name='每日指标计算与推荐',
            replace_existing=True
        )

    # 每10分钟自检一次
    scheduler.add_job(
        func=health_check,
        trigger=IntervalTrigger(minutes=10),
        id='health_check',
        name='系统自检',
        replace_existing=True
    )

    logger.info("定时任务配置完成")


def health_check():
    """系统自检任务"""
    logger.info(f"[{datetime.now()}] 系统自检 - 运行正常")


def start_scheduler(stock_collector=None, fund_collector=None, analyzer=None):
    """启动调度器"""
    setup_scheduler(stock_collector, fund_collector, analyzer)
    if not scheduler.running:
        scheduler.start()
        logger.info("调度器已启动")
    return scheduler


def stop_scheduler():
    """停止调度器"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("调度器已停止")
