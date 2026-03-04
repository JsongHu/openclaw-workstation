"""
股票数据采集服务（优化版）
- 并发HTTP请求替代串行请求
- 批量commit替代逐条commit
- 预加载code→id映射替代逐条查询
- 利用东方财富批量接口替代逐只查询
"""
import requests
import time
import json
import logging
from datetime import datetime, date
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.database import engine, Stock, StockDaily, FundPortfolio

logger = logging.getLogger(__name__)


class StockCollector:
    """股票数据采集器"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.base_url = "https://hq.sinajs.cn/list="
        self.eastmoney_url = "https://push2.eastmoney.com/api/qt/stock/get"
        self.eastmoney_list_url = "https://push2.eastmoney.com/api/qt/clist/get"
        # 不使用代理
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers.update(self.headers)

    def get_realtime_quote(self, stock_code: str) -> dict:
        """获取实时行情 - 优先使用东方财富API"""
        quote = self._get_quote_eastmoney(stock_code)
        if quote:
            return quote

        # 备用新浪（复用 session）
        full_code = self._convert_code(stock_code)
        url = f"{self.base_url}{full_code}"

        try:
            response = self.session.get(url, timeout=5)
            if response.status_code == 200:
                return self._parse_quote(response.text, stock_code)
        except Exception as e:
            logger.warning(f"获取 {stock_code} 行情失败: {e}")
        return None

    def _get_quote_eastmoney(self, stock_code: str) -> dict:
        """使用东方财富API获取行情"""
        try:
            if stock_code.startswith('sh'):
                secid = f"1.{stock_code[2:]}"
            elif stock_code.startswith('sz'):
                secid = f"0.{stock_code[2:]}"
            else:
                secid = f"1.{stock_code}" if stock_code.startswith('6') else f"0.{stock_code}"

            params = {
                "secid": secid,
                "fields": "f43,f44,f45,f46,f47,f48,f50,f51,f52,f57,f58,f59,f60,f116,f117,f118"
            }

            response = self.session.get(self.eastmoney_url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    return self._parse_eastmoney(data["data"], stock_code)
        except Exception as e:
            logger.warning(f"东方财富API获取失败 {stock_code}: {e}")
        return None

    def _get_batch_quotes_eastmoney(self, page: int = 1, page_size: int = 500) -> list:
        """使用东方财富批量接口一次获取多只股票行情（替代逐只请求）"""
        try:
            params = {
                "pn": page,
                "pz": page_size,
                "po": 1,
                "np": 1,
                "fltt": 2,
                "invt": 2,
                "fid": "f3",
                "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
                "fields": "f2,f3,f4,f5,f6,f7,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f45,f57,f58,f60,f116,f117,f162,f167"
            }
            response = self.session.get(self.eastmoney_list_url, params=params, timeout=30)
            if response.status_code != 200:
                return []

            data = response.json()
            diff = data.get("data", {}).get("diff", [])
            quotes = []
            for item in diff:
                market_id = item.get('f13')
                code_num = item.get('f12', '')
                code = f"sh{code_num}" if market_id == 1 else f"sz{code_num}"
                quotes.append({
                    'code': code,
                    'name': item.get('f14'),
                    'open': item.get('f17'),
                    'high': item.get('f15'),
                    'low': item.get('f16'),
                    'close': item.get('f2'),
                    'volume': item.get('f5'),
                    'amount': item.get('f6'),
                    'price': item.get('f2'),
                    'change': item.get('f4'),
                    'change_pct': item.get('f3'),
                    'pe': item.get('f162'),
                    'pb': item.get('f167'),
                    'total_market_cap': item.get('f20'),
                    'circulating_market_cap': item.get('f21'),
                    'market': 'sh' if market_id == 1 else 'sz',
                })
            return quotes
        except Exception as e:
            logger.error(f"批量获取行情失败 (page={page}): {e}")
            return []

    def _parse_eastmoney(self, data: dict, code: str) -> dict:
        """解析东方财富数据"""
        try:
            return {
                'code': code,
                'name': data.get('f58'),
                'open': data.get('f43') / 100 if data.get('f43') else None,
                'high': data.get('f44') / 100 if data.get('f44') else None,
                'low': data.get('f45') / 100 if data.get('f45') else None,
                'close': data.get('f46') / 100 if data.get('f46') else None,
                'volume': data.get('f47'),
                'amount': data.get('f48'),
                'price': data.get('f46') / 100 if data.get('f46') else None,
                'change': ((data.get('f46') or 0) - (data.get('f43') or 0)) / 100,
                'change_pct': data.get('f60') / 100 if data.get('f60') else None,
                'pe': data.get('f162'),
                'pb': data.get('f167') / 100 if data.get('f167') else None,
                'total_market_cap': data.get('f116'),
                'circulating_market_cap': data.get('f117'),
            }
        except Exception as e:
            logger.warning(f"解析东方财富数据失败: {e}")
            return None

    def _convert_code(self, code: str) -> str:
        """转换股票代码格式"""
        if code.startswith('sh') or code.startswith('sz'):
            return code
        return f"sh{code}" if code.startswith('6') else f"sz{code}"

    def _parse_quote(self, content: str, code: str) -> dict:
        """解析新浪行情数据"""
        try:
            var_name = f"hq_str_{self._convert_code(code)}"
            if var_name in content:
                data = content.split('=')[1].strip('";\n')
                fields = data.split(',')
                if len(fields) > 30:
                    return {
                        'code': code,
                        'name': fields[0],
                        'open': float(fields[1]) if fields[1] else None,
                        'high': float(fields[2]) if fields[2] else None,
                        'low': float(fields[3]) if fields[3] else None,
                        'close': float(fields[4]) if fields[4] else None,
                        'volume': float(fields[5]) if fields[5] else None,
                        'amount': float(fields[6]) if fields[6] else None,
                    }
        except Exception as e:
            logger.warning(f"解析行情失败: {e}")
        return None

    def batch_collect(self, stock_codes: list, delay: float = 0.1):
        """批量采集 - 使用线程池并发请求"""
        results = []

        def _fetch(code):
            return self.get_realtime_quote(code)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(_fetch, code): code for code in stock_codes}
            for future in as_completed(futures):
                try:
                    quote = future.result()
                    if quote:
                        results.append(quote)
                except Exception as e:
                    logger.warning(f"并发采集异常 {futures[future]}: {e}")

        return results

    def _load_stock_code_map(self, db: Session) -> dict:
        """预加载 code→Stock 映射，避免逐条查询"""
        stocks = db.query(Stock).all()
        return {s.code: s for s in stocks}

    def _load_existing_daily_keys(self, db: Session, trade_date: date) -> set:
        """预加载当日已存在的 (stock_id, trade_date) 集合，避免逐条查重"""
        rows = db.query(StockDaily.stock_id).filter(
            StockDaily.trade_date == trade_date
        ).all()
        return {row[0] for row in rows}

    def collect_stock_list_basic(self):
        """批量获取股票列表基本信息（东方财富）- 优化版：减少commit次数"""
        try:
            url = self.eastmoney_list_url
            params = {
                "pn": 1,
                "pz": 100,
                "po": 1,
                "np": 1,
                "fltt": 2,
                "invt": 2,
                "fid": "f3",
                "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
                "fields": "f2,f3,f4,f12,f13,f14,f20,f21,f23,f24,f25,f37,f38,f45,f57,f58,f59,f60,f115,f116,f117,f118,f162,f163,f164,f167,f168,f169,f170,f171,f173,f177"
            }

            db = Session(engine)
            total_pages = 10
            today = date.today()

            # 预加载映射，避免循环内逐条查询
            code_map = self._load_stock_code_map(db)
            existing_daily = self._load_existing_daily_keys(db, today)

            for page in range(1, total_pages + 1):
                params["pn"] = page
                response = self.session.get(url, params=params, timeout=30)
                if response.status_code != 200:
                    continue

                data = response.json()
                diff = data.get("data", {}).get("diff", [])
                new_dailies = []

                for item in diff:
                    code_num = item.get('f12', '')
                    market_id = item.get('f13')
                    code = f"sh{code_num}" if market_id == 1 else f"sz{code_num}"

                    # 查找或创建股票（用内存映射）
                    stock = code_map.get(code)
                    if not stock:
                        stock = Stock(
                            code=code,
                            name=item.get('f14'),
                            market='sh' if market_id == 1 else 'sz'
                        )
                        db.add(stock)
                        db.flush()  # flush 获取 id，不 commit
                        code_map[code] = stock

                    # 更新基本信息
                    stock.name = item.get('f14')
                    pe = item.get('f162')
                    pb = item.get('f167')
                    if pe and pe != "-":
                        stock.pe = float(pe)
                    if pb and pb != "-":
                        stock.pb = float(pb)
                    if item.get('f20'):
                        stock.total_market_cap = item.get('f20')
                    if item.get('f21'):
                        stock.circulating_market_cap = item.get('f21')

                    # 保存日线数据（仅当不存在时）
                    if stock.id not in existing_daily:
                        new_dailies.append(StockDaily(
                            stock_id=stock.id,
                            trade_date=today,
                            price=item.get('f2'),
                            change_pct=item.get('f3'),
                            volume=item.get('f45'),
                            amount=item.get('f58')
                        ))
                        existing_daily.add(stock.id)

                # 每页批量添加日线 + 统一commit
                if new_dailies:
                    db.bulk_save_objects(new_dailies)
                db.commit()

                logger.info(f"第 {page} 页处理完成，获取 {len(diff)} 只股票")
                time.sleep(0.3)

            db.close()
            logger.info("股票列表基本信息更新完成")
            return True
        except Exception as e:
            logger.error(f"批量获取股票列表失败: {e}")
            return False

    def collect_all_stocks_quotes(self):
        """采集所有股票行情 - 优先 baostock，失败时回退到东方财富批量接口"""
        # 优先使用 baostock
        try:
            saved = self.collect_with_baostock()
            if saved > 0:
                return saved
            logger.warning("baostock 采集结果为空，回退到东方财富批量接口")
        except Exception as e:
            logger.warning(f"baostock 采集异常，回退到东方财富: {e}")

        # 回退到东方财富批量接口
        db = Session(engine)
        try:
            logger.info("开始使用东方财富批量接口采集行情...")
            all_quotes = []
            page = 1
            page_size = 500

            while True:
                quotes = self._get_batch_quotes_eastmoney(page=page, page_size=page_size)
                if not quotes:
                    break
                all_quotes.extend(quotes)
                logger.info(f"批量采集进度: 已获取 {len(all_quotes)} 只股票")
                page += 1
                time.sleep(0.3)

            if all_quotes:
                self._save_to_db_batch(db, all_quotes)

            logger.info(f"股票行情更新完成: {len(all_quotes)} 只")
            return len(all_quotes)
        except Exception as e:
            logger.error(f"采集股票行情失败: {e}")
            return 0
        finally:
            db.close()

    def _save_to_db_batch(self, db: Session, quotes: list):
        """批量保存到数据库 - 优化版：预加载映射 + 批量commit"""
        try:
            today = date.today()

            # 预加载映射
            code_map = self._load_stock_code_map(db)
            existing_daily = self._load_existing_daily_keys(db, today)

            new_stocks = []
            new_dailies = []

            for quote in quotes:
                code = quote['code']
                stock = code_map.get(code)

                # 创建新股票
                if not stock:
                    stock = Stock(
                        code=code,
                        name=quote.get('name'),
                        market=quote.get('market', 'sh' if code.startswith('sh') else 'sz')
                    )
                    db.add(stock)
                    db.flush()
                    code_map[code] = stock

                # 更新基本信息
                if quote.get('pe') or quote.get('pb') or quote.get('total_market_cap'):
                    stock.pe = quote.get('pe')
                    stock.pb = quote.get('pb')
                    stock.total_market_cap = quote.get('total_market_cap')
                    stock.circulating_market_cap = quote.get('circulating_market_cap')

                # 新增日线数据
                if stock.id not in existing_daily:
                    new_dailies.append(StockDaily(
                        stock_id=stock.id,
                        trade_date=today,
                        open=quote.get('open'),
                        high=quote.get('high'),
                        low=quote.get('low'),
                        close=quote.get('close'),
                        volume=quote.get('volume'),
                        amount=quote.get('amount'),
                        price=quote.get('price'),
                        change=quote.get('change'),
                        change_pct=quote.get('change_pct')
                    ))
                    existing_daily.add(stock.id)

            # 一次性批量写入
            if new_dailies:
                db.bulk_save_objects(new_dailies)
            db.commit()

            logger.info(f"成功保存 {len(new_dailies)} 条日线, 更新 {len(quotes)} 条基本信息")
        except Exception as e:
            db.rollback()
            logger.error(f"批量保存失败: {e}")

    def save_to_db(self, quotes: list):
        """保存到数据库（兼容旧调用，内部使用优化版）"""
        db = Session(engine)
        try:
            self._save_to_db_batch(db, quotes)
        finally:
            db.close()

    @staticmethod
    def _bs_convert_code(code: str) -> str:
        """baostock 代码 (sh.600036) → 数据库代码 (sh600036)"""
        return code.replace('.', '')

    @staticmethod
    def _db_to_bs_code(db_code: str) -> str:
        """数据库代码 (sh600036) → baostock 代码 (sh.600036)"""
        return db_code[:2] + '.' + db_code[2:]

    def _bs_query_single(self, bs, code: str, start_date: str, end_date: str) -> list:
        """查询单只股票的 baostock 日线数据，返回多日记录列表"""
        try:
            rs = bs.query_history_k_data_plus(
                code,
                "date,open,high,low,close,volume,amount,pctChg",
                start_date=start_date,
                end_date=end_date,
                frequency="d",
                adjustflag="3"  # 不复权
            )
            rows = []
            if rs.error_code == '0':
                while rs.next():
                    rows.append(rs.get_row_data())
            return rows
        except Exception as e:
            logger.warning(f"baostock 获取 {code} 失败: {e}")
            return []

    def collect_with_baostock(self, start_date: str = None, end_date: str = None, batch_size: int = 100, db_only: bool = False):
        """使用 baostock 采集股票日K线数据（主力数据源）

        参数：
        - start_date/end_date: 日期范围，默认当日
        - batch_size: 每批写入数据库的股票数量
        - db_only: True 时只回填数据库已有的股票（回填模式），False 时拉取 baostock 全量股票
        """
        try:
            import baostock as bs
            lg = bs.login()
            if lg.error_code != '0':
                logger.error(f"baostock 登录失败: {lg.error_msg}")
                return 0

            # 默认日期
            today = date.today()
            if not end_date:
                end_date = today.strftime('%Y-%m-%d')
            if not start_date:
                start_date = end_date

            db = Session(engine)
            code_map = self._load_stock_code_map(db)

            if db_only and code_map:
                # 回填模式：只查数据库已有的股票
                stocks_data = [
                    [self._db_to_bs_code(code), stock.name]
                    for code, stock in code_map.items()
                ]
                logger.info(f"回填模式: 从数据库读取 {len(stocks_data)} 只股票，日期范围 {start_date} ~ {end_date}")
            else:
                # 全量模式：从 baostock 获取所有股票
                rs = bs.query_stock_basic()
                stocks_data = []
                while rs.next():
                    row = rs.get_row_data()
                    if len(row) >= 6 and row[4] == '1' and row[5] == '1':
                        stocks_data.append(row)
                if not stocks_data:
                    rs = bs.query_stock_basic()
                    stocks_data = []
                    while rs.next():
                        stocks_data.append(rs.get_row_data())
                logger.info(f"全量模式: baostock 获取到 {len(stocks_data)} 只股票，日期范围 {start_date} ~ {end_date}")

            saved = 0
            total_stocks = len(stocks_data)

            # 预加载已存在的日线记录
            existing_pairs = set()
            if start_date == end_date:
                target_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                rows = db.query(StockDaily.stock_id).filter(
                    StockDaily.trade_date == target_date
                ).all()
                existing_pairs = {(row[0], end_date) for row in rows}
            else:
                target_start = datetime.strptime(start_date, '%Y-%m-%d').date()
                target_end = datetime.strptime(end_date, '%Y-%m-%d').date()
                rows = db.query(StockDaily.stock_id, StockDaily.trade_date).filter(
                    StockDaily.trade_date >= target_start,
                    StockDaily.trade_date <= target_end
                ).all()
                existing_pairs = {(row[0], row[1].strftime('%Y-%m-%d')) for row in rows}

            for batch_start in range(0, total_stocks, batch_size):
                batch_end = min(batch_start + batch_size, total_stocks)
                batch = stocks_data[batch_start:batch_end]
                batch_codes = [row[0] for row in batch]
                batch_names = {row[0]: row[1] for row in batch}

                # 批量创建缺失的股票记录（仅全量模式）
                if not db_only:
                    new_stock_added = False
                    for code in batch_codes:
                        db_code = self._bs_convert_code(code)
                        if db_code not in code_map:
                            stock = Stock(
                                code=db_code,
                                name=batch_names.get(code, ''),
                                market=db_code[:2]
                            )
                            db.add(stock)
                            code_map[db_code] = stock
                            new_stock_added = True
                    if new_stock_added:
                        db.flush()

                # 串行查询 baostock（单 TCP 连接，多线程不安全）
                daily_records = []
                for i, code in enumerate(batch_codes):
                    rows = self._bs_query_single(bs, code, start_date, end_date)

                    # 每 10 只输出一次进度
                    global_idx = batch_start + i + 1
                    if global_idx % 10 == 0 or global_idx == total_stocks:
                        logger.info(f"baostock 查询进度: {global_idx}/{total_stocks}")

                    if not rows:
                        continue

                    db_code = self._bs_convert_code(code)
                    stock = code_map.get(db_code)
                    if not stock or not stock.id:
                        continue

                    for row in rows:
                        # row: [date, open, high, low, close, volume, amount, pctChg]
                        trade_date_str = row[0]
                        if (stock.id, trade_date_str) in existing_pairs:
                            continue

                        trade_date = datetime.strptime(trade_date_str, '%Y-%m-%d').date()
                        open_p = float(row[1]) if row[1] else None
                        close_p = float(row[4]) if row[4] else None
                        change = (close_p - open_p) if (close_p and open_p) else None

                        daily_records.append(StockDaily(
                            stock_id=stock.id,
                            trade_date=trade_date,
                            open=open_p,
                            high=float(row[2]) if row[2] else None,
                            low=float(row[3]) if row[3] else None,
                            close=close_p,
                            volume=float(row[5]) if row[5] else None,
                            amount=float(row[6]) if row[6] else None,
                            price=close_p,
                            change=change,
                            change_pct=float(row[7]) if row[7] else None,
                        ))
                        existing_pairs.add((stock.id, trade_date_str))

                # 每批次批量写入
                if daily_records:
                    db.bulk_save_objects(daily_records)
                    db.commit()
                    saved += len(daily_records)

                logger.info(f"baostock 写入进度: {batch_end}/{total_stocks}, 本批 {len(daily_records)} 条, 累计 {saved} 条")

            db.close()
            bs.logout()
            logger.info(f"baostock 采集完成: {saved} 条新数据")
            return saved
        except ImportError:
            logger.error("baostock 未安装，请执行: pip install baostock")
            return 0
        except Exception as e:
            logger.error(f"baostock 采集失败: {e}")
            return 0

    def cleanup_old_daily_data(self, days: int = 30):
        """清理超过指定天数的旧日线和指标数据"""
        from datetime import timedelta
        from app.models.database import StockIndicator
        cutoff = date.today() - timedelta(days=days)
        db = Session(engine)
        try:
            daily_deleted = db.query(StockDaily).filter(StockDaily.trade_date < cutoff).delete()
            indicator_deleted = db.query(StockIndicator).filter(StockIndicator.trade_date < cutoff).delete()
            db.commit()
            logger.info(f"数据清理完成: 删除 {daily_deleted} 条日线, {indicator_deleted} 条指标 (截止 {cutoff})")
            return daily_deleted + indicator_deleted
        except Exception as e:
            db.rollback()
            logger.error(f"数据清理失败: {e}")
            return 0
        finally:
            db.close()

    def backfill_history(self, days: int = 60):
        """回填最近N个交易日的历史数据（使用 baostock，仅回填数据库已有的股票）"""
        from datetime import timedelta
        end_date = date.today().strftime('%Y-%m-%d')
        start_date = (date.today() - timedelta(days=days)).strftime('%Y-%m-%d')
        logger.info(f"开始回填历史数据: {start_date} ~ {end_date}")
        return self.collect_with_baostock(start_date=start_date, end_date=end_date, db_only=True)


class FundCollector:
    """基金数据采集器"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers.update(self.headers)

    def get_fund_nav(self, fund_code: str) -> dict:
        """获取基金净值"""
        url = f"https://fundf10.eastmoney.com/F10DataApi.aspx?type=NAV&rt=ts_{fund_code}"

        try:
            response = self.session.get(url, timeout=5)
            if response.status_code == 200:
                return self._parse_nav(response.text, fund_code)
        except Exception as e:
            logger.warning(f"获取基金 {fund_code} NAV 失败: {e}")
        return None

    def _parse_nav(self, content: str, fund_code: str) -> dict:
        """解析基金净值数据"""
        try:
            if 'apidata' in content:
                json_str = content.split('apidata=')[1].rstrip(';')
                data = json.loads(json_str)

                if data.get('Datas') and len(data['Datas']) > 0:
                    latest = data['Datas'][0]
                    return {
                        'fund_code': fund_code,
                        'nav': float(latest.get('NAV', 0)),
                        'acc_nav': float(latest.get('ACCNAV', 0)),
                        'trade_date': latest.get('FSRQ'),
                        'change_pct': float(latest.get('SD', 0).replace('%', '')) if latest.get('SD') else 0
                    }
        except Exception as e:
            logger.warning(f"解析基金净值失败: {e}")
        return None

    def update_all_funds_nav(self):
        """更新所有持仓基金的净值"""
        db = Session(engine)
        try:
            funds = db.query(FundPortfolio).all()
            updated = 0

            for fund in funds:
                nav_data = self.get_fund_nav(fund.fund_code)
                if nav_data and nav_data.get('nav'):
                    fund.nav = nav_data['nav']
                    fund.updated_at = datetime.utcnow()
                    updated += 1
                    logger.info(f"更新基金 {fund.fund_code} NAV: {nav_data['nav']}")

                time.sleep(0.5)

            db.commit()
            logger.info(f"基金净值更新完成: {updated}/{len(funds)}")
            return updated
        except Exception as e:
            db.rollback()
            logger.error(f"更新基金净值失败: {e}")
        finally:
            db.close()


# 测试
if __name__ == "__main__":
    collector = StockCollector()
    quote = collector.get_realtime_quote("sh601857")
    print(quote)
