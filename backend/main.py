"""
股票集合竞价智能分析工具 - 命令行入口
"""
import sys
import os
import argparse
import logging
from datetime import datetime
import time
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import LOG_FILE, LOG_LEVEL, CACHE_DIR, SELECT_TOP_N, MAX_STOCK_PRICE, DATA_UPDATE_INTERVAL
from core.data_fetcher import DataFetcher
from core.pre_market import PreMarketAnalyzer
from strategies.composite import CompositeStrategy

# 确保目录存在
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# 配置日志
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


class SimpleAnalyzer:
    """简化版分析引擎"""

    def __init__(self):
        self.fetcher = DataFetcher()
        self.pre_market = PreMarketAnalyzer()
        self.composite_strategy = CompositeStrategy()
        self.analysis_results = []
        self.last_analysis_time = None

    def run_analysis(self):
        """执行分析"""
        logger.info("=" * 50)
        logger.info("开始执行股票智能分析...")
        start_time = time.time()

        try:
            # 获取股票列表（包含实时行情）
            logger.info("Step 1: 获取股票实时数据...")
            all_stocks = self.fetcher.get_all_a_stocks()

            if all_stocks.empty:
                logger.error("获取股票列表失败")
                return []

            # 快速筛选（使用已获取的数据）
            logger.info("Step 2: 快速筛选...")
            potential_stocks = self._quick_filter(all_stocks, None)

            if potential_stocks.empty:
                logger.warning("筛选后无符合条件的股票")
                return []

            potential_codes = potential_stocks['代码'].tolist()
            logger.info(f"筛选出 {len(potential_codes)} 只潜在股票")

            # 获取历史数据
            logger.info("Step 3: 批量获取历史数据...")
            history_data = self.fetcher.batch_get_history(potential_codes, days=30)

            # 深度分析
            logger.info("Step 4: 深度分析...")
            results = self._analyze_stocks(potential_stocks, history_data)

            # 排序选Top N
            logger.info("Step 5: 排序选Top N...")
            top_stocks = sorted(results, key=lambda x: x.get('composite_score', 0), reverse=True)[:SELECT_TOP_N]

            self.analysis_results = top_stocks
            self.last_analysis_time = datetime.now()

            end_time = time.time()
            logger.info(f"分析完成，耗时: {end_time - start_time:.2f}秒")

            return top_stocks

        except Exception as e:
            logger.error(f"分析过程出错: {e}")
            raise

    def _quick_filter(self, all_stocks, bid_data):
        """快速筛选"""
        try:
            # sina数据源返回代码格式为sh600000/sz000001
            # 合并数据时需要处理
            merged = all_stocks.copy()

            # 直接使用all_stocks进行筛选（因为bid_data和all_stocks可能是同一数据）
            filtered = merged[
                (merged['最新价'] <= MAX_STOCK_PRICE) &
                (merged['最新价'] > 1.0) &
                (merged['最新价'] > 0) &
                (merged['代码'].str.match(r'^(sh|sz)[036]\d{5}$'))  # 沪深A股
            ].copy()

            if filtered.empty:
                logger.warning("筛选后无股票，返回空数据")
                return pd.DataFrame()

            # 计算涨幅作为快速评分
            filtered['涨幅'] = (filtered['最新价'] - filtered['昨收']) / filtered['昨收'] * 100
            filtered['quick_score'] = filtered['涨幅'] * 50 + 10  # 简化评分

            # 筛选涨幅>0的股票
            filtered = filtered[filtered['涨幅'] > 0]
            filtered = filtered.sort_values('quick_score', ascending=False)

            # 只取前20只进行深度分析（避免并发请求过多导致崩溃）
            return filtered.head(20)

        except Exception as e:
            logger.warning(f"快速筛选失败: {e}")
            return all_stocks.head(10)

    def _analyze_stocks(self, stocks, history_data):
        """分析股票"""
        results = []

        for _, stock in stocks.iterrows():
            code = stock['代码']
            if code not in history_data:
                continue

            # 计算涨幅
            change_pct = (stock['最新价'] - stock['昨收']) / stock['昨收']

            stock_data = {
                'code': code,
                'name': stock['名称'],
                'bid_price': stock['最新价'],
                'prev_close': stock['昨收'],
                'bid_change_pct': change_pct,
                'bid_volume': stock['成交量'],
                'amount': stock['成交额'],
                'turnover_rate': 0.5,  # 默认值
                'volume_ratio': 1.5,   # 默认值
                'price_position': self._calc_price_position(stock['最新价'], history_data[code]),
            }

            try:
                analysis = self.composite_strategy.analyze(stock_data, history_data[code])
                result = {**stock_data, **analysis}
                result['bid_change_pct_display'] = f"{stock_data['bid_change_pct'] * 100:.2f}%"
                result['volume_ratio_display'] = f"{stock_data['volume_ratio']:.2f}倍"
                results.append(result)
            except Exception as e:
                logger.warning(f"股票 {code} 分析失败: {e}")

        return results

    def _calc_price_position(self, current_price, history):
        """计算价格位置"""
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

    def format_report(self):
        """格式化报告"""
        if not self.analysis_results:
            return "暂无分析结果"

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

        report.append("")
        report.append("-" * 60)
        report.append("【风险提示】本分析仅供参考，股市有风险，投资需谨慎。")
        report.append("=" * 60)

        return "\n".join(report)

    def export_to_csv(self, filepath):
        """导出CSV"""
        try:
            if not self.analysis_results:
                return False
            df = pd.DataFrame(self.analysis_results)
            columns = ['code', 'name', 'bid_price', 'bid_change_pct_display', 'volume_ratio_display', 'composite_score', 'risk_level', 'recommendation']
            df = df[[c for c in columns if c in df.columns]]
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            logger.info(f"结果已导出到 {filepath}")
            return True
        except Exception as e:
            logger.error(f"导出CSV失败: {e}")
            return False


def cmd_analyze(args):
    """
    执行分析命令

    Args:
        args: 命令行参数
    """
    logger.info("执行股票分析...")

    analyzer = SimpleAnalyzer()

    try:
        results = analyzer.run_analysis()

        if args.output == 'table':
            print(analyzer.format_report())
        elif args.output == 'json':
            import json
            print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
        else:
            print(analyzer.format_report())

        if args.export:
            analyzer.export_to_csv(args.export)
            logger.info(f"结果已导出到: {args.export}")

        return results

    except Exception as e:
        logger.error(f"分析失败: {e}")
        print(f"分析失败: {e}")
        return []


def cmd_watch(args):
    """
    监控模式命令

    Args:
        args: 命令行参数
    """
    logger.info("启动监控模式...")
    print("=" * 50)
    print("  股票集合竞价智能分析工具 - 监控模式")
    print("=" * 50)
    print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("等待集合竞价结束自动执行分析...")
    print("-" * 50)

    analyzer = SimpleAnalyzer()
    pre_market = PreMarketAnalyzer()

    if not pre_market.is_trading_day():
        print("提示: 今天不是交易日（周末或节假日）")
        logger.info("非交易日，监控模式退出")
        return

    while pre_market.is_pre_market_time():
        current_time = datetime.now().strftime('%H:%M:%S')
        remaining = time_until_market_open()

        print(f"[{current_time}] 集合竞价进行中，距离开盘还有 {remaining} 分钟...")
        time.sleep(args.interval)

    print("-" * 50)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 集合竞价结束，开始分析...")
    print()

    try:
        results = analyzer.run_analysis()
        print(analyzer.format_report())

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        export_file = f"result_{timestamp}.csv"
        analyzer.export_to_csv(export_file)
        print(f"\n结果已导出到: {export_file}")

        return results

    except Exception as e:
        logger.error(f"分析失败: {e}")
        print(f"分析失败: {e}")
        return []


def cmd_backtest(args):
    """
    回测模式命令（用于验证策略）

    Args:
        args: 命令行参数
    """
    logger.info("执行回测模式...")
    print("=" * 50)
    print("  股票集合竞价智能分析工具 - 回测模式")
    print("=" * 50)
    print("回测功能开发中...")
    print()

    # TODO: 实现回测功能
    print("回测模式将使用历史竞价数据验证策略准确性")
    print("请等待后续版本更新")


def cmd_status(args):
    """
    显示状态信息

    Args:
        args: 命令行参数
    """
    print("=" * 50)
    print("  股票集合竞价智能分析工具 - 状态信息")
    print("=" * 50)

    pre_market = PreMarketAnalyzer()

    # 时间状态
    now = datetime.now()
    print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"是否交易日: {'是' if pre_market.is_trading_day() else '否（周末/节假日）'}")
    print(f"是否竞价时段: {'是' if pre_market.is_pre_market_time() else '否'}")

    # 时间建议
    if pre_market.is_trading_day():
        if now.hour < 9:
            print(f"\n建议: 等待9:15集合竞价开始后执行分析")
        elif pre_market.is_pre_market_time():
            remaining = time_until_market_open()
            print(f"\n建议: 竉价进行中，等待9:30开盘前执行分析（还有 {remaining} 分钟）")
        else:
            print(f"\n建议: 可立即执行分析，或等待明天竞价时段")

    print("-" * 50)


def time_until_market_open() -> int:
    """
    计算距离开盘还有多少分钟

    Returns:
        距离开盘的分钟数
    """
    now = datetime.now()
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)

    if now < market_open:
        return int((market_open - now).total_seconds() / 60)
    return 0


def main():
    """
    主入口函数
    """
    parser = argparse.ArgumentParser(
        description='股票集合竞价智能分析工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python main.py analyze          # 立即执行分析
  python main.py watch            # 监控模式，等竞价结束自动分析
  python main.py watch -i 60      # 监控模式，每60秒检查一次
  python main.py analyze --export result.csv  # 分析并导出结果
  python main.py status           # 显示当前状态

时间说明:
  集合竞价时间: 9:15 - 9:25
  开盘时间: 9:30
  建议分析时间: 9:25 - 9:30（竞价结束后开盘前）
        '''
    )

    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # analyze 命令
    analyze_parser = subparsers.add_parser('analyze', help='立即执行股票分析')
    analyze_parser.add_argument(
        '-o', '--output',
        choices=['table', 'json', 'text'],
        default='table',
        help='输出格式（默认: table）'
    )
    analyze_parser.add_argument(
        '-e', '--export',
        metavar='FILE',
        help='导出结果到CSV文件'
    )

    # watch 命令
    watch_parser = subparsers.add_parser('watch', help='监控模式，等竞价结束自动分析')
    watch_parser.add_argument(
        '-i', '--interval',
        type=int,
        default=30,
        help='检查间隔秒数（默认: 30）'
    )

    # backtest 命令
    backtest_parser = subparsers.add_parser('backtest', help='回测模式（开发中）')

    # status 命令
    status_parser = subparsers.add_parser('status', help='显示当前状态信息')

    # 解析参数
    args = parser.parse_args()

    # 执行对应命令
    if args.command == 'analyze':
        cmd_analyze(args)
    elif args.command == 'watch':
        cmd_watch(args)
    elif args.command == 'backtest':
        cmd_backtest(args)
    elif args.command == 'status':
        cmd_status(args)
    else:
        # 无命令时显示帮助
        parser.print_help()
        print("\n提示: 请使用 analyze, watch, status 等命令")


if __name__ == '__main__':
    main()