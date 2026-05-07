"""
股票集合竞价智能分析工具配置模块
"""
import os
from datetime import time

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 数据缓存目录
CACHE_DIR = os.path.join(BASE_DIR, 'cache')

# A股交易时间配置
PRE_MARKET_START = time(9, 15)   # 集合竞价开始
PRE_MARKET_END = time(9, 25)     # 集合竞价结束
MARKET_OPEN = time(9, 30)        # 开盘时间
MARKET_CLOSE = time(15, 0)       # 收盘时间

# 筛选条件配置
MAX_STOCK_PRICE = 20.0           # 最大股票价格（元）
SELECT_TOP_N = 5                 # 选择前N只股票

# 分析策略权重配置
STRATEGY_WEIGHTS = {
    'volume_price': 0.30,        # 量价配合权重
    'technical': 0.25,           # 技术指标权重
    'capital_flow': 0.25,        # 资金流向权重
    'composite': 0.20            # 综合因子权重
}

# 量价策略阈值
VOLUME_PRICE_THRESHOLDS = {
    'min_volume_ratio': 1.5,     # 最小竞价量比（倍）
    'min_price_change': 0.01,    # 最小价格涨幅（1%）
    'max_price_change': 0.10,    # 最大价格涨幅（10%，避免过度追涨）
}

# 技术指标阈值
TECHNICAL_THRESHOLDS = {
    'macd_cross': True,          # MACD金叉
    'kdj_oversell': 20,          # KDJ超卖阈值
    'kdj_overbuy': 80,           # KDJ超买阈值
}

# 资金流向阈值
CAPITAL_FLOW_THRESHOLDS = {
    'min_main_inflow': 1000000,  # 主力最小净流入（元）
    'min_big_order_ratio': 0.3,  # 大单买入最小占比
}

# 数据更新配置
DATA_UPDATE_INTERVAL = 30        # 数据更新间隔（秒）

# 输出配置
OUTPUT_FORMAT = 'table'          # 输出格式：table, json, text

# 日志配置
LOG_LEVEL = 'INFO'
LOG_FILE = os.path.join(BASE_DIR, 'logs', 'analyzer.log')

# 确保必要目录存在
def ensure_dirs():
    """确保必要的目录存在"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

ensure_dirs()