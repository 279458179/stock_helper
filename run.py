#!/usr/bin/env python3
"""
股票集合竞价智能分析工具启动脚本
跨平台兼容：支持 Windows、macOS、Linux

使用方法：
    Windows: python run.py analyze
    macOS/Linux: python3 run.py analyze
"""
import sys
import subprocess
from pathlib import Path

# 获取 backend 目录路径
backend_dir = Path(__file__).resolve().parent / 'backend'

# 确保 backend 目录存在
if not backend_dir.exists():
    print(f"错误: backend 目录不存在: {backend_dir}")
    sys.exit(1)

def main():
    """主入口函数"""
    # 构建命令
    main_script = backend_dir / 'main.py'

    # 将用户参数传递给 main.py
    args = [sys.executable, str(main_script)] + sys.argv[1:]

    # 执行命令
    try:
        subprocess.run(args, cwd=str(backend_dir))
    except KeyboardInterrupt:
        print("\n程序已中断")
    except Exception as e:
        print(f"执行错误: {e}")
        sys.exit(1)

if __name__ == '__main__':
    # 如果没有参数，显示帮助
    if len(sys.argv) == 1:
        print("=" * 50)
        print("  股票集合竞价智能分析工具")
        print("=" * 50)
        print("\n使用方法:")
        print("  python run.py analyze          # 立即执行分析")
        print("  python run.py watch            # 监控模式")
        print("  python run.py status           # 显示当前状态")
        print("  python run.py test             # 运行模拟测试")
        print("\n更多帮助请执行:")
        print("  python run.py analyze --help")
        print()
        sys.exit(0)

    # 特殊命令处理
    if sys.argv[1] == 'test':
        # 运行模拟测试
        test_script = backend_dir / 'test_mock.py'
        subprocess.run([sys.executable, str(test_script)], cwd=str(backend_dir))
    else:
        main()