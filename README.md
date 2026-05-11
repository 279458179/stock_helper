# 股票集合竞价智能分析工具

一款专注于A股集合竞价的智能分析工具，在9:15-9:25竞价时段结束后，快速筛选出看涨潜力股。

**跨平台兼容**：支持 Windows、macOS、Linux

## 功能特点

- **时效性强**: 竞价结束后立即分析，开盘前完成筛选
- **智能分析**: 多策略综合评分（量价配合、技术指标、资金流向）
- **精准筛选**: 价格≤20元，看涨评分排序，选出Top 5
- **操作建议**: 每只股票提供详细的操作建议和风险提示
- **买卖指导**: 包含买入时机、价位、卖出条件、止盈止损等详细建议

## 快速开始

### 1. 安装依赖

```bash
# Windows
cd backend
pip install -r requirements.txt

# macOS/Linux
cd backend
pip3 install -r requirements.txt
```

### 2. 使用方法

#### 方式一：使用启动脚本（推荐）

```bash
# Windows
python run.py analyze          # 立即执行分析
python run.py watch            # 监控模式
python run.py status           # 显示当前状态
python run.py test             # 运行模拟测试

# macOS/Linux
python3 run.py analyze         # 立即执行分析
python3 run.py watch           # 监控模式
python3 run.py status          # 显示当前状态
python3 run.py test            # 运行模拟测试
```

#### 方式二：直接运行 backend/main.py

```bash
# Windows
cd backend
python main.py analyze

# macOS/Linux
cd backend
python3 main.py analyze
```

#### 立即执行分析
```bash
python main.py analyze
```

#### 监控模式（等待竞价结束自动分析）
```bash
python main.py watch
```

#### 查看状态
```bash
python main.py status
```

#### 导出结果到CSV
```bash
python main.py analyze --export result.csv
```

## 最佳使用时间

| 时间 | 状态 | 建议 |
|------|------|------|
| 9:15-9:25 | 集合竞价 | 运行 `watch` 监控模式 |
| 9:25-9:30 | 竞价结束 | 运行 `analyze` 立即分析 |
| 9:30 | 开盘 | 根据分析结果操作 |

## 分析策略说明

### 1. 量价配合策略
- 竞价量比（成交量放大程度）
- 竞价涨幅（价格变化）
- 量价齐升评分

### 2. 技术指标组合
- MACD金叉/死叉
- KDJ超买/超卖
- 均线系统（MA5/MA10/MA20）

### 3. 资金流向分析
- 成交额活跃度
- 换手率
- 成交量趋势

### 4. 综合智能评分
- 多因子加权模型
- 价格动量因子
- 波动率因子
- 相对强度因子

## 买卖操作建议说明

分析报告中包含以下买卖建议：

- **买入条件**: 何时买入的具体条件说明
- **买入价位**: 建议买入的价格区间
- **买入时机**: 最佳买入时间段
- **卖出条件**: 达到什么条件卖出
- **卖出目标**: 目标卖出价位
- **卖出时机**: 最佳卖出时间段
- **止盈目标**: 预期盈利目标价
- **止损价位**: 风险控制止损价
- **持有周期**: 建议持有时间
- **建议仓位**: 推荐的仓位比例

## 输出示例

```
============================================================
          股票集合竞价智能分析报告
============================================================
分析时间: 2026-05-07 09:26:30
筛选条件: 价格≤20元, 看涨评分排序
推荐数量: 5 只
------------------------------------------------------------

【第1名】 600123 - XX科技
  竞价价格: 12.35元 (+2.80%)
  竞价量比: 3.2倍
  综合评分: 92.00分
  风险等级: 低
  操作建议: 强烈推荐，多个看涨信号共振，建议开盘重点关注

【第2名】 000456 - XX电子
  竞价价格: 8.56元 (+1.50%)
  竞价量比: 2.1倍
  综合评分: 87.00分
  ...
```

## 项目结构

```
backend/
├── core/
│   ├── config.py        # 配置模块
│   ├── data_fetcher.py  # 数据获取（akshare）
│   ├── pre_market.py    # 集合竞价处理
│   └── analyzer.py      # 分析引擎
├── strategies/
│   ├── volume_price.py  # 量价配合策略
│   ├── technical.py     # 技术指标策略
│   ├── capital_flow.py  # 资金流向策略
│   └── composite.py     # 综合评分策略
├── utils/
│   └ helpers.py         # 工具函数
├── main.py              # CLI入口
└ requirements.txt       # 依赖包
```

## 配置说明

可在 `core/config.py` 中调整以下参数：

```python
MAX_STOCK_PRICE = 20.0    # 最大股票价格（元）
SELECT_TOP_N = 5          # 选择前N只股票

STRATEGY_WEIGHTS = {
    'volume_price': 0.30,  # 量价配合权重
    'technical': 0.25,     # 技术指标权重
    'capital_flow': 0.25,  # 资金流向权重
    'composite': 0.20      # 综合因子权重
}
```

## 注意事项

1. **数据延迟**: akshare免费数据可能有1-2分钟延迟
2. **交易时间**: 仅在A股交易日有效（9:15-9:25竞价时段）
3. **风险提示**: 分析结果仅供参考，不构成投资建议
4. **API限制**: akshare无官方限制，但建议合理使用

## 免责声明

本工具仅用于技术学习和研究目的。股市投资有风险，请根据自身情况谨慎决策。本工具的分析结果不构成任何投资建议，使用者需自行承担投资风险。

## 技术支持

- 数据源: [Akshare](https://github.com/akfamily/akshare)
- Python版本: 3.8+