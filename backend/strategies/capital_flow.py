"""
资金流向分析策略模块
分析主力资金、大单资金流向，识别资金动向
"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple
import logging
import akshare as ak
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import CAPITAL_FLOW_THRESHOLDS

logger = logging.getLogger(__name__)


class CapitalFlowStrategy:
    """资金流向策略"""

    def __init__(self):
        """初始化资金流向策略"""
        self.min_main_inflow = CAPITAL_FLOW_THRESHOLDS['min_main_inflow']
        self.min_big_order_ratio = CAPITAL_FLOW_THRESHOLDS['min_big_order_ratio']

    def analyze(self, stock_data: Dict, history_data: pd.DataFrame) -> Dict:
        """
        分析资金流向

        Args:
            stock_data: 竞价数据
            history_data: 历史K线数据

        Returns:
            资金流向分析结果
        """
        try:
            score = 0
            signals = []

            # 1. 成交额分析
            amount_score, amount_signal = self._analyze_amount(stock_data)
            score += amount_score
            if amount_signal:
                signals.append(amount_signal)

            # 2. 换手率分析
            turnover_score, turnover_signal = self._analyze_turnover(stock_data)
            score += turnover_score
            if turnover_signal:
                signals.append(turnover_signal)

            # 3. 成交量趋势分析
            vol_trend_score, vol_trend_signal = self._analyze_volume_trend(history_data)
            score += vol_trend_score
            if vol_trend_signal:
                signals.append(vol_trend_signal)

            # 4. 资金流向分析（如果有数据）
            flow_score, flow_signal = self._analyze_capital_flow(stock_data.get('code', ''))
            score += flow_score
            if flow_signal:
                signals.append(flow_signal)

            return {
                'capital_flow_score': score,
                'capital_flow_signals': signals,
                'recommendation': self._generate_recommendation(score, signals)
            }

        except Exception as e:
            logger.warning(f"资金流向分析失败: {e}")
            return {
                'capital_flow_score': 0,
                'capital_flow_signals': [],
                'recommendation': '分析出错'
            }

    def _analyze_amount(self, stock_data: Dict) -> Tuple[int, str]:
        """
        分析成交额

        Args:
            stock_data: 竞价数据

        Returns:
            (评分, 信号描述)
        """
        score = 0
        signal = ""

        try:
            amount = stock_data.get('amount', 0)
            prev_close = stock_data.get('prev_close', 0)

            if amount <= 0 or prev_close <= 0:
                return 10, "成交额数据不足"

            # 成交额与昨日收盘价的比例（估算活跃度）
            # 一般活跃股票的日成交额在几千万到几亿
            amount_ratio = amount / (prev_close * 1000000)  # 百万为单位

            if amount >= 5000000:  # 500万以上
                score = 25
                signal = "成交额活跃"
            elif amount >= 2000000:  # 200万以上
                score = 20
                signal = "成交额中等"
            elif amount >= 1000000:  # 100万以上
                score = 15
                signal = "成交额偏低"
            else:
                score = 10
                signal = "成交额低迷"

            return score, signal

        except Exception as e:
            logger.warning(f"成交额分析失败: {e}")
            return 10, "分析出错"

    def _analyze_turnover(self, stock_data: Dict) -> Tuple[int, str]:
        """
        分析换手率

        Args:
            stock_data: 竞价数据

        Returns:
            (评分, 信号描述)
        """
        score = 0
        signal = ""

        try:
            turnover_rate = stock_data.get('turnover_rate', 0)

            if turnover_rate <= 0:
                return 10, "换手率数据缺失"

            # 换手率判断（竞价期间的换手率通常较低）
            # 竞价换手率在0.5%-2%之间较为活跃
            if 1.0 <= turnover_rate <= 3.0:
                score = 25
                signal = "换手率活跃"
            elif 0.5 <= turnover_rate < 1.0:
                score = 20
                signal = "换手率适中"
            elif turnover_rate >= 3.0:
                score = 15
                signal = "换手率过高，注意风险"
            else:
                score = 10
                signal = "换手率偏低"

            return score, signal

        except Exception as e:
            logger.warning(f"换手率分析失败: {e}")
            return 10, "分析出错"

    def _analyze_volume_trend(self, history_data: pd.DataFrame) -> Tuple[int, str]:
        """
        分析成交量趋势

        Args:
            history_data: 历史数据

        Returns:
            (评分, 信号描述)
        """
        score = 0
        signal = ""

        try:
            if history_data.empty or len(history_data) < 5:
                return 10, "历史数据不足"

            volume = history_data['成交量']

            # 近5日成交量趋势
            vol_5 = volume.tail(5).values
            vol_trend = np.polyfit(range(5), vol_5, 1)[0]  # 线性趋势斜率

            if vol_trend > 0:
                score = 20
                signal = "成交量上升趋势"
            elif vol_trend < 0:
                score = 8
                signal = "成交量下降趋势"
            else:
                score = 15
                signal = "成交量平稳"

            # 成交量波动率
            vol_std = np.std(vol_5) / np.mean(vol_5) if np.mean(vol_5) > 0 else 0

            if vol_std > 0.5:
                score += 5
                signal += "，波动较大"

            return score, signal

        except Exception as e:
            logger.warning(f"成交量趋势分析失败: {e}")
            return 10, "分析出错"

    def _analyze_capital_flow(self, stock_code: str) -> Tuple[int, str]:
        """
        分析个股资金流向（实时）

        Args:
            stock_code: 股票代码

        Returns:
            (评分, 信号描述)
        """
        score = 0
        signal = ""

        try:
            # 尝试获取实时资金流向数据
            # 注意：这个接口可能需要实时数据支持
            try:
                flow_data = ak.stock_individual_fund_flow(stock=stock_code, market="sh")

                if flow_data.empty:
                    return 15, "资金流向数据缺失"

                # 获取最近的资金流向数据
                latest_flow = flow_data.iloc[-1]

                main_inflow = latest_flow.get('主力净流入', 0)
                retail_inflow = latest_flow.get('散户净流入', 0)

                # 主力资金判断
                if main_inflow > self.min_main_inflow:
                    score = 25
                    signal = "主力资金流入"
                elif main_inflow > 0:
                    score = 20
                    signal = "主力资金微流入"
                elif main_inflow < -self.min_main_inflow:
                    score = 5
                    signal = "主力资金流出"
                else:
                    score = 15
                    signal = "主力资金平衡"

                return score, signal

            except Exception as e:
                logger.warning(f"获取资金流向数据失败: {e}")
                # 如果获取失败，返回默认评分
                return 15, "资金流向数据获取失败"

        except Exception as e:
            logger.warning(f"资金流向分析失败: {e}")
            return 10, "分析出错"

    def get_market_capital_flow(self) -> pd.DataFrame:
        """
        获取市场整体资金流向

        Returns:
            市场资金流向DataFrame
        """
        try:
            market_flow = ak.stock_market_fund_flow()
            return market_flow
        except Exception as e:
            logger.warning(f"获取市场资金流向失败: {e}")
            return pd.DataFrame()

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
            return "资金面活跃，主力关注度高，建议关注"
        elif score >= 60:
            return "资金面较为活跃，可适当关注"
        elif score >= 40:
            return "资金面一般，建议观望"
        else:
            return "资金面低迷，建议回避"

    def calculate_score(self, stock_data: Dict, history_data: pd.DataFrame) -> int:
        """
        计算资金流向评分（简化版）

        Args:
            stock_data: 竞价数据
            history_data: 历史数据

        Returns:
            评分（0-100）
        """
        result = self.analyze(stock_data, history_data)
        return result.get('capital_flow_score', 0)