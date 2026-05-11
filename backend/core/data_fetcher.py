"""
股票数据获取模块
使用akshare获取A股实时行情和历史数据
跨平台兼容：支持 Windows、macOS、Linux
"""
import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
from typing import List, Dict, Optional
import time
import logging

from .config import get_cache_dir_path, MAX_STOCK_PRICE

logger = logging.getLogger(__name__)


class DataFetcher:
    """股票数据获取器"""

    def __init__(self, use_cache: bool = True):
        """
        初始化数据获取器

        Args:
            use_cache: 是否使用缓存
        """
        self.use_cache = use_cache
        self.cache_dir = Path(get_cache_dir_path())
        self.cache_file = self.cache_dir / 'stock_list.json'

    def get_all_a_stocks(self) -> pd.DataFrame:
        """
        获取所有A股股票列表

        Returns:
            包含股票代码、名称等信息的DataFrame
        """
        try:
            logger.info("正在获取A股股票列表...")
            # 使用akshare获取A股列表（sina数据源更稳定）
            try:
                stock_info = ak.stock_zh_a_spot()
                logger.info(f"获取到 {len(stock_info)} 只股票数据(sina)")
            except Exception as e1:
                logger.warning(f"sina数据源失败: {e1}")
                # 尝试eastmoney源作为备用
                stock_info = ak.stock_zh_a_spot_em()
                logger.info(f"获取到 {len(stock_info)} 只股票数据(eastmoney)")

            # 筛选条件：价格不超过20元且正在交易的股票
            # sina数据源返回代码格式为 sh600000 或 sz000001
            stock_info = stock_info[
                (stock_info['最新价'] <= MAX_STOCK_PRICE) &
                (stock_info['最新价'] > 0) &
                (stock_info['最新价'] > 1) &
                (stock_info['代码'].str.match(r'^(sh|sz)[036]\d{5}$'))  # 沪深A股
            ]

            logger.info(f"筛选出符合条件的股票: {len(stock_info)}只")
            return stock_info

        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            raise

    def get_realtime_quotes(self, stock_codes: List[str]) -> pd.DataFrame:
        """
        批量获取实时行情数据

        Args:
            stock_codes: 股票代码列表

        Returns:
            实时行情DataFrame
        """
        try:
            logger.info(f"正在获取 {len(stock_codes)} 只股票的实时行情...")

            # 获取实时行情
            realtime_data = ak.stock_zh_a_spot_em()

            # 过滤目标股票
            realtime_data = realtime_data[realtime_data['代码'].isin(stock_codes)]

            return realtime_data

        except Exception as e:
            logger.error(f"获取实时行情失败: {e}")
            raise

    def get_stock_history(self, stock_code: str, days: int = 30) -> pd.DataFrame:
        """
        获取单只股票的历史行情数据

        Args:
            stock_code: 股票代码 (格式: sh600000 或 sz000001 或 纯代码)
            days: 获取的历史天数

        Returns:
            历史行情DataFrame
        """
        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

            # 处理代码格式 - akshare的stock_zh_a_daily需要带市场前缀
            if not stock_code.startswith(('sh', 'sz')):
                if stock_code.startswith('6'):
                    stock_code = 'sh' + stock_code
                else:
                    stock_code = 'sz' + stock_code

            # 使用akshare获取历史数据 (使用stock_zh_a_daily接口)
            hist_data = ak.stock_zh_a_daily(
                symbol=stock_code,
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"  # 前复权
            )

            # 重命名列以匹配后续分析
            column_mapping = {
                'date': '日期',
                'open': '开盘',
                'high': '最高',
                'low': '最低',
                'close': '收盘',
                'volume': '成交量',
                'amount': '成交额'
            }
            for eng, chn in column_mapping.items():
                if eng in hist_data.columns:
                    hist_data = hist_data.rename(columns={eng: chn})

            return hist_data

        except Exception as e:
            logger.warning(f"获取股票 {stock_code} 历史数据失败: {e}")
            return pd.DataFrame()

    def batch_get_history(self, stock_codes: List[str], days: int = 30) -> Dict[str, pd.DataFrame]:
        """
        批量获取多只股票的历史数据（串行，避免并发崩溃）

        Args:
            stock_codes: 股票代码列表
            days: 获取的历史天数

        Returns:
            字典：{股票代码: 历史数据DataFrame}
        """
        import time
        result = {}
        logger.info(f"串行获取 {len(stock_codes)} 只股票历史数据...")

        # 串行获取以避免py_mini_racer并发崩溃
        for i, code in enumerate(stock_codes):
            try:
                logger.info(f"获取 {code} ({i+1}/{len(stock_codes)})...")
                data = self.get_stock_history(code, days)
                if not data.empty:
                    result[code] = data
                # 添加小延迟避免请求过快
                time.sleep(0.5)
            except Exception as e:
                logger.warning(f"股票 {code} 获取失败: {e}")

        logger.info(f"成功获取 {len(result)} 只股票历史数据")
        return result

    def get_bid_data(self) -> pd.DataFrame:
        """
        获取集合竞价数据

        Returns:
            集合竞价数据DataFrame，包含竞价价格、竞价量等
        """
        try:
            logger.info("正在获取集合竞价数据...")

            # 使用akshare获取集合竞价数据
            # 注意：这个接口可能需要在交易时段才能获取有效数据
            bid_data = ak.stock_zh_a_spot_em()

            # 提取竞价相关字段
            bid_info = bid_data[['代码', '名称', '最新价', '昨收', '成交量', '成交额']].copy()

            # 计算竞价相关指标
            bid_info['竞价涨幅'] = (bid_info['最新价'] - bid_info['昨收']) / bid_info['昨收'] * 100
            bid_info['竞价量比'] = bid_info['成交量']  # 需要对比历史数据计算真正的量比

            return bid_info

        except Exception as e:
            logger.error(f"获取集合竞价数据失败: {e}")
            raise

    def get_capital_flow(self, stock_code: str) -> pd.DataFrame:
        """
        获取个股资金流向数据

        Args:
            stock_code: 股票代码

        Returns:
            资金流向DataFrame
        """
        try:
            # 使用akshare获取资金流向
            flow_data = ak.stock_individual_fund_flow(stock=stock_code)

            return flow_data

        except Exception as e:
            logger.warning(f"获取股票 {stock_code} 资金流向失败: {e}")
            return pd.DataFrame()

    def get_market_capital_flow(self) -> pd.DataFrame:
        """
        获取全市场资金流向数据

        Returns:
            市场资金流向DataFrame
        """
        try:
            logger.info("正在获取市场资金流向数据...")

            # 获取市场资金流向
            flow_data = ak.stock_market_fund_flow()

            return flow_data

        except Exception as e:
            logger.error(f"获取市场资金流向失败: {e}")
            return pd.DataFrame()

    def save_cache(self, data: Dict, filename: str):
        """
        保存数据到缓存

        Args:
            data: 要缓存的数据
            filename: 缓存文件名
        """
        if not self.use_cache:
            return

        cache_path = self.cache_dir / filename
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, default=str)
            logger.info(f"数据已缓存到 {cache_path}")
        except Exception as e:
            logger.warning(f"缓存保存失败: {e}")

    def load_cache(self, filename: str, max_age_minutes: int = 30) -> Optional[Dict]:
        """
        从缓存加载数据

        Args:
            filename: 缓存文件名
            max_age_minutes: 缓存最大有效时间（分钟）

        Returns:
            缓存数据，如果过期或不存在则返回None
        """
        if not self.use_cache:
            return None

        cache_path = self.cache_dir / filename
        if not cache_path.exists():
            return None

        # 检查缓存是否过期
        file_mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        if datetime.now() - file_mtime > timedelta(minutes=max_age_minutes):
            logger.info("缓存已过期")
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"缓存读取失败: {e}")
            return None

    def get_filtered_stocks(self, min_price: float = 2.0, max_price: float = MAX_STOCK_PRICE) -> pd.DataFrame:
        """
        获取经过价格筛选的股票列表

        Args:
            min_price: 最小价格
            max_price: 最大价格

        Returns:
            筛选后的股票列表DataFrame
        """
        all_stocks = self.get_all_a_stocks()

        # 进一步筛选
        filtered = all_stocks[
            (all_stocks['最新价'] >= min_price) &
            (all_stocks['最新价'] <= max_price)
        ]

        return filtered