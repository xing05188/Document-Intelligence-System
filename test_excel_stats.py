"""
测试脚本：验证 Excel 统计和日志功能
"""
import sys
sys.path.insert(0, 'src')

from utils.document_reader import read_document, ExcelReader, get_excel_statistics

# 测试文件路径（请替换为你的Excel文件路径）
test_file = "test_data.xlsx"  # 如果没有，会创建一个示例

import os
if not os.path.exists(test_file):
    print(f"测试文件 '{test_file}' 不存在，正在创建一个示例...")
    
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "测试数据"
    
    # 写入表头
    headers = ["日期", "销售额", "成本", "利润", "产品类别"]
    ws.append(headers)
    
    # 写入100行测试数据
    import random
    categories = ["电子产品", "服装", "食品", "家居", "图书"]
    
    for i in range(100):
        date = f"2024-{(i % 12) + 1:02d}"
        sales = random.randint(1000, 10000)
        cost = int(sales * random.uniform(0.5, 0.8))
        profit = sales - cost
        category = random.choice(categories)
        ws.append([date, sales, cost, profit, category])
    
    wb.save(test_file)
    print(f"示例文件已创建: {test_file}")

print("\n" + "="*60)
print("测试 read_document 函数（含统计）:")
print("="*60)
result = read_document(test_file, max_rows=20, compute_stats=True)
print(result)

print("\n" + "="*60)
print("测试 get_excel_statistics 函数（仅统计）:")
print("="*60)
stats = get_excel_statistics(test_file, max_rows=100)
print(stats)
