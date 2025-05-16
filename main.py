#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import argparse
from datetime import datetime

from scripts.meituan_cli import main as meituan_main
from scripts.duowei_cli import main as duowei_main
from config.settings import MEITUAN_CONFIG, DUOWEI_CONFIG

def merge_results(meituan_file, duowei_file, output_file):
    """
    合并美团和多维的数据结果，将所有仓库数据放在一个列表中
    
    Args:
        meituan_file: 美团数据文件路径
        duowei_file: 多维数据文件路径
        output_file: 输出文件路径
        
    Returns:
        合并后的数据列表
    """
    try:
        # 读取美团数据
        with open(meituan_file, 'r', encoding='utf-8') as f:
            meituan_data = json.load(f)
        
        # 读取多维数据
        with open(duowei_file, 'r', encoding='utf-8') as f:
            duowei_data = json.load(f)
        
        # 直接合并两个列表
        results = meituan_data + duowei_data
        
        # 按仓库名称排序
        results.sort(key=lambda x: x["name"])
        
        # 保存合并结果
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
        return results
    except Exception as e:
        print(f"合并数据文件时出错: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='获取美团POS和多维系统的销售数据')
    parser.add_argument('--date', type=str, help='查询日期 (YYYY-MM-DD格式，默认为今天)')
    parser.add_argument('--meituan', action='store_true', help='仅获取美团数据')
    parser.add_argument('--duowei', action='store_true', help='仅获取多维数据')
    parser.add_argument('--output', type=str, default='sales_merged.json', help='合并数据输出文件名')
    
    args = parser.parse_args()
    
    # 验证日期格式
    date = args.date
    if date:
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            print("错误: 日期格式无效，请使用YYYY-MM-DD格式")
            return False
    
    # 根据参数决定获取哪些数据
    get_meituan = True
    get_duowei = True
    
    if args.meituan and not args.duowei:
        get_duowei = False
    elif args.duowei and not args.meituan:
        get_meituan = False
    
    meituan_success = None
    duowei_success = None
    
    # 获取美团数据
    if get_meituan:
        print("=" * 50)
        print("获取美团POS销售数据")
        print("=" * 50)
        meituan_success = meituan_main(date)
    
    # 获取多维数据
    if get_duowei:
        print("=" * 50)
        print("获取多维系统销售数据")
        print("=" * 50)
        duowei_success = duowei_main(date)
    
    # 如果两个数据源都获取成功，合并结果
    if get_meituan and get_duowei and meituan_success and duowei_success:
        print("=" * 50)
        print("合并销售数据")
        results = merge_results(
            MEITUAN_CONFIG["OUTPUT_FILE"],
            DUOWEI_CONFIG["OUTPUT_FILE"],
            args.output
        )
        
        if results:
            print(f"成功合并 {len(results)} 个仓库的销售数据")
            print(f"合并数据已保存到: {args.output}")
    
    # 数据获取状态汇报
    print("=" * 50)
    print("数据获取状态:")
    if get_meituan:
        print(f"- 美团POS: {'成功' if meituan_success else '失败'}")
    if get_duowei:
        print(f"- 多维系统: {'成功' if duowei_success else '失败'}")
    
    # 只要有一个成功就返回True
    return meituan_success or duowei_success


if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1) 