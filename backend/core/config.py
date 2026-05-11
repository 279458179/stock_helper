"""
股票集合竞价智能分析工具配置模块
跨平台兼容：支持 Windows、macOS、Linux
"""
import os
import sys
from pathlib import Path
from datetime import time

# 项目根目录（使用 pathlib 确保跨平台兼容）
# config.py 位于 backend/core/ 目录，需要向上两级获取 backend 目录
BASE_DIR = Path(__file__).resolve().parent.parent  # backend 目录
PROJECT_ROOT = BASE_DIR.parent  # stock-helper 目录

# 数据缓存目录
CACHE_DIR = BASE_DIR / 'cache'

# 日志目录和文件
LOG_DIR = BASE_DIR / 'logs'
LOG_FILE = LOG_DIR / 'analyzer.log'

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

# 确保必要目录存在
def ensure_dirs():
    """确保必要的目录存在（跨平台兼容）"""
    # 使用 pathlib 的 mkdir 方法，parents=True 会创建父目录
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

# 在模块加载时确保目录存在
ensure_dirs()

# 获取日志文件路径（返回字符串以兼容 logging 模块）
def get_log_file_path() -> str:
    """获取日志文件路径（返回字符串格式以兼容 logging）"""
    return str(LOG_FILE)

# 获取缓存目录路径（返回字符串以兼容其他模块）
def get_cache_dir_path() -> str:
    """获取缓存目录路径（返回字符串格式）"""
    return str(CACHE_DIR)