"""
真实数据测试脚本 - 使用真实股票数据测试分析流程
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime
import akshare as ak
import time
from strategies.composite import CompositeStrategy

def get_real_stocks():
    """获取真实A股数据"""
    print("正在获取A股实时数据...")

    # 优先使用sina数据源（更稳定，返回代码格式为sh600000/sz000001）
    try:
        stock_data = ak.stock_zh_a_spot()
        print(f"获取到 {len(stock_data)} 只股票数据(sina)")
        return stock_data
    except Exception as e:
        print(f"sina数据源失败: {e}")
        return None

def get_stock_history_real(code, days=30):
    """获取真实历史数据 - 使用stock_zh_a_daily接口"""
    try:
        # akshare的stock_zh_a_daily需要带市场前缀的代码
        # 如果代码是纯数字，需要添加市场前缀
        if not code.startswith(('sh', 'sz')):
            # 根据代码判断市场
            if code.startswith('6'):
                code = 'sh' + code
            else:
                code = 'sz' + code

        start_date = (datetime.now() - pd.Timedelta(days=days)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')

        # 使用stock_zh_a_daily接口（不依赖eastmoney）
        hist = ak.stock_zh_a_daily(symbol=code, start_date=start_date, end_date=end_date, adjust='qfq')

        # 重命名列以匹配后续分析需要的格式
        if 'date' in hist.columns:
            hist = hist.rename(columns={
                'date': '日期',
                'open': '开盘',
                'high': '最高',
                'low': '最低',
                'close': '收盘',
                'volume': '成交量',
                'amount': '成交额'
            })

        return hist
    except Exception as e:
        print(f"获取 {code} 历史数据失败: {e}")
        return None

def test_real_analysis():
    """使用真实数据进行测试"""
    print("=" * 60)
    print("          真实数据测试 - 股票智能分析")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)

    # Step 1: 获取真实股票列表
    print("\nStep 1: 获取A股实时数据...")
    stocks = get_real_stocks()

    if stocks is None or stocks.empty:
        print("获取数据失败，无法继续测试")
        return

    # Step 2: 筛选符合条件的股票
    print("\nStep 2: 筛选价格<=20元的A股...")

    # 确保列名正确
    print(f"数据列: {stocks.columns.tolist()}")

    # sina数据源返回的代码格式是 sh600000 或 sz000001
    # 筛选沪深A股 (sh开头或sz开头)
    filtered = stocks[
        (stocks['最新价'] > 0) &
        (stocks['最新价'] <= 20) &
        (stocks['最新价'] > 1) &
        (stocks['代码'].str.match(r'^(sh|sz)[036]\d{5}$'))  # 沪深A股: sh/sz + 6位数字
    ].copy()

    print(f"筛选出 {len(filtered)} 只符合条件的沪深A股")

    if filtered.empty:
        print("筛选后无股票，显示列名诊断...")
        print(f"代码示例: {stocks['代码'].head(20).tolist()}")
        # 使用前10只作为备用
        filtered = stocks.head(10).copy()

    # Step 3: 选择涨幅靠前的股票进行分析
    print("\nStep 3: 选择涨幅较大的股票...")

    # 计算涨幅
    filtered['涨幅'] = (filtered['最新价'] - filtered['昨收']) / filtered['昨收'] * 100

    # 筛选涨幅>0的股票
    rising = filtered[filtered['涨幅'] > 0].copy()
    rising = rising.sort_values('涨幅', ascending=False)

    print(f"涨幅>0的股票有 {len(rising)} 只")

    # 显示前几只股票
    print("涨幅前5名:")
    for i, row in rising.head(5).iterrows():
        print(f"  {row['代码']} - {row['名称']}: {row['最新价']:.2f}元 (+{row['涨幅']:.2f}%)")

    # 取前5只进行深度分析
    top5_codes = rising.head(5)['代码'].tolist()

    print(f"选择分析: {top5_codes}")

    # Step 4: 获取历史数据并分析
    print("\nStep 4: 获取历史数据并分析...")
    strategy = CompositeStrategy()
    results = []

    for code in top5_codes:
        print(f"\n正在分析 {code}...")

        # 获取股票信息
        stock_info = rising[rising['代码'] == code].iloc[0]

        # 获取历史数据 (sina返回的代码是sh600000格式)
        hist = get_stock_history_real(code, days=30)

        if hist is None or hist.empty:
            print(f"  {code} 历史数据获取失败，跳过")
            continue

        print(f"  获取到 {len(hist)} 天历史数据")

        # 准备分析数据
        stock_data = {
            'code': code,  # 保持原始代码格式 (sh600000)
            'name': stock_info['名称'],
            'bid_price': float(stock_info['最新价']),
            'prev_close': float(stock_info['昨收']),
            'bid_change_pct': float(stock_info['涨幅']) / 100,
            'bid_volume': float(stock_info['成交量']),
            'amount': float(stock_info['成交额']),
            'turnover_rate': 0.5,  # 模拟换手率
            'volume_ratio': 1.5,   # 模拟量比
            'price_position': 0.5, # 模拟价格位置
        }

        # 执行分析
        try:
            analysis = strategy.analyze(stock_data, hist)
            result = {**stock_data, **analysis}
            result['bid_change_pct_display'] = f"{stock_data['bid_change_pct'] * 100:.2f}%"
            result['volume_ratio_display'] = f"{stock_data['volume_ratio']:.2f}倍"
            results.append(result)
            print(f"  分析完成: 综合评分 {result['composite_score']:.2f}")
        except Exception as e:
            print(f"  分析失败: {e}")

    # Step 5: 输出结果
    print("\n" + "=" * 60)
    print("          分析结果")
    print("=" * 60)

    if not results:
        print("无分析结果")
        return

    # 按评分排序
    results = sorted(results, key=lambda x: x['composite_score'], reverse=True)

    for i, stock in enumerate(results, 1):
        print(f"\n【第{i}名】 {stock['code']} - {stock['name']}")
        print(f"  当前价格: {stock['bid_price']:.2f}元 ({stock['bid_change_pct_display']})")
        print(f"  综合评分: {stock['composite_score']:.2f}分")
        print(f"  风险等级: {stock.get('risk_level', '未知')}")
        print(f"  操作建议: {stock['recommendation']}")

        # 显示信号
        if stock.get('all_signals'):
            print(f"  关键信号: {', '.join(stock['all_signals'][:3])}")

    print("\n" + "-" * 60)
    print("【风险提示】本分析仅供参考，股市有风险，投资需谨慎。")
    print("=" * 60)

    # 导出结果
    df = pd.DataFrame(results)
    df.to_csv('real_result.csv', index=False, encoding='utf-8-sig')
    print(f"\n结果已导出到: real_result.csv")

if __name__ == '__main__':
    test_real_analysis()