"""
集合竞价数据处理模块
专注于9:15-9:25竞价时段的数据获取和分析
跨平台兼容：支持 Windows、macOS、Linux
"""
import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Tuple
import logging
import time as time_module
from pathlib import Path
import sys

# 使用 pathlib 确保跨平台路径兼容
backend_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_path))

from core.config import (
    PRE_MARKET_START, PRE_MARKET_END, MARKET_OPEN,
    VOLUME_PRICE_THRESHOLDS, get_cache_dir_path
)
from core.data_fetcher import DataFetcher

logger = logging.getLogger(__name__)


class PreMarketAnalyzer:
    """集合竞价分析器"""

    def __init__(self):
        """初始化竞价分析器"""
        self.fetcher = DataFetcher()
        self.pre_market_data = None
        self.last_update_time = None

    def is_pre_market_time(self) -> bool:
        """
        判断当前是否在集合竞价时段

        Returns:
            是否在竞价时段
        """
        now = datetime.now().time()
        return PRE_MARKET_START <= now <= PRE_MARKET_END

    def is_trading_day(self) -> bool:
        """
        判断今天是否为交易日

        Returns:
            是否为交易日
        """
        # 简单判断：周末不是交易日
        weekday = datetime.now().weekday()
        if weekday >= 5:  # 周六、周日
            return False

        # TODO: 添加节假日判断
        return True

    def get_bid_quotes(self) -> pd.DataFrame:
        """
        获取集合竞价行情

        Returns:
            集合竞价行情DataFrame
        """
        try:
            logger.info("正在获取集合竞价行情...")

            # 使用akshare获取实时行情（sina数据源更稳定）
            try:
                quotes = ak.stock_zh_a_spot()
                logger.info(f"获取到 {len(quotes)} 只股票数据(sina)")
            except Exception as e:
                logger.warning(f"sina数据源失败: {e}, 尝试eastmoney...")
                quotes = ak.stock_zh_a_spot_em()
                logger.info(f"获取到 {len(quotes)} 只股票数据(eastmoney)")

            # 添加时间戳
            quotes['获取时间'] = datetime.now()

            # 筛选有效竞价数据
            quotes = quotes[
                (quotes['最新价'] > 0) &
                (quotes['成交量'] > 0)
            ]

            self.pre_market_data = quotes
            self.last_update_time = datetime.now()

            logger.info(f"筛选出 {len(quotes)} 只有效股票数据")
            return quotes

        except Exception as e:
            logger.error(f"获取竞价行情失败: {e}")
            raise

    def calculate_bid_metrics(self, stock_code: str, history_data: pd.DataFrame) -> Dict:
        """
        计算集合竞价指标

        Args:
            stock_code: 股票代码
            history_data: 历史数据

        Returns:
            竞价指标字典
        """
        try:
            if self.pre_market_data is None:
                return {}

            # 获取当前股票竞价数据
            stock_bid = self.pre_market_data[
                self.pre_market_data['代码'] == stock_code
            ]

            if stock_bid.empty:
                return {}

            bid_info = stock_bid.iloc[0]

            # 竞价价格
            bid_price = float(bid_info['最新价'])
            # 昨收价格
            prev_close = float(bid_info['昨收'])
            # 竞价成交量
            bid_volume = float(bid_info['成交量'])

            # 计算竞价涨幅
            bid_change_pct = (bid_price - prev_close) / prev_close if prev_close > 0 else 0

            # 计算竞价量比（需要历史数据）
            volume_ratio = self._calculate_volume_ratio(bid_volume, history_data)

            # 计算价格位置（相对于近期高低点）
            price_position = self._calculate_price_position(bid_price, history_data)

            return {
                'code': stock_code,
                'name': bid_info['名称'],
                'bid_price': bid_price,
                'prev_close': prev_close,
                'bid_change_pct': bid_change_pct,
                'bid_volume': bid_volume,
                'volume_ratio': volume_ratio,
                'price_position': price_position,
                'amount': float(bid_info['成交额']),
                'turnover_rate': float(bid_info.get('换手率', 0)),
            }

        except Exception as e:
            logger.warning(f"计算股票 {stock_code} 竞价指标失败: {e}")
            return {}

    def _calculate_volume_ratio(self, bid_volume: float, history_data: pd.DataFrame) -> float:
        """
        计算竞价量比

        Args:
            bid_volume: 竞价成交量
            history_data: 历史数据

        Returns:
            量比（当前量/近期平均量）
        """
        if history_data.empty or len(history_data) < 5:
            return 1.0

        try:
            # 计算近5日平均竞价量（简化：用日成交量估算）
            recent_volumes = history_data['成交量'].tail(5).values
            avg_volume = np.mean(recent_volumes)

            if avg_volume > 0:
                # 竞价量相对于日均量的比例
                # 注意：实际竞价量需要除以时间系数调整
                return bid_volume / (avg_volume * 0.1)  # 假设竞价量约占日量的10%
            return 1.0
        except:
            return 1.0

    def _calculate_price_position(self, current_price: float, history_data: pd.DataFrame) -> float:
        """
        计算当前价格在近期价格区间的位置

        Args:
            current_price: 当前价格
            history_data: 历史数据

        Returns:
            价格位置（0-1之间，越接近1表示越接近高点）
        """
        if history_data.empty or len(history_data) < 5:
            return 0.5

        try:
            # 获取近20日最高价和最低价
            high_20 = history_data['最高'].tail(20).max()
            low_20 = history_data['最低'].tail(20).min()

            if high_20 == low_20:
                return 0.5

            # 计算位置
            position = (current_price - low_20) / (high_20 - low_20)
            return position

        except:
            return 0.5

    def analyze_bid_activity(self, stock_data: Dict) -> Dict:
        """
        分析竞价活跃度

        Args:
            stock_data: 股票数据字典

        Returns:
            竞价活跃度分析结果
        """
        bid_change_pct = stock_data.get('bid_change_pct', 0)
        volume_ratio = stock_data.get('volume_ratio', 1.0)
        price_position = stock_data.get('price_position', 0.5)

        # 竞价活跃度评分（0-100）
        activity_score = 0

        # 价格涨幅评分（涨幅适中得分更高）
        if 0.01 <= bid_change_pct <= 0.03:  # 1%-3%涨幅
            activity_score += 30
        elif 0.03 < bid_change_pct <= 0.05:  # 3%-5%涨幅
            activity_score += 25
        elif 0 < bid_change_pct < 0.01:  # 0-1%涨幅
            activity_score += 20
        elif 0.05 < bid_change_pct <= 0.10:  # 5%-10%涨幅
            activity_score += 15
        else:
            activity_score += 10

        # 量比评分（量比越大得分越高，但避免过度放量）
        if 2.0 <= volume_ratio <= 3.0:
            activity_score += 35
        elif 3.0 < volume_ratio <= 5.0:
            activity_score += 30
        elif 1.5 <= volume_ratio < 2.0:
            activity_score += 25
        elif volume_ratio > 5.0:
            activity_score += 20
        else:
            activity_score += 15

        # 价格位置评分（价格在中间位置更安全）
        if 0.3 <= price_position <= 0.7:
            activity_score += 35
        elif 0.7 < price_position <= 0.9:
            activity_score += 30
        elif 0.1 <= price_position < 0.3:
            activity_score += 25
        else:
            activity_score += 20

        return {
            **stock_data,
            'activity_score': activity_score,
        }

    def get_pre_market_summary(self, stock_codes: List[str], history_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        获取集合竞价综合分析

        Args:
            stock_codes: 股票代码列表
            history_data: 历史数据字典

        Returns:
            综合分析结果DataFrame
        """
        if self.pre_market_data is None:
            self.get_bid_quotes()

        results = []
        for code in stock_codes:
            if code in history_data:
                metrics = self.calculate_bid_metrics(code, history_data[code])
                if metrics:
                    activity = self.analyze_bid_activity(metrics)
                    results.append(activity)

        if not results:
            return pd.DataFrame()

        df = pd.DataFrame(results)

        # 按活跃度评分排序
        df = df.sort_values('activity_score', ascending=False)

        return df

    def watch_pre_market(self, callback=None, interval: int = 30):
        """
        监控集合竞价（用于实时监控）

        Args:
            callback: 每次更新后的回调函数
            interval: 更新间隔（秒）
        """
        logger.info("开始监控集合竞价...")

        while self.is_pre_market_time():
            try:
                data = self.get_bid_quotes()
                if callback:
                    callback(data)
                time_module.sleep(interval)
            except Exception as e:
                logger.error(f"监控出错: {e}")
                time_module.sleep(5)

        logger.info("集合竞价时段结束")