"""
技术指标组合策略模块
使用MACD、KDJ、均线等技术指标分析股票走势
"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple, List
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import TECHNICAL_THRESHOLDS

logger = logging.getLogger(__name__)


class TechnicalStrategy:
    """技术指标策略"""

    def __init__(self):
        """初始化技术指标策略"""
        self.macd_cross = TECHNICAL_THRESHOLDS['macd_cross']
        self.kdj_oversell = TECHNICAL_THRESHOLDS['kdj_oversell']
        self.kdj_overbuy = TECHNICAL_THRESHOLDS['kdj_overbuy']

    def analyze(self, stock_data: Dict, history_data: pd.DataFrame) -> Dict:
        """
        分析技术指标

        Args:
            stock_data: 竞价数据
            history_data: 历史K线数据

        Returns:
            技术指标分析结果
        """
        try:
            if history_data.empty or len(history_data) < 20:
                return {
                    'technical_score': 0,
                    'technical_signals': [],
                    'recommendation': '历史数据不足，无法分析'
                }

            score = 0
            signals = []

            # 1. MACD分析
            macd_score, macd_signal = self._analyze_macd(history_data)
            score += macd_score
            if macd_signal:
                signals.append(f"MACD: {macd_signal}")

            # 2. KDJ分析
            kdj_score, kdj_signal = self._analyze_kdj(history_data)
            score += kdj_score
            if kdj_signal:
                signals.append(f"KDJ: {kdj_signal}")

            # 3. 均线系统分析
            ma_score, ma_signal = self._analyze_ma(history_data)
            score += ma_score
            if ma_signal:
                signals.append(f"均线: {ma_signal}")

            # 4. 成交量分析
            vol_score, vol_signal = self._analyze_volume(history_data)
            score += vol_score
            if vol_signal:
                signals.append(f"成交量: {vol_signal}")

            # 5. 突破分析
            break_score, break_signal = self._analyze_breakout(stock_data, history_data)
            score += break_score
            if break_signal:
                signals.append(f"突破: {break_signal}")

            return {
                'technical_score': score,
                'technical_signals': signals,
                'recommendation': self._generate_recommendation(score, signals)
            }

        except Exception as e:
            logger.warning(f"技术指标分析失败: {e}")
            return {
                'technical_score': 0,
                'technical_signals': [],
                'recommendation': '分析出错'
            }

    def _calculate_macd(self, data: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple:
        """
        计算MACD指标

        Args:
            data: 价格数据
            fast: 快线周期
            slow: 慢线周期
            signal: 信号线周期

        Returns:
            (DIF, DEA, MACD柱)
        """
        close = data['收盘']

        # 计算EMA
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()

        # DIF线
        dif = ema_fast - ema_slow

        # DEA线（信号线）
        dea = dif.ewm(span=signal, adjust=False).mean()

        # MACD柱
        macd = (dif - dea) * 2

        return dif, dea, macd

    def _analyze_macd(self, history_data: pd.DataFrame) -> Tuple[int, str]:
        """
        分析MACD指标

        Args:
            history_data: 历史数据

        Returns:
            (评分, 信号描述)
        """
        score = 0
        signal = ""

        try:
            dif, dea, macd = self._calculate_macd(history_data)

            # 获取最近几天的MACD值
            dif_last = dif.iloc[-1]
            dea_last = dea.iloc[-1]
            macd_last = macd.iloc[-1]

            dif_prev = dif.iloc[-2] if len(dif) > 1 else dif_last
            dea_prev = dea.iloc[-2] if len(dea) > 1 else dea_last

            # 判断金叉/死叉
            if dif_last > dea_last and dif_prev <= dea_prev:
                score = 25
                signal = "金叉形成，看涨信号强"
            elif dif_last > dea_last and dif_prev > dea_prev:
                score = 20
                signal = "多头运行，趋势向上"
            elif dif_last < dea_last and dif_prev >= dea_prev:
                score = 5
                signal = "死叉形成，看跌信号"
            else:
                if dif_last > 0:
                    score = 15
                    signal = "零轴上方，偏多头"
                else:
                    score = 10
                    signal = "零轴下方，偏空头"

            # 考虑MACD柱的变化
            if macd_last > 0 and len(macd) > 1:
                if macd_last > macd.iloc[-2]:
                    score += 5
                    signal += "，动能增强"

            return score, signal

        except Exception as e:
            logger.warning(f"MACD分析失败: {e}")
            return 10, "分析出错"

    def _calculate_kdj(self, data: pd.DataFrame, n: int = 9) -> Tuple:
        """
        计算KDJ指标

        Args:
            data: 价格数据
            n: 计算周期

        Returns:
            (K值, D值, J值)
        """
        low = data['最低']
        high = data['最高']
        close = data['收盘']

        # 计算RSV
        low_n = low.rolling(window=n).min()
        high_n = high.rolling(window=n).max()

        rsv = (close - low_n) / (high_n - low_n) * 100

        # 计算K、D、J
        k = rsv.ewm(com=2, adjust=False).mean()
        d = k.ewm(com=2, adjust=False).mean()
        j = 3 * k - 2 * d

        return k, d, j

    def _analyze_kdj(self, history_data: pd.DataFrame) -> Tuple[int, str]:
        """
        分析KDJ指标

        Args:
            history_data: 历史数据

        Returns:
            (评分, 信号描述)
        """
        score = 0
        signal = ""

        try:
            k, d, j = self._calculate_kdj(history_data)

            # 获取最近的KDJ值
            k_last = k.iloc[-1]
            d_last = d.iloc[-1]
            j_last = j.iloc[-1]

            k_prev = k.iloc[-2] if len(k) > 1 else k_last
            d_prev = d.iloc[-2] if len(d) > 1 else d_last

            # 超卖/超买判断
            if k_last < self.kdj_oversell and d_last < self.kdj_oversell:
                score = 25
                signal = "超卖区域，反弹概率大"
            elif k_last > self.kdj_overbuy and d_last > self.kdj_overbuy:
                score = 5
                signal = "超买区域，回调风险大"
            else:
                # 金叉/死叉判断
                if k_last > d_last and k_prev <= d_prev:
                    score = 20
                    signal = "KDJ金叉，看涨信号"
                elif k_last < d_last and k_prev >= d_prev:
                    score = 8
                    signal = "KDJ死叉，看跌信号"
                else:
                    score = 15
                    signal = "KDJ中性"

            # J值极端情况
            if j_last > 100:
                score -= 5
                signal += "，J值过高"
            elif j_last < 0:
                score += 5
                signal += "，J值过低"

            return score, signal

        except Exception as e:
            logger.warning(f"KDJ分析失败: {e}")
            return 10, "分析出错"

    def _analyze_ma(self, history_data: pd.DataFrame) -> Tuple[int, str]:
        """
        分析均线系统

        Args:
            history_data: 历史数据

        Returns:
            (评分, 信号描述)
        """
        score = 0
        signal = ""

        try:
            close = history_data['收盘']

            # 计算均线
            ma5 = close.rolling(window=5).mean()
            ma10 = close.rolling(window=10).mean()
            ma20 = close.rolling(window=20).mean()

            last_close = close.iloc[-1]
            last_ma5 = ma5.iloc[-1]
            last_ma10 = ma10.iloc[-1]
            last_ma20 = ma20.iloc[-1]

            # 均线多头排列
            if last_ma5 > last_ma10 > last_ma20:
                if last_close > last_ma5:
                    score = 25
                    signal = "多头排列，趋势向上"
                else:
                    score = 18
                    signal = "多头排列，短期回调"
            # 均线空头排列
            elif last_ma5 < last_ma10 < last_ma20:
                score = 5
                signal = "空头排列，趋势向下"
            # 交叉状态
            else:
                if last_close > last_ma5 > last_ma10:
                    score = 15
                    signal = "短期均线向上"
                elif last_close < last_ma5 < last_ma10:
                    score = 10
                    signal = "短期均线向下"
                else:
                    score = 12
                    signal = "均线纠缠"

            return score, signal

        except Exception as e:
            logger.warning(f"均线分析失败: {e}")
            return 10, "分析出错"

    def _analyze_volume(self, history_data: pd.DataFrame) -> Tuple[int, str]:
        """
        分析成交量

        Args:
            history_data: 历史数据

        Returns:
            (评分, 信号描述)
        """
        score = 0
        signal = ""

        try:
            volume = history_data['成交量']
            close = history_data['收盘']

            # 计算平均成交量
            avg_vol_5 = volume.tail(5).mean()
            avg_vol_10 = volume.tail(10).mean()

            last_vol = volume.iloc[-1]
            last_close = close.iloc[-1]

            # 成交量变化
            vol_ratio = last_vol / avg_vol_5 if avg_vol_5 > 0 else 1

            # 价格变化
            close_prev = close.iloc[-2] if len(close) > 1 else last_close
            price_change = (last_close - close_prev) / close_prev if close_prev > 0 else 0

            # 量价关系判断
            if vol_ratio > 1.5 and price_change > 0:
                score = 20
                signal = "量价齐升"
            elif vol_ratio > 1.5 and price_change < 0:
                score = 8
                signal = "价跌量增，可能底部"
            elif vol_ratio < 0.8 and price_change > 0:
                score = 10
                signal = "价涨量缩"
            elif vol_ratio > 2:
                score = 12
                signal = "成交量放大"
            else:
                score = 15
                signal = "量能正常"

            return score, signal

        except Exception as e:
            logger.warning(f"成交量分析失败: {e}")
            return 10, "分析出错"

    def _analyze_breakout(self, stock_data: Dict, history_data: pd.DataFrame) -> Tuple[int, str]:
        """
        分析突破情况

        Args:
            stock_data: 竞价数据
            history_data: 历史数据

        Returns:
            (评分, 信号描述)
        """
        score = 0
        signal = ""

        try:
            bid_price = stock_data.get('bid_price', 0)

            if bid_price <= 0:
                return 10, "价格数据缺失"

            close = history_data['收盘']
            high = history_data['最高']

            # 近期高点
            high_5 = high.tail(5).max()
            high_10 = high.tail(10).max()
            high_20 = high.tail(20).max()

            # 近期收盘价均值
            avg_close_5 = close.tail(5).mean()

            # 判断突破
            if bid_price > high_20:
                score = 25
                signal = "突破20日高点"
            elif bid_price > high_10:
                score = 20
                signal = "突破10日高点"
            elif bid_price > high_5:
                score = 15
                signal = "突破5日高点"
            elif bid_price > avg_close_5:
                score = 12
                signal = "高于5日均价"
            else:
                score = 8
                signal = "未突破"

            return score, signal

        except Exception as e:
            logger.warning(f"突破分析失败: {e}")
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
            return "技术面强势，多个看涨信号共振，建议关注"
        elif score >= 60:
            return "技术面偏强，部分看涨信号，可适当关注"
        elif score >= 40:
            return "技术面中性，信号不明确，建议观望"
        else:
            return "技术面偏弱，建议回避"

    def calculate_score(self, stock_data: Dict, history_data: pd.DataFrame) -> int:
        """
        计算技术指标评分（简化版）

        Args:
            stock_data: 竞价数据
            history_data: 历史数据

        Returns:
            评分（0-100）
        """
        result = self.analyze(stock_data, history_data)
        return result.get('technical_score', 0)