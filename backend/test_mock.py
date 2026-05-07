"""
模拟测试脚本 - 使用假数据测试完整分析流程
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime
from strategies.composite import CompositeStrategy

def create_mock_data():
    """创建模拟股票数据"""
    # 模拟10只股票
    stocks = []
    for i in range(10):
        code = f"600{100+i}"
        name = f"测试股票{i+1}"
        prev_close = 10 + i * 0.5  # 昨收价10-15元

        # 模拟竞价涨幅（1%-5%）
        bid_change_pct = 0.01 + (i % 5) * 0.01

        # 模拟竞价价格
        bid_price = prev_close * (1 + bid_change_pct)

        # 模拟竞价量比
        volume_ratio = 1.5 + i * 0.3

        stocks.append({
            'code': code,
            'name': name,
            'bid_price': bid_price,
            'prev_close': prev_close,
            'bid_change_pct': bid_change_pct,
            'bid_volume': 1000000 + i * 100000,
            'amount': 10000000 + i * 1000000,
            'turnover_rate': 0.5 + i * 0.1,
            'volume_ratio': volume_ratio,
            'price_position': 0.3 + i * 0.05,
        })

    return stocks

def create_mock_history(days=30):
    """创建模拟历史K线数据"""
    dates = pd.date_range(end=datetime.now(), periods=days)

    histories = {}
    for i in range(10):
        code = f"600{100+i}"

        # 基础价格
        base_price = 10 + i * 0.5

        # 模拟K线数据
        data = pd.DataFrame({
            '日期': dates,
            '开盘': base_price + np.random.randn(days) * 0.3,
            '收盘': base_price + np.random.randn(days) * 0.3,
            '最高': base_price + 0.5 + np.random.randn(days) * 0.2,
            '最低': base_price - 0.5 + np.random.randn(days) * 0.2,
            '成交量': 1000000 + np.random.randint(0, 500000, days),
        })

        # 确保价格逻辑正确
        data['最高'] = data[['开盘', '收盘']].max(axis=1) + 0.1
        data['最低'] = data[['开盘', '收盘']].min(axis=1) - 0.1

        histories[code] = data

    return histories

def test_analysis():
    """测试完整分析流程"""
    print("=" * 60)
    print("          模拟测试 - 股票智能分析")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)

    # 创建模拟数据
    print("Step 1: 创建模拟数据...")
    stocks = create_mock_data()
    histories = create_mock_history()
    print(f"创建了 {len(stocks)} 只股票的模拟数据")

    # 执行分析
    print("\nStep 2: 执行综合分析...")
    strategy = CompositeStrategy()
    results = []

    for stock in stocks:
        code = stock['code']
        if code in histories:
            analysis = strategy.analyze(stock, histories[code])
            result = {
                **stock,
                **analysis,
                'bid_change_pct_display': f"{stock['bid_change_pct'] * 100:.2f}%",
                'volume_ratio_display': f"{stock['volume_ratio']:.2f}倍",
            }
            results.append(result)

    # 排序
    results = sorted(results, key=lambda x: x['composite_score'], reverse=True)[:5]

    # 输出报告
    print("\nStep 3: 输出分析报告")
    print("-" * 60)

    for i, stock in enumerate(results, 1):
        print(f"\n【第{i}名】 {stock['code']} - {stock['name']}")
        print(f"  竞价价格: {stock['bid_price']:.2f}元 ({stock['bid_change_pct_display']})")
        print(f"  竞价量比: {stock['volume_ratio_display']}")
        print(f"  综合评分: {stock['composite_score']:.2f}分")
        print(f"  风险等级: {stock.get('risk_level', '未知')}")
        print(f"  操作建议: {stock['recommendation']}")

    print("\n" + "-" * 60)
    print("【风险提示】本分析仅供参考，股市有风险，投资需谨慎。")
    print("=" * 60)

    print("\n[OK] 测试成功！所有分析模块正常工作")

    # 导出CSV
    df = pd.DataFrame(results)
    df.to_csv('mock_result.csv', index=False, encoding='utf-8-sig')
    print(f"结果已导出到: mock_result.csv")

if __name__ == '__main__':
    test_analysis()