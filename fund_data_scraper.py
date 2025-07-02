#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基金数据爬取模块
使用Selenium从东方财富网爬取基金排行数据
"""

import pandas as pd
import numpy as np
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import os
import sys

max_pages = 160  # 最大爬取页数，避免无限循环
page_size = 50  # 每页数据量

def get_data(data_type):
    """使用Selenium模拟浏览器从东方财富网获取基金排行数据"""
    url = f"http://fund.eastmoney.com/data/fundranking.html#{data_type};c0;r;s1nzf;pn50;ddesc;qsd20240701;qed20250701;qdii;zq;gg;gzbd;gzfs;bbzt;sfbb"
    
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

            # 如果解析数据小于 page_size，则跳出循环
            if len(data_rows) < page_size:
                break
            
            # 尝试点击下一页按钮
            try:
                # 等待下一页按钮出现
                next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="pagebar"]/label[8]')))
                
                # 检查按钮是否可点击（不是最后一页）
                if 'disabled' in next_button.get_attribute('class') or 'current' in next_button.get_attribute('class'):
                    print("已到达最后一页")
                    break
                
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
            
            # 确保data目录存在
            os.makedirs('data', exist_ok=True)
            
            # 保存数据到CSV文件, 存入data目录
            # 根据基金类型生成文件名
            type_names = {
                'tzs': '指数型',
                'tgp': '股票型', 
                'thh': '混合型',
                'tzq': '债券型'
            }
            type_name = type_names.get(data_type, data_type)
            date_str = datetime.now().strftime("%Y%m%d")
            output_file = f"data/fund_ranking_{data_type}_{type_name}_{date_str}.csv"
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

def main():
    """主函数，用于独立运行数据爬取"""
    # 定义基金类型映射
    fund_types = {
        '1': ('tzs', '指数型'),
        '2': ('tgp', '股票型'),
        '3': ('thh', '混合型'),
        '4': ('tzq', '债券型')
    }
    
    print("基金数据爬取工具")
    print("=" * 40)
    print("请选择要爬取的基金类型（可多选，用逗号分隔）：")
    print("1. 指数型 (tzs)")
    print("2. 股票型 (tgp)")
    print("3. 混合型 (thh)")
    print("4. 债券型 (tzq)")
    print("5. 全部类型")
    print("0. 退出")
    print("-" * 40)
    
    # 获取用户输入
    if len(sys.argv) > 1:
        # 从命令行参数获取选择
        choice = sys.argv[1]
    else:
        # 交互式输入
        choice = input("请输入选择（如：1,2,3 或 5）：").strip()
    
    if choice == '0':
        print("退出程序")
        return
    
    selected_types = []
    
    if choice == '5':
        # 选择全部类型
        selected_types = list(fund_types.values())
        print("已选择全部基金类型")
    else:
        # 解析用户选择
        choices = choice.split(',')
        for c in choices:
            c = c.strip()
            if c in fund_types:
                selected_types.append(fund_types[c])
            else:
                print(f"无效选择: {c}")
    
    if not selected_types:
        print("未选择任何基金类型，退出程序")
        return
    
    print(f"\n将爬取以下基金类型：")
    for i, (code, name) in enumerate(selected_types, 1):
        print(f"{i}. {name} ({code})")
    
    # 确认是否继续
    if len(sys.argv) <= 2:  # 非命令行模式才需要确认
        confirm = input("\n确认开始爬取？(y/n): ").strip().lower()
        if confirm not in ['y', 'yes', '是']:
            print("取消爬取")
            return
    
    # 开始爬取
    total_records = 0
    for i, (data_type, type_name) in enumerate(selected_types, 1):
        print(f"\n{'='*50}")
        print(f"正在爬取第 {i}/{len(selected_types)} 种类型：{type_name}")
        print(f"{'='*50}")
        
        df = get_data(data_type)
        if df is not None:
            print(f"{type_name}数据爬取成功，共获取 {len(df)} 条记录")
            total_records += len(df)
        else:
            print(f"{type_name}数据爬取失败")
    
    print(f"\n{'='*50}")
    print(f"爬取完成！总共获取 {total_records} 条记录")
    print(f"数据文件保存在 data/ 目录下")
    print(f"{'='*50}")

if __name__ == "__main__":
    main() 