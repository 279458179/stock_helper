"""
股票智能分析引擎
整合数据获取、竞价分析、策略评估，输出最终推荐结果
跨平台兼容：支持 Windows、macOS、Linux
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import sys
from pathlib import Path

# 使用 pathlib 确保跨平台路径兼容
backend_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_path))

from core.config import (
    MAX_STOCK_PRICE, SELECT_TOP_N, get_cache_dir_path,
    PRE_MARKET_START, PRE_MARKET_END, DATA_UPDATE_INTERVAL
)
from core.data_fetcher import DataFetcher
from core.pre_market import PreMarketAnalyzer
from strategies.composite import CompositeStrategy

logger = logging.getLogger(__name__)


class StockAnalyzer:
    """股票智能分析引擎"""

    def __init__(self):
        """初始化分析引擎"""
        self.fetcher = DataFetcher()
        self.pre_market = PreMarketAnalyzer()
        self.composite_strategy = CompositeStrategy()
        self.analysis_results = []
        self.last_analysis_time = None

    def run_analysis(self) -> List[Dict]:
        """
        执行完整分析流程

        Returns:
            分析结果列表（包含Top N推荐股票）
        """
        logger.info("=" * 50)
        logger.info("开始执行股票智能分析...")
        start_time = time.time()

        try:
            # Step 1: 获取所有A股股票列表
            logger.info("Step 1: 获取股票列表...")
            all_stocks = self.fetcher.get_all_a_stocks()

            if all_stocks.empty:
                logger.error("获取股票列表失败")
                return []

            # Step 2: 获取集合竞价数据
            logger.info("Step 2: 获取集合竞价数据...")
            bid_data = self.pre_market.get_bid_quotes()

            # Step 3: 批量获取历史数据
            logger.info("Step 3: 批量获取历史数据...")
            stock_codes = all_stocks['代码'].tolist()

            # 为了时效性，只获取部分股票的历史数据进行深度分析
            # 先筛选出竞价数据表现较好的股票
            potential_stocks = self._quick_filter(all_stocks, bid_data)

            if potential_stocks.empty:
                logger.warning("快速筛选后无符合条件的股票")
                return []

            potential_codes = potential_stocks['代码'].tolist()
            logger.info(f"快速筛选出 {len(potential_codes)} 只潜在股票")

            # 获取历史数据
            history_data = self.fetcher.batch_get_history(potential_codes, days=30)

            # Step 4: 执行深度分析
            logger.info("Step 4: 执行深度分析...")
            results = self._analyze_stocks(potential_stocks, history_data)

            # Step 5: 排序并选出Top N
            logger.info("Step 5: 排序并选出Top N...")
            top_stocks = self.composite_strategy.rank_stocks(results)

            # 记录结果
            self.analysis_results = top_stocks
            self.last_analysis_time = datetime.now()

            end_time = time.time()
            logger.info(f"分析完成，耗时: {end_time - start_time:.2f}秒")
            logger.info(f"共筛选出 {len(top_stocks)} 只推荐股票")

            return top_stocks

        except Exception as e:
            logger.error(f"分析过程出错: {e}")
            raise

    def _quick_filter(self, all_stocks: pd.DataFrame, bid_data: pd.DataFrame) -> pd.DataFrame:
        """
        快速筛选有潜力的股票

        Args:
            all_stocks: 所有股票列表
            bid_data: 竞价数据

        Returns:
            筛选后的股票列表
        """
        try:
            # 合并数据
            merged = pd.merge(
                all_stocks,
                bid_data,
                on='代码',
                how='inner',
                suffixes=('', '_bid')
            )

            # 快速筛选条件：
            # 1. 价格不超过20元
            # 2. 竞价涨幅在合理范围（0%-7%）
            # 3. 竞价成交量不为0

            filtered = merged[
                (merged['最新价'] <= MAX_STOCK_PRICE) &
                (merged['最新价'] > 1.0) &  # 避免极端低价股
                (merged['竞价涨幅'] > 0) &
                (merged['竞价涨幅'] < 0.07) &  # 竞价涨幅不超过7%
                (merged['成交量'] > 0)
            ]

            # 进一步筛选：按竞价涨幅和量比排序，取前100只进行深度分析
            filtered['quick_score'] = (
                filtered['竞价涨幅'] * 50 +  # 涨幅权重
                (filtered['竞价量比'].fillna(1) - 1) * 30  # 量比权重
            )

            filtered = filtered.sort_values('quick_score', ascending=False)

            # 取前100只进行深度分析
            return filtered.head(100)

        except Exception as e:
            logger.warning(f"快速筛选失败: {e}")
            # 如果筛选失败，返回原始数据的前50只
            return all_stocks.head(50)

    def _analyze_stocks(self, stocks: pd.DataFrame, history_data: Dict[str, pd.DataFrame]) -> List[Dict]:
        """
        批量分析股票（并行）

        Args:
            stocks: 股票列表
            history_data: 历史数据字典

        Returns:
            分析结果列表
        """
        results = []

        # 并行分析
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_stock = {}
            for _, stock in stocks.iterrows():
                code = stock['代码']
                if code in history_data:
                    stock_data = {
                        'code': code,
                        'name': stock['名称'],
                        'bid_price': stock['最新价'],
                        'prev_close': stock['昨收'],
                        'bid_change_pct': stock['竞价涨幅'] / 100,  # 转为比例
                        'bid_volume': stock['成交量'],
                        'amount': stock['成交额'],
                        'turnover_rate': stock.get('换手率', 0),
                        'volume_ratio': stock.get('竞价量比', 1.0),
                        'price_position': self._calc_price_position(stock['最新价'], history_data[code]),
                    }

                    future = executor.submit(
                        self.composite_strategy.analyze,
                        stock_data,
                        history_data[code]
                    )
                    future_to_stock[future] = stock_data

            for future in as_completed(future_to_stock):
                stock_data = future_to_stock[future]
                try:
                    analysis = future.result()

                    # 合合股票基本信息和分析结果
                    result = {
                        **stock_data,
                        **analysis,
                        'bid_change_pct_display': f"{stock_data['bid_change_pct'] * 100:.2f}%",
                        'volume_ratio_display': f"{stock_data['volume_ratio']:.2f}倍",
                    }

                    results.append(result)

                except Exception as e:
                    logger.warning(f"股票 {stock_data['code']} 分析失败: {e}")

        return results

    def _calc_price_position(self, current_price: float, history: pd.DataFrame) -> float:
        """
        计算价格位置

        Args:
            current_price: 当前价格
            history: 历史数据

        Returns:
            价格位置（0-1）
        """
        try:
            if history.empty or len(history) < 5:
                return 0.5

            high_20 = history['最高'].tail(20).max()
            low_20 = history['最低'].tail(20).min()

            if high_20 == low_20:
                return 0.5

            return (current_price - low_20) / (high_20 - low_20)

        except:
            return 0.5

    def get_recommendations(self) -> List[Dict]:
        """
        获取推荐股票列表

        Returns:
            推荐股票列表
        """
        if not self.analysis_results:
            self.run_analysis()

        return self.analysis_results

    def format_report(self) -> str:
        """
        格式化分析报告

        Returns:
            格式化的报告文本
        """
        if not self.analysis_results:
            return "暂无分析结果，请先执行分析"

        report = []
        report.append("=" * 60)
        report.append("          股票集合竞价智能分析报告")
        report.append("=" * 60)
        report.append(f"分析时间: {self.last_analysis_time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"筛选条件: 价格≤{MAX_STOCK_PRICE}元, 看涨评分排序")
        report.append(f"推荐数量: {len(self.analysis_results)} 只")
        report.append("-" * 60)

        for i, stock in enumerate(self.analysis_results, 1):
            report.append("")
            report.append(f"【第{i}名】 {stock['code']} - {stock['name']}")
            report.append(f"  竞价价格: {stock['bid_price']:.2f}元 ({stock['bid_change_pct_display']})")
            report.append(f"  竞价量比: {stock['volume_ratio_display']}")
            report.append(f"  综合评分: {stock['composite_score']:.2f}分")
            report.append(f"  风险等级: {stock.get('risk_level', '未知')}")
            report.append(f"  操作建议: {stock['recommendation']}")

            # 显示关键信号
            if stock.get('all_signals'):
                report.append(f"  关键信号: {', '.join(stock['all_signals'][:3])}")

        report.append("")
        report.append("-" * 60)
        report.append("【风险提示】本分析仅供参考，股市有风险，投资需谨慎。")
        report.append("=" * 60)

        return "\n".join(report)

    def export_to_csv(self, filepath: str) -> bool:
        """
        导出分析结果到CSV

        Args:
            filepath: CSV文件路径

        Returns:
            是否成功
        """
        try:
            if not self.analysis_results:
                return False

            # 转换为DataFrame
            df = pd.DataFrame(self.analysis_results)

            # 选择关键列导出
            columns = [
                'code', 'name', 'bid_price', 'bid_change_pct_display',
                'volume_ratio_display', 'composite_score', 'risk_level',
                'recommendation'
            ]

            df = df[[c for c in columns if c in df.columns]]

            # 导出
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            logger.info(f"结果已导出到 {filepath}")

            return True

        except Exception as e:
            logger.error(f"导出CSV失败: {e}")
            return False

    def watch_mode(self, callback=None):
        """
        监控模式：等待竞价结束自动分析

        Args:
            callback: 分析完成后的回调函数
        """
        logger.info("启动监控模式...")

        # 等待竞价结束
        while self.pre_market.is_pre_market_time():
            current_time = datetime.now().strftime('%H:%M:%S')
            logger.info(f"当前时间: {current_time}, 集合竞价进行中...")
            time.sleep(DATA_UPDATE_INTERVAL)

        # 竞价结束，执行分析
        logger.info("集合竞价结束，开始执行分析...")
        results = self.run_analysis()

        if callback:
            callback(results)

        return results