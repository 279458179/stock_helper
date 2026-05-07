"""
工具函数模块
"""
import pandas as pd
import numpy as np
from datetime import datetime, time
from typing import Optional
import os


def format_price(price: float) -> str:
    """
    格式化价格显示

    Args:
        price: 价格

    Returns:
        格式化的价格字符串
    """
    if price <= 0:
        return "无效"
    return f"{price:.2f}元"


def format_change_pct(change_pct: float) -> str:
    """
    格式化涨跌幅显示

    Args:
        change_pct: 涨跌幅（比例）

    Returns:
        格式化的涨跌幅字符串
    """
    if change_pct > 0:
        return f"+{change_pct * 100:.2f}%"
    elif change_pct < 0:
        return f"{change_pct * 100:.2f}%"
    else:
        return "0.00%"


def format_volume(volume: float) -> str:
    """
    格式化成交量显示

    Args:
        volume: 成交量

    Returns:
        格式化的成交量字符串
    """
    if volume >= 1e8:  # 1亿以上
        return f"{volume / 1e8:.2f}亿"
    elif volume >= 1e6:  # 100万以上
        return f"{volume / 1e6:.2f}万"
    else:
        return f"{volume:.0f}"


def format_amount(amount: float) -> str:
    """
    格式化成交额显示

    Args:
        amount: 成交额

    Returns:
        格式化的成交额字符串
    """
    if amount >= 1e8:  # 1亿以上
        return f"{amount / 1e8:.2f}亿"
    elif amount >= 1e6:  # 100万以上
        return f"{amount / 1e6:.2f}万"
    else:
        return f"{amount:.0f}"


def is_trading_time() -> bool:
    """
    判断是否在交易时段

    Returns:
        是否在交易时段
    """
    now = datetime.now().time()

    # A股交易时间：9:30-11:30, 13:00-15:00
    morning_session = time(9, 30) <= now <= time(11, 30)
    afternoon_session = time(13, 0) <= now <= time(15, 0)

    return morning_session or afternoon_session


def is_pre_market_time() -> bool:
    """
    判断是否在集合竞价时段

    Returns:
        是否在竞价时段
    """
    now = datetime.now().time()
    return time(9, 15) <= now <= time(9, 25)


def get_market_phase() -> str:
    """
    获取当前市场阶段

    Returns:
        市场阶段描述
    """
    now = datetime.now().time()

    if time(9, 15) <= now < time(9, 25):
        return "集合竞价（集合竞价阶段）"
    elif time(9, 25) <= now < time(9, 30):
        return "竞价结束等待开盘"
    elif time(9, 30) <= now < time(11, 30):
        return "上午交易时段"
    elif time(11, 30) <= now < time(13, 0):
        return "午间休市"
    elif time(13, 0) <= now < time(15, 0):
        return "下午交易时段"
    elif now >= time(15, 0):
        return "已收盘"
    else:
        return "未开盘"


def validate_stock_code(code: str) -> bool:
    """
    验证股票代码格式

    Args:
        code: 股票代码

    Returns:
        是否有效
    """
    # A股代码格式：6位数字，以6、0、3开头
    if len(code) != 6:
        return False

    if not code.isdigit():
        return False

    return code.startswith(('6', '0', '3'))


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    清理DataFrame数据

    Args:
        df: 输入DataFrame

    Returns:
        清理后的DataFrame
    """
    # 删除空值行
    df = df.dropna()

    # 删除重复行
    df = df.drop_duplicates()

    return df


def save_json(data: dict, filepath: str) -> bool:
    """
    保存数据为JSON文件

    Args:
        data: 数据字典
        filepath: 文件路径

    Returns:
        是否成功
    """
    import json

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        return True
    except Exception as e:
        print(f"保存JSON失败: {e}")
        return False


def load_json(filepath: str) -> Optional[dict]:
    """
    从JSON文件加载数据

    Args:
        filepath: 文件路径

    Returns:
        数据字典，失败返回None
    """
    import json

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载JSON失败: {e}")
        return None