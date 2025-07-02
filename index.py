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
    import os
    # 立即执行一次
    filename = "data/fund_ranking_data.csv"
    do_ansys(filename)
    
    