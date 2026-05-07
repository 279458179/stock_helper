"""
综合评分策略模块
整合量价、技术指标、资金流向等多个因子，进行综合智能评分
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import logging
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import STRATEGY_WEIGHTS, SELECT_TOP_N
from strategies.volume_price import VolumePriceStrategy
from strategies.technical import TechnicalStrategy
from strategies.capital_flow import CapitalFlowStrategy

logger = logging.getLogger(__name__)


class CompositeStrategy:
    """综合评分策略"""

    def __init__(self):
        """初始化综合评分策略"""
        self.volume_price = VolumePriceStrategy()
        self.technical = TechnicalStrategy()
        self.capital_flow = CapitalFlowStrategy()
        self.weights = STRATEGY_WEIGHTS

    def analyze(self, stock_data: Dict, history_data: pd.DataFrame) -> Dict:
        """
        进行综合分析

        Args:
            stock_data: 竞价数据
            history_data: 历史K线数据

        Returns:
            综合分析结果
        """
        try:
            # 各策略分析
            vp_result = self.volume_price.analyze(stock_data, history_data)
            tech_result = self.technical.analyze(stock_data, history_data)
            cf_result = self.capital_flow.analyze(stock_data, history_data)

            # 获取各策略评分
            vp_score = vp_result.get('volume_price_score', 0)
            tech_score = tech_result.get('technical_score', 0)
            cf_score = cf_result.get('capital_flow_score', 0)

            # 综合评分（加权平均）
            composite_score = (
                vp_score * self.weights['volume_price'] +
                tech_score * self.weights['technical'] +
                cf_score * self.weights['capital_flow']
            )

            # 额外的综合因子评分
            composite_factor_score = self._calculate_composite_factor(stock_data, history_data)
            composite_score += composite_factor_score * self.weights['composite']

            # 收集所有信号
            all_signals = []
            all_signals.extend(vp_result.get('volume_price_signals', []))
            all_signals.extend(tech_result.get('technical_signals', []))
            all_signals.extend(cf_result.get('capital_flow_signals', []))

            # 生成综合建议
            recommendation = self._generate_composite_recommendation(
                composite_score, all_signals
            )

            # 计算风险等级
            risk_level = self._calculate_risk_level(stock_data, history_data)

            return {
                'composite_score': round(composite_score, 2),
                'volume_price_score': vp_score,
                'technical_score': tech_score,
                'capital_flow_score': cf_score,
                'composite_factor_score': round(composite_factor_score, 2),
                'all_signals': all_signals,
                'recommendation': recommendation,
                'risk_level': risk_level,
                'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

        except Exception as e:
            logger.warning(f"综合分析失败: {e}")
            return {
                'composite_score': 0,
                'recommendation': '分析出错',
                'risk_level': '未知'
            }

    def _calculate_composite_factor(self, stock_data: Dict, history_data: pd.DataFrame) -> float:
        """
        计算综合因子评分

        Args:
            stock_data: 竞价数据
            history_data: 历史数据

        Returns:
            综合因子评分（0-100）
        """
        score = 0

        try:
            if history_data.empty or len(history_data) < 5:
                return 50

            # 1. 价格动量因子
            price_momentum_score = self._calculate_price_momentum(history_data)
            score += price_momentum_score * 0.25

            # 2. 波动率因子
            volatility_score = self._calculate_volatility(history_data)
            score += volatility_score * 0.20

            # 3. 相对强度因子
            relative_strength_score = self._calculate_relative_strength(stock_data, history_data)
            score += relative_strength_score * 0.25

            # 4. 趋势一致性因子
            trend_consistency_score = self._calculate_trend_consistency(history_data)
            score += trend_consistency_score * 0.30

            return score

        except Exception as e:
            logger.warning(f"综合因子计算失败: {e}")
            return 50

    def _calculate_price_momentum(self, history_data: pd.DataFrame) -> float:
        """
        计算价格动量

        Args:
            history_data: 历史数据

        Returns:
            动量评分（0-100）
        """
        try:
            close = history_data['收盘']

            # 计算不同周期的收益率
            return_5 = (close.iloc[-1] - close.iloc[-5]) / close.iloc[-5] if len(close) >= 5 else 0
            return_10 = (close.iloc[-1] - close.iloc[-10]) / close.iloc[-10] if len(close) >= 10 else 0

            # 动量评分
            avg_return = (return_5 * 0.6 + return_10 * 0.4)

            if avg_return > 0.05:  # 5%以上涨幅
                score = 80
            elif avg_return > 0.02:
                score = 70
            elif avg_return > 0:
                score = 60
            elif avg_return > -0.02:
                score = 40
            else:
                score = 20

            return score

        except Exception as e:
            logger.warning(f"价格动量计算失败: {e}")
            return 50

    def _calculate_volatility(self, history_data: pd.DataFrame) -> float:
        """
        计算波动率评分

        Args:
            history_data: 历史数据

        Returns:
            波动率评分（0-100）
        """
        try:
            close = history_data['收盘']

            # 计算收益率标准差
            returns = close.pct_change().dropna()
            volatility = returns.std()

            # 波动率评分（适中波动率得分更高）
            if volatility < 0.02:  # 低波动
                score = 60
            elif volatility < 0.03:  # 适中波动
                score = 70
            elif volatility < 0.05:  # 较高波动
                score = 50
            else:  # 高波动
                score = 30

            return score

        except Exception as e:
            logger.warning(f"波动率计算失败: {e}")
            return 50

    def _calculate_relative_strength(self, stock_data: Dict, history_data: pd.DataFrame) -> float:
        """
        计算相对强度

        Args:
            stock_data: 竞价数据
            history_data: 历史数据

        Returns:
            相对强度评分（0-100）
        """
        try:
            bid_change_pct = stock_data.get('bid_change_pct', 0)

            # 竞价涨幅作为相对强度的代理指标
            # 市场平均涨幅通常在0附近
            # 相对强度评分
            if bid_change_pct > 0.05:  # 超过5%
                score = 90
            elif bid_change_pct > 0.03:  # 超过3%
                score = 80
            elif bid_change_pct > 0.01:  # 超过1%
                score = 70
            elif bid_change_pct > 0:
                score = 60
            elif bid_change_pct > -0.01:
                score = 40
            else:
                score = 20

            return score

        except Exception as e:
            logger.warning(f"相对强度计算失败: {e}")
            return 50

    def _calculate_trend_consistency(self, history_data: pd.DataFrame) -> float:
        """
        计算趋势一致性

        Args:
            history_data: 历史数据

        Returns:
            趋势一致性评分（0-100）
        """
        try:
            close = history_data['收盘']

            # 计算短期、中期、长期趋势
            ma5 = close.tail(5).mean()
            ma10 = close.tail(10).mean() if len(close) >= 10 else ma5
            ma20 = close.tail(20).mean() if len(close) >= 20 else ma10

            # 判断趋势一致性
            consistency_count = 0

            if ma5 > ma10:
                consistency_count += 1
            if ma10 > ma20:
                consistency_count += 1
            if close.iloc[-1] > ma5:
                consistency_count += 1

            # 趋势一致性评分
            if consistency_count == 3:
                score = 90
            elif consistency_count == 2:
                score = 70
            elif consistency_count == 1:
                score = 50
            else:
                score = 30

            return score

        except Exception as e:
            logger.warning(f"趋势一致性计算失败: {e}")
            return 50

    def _generate_composite_recommendation(self, score: float, signals: List) -> str:
        """
        生成综合操作建议

        Args:
            score: 综合评分
            signals: 信号列表

        Returns:
            操作建议
        """
        if score >= 75:
            return "强烈推荐，多个看涨信号共振，建议开盘重点关注"
        elif score >= 65:
            return "推荐关注，看涨信号较强，开盘后可择机入场"
        elif score >= 55:
            return "可以关注，有一定看涨迹象，建议谨慎操作"
        elif score >= 45:
            return "中性观望，信号不明确，建议等待确认"
        elif score >= 35:
            return "谨慎对待，部分看跌信号，建议观望"
        else:
            return "建议回避，看跌信号较强"

    def _calculate_risk_level(self, stock_data: Dict, history_data: pd.DataFrame) -> str:
        """
        计算风险等级

        Args:
            stock_data: 竞价数据
            history_data: 历史数据

        Returns:
            风险等级（低、中、高）
        """
        try:
            risk_score = 0

            # 竞价涨幅过大，风险高
            bid_change_pct = stock_data.get('bid_change_pct', 0)
            if bid_change_pct > 0.07:
                risk_score += 3
            elif bid_change_pct > 0.05:
                risk_score += 2
            elif bid_change_pct < -0.03:
                risk_score += 2

            # 量比过大，风险高
            volume_ratio = stock_data.get('volume_ratio', 1.0)
            if volume_ratio > 5.0:
                risk_score += 2
            elif volume_ratio > 3.0:
                risk_score += 1

            # 价格位置过高，风险高
            price_position = stock_data.get('price_position', 0.5)
            if price_position > 0.9:
                risk_score += 2
            elif price_position > 0.7:
                risk_score += 1

            # 判断风险等级
            if risk_score >= 5:
                return "高"
            elif risk_score >= 3:
                return "中"
            else:
                return "低"

        except Exception as e:
            logger.warning(f"风险等级计算失败: {e}")
            return "中"

    def rank_stocks(self, stock_results: List[Dict]) -> List[Dict]:
        """
        对股票进行排序并选出Top N

        Args:
            stock_results: 股票分析结果列表

        Returns:
            排序后的Top N股票列表
        """
        try:
            # 按综合评分排序
            ranked = sorted(
                stock_results,
                key=lambda x: x.get('composite_score', 0),
                reverse=True
            )

            # 返回前N只
            return ranked[:SELECT_TOP_N]

        except Exception as e:
            logger.warning(f"股票排序失败: {e}")
            return stock_results[:SELECT_TOP_N]

    def calculate_score(self, stock_data: Dict, history_data: pd.DataFrame) -> float:
        """
        计算综合评分（简化版）

        Args:
            stock_data: 竞价数据
            history_data: 历史数据

        Returns:
            综合评分（0-100）
        """
        result = self.analyze(stock_data, history_data)
        return result.get('composite_score', 0)