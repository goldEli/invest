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

max_pages = 85  # 最大爬取页数，避免无限循环

def get_data():
    """使用Selenium模拟浏览器从东方财富网获取基金排行数据"""
    url = "http://fund.eastmoney.com/data/fundranking.html#tzq;c0;r;s1nzf;pn50;ddesc;qsd20240701;qed20250701;qdii;zq;gg;gzbd;gzfs;bbzt;sfbb"
    
    driver = None
    try:
        print("正在启动Chrome浏览器...")
        
        # 配置Chrome选项
        chrome_options = Options()
        # chrome_options.add_argument('--headless')  # 无界面模式
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        # 启动浏览器
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        print("浏览器启动成功，正在访问网页...")
        driver.get(url)
        
        # 等待页面加载
        print("等待页面加载...")
        driver.implicitly_wait(10)
        
        # 等待表格元素出现
        wait = WebDriverWait(driver, 20)
        try:
            table_element = wait.until(EC.presence_of_element_located((By.ID, "dbtable")))
            print("成功找到目标表格元素")
        except Exception as e:
            print(f"等待表格元素超时: {str(e)}")
            # 尝试查找其他表格
            tables = driver.find_elements(By.TAG_NAME, "table")
            print(f"页面中共找到 {len(tables)} 个表格")
            for i, table in enumerate(tables):
                table_id = table.get_attribute('id')
                table_class = table.get_attribute('class')
                print(f"表格 {i+1}: id='{table_id}' class='{table_class}'")
            return None
        
        # 存储所有页面的数据
        all_data = []
        page_num = 1
        page_size = 50
        
        while page_num <= max_pages:
            print(f"\n正在处理第 {page_num} 页...")
            
            # 等待页面数据加载完成
            time.sleep(3)  # 等待页面渲染
            
            # 获取当前页面HTML
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 查找表格元素
            table = soup.find('table', id='dbtable')
            
            if not table:
                print(f"第 {page_num} 页未找到目标表格")
                break
            
            # 解析表格数据
            rows = table.find_all('tr')
            if len(rows) <= 1:  # 只有表头或空表格
                print(f"第 {page_num} 页表格数据为空")
                break
            
            # 提取表头（只在第一页提取）
            if page_num == 1:
                header_row = rows[0]
                headers = []
                for th in header_row.find_all(['th', 'td']):
                    header_text = th.get_text(strip=True)
                    if header_text:  # 只添加非空表头
                        headers.append(header_text)
                print(f"表头: {headers}")
            
            # 提取数据行
            data_rows = []
            for row in rows[1:]:  # 跳过表头行
                cells = row.find_all(['td', 'th'])
                if len(cells) > 0:
                    row_data = []
                    for cell in cells:
                        cell_text = cell.get_text(strip=True)
                        row_data.append(cell_text)
                    
                    # 确保数据行与表头列数匹配
                    if len(row_data) >= len(headers):
                        data_rows.append(row_data[:len(headers)])
            
            print(f"第 {page_num} 页解析到 {len(data_rows)} 行数据")
            
            # 将当前页面数据添加到总数据中
            all_data.extend(data_rows)

            # 如果当前页数据行数小于 page_size，则跳出循环
            if len(data_rows) < page_size:
                print("已到达最后一页")
                break
            
            # 尝试点击下一页按钮
            try:
                # 等待下一页按钮出现
                # next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="pagebar"]/label[8]')))
                input_page = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="pnum"]')))
                input_page.send_keys(page_num + 1)
                next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="pagebar"]/input[2]')))
                
                # 检查按钮是否可点击（不是最后一页）
                # if 'disabled' in next_button.get_attribute('class') or 'current' in next_button.get_attribute('class'):
                #     print("已到达最后一页")
                #     break
                
                # 点击下一页
                print("点击下一页按钮...")
                driver.execute_script("arguments[0].click();", next_button)
                
                # 添加随机延迟，避免被封
                delay = 2 + random.random() * 3  # 2-5秒随机延迟
                print(f"等待 {delay:.1f} 秒...")
                time.sleep(delay)
                
                page_num += 1
                
            except Exception as e:
                print(f"点击下一页失败或已到最后一页: {str(e)}")
                break
        
        print(f"\n总共获取了 {len(all_data)} 行数据，来自 {page_num} 页")
        
        # 创建DataFrame
        if all_data and headers:
            df = pd.DataFrame(all_data, columns=headers)
            print("数据解析完成，前5行数据:")
            print(df.head())
            
            # 保存数据到CSV文件, 存入data目录
            output_file = "data/fund_ranking_data.csv"
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"数据已保存到 {output_file}")
            
            return df
        else:
            print("未解析到有效数据")
            return None
            
    except Exception as e:
        print(f"数据获取失败: {str(e)}")
        return None
    finally:
        if driver:
            print("关闭浏览器...")
            driver.quit()

# ===================== 基金筛选函数 =====================
def screen_bond_funds():
    """获取并筛选债券基金前10名"""
    try:
        # 获取全市场债券基金数据
        df_all = pd.read_csv("data/fund_ranking_data.csv")
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

# ===================== 定投执行函数 =====================
def execute_investment(top_funds):
    """模拟定投操作并生成报告"""
    report = []
    today = datetime.now().strftime("%Y-%m-%d")
    total_investment = 0
    
    for _, fund in top_funds.iterrows():
        fund_code = fund['基金代码']
        fund_name = fund['基金简称']
        
        # 此处可接入券商API执行真实交易
        # 示例：your_broker.buy(fund_code, INVESTMENT_PER_FUND)
        
        report.append({
            '基金代码': fund_code,
            '基金名称': fund_name,
            '投资金额': INVESTMENT_PER_FUND,
            '费率': fund['手续费'],
            '操作': '定投成功'  # 实际中根据API返回结果修改
        })
        total_investment += INVESTMENT_PER_FUND
    
    # 生成报告摘要
    summary = (
        f"📅 定投日期: {today}\n"
        f"💰 总投资额: {total_investment}元\n"
        f"📊 定投基金数: {len(top_funds)}\n"
        f"🏆 最佳基金: {top_funds.iloc[0]['基金简称']}({top_funds.iloc[0]['基金代码']}) "
        f"评分:{top_funds.iloc[0]['综合评分']:.2f}"
    )
    return report, summary

# ===================== 邮件通知函数 =====================

# ===================== 定时任务 =====================
def scheduled_task():
    print(f"\n{'='*40}")
    print(f"开始执行定期任务 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 步骤1: 筛选基金
    top_funds = screen_bond_funds()
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
    
    # 如果data/fund_ranking_data.csv不存在，则获取数据
    if not os.path.exists("data/fund_ranking_data.csv"):
        get_data()
    
    # 立即执行一次
    scheduled_task()
    
    # 设置定时执行 (每月第一个交易日)
    # schedule.every().monday.at("09:30").do(scheduled_task)  # 实际中应使用交易日历
    
    print("定时任务已启动，每月第一个交易日09:30执行...")
    # while True:
    #     schedule.run_pending()
    #     time.sleep(60)