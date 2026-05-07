"""
量价配合策略模块
分析集合竞价期间的量价关系，识别看涨信号
"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import VOLUME_PRICE_THRESHOLDS

logger = logging.getLogger(__name__)


class VolumePriceStrategy:
    """量价配合策略"""

    def __init__(self):
        """初始化量价策略"""
        self.min_volume_ratio = VOLUME_PRICE_THRESHOLDS['min_volume_ratio']
        self.min_price_change = VOLUME_PRICE_THRESHOLDS['min_price_change']
        self.max_price_change = VOLUME_PRICE_THRESHOLDS['max_price_change']

    def analyze(self, stock_data: Dict, history_data: pd.DataFrame) -> Dict:
        """
        分析量价配合情况

        Args:
            stock_data: 股票竞价数据字典
            history_data: 历史K线数据

        Returns:
            量价分析结果字典
        """
        try:
            # 提取关键数据
            bid_price = stock_data.get('bid_price', 0)
            prev_close = stock_data.get('prev_close', 0)
            bid_volume = stock_data.get('bid_volume', 0)
            volume_ratio = stock_data.get('volume_ratio', 1.0)
            bid_change_pct = stock_data.get('bid_change_pct', 0)

            # 评分结果
            score = 0
            signals = []

            # 1. 量比分析（竞价量放大）
            volume_score, volume_signal = self._analyze_volume_ratio(volume_ratio)
            score += volume_score
            if volume_signal:
                signals.append(volume_signal)

            # 2. 价格涨幅分析
            price_score, price_signal = self._analyze_price_change(bid_change_pct)
            score += price_score
            if price_signal:
                signals.append(price_signal)

            # 3. 量价配合度分析
            vp_score, vp_signal = self._analyze_volume_price_match(volume_ratio, bid_change_pct)
            score += vp_score
            if vp_signal:
                signals.append(vp_signal)

            # 4. 价格位置分析
            pos_score, pos_signal = self._analyze_price_position(stock_data, history_data)
            score += pos_score
            if pos_signal:
                signals.append(pos_signal)

            # 5. 近期趋势分析
            trend_score, trend_signal = self._analyze_trend(history_data)
            score += trend_score
            if trend_signal:
                signals.append(trend_signal)

            return {
                'volume_price_score': score,
                'volume_price_signals': signals,
                'volume_ratio': volume_ratio,
                'bid_change_pct': bid_change_pct,
                'recommendation': self._generate_recommendation(score, signals)
            }

        except Exception as e:
            logger.warning(f"量价分析失败: {e}")
            return {
                'volume_price_score': 0,
                'volume_price_signals': [],
                'recommendation': '数据不足，无法分析'
            }

    def _analyze_volume_ratio(self, volume_ratio: float) -> Tuple[int, str]:
        """
        分析量比

        Args:
            volume_ratio: 竞价量比

        Returns:
            (评分, 信号描述)
        """
        score = 0
        signal = ""

        if volume_ratio >= 5.0:
            score = 30
            signal = "极度放量"
        elif volume_ratio >= 3.0:
            score = 25
            signal = "显著放量"
        elif volume_ratio >= 2.0:
            score = 20
            signal = "温和放量"
        elif volume_ratio >= 1.5:
            score = 15
            signal = "轻微放量"
        elif volume_ratio >= 1.0:
            score = 10
            signal = "量能正常"
        else:
            score = 5
            signal = "量能不足"

        return score, signal

    def _analyze_price_change(self, bid_change_pct: float) -> Tuple[int, str]:
        """
        分析竞价价格涨幅

        Args:
            bid_change_pct: 竞价涨幅（百分比）

        Returns:
            (评分, 信号描述)
        """
        score = 0
        signal = ""

        # 理想涨幅区间：1%-3%
        if 0.01 <= bid_change_pct <= 0.03:
            score = 30
            signal = "涨幅适中，看涨信号强"
        elif 0.03 < bid_change_pct <= 0.05:
            score = 25
            signal = "涨幅较大，关注追涨风险"
        elif 0.005 <= bid_change_pct < 0.01:
            score = 20
            signal = "小幅上涨"
        elif 0.05 < bid_change_pct <= 0.07:
            score = 15
            signal = "涨幅过大，注意风险"
        elif 0 < bid_change_pct < 0.005:
            score = 10
            signal = "微涨"
        elif bid_change_pct > 0.07:
            score = 5
            signal = "涨幅过大，警惕冲高回落"
        else:
            score = 0
            signal = "下跌或持平"

        return score, signal

    def _analyze_volume_price_match(self, volume_ratio: float, bid_change_pct: float) -> Tuple[int, str]:
        """
        分析量价配合度

        Args:
            volume_ratio: 量比
            bid_change_pct: 涨幅

        Returns:
            (评分, 信号描述)
        """
        score = 0
        signal = ""

        # 理想状态：量价齐升，量比适中
        if bid_change_pct > 0 and volume_ratio >= 1.5:
            if volume_ratio <= 3.0:
                score = 20
                signal = "量价配合良好"
            else:
                score = 15
                signal = "放量上涨，但量能过大"
        elif bid_change_pct > 0 and volume_ratio < 1.5:
            score = 10
            signal = "价涨量缩，上涨动力不足"
        elif bid_change_pct < 0 and volume_ratio >= 1.5:
            score = 5
            signal = "价跌量增，可能有资金出逃"
        else:
            score = 5
            signal = "量价平淡"

        return score, signal

    def _analyze_price_position(self, stock_data: Dict, history_data: pd.DataFrame) -> Tuple[int, str]:
        """
        分析价格相对于近期高低点的位置

        Args:
            stock_data: 竞价数据
            history_data: 历史数据

        Returns:
            (评分, 信号描述)
        """
        score = 0
        signal = ""

        if history_data.empty or len(history_data) < 5:
            return 10, "历史数据不足"

        try:
            bid_price = stock_data.get('bid_price', 0)
            high_20 = history_data['最高'].tail(20).max()
            low_20 = history_data['最低'].tail(20).min()

            if high_20 == low_20:
                return 10, "价格区间狭窄"

            # 计算价格位置
            position = (bid_price - low_20) / (high_20 - low_20)

            # 价格在底部区域，上涨空间大
            if position < 0.3:
                score = 20
                signal = "价格处于底部区域，上涨空间大"
            elif 0.3 <= position < 0.5:
                score = 15
                signal = "价格处于中低位，有上涨空间"
            elif 0.5 <= position < 0.7:
                score = 10
                signal = "价格处于中间区域"
            elif 0.7 <= position < 0.9:
                score = 8
                signal = "价格接近高位，注意风险"
            else:
                score = 5
                signal = "价格接近历史高位，风险较大"

            return score, signal

        except Exception as e:
            logger.warning(f"价格位置分析失败: {e}")
            return 10, "分析出错"

    def _analyze_trend(self, history_data: pd.DataFrame) -> Tuple[int, str]:
        """
        分析近期趋势

        Args:
            history_data: 历史数据

        Returns:
            (评分, 信号描述)
        """
        score = 0
        signal = ""

        if history_data.empty or len(history_data) < 5:
            return 10, "数据不足"

        try:
            # 计算近5日均价线
            ma5 = history_data['收盘'].tail(5).mean()
            # 计算近10日均价线
            ma10 = history_data['收盘'].tail(10).mean() if len(history_data) >= 10 else ma5

            last_close = history_data['收盘'].iloc[-1]

            # 判断趋势
            if ma5 > ma10 and last_close > ma5:
                score = 20
                signal = "上升趋势，多头排列"
            elif ma5 > ma10 and last_close < ma5:
                score = 15
                signal = "上升趋势，短期回调"
            elif ma5 < ma10 and last_close > ma5:
                score = 12
                signal = "下降趋势，可能反转"
            else:
                score = 5
                signal = "下降趋势，空头排列"

            return score, signal

        except Exception as e:
            logger.warning(f"趋势分析失败: {e}")
            return 10, "分析出错"

    def _generate_recommendation(self, score: int, signals: list) -> str:
        """
        生成操作建议

        Args:
            score: 综合评分
            signals: 信号列表

        Returns:
            操作建议
        """
        if score >= 80:
            return "强烈看涨，建议开盘重点关注，可择机买入"
        elif score >= 60:
            return "看涨信号较强，建议关注开盘走势，回调可低吸"
        elif score >= 40:
            return "有一定看涨迹象，建议谨慎关注"
        elif score >= 20:
            return "信号不明显，建议观望"
        else:
            return "看涨信号弱，建议回避"

    def calculate_score(self, stock_data: Dict, history_data: pd.DataFrame) -> int:
        """
        计算量价策略评分（简化版）

        Args:
            stock_data: 竞价数据
            history_data: 历史数据

        Returns:
            评分（0-100）
        """
        result = self.analyze(stock_data, history_data)
        return result.get('volume_price_score', 0)