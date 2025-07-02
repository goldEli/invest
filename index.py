import pandas as pd
import numpy as np
import akshare as ak
import smtplib
from email.mime.text import MIMEText
import time
import schedule
from datetime import datetime
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re
import os

# ===================== 配置参数 =====================
INVESTMENT_PER_FUND = 1000  # 单只基金定投金额

# ===================== 基金筛选函数 =====================
def screen_bond_funds(filename):
    """获取并筛选债券基金前10名"""
    try:
        # 获取全市场债券基金数据
        df_all = pd.read_csv(filename)
        print(f"共获取 {len(df_all)} 只债券基金")


        # 数据清洗处理
        df = df_all.copy()
        
        # 处理特殊字符，将 '---' 替换为 NaN
        df = df.replace('---', np.nan)
        df = df.replace('--', np.nan)
        
        # 必须有3年历史数据
        df = df.dropna(subset=['近3年'])
        
        # 数值转换，处理百分比和特殊字符
        def safe_convert_to_float(value):
            """安全转换为浮点数，处理特殊字符"""
            if pd.isna(value) or value == '---' or value == '--':
                return np.nan
            try:
                # 移除百分比符号并转换为浮点数
                if isinstance(value, str):
                    value = value.replace('%', '').replace(',', '')
                return float(value)
            except (ValueError, TypeError):
                return np.nan
        
        # 转换数值列
        df['近3年'] = df['近3年'].apply(safe_convert_to_float)
        df['手续费'] = df['手续费'].apply(safe_convert_to_float)
        
        # 转换其他可能的时间段收益率列
        time_periods = ['近1年', '近6月', '近3月', '近1月', '近1周']
        for col in time_periods:
            if col in df.columns:
                df[col] = df[col].apply(safe_convert_to_float)
        
        # 移除转换后仍为NaN的行
        df = df.dropna(subset=['近3年'])
        
        # 核心指标计算 - 使用更合理的风险指标
        # 方法1：如果有多个时间段的收益率数据，计算波动率
        volatility_columns = ['近1年', '近6月', '近3月', '近1月']
        available_volatility_cols = [col for col in volatility_columns if col in df.columns]
        
        print(f"可用的波动率计算列: {available_volatility_cols}")
        
        if len(available_volatility_cols) >= 2:
            # 计算收益率的标准差作为波动率
            df['波动率'] = df[available_volatility_cols].std(axis=1)
            df['风险调整收益'] = df['近3年'] / (df['波动率'] + 0.01)  # 加0.01避免除零
            print("使用波动率计算风险调整收益")
        else:
            # 方法2：使用手续费作为风险代理指标（费率越高，风险相对越高）
            df['风险调整收益'] = df['近3年'] / (df['手续费'] + 1)  # 加1避免除零
            print("使用手续费作为风险代理指标计算风险调整收益")
        
        # 综合评分模型
        df['收益评分'] = (df['近3年'] / df['近3年'].max()) * 40
        df['风险评分'] = (df['风险调整收益'] / df['风险调整收益'].max()) * 30
        df['费率评分'] = (1 - df['手续费'] / df['手续费'].max()) * 20
        df['综合评分'] = df[['收益评分', '风险评分', '费率评分']].sum(axis=1)
        
        # 筛选前10名
        top_10 = df.sort_values('综合评分', ascending=False).head(10)
        return top_10[['基金代码', '基金简称', '综合评分', '近3年', '手续费']]
    
    except Exception as e:
        print(f"数据获取失败: {str(e)}")
        return None

# ===================== 定时任务 =====================
def do_ansys(filename):
    # 步骤1: 筛选基金
    top_funds = screen_bond_funds(filename)
    if top_funds is None or len(top_funds) == 0:
        print("未筛选到符合条件的基金")
        return
    
    print(f"筛选出前{len(top_funds)}只优质债券基金:")
    print(top_funds[['基金代码', '基金简称', '综合评分']])
    
    # 步骤2: 执行定投
    # report, summary = execute_investment(top_funds)
    
    # 步骤3: 发送报告
    # report_content = "基金定投执行详情:\n\n"
    # for item in report:
    #     report_content += f"{item['基金代码']} {item['基金名称']}: {item['投资金额']}元 (费率:{item['费率']}%)\n"
    
    # full_content = summary + "\n\n" + report_content
    # send_email("债券基金定投执行报告", full_content)
    # print("债券基金定投执行报告", full_content)
    
    # # 保存历史记录
    # history_file = "bond_fund_investment_history.csv"
    # history_df = pd.DataFrame(report)
    # history_df['定投日期'] = datetime.now().strftime("%Y-%m-%d")
    # history_df.to_csv(history_file, mode='a', header=not os.path.exists(history_file), index=False)
    
    # print(f"任务完成! 报告已发送并保存至{history_file}")

# ===================== 主程序 =====================
if __name__ == "__main__":
    # 定义基金类型映射
    fund_types = {
        '1': ('tzs', '指数型'),
        '2': ('tgp', '股票型'),
        '3': ('thh', '混合型'),
        '4': ('tzq', '债券型')
    }
    
    # 获取当前月份
    month_str = datetime.now().strftime("%Y%m")
    data_dir = f"data/top_10/{month_str}"
    os.makedirs(data_dir, exist_ok=True)
    source_data_dir = f"data/{month_str}"
    
    print("基金分析工具")
    print("=" * 50)
    print(f"分析目录: {source_data_dir}")
    print("=" * 50)
    
    # 检查数据目录是否存在
    if not os.path.exists(source_data_dir):
        print(f"数据目录 {source_data_dir} 不存在，请先运行 fund_data_scraper.py 爬取数据")
        exit(1)
    
    # 循环处理每种基金类型
    # all_top_funds = []
    
    for type_code, (data_type, type_name) in fund_types.items():
        filename = f"{source_data_dir}/fund_ranking_{data_type}_{type_name}.csv"
        
        print(f"\n{'='*50}")
        print(f"正在分析: {type_name} ({data_type})")
        print(f"文件: {filename}")
        print(f"{'='*50}")
        
        # 检查文件是否存在
        if not os.path.exists(filename):
            print(f"文件不存在: {filename}")
            continue
        
        # 分析该类型的基金
        top_funds = screen_bond_funds(filename)
        
        if top_funds is None or len(top_funds) == 0:
            print(f"未筛选到符合条件的{type_name}基金")
            continue
        
        print(f"筛选出前{len(top_funds)}只优质{type_name}基金:")
        print(top_funds[['基金代码', '基金简称', '综合评分']])
        
        # 添加基金类型信息
        top_funds['基金类型'] = type_name
        top_funds['类型代码'] = data_type
        
        # 保存该类型的前10名到CSV
        top_10_filename = f"{data_dir}/top10_{data_type}_{type_name}.csv"
        top_funds.to_csv(top_10_filename, index=False, encoding='utf-8-sig')
        print(f"前10名{type_name}基金已保存到: {top_10_filename}")
        
        # 添加到总列表
        # all_top_funds.append(top_funds)
    
    # 合并所有类型的前10名基金
    # if all_top_funds:
    #     print(f"\n{'='*50}")
    #     print("合并所有类型的前10名基金")
    #     print(f"{'='*50}")
        
    #     # 合并所有DataFrame
    #     combined_top_funds = pd.concat(all_top_funds, ignore_index=True)
        
    #     # 按综合评分重新排序
    #     combined_top_funds = combined_top_funds.sort_values('综合评分', ascending=False)
        
    #     print(f"总共筛选出 {len(combined_top_funds)} 只优质基金")
    #     print("\n前20名基金:")
    #     print(combined_top_funds[['基金代码', '基金简称', '基金类型', '综合评分']].head(20))
        
    #     # 保存合并后的前10名到CSV
    #     combined_filename = f"{data_dir}/top10_combined_all_types.csv"
    #     combined_top_funds.to_csv(combined_filename, index=False, encoding='utf-8-sig')
    #     print(f"\n合并后的前10名基金已保存到: {combined_filename}")
        
    #     # 按基金类型分别保存前10名
    #     for type_code, (data_type, type_name) in fund_types.items():
    #         type_funds = combined_top_funds[combined_top_funds['基金类型'] == type_name]
    #         if len(type_funds) > 0:
    #             type_top10_filename = f"{data_dir}/top10_{data_type}_{type_name}_from_combined.csv"
    #             type_funds.head(10).to_csv(type_top10_filename, index=False, encoding='utf-8-sig')
    #             print(f"{type_name}前10名（从合并数据中）已保存到: {type_top10_filename}")
    
    print(f"\n{'='*50}")
    print("分析完成！")
    print(f"所有结果文件保存在: {data_dir}")
    print(f"{'='*50}")
    
    