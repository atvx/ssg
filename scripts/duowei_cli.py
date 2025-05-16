#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from datetime import datetime

from config.settings import DUOWEI_CONFIG
from core.duowei.data import get_all_duowei_data


def main(date=None):
    """
    获取多维系统数据的主函数
    
    Args:
        date: 查询日期，格式为YYYY-MM-DD，默认为当天
    
    Returns:
        成功返回True，失败返回None
    """
    print("启动多维系统数据获取工具...")
    
    try:
        # 获取所有仓库的销售数据
        results = get_all_duowei_data(DUOWEI_CONFIG, date)
        
        if results:
            print(f"成功获取 {len(results)} 个仓库的销售数据")
            print(f"数据已保存到: {DUOWEI_CONFIG['OUTPUT_FILE']}")
            return True
        else:
            print("未能获取销售数据")
            return None
    except Exception as e:
        print(f"获取多维系统数据过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # 获取命令行参数中的日期（如果有）
    date_arg = None
    if len(sys.argv) > 1:
        date_arg = sys.argv[1]
        try:
            # 验证日期格式
            datetime.strptime(date_arg, '%Y-%m-%d')
        except ValueError:
            print(f"错误: 日期格式无效，请使用YYYY-MM-DD格式")
            sys.exit(1)
    
    # 运行主程序
    success = main(date_arg)
    if not success:
        sys.exit(1) 