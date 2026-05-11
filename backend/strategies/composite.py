"""
综合评分策略模块
整合量价、技术指标、资金流向等多个因子，进行综合智能评分
跨平台兼容：支持 Windows、macOS、Linux
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import logging
from datetime import datetime
import sys
from pathlib import Path

# 使用 pathlib 确保跨平台路径兼容
backend_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_path))

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

            # 生成买卖操作建议
            buy_sell_advice = self._generate_buy_sell_advice(
                stock_data, history_data, composite_score, risk_level, all_signals
            )

            return {
                'composite_score': round(composite_score, 2),
                'volume_price_score': vp_score,
                'technical_score': tech_score,
                'capital_flow_score': cf_score,
                'composite_factor_score': round(composite_factor_score, 2),
                'all_signals': all_signals,
                'recommendation': recommendation,
                'risk_level': risk_level,
                'buy_sell_advice': buy_sell_advice,
                'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

        except Exception as e:
            logger.warning(f"综合分析失败: {e}")
            return {
                'composite_score': 0,
                'recommendation': '分析出错',
                'risk_level': '未知',
                'buy_sell_advice': {'buy': '暂无建议', 'sell': '暂无建议'}
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

    def _generate_buy_sell_advice(self, stock_data: Dict, history_data: pd.DataFrame,
                                      composite_score: float, risk_level: str,
                                      signals: List) -> Dict:
        """
        生成详细的买卖操作建议

        Args:
            stock_data: 竞价数据
            history_data: 历史数据
            composite_score: 综合评分
            risk_level: 风险等级
            signals: 信号列表

        Returns:
            买卖建议字典，包含买入时机、买入价格、卖出时机、卖出价格、止盈止损等
        """
        try:
            current_price = stock_data.get('bid_price', 0)
            prev_close = stock_data.get('prev_close', current_price)
            bid_change_pct = stock_data.get('bid_change_pct', 0)

            # 计算关键价格位
            support_price, resistance_price, ma5, ma10, ma20 = self._calculate_key_prices(history_data)

            advice = {
                'buy_condition': '',
                'buy_price_range': '',
                'buy_time': '',
                'sell_condition': '',
                'sell_price_target': '',
                'sell_time': '',
                'stop_loss': '',
                'take_profit': '',
                'holding_period': '',
                'position_size': '',
            }

            # 根据评分和风险等级生成建议
            if composite_score >= 75:
                # 高分股票 - 积极买入建议
                advice['buy_condition'] = '开盘后观察5-10分钟，若价格稳定在当前价位或小幅回调，可积极买入'
                advice['buy_price_range'] = self._format_price_range(current_price * 0.98, current_price * 1.02)
                advice['buy_time'] = '建议在9:30-9:40开盘初期买入，或等待开盘后首次回调时买入'
                advice['sell_condition'] = '当出现明显滞涨信号或涨幅超过预期目标时卖出'
                advice['sell_price_target'] = self._format_price_range(current_price * 1.05, current_price * 1.10)
                advice['sell_time'] = '若早盘强势可持有至下午，若走弱则在上午11点前卖出'
                advice['stop_loss'] = f'止损价: {current_price * 0.95:.2f}元 (跌幅约5%)'
                advice['take_profit'] = f'止盈目标: {current_price * 1.08:.2f}元 (涨幅约8%)'
                advice['holding_period'] = '短线持有1-3天，若趋势持续可延长'
                advice['position_size'] = '建议仓位: 30%-40%'

            elif composite_score >= 65:
                # 中高分股票 - 适度买入建议
                advice['buy_condition'] = '开盘观察15-20分钟，确认走势平稳后分批买入'
                advice['buy_price_range'] = self._format_price_range(current_price * 0.97, current_price * 1.01)
                advice['buy_time'] = '建议在9:35-10:00时段买入，避免开盘追高'
                advice['sell_condition'] = '达到目标涨幅或出现技术破位信号时卖出'
                advice['sell_price_target'] = self._format_price_range(current_price * 1.03, current_price * 1.06)
                advice['sell_time'] = '当日涨幅达标可卖出，或持有至次日开盘'
                advice['stop_loss'] = f'止损价: {current_price * 0.94:.2f}元 (跌幅约6%)'
                advice['take_profit'] = f'止盈目标: {current_price * 1.05:.2f}元 (涨幅约5%)'
                advice['holding_period'] = '短线持有1-2天'
                advice['position_size'] = '建议仓位: 20%-30%'

            elif composite_score >= 55:
                # 中等分数股票 - 谨慎买入建议
                advice['buy_condition'] = '开盘后观察30分钟以上，确认有成交量配合且走势向上时小仓位试探'
                advice['buy_price_range'] = self._format_price_range(current_price * 0.96, current_price)
                advice['buy_time'] = '建议在10:00-10:30时段，等待回调企稳后再买入'
                advice['sell_condition'] = '涨幅达3%以上或走势转弱时及时卖出'
                advice['sell_price_target'] = f'{current_price * 1.03:.2f}元附近'
                advice['sell_time'] = '当日冲高回落前卖出，不建议过夜持有'
                advice['stop_loss'] = f'止损价: {current_price * 0.93:.2f}元 (跌幅约7%)'
                advice['take_profit'] = f'止盈目标: {current_price * 1.03:.2f}元 (涨幅约3%)'
                advice['holding_period'] = '日内交易为主，不建议持有过夜'
                advice['position_size'] = '建议仓位: 10%-15%'

            elif composite_score >= 45:
                # 中低分数股票 - 观望为主
                advice['buy_condition'] = '暂不建议买入，等待更多确认信号'
                advice['buy_price_range'] = '观望，不设买入区间'
                advice['buy_time'] = '等待评分提升至55分以上再考虑'
                advice['sell_condition'] = '若已持有，建议择机减仓'
                advice['sell_price_target'] = f'{current_price:.2f}元附近止损离场'
                advice['sell_time'] = '开盘后尽快处理持仓'
                advice['stop_loss'] = f'止损价: {current_price * 0.92:.2f}元'
                advice['take_profit'] = '不设止盈，优先止损'
                advice['holding_period'] = '不建议持有'
                advice['position_size'] = '建议仓位: 0%'

            else:
                # 低分股票 - 建议回避
                advice['buy_condition'] = '不建议买入，风险较高'
                advice['buy_price_range'] = '回避'
                advice['buy_time'] = '不建议买入'
                advice['sell_condition'] = '若已持有，建议尽快清仓'
                advice['sell_price_target'] = f'{current_price:.2f}元附近清仓'
                advice['sell_time'] = '开盘第一时间卖出'
                advice['stop_loss'] = '已持有建议立即止损'
                advice['take_profit'] = '不设止盈'
                advice['holding_period'] = '不建议持有'
                advice['position_size'] = '建议仓位: 0%'

            # 根据风险等级调整建议
            if risk_level == "高":
                advice['position_size'] = self._reduce_position(advice['position_size'])
                advice['stop_loss'] = f'止损价: {current_price * 0.92:.2f}元 (跌幅约8%，风险较高需更严格止损)'

            # 根据技术信号补充建议
            if resistance_price and resistance_price > current_price:
                advice['sell_price_target'] = f'{resistance_price:.2f}元 (20日高点压力位附近)'
            if support_price and support_price < current_price:
                advice['buy_price_range'] = f'{support_price:.2f}元附近可考虑加仓 (支撑位)'

            # 根据竞价涨幅调整
            if bid_change_pct > 0.05:
                advice['buy_time'] = '开盘涨幅较大，建议等待回调至' + f'{current_price * 0.98:.2f}元附近再买入'
                advice['position_size'] = self._reduce_position(advice['position_size'])

            return advice

        except Exception as e:
            logger.warning(f"买卖建议生成失败: {e}")
            return {
                'buy_condition': '暂无建议',
                'sell_condition': '暂无建议'
            }

    def _calculate_key_prices(self, history_data: pd.DataFrame) -> Tuple:
        """
        计算关键价格位（支撑位、压力位、均线等）

        Args:
            history_data: 历史数据

        Returns:
            (支撑价, 压力价, MA5, MA10, MA20)
        """
        try:
            if history_data.empty or len(history_data) < 5:
                return (None, None, None, None, None)

            close = history_data['收盘']

            # 计算均线
            ma5 = close.tail(5).mean()
            ma10 = close.tail(10).mean() if len(close) >= 10 else ma5
            ma20 = close.tail(20).mean() if len(close) >= 20 else ma10

            # 计算支撑位（20日最低价附近）
            low_20 = history_data['最低'].tail(20).min() if len(history_data) >= 20 else history_data['最低'].min()
            support_price = low_20

            # 计算压力位（20日最高价附近）
            high_20 = history_data['最高'].tail(20).max() if len(history_data) >= 20 else history_data['最高'].max()
            resistance_price = high_20

            return (support_price, resistance_price, ma5, ma10, ma20)

        except Exception as e:
            logger.warning(f"关键价格计算失败: {e}")
            return (None, None, None, None, None)

    def _format_price_range(self, low: float, high: float) -> str:
        """格式化价格区间"""
        return f'{low:.2f}元 - {high:.2f}元'

    def _reduce_position(self, position_str: str) -> str:
        """降低仓位建议"""
        # 简单处理：将仓位比例降低
        if '30%-40%' in position_str:
            return '建议仓位: 15%-20% (风险调降)'
        elif '20%-30%' in position_str:
            return '建议仓位: 10%-15% (风险调降)'
        elif '10%-15%' in position_str:
            return '建议仓位: 5%-10% (风险调降)'
        return position_str

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