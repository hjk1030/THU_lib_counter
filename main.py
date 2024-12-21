import re
import collections
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime, timedelta
import json
import requests
import platform
from tqdm import tqdm

seat_pattern = r'((([A-Z]{0,2}F)[0-9][A-Z]?)\-?[0-9]{3})</td><td>(((202[1-4])-[0-1][0-9])-[0-3][0-9])([0-2][0-9]:[0-5][0-9]:[0-5][0-9])'
lib_mapping = {
    "LF": "法图",
    "WF": "西馆",
    "NF": "北馆",
    "F": "文图",
    "AF": "美图",
    "WNF": "北/西馆连廊"
}

def print_dict_by_key_order(d):
    for k in sorted(d.keys()):
        print(f'"{k}": {d[k]}',end=', ')
    print('')

def plot_pie_chart(d, splot, title):
    cnt = 0
    others_cnt = 0
    for k, v in d.items():
        cnt += v
    keys = []
    values = []
    for k, v in d.items():
        if v * 50 >= cnt:
            keys.append(k)
            values.append(v)
        else:
            others_cnt += v
    vk = sorted(zip(values, keys))
    values = [v[0] for v in vk]
    keys = [v[1] for v in vk]
    keys.append('其他')
    values.append(others_cnt)
    splot.pie(values, labels=keys, autopct='%1.1f%%', startangle=140)
    splot.set_title(title)

def plot_bar_graph(d, splot, title):
    labels = list(d.keys())  # The keys of the Counter (e.g., 'A', 'B', 'C', 'D')
    values = list(d.values())  # The counts/values of the Counter (e.g., 10, 15, 7, 12)

    # Create the bar plot
    splot.bar(labels, values)

    # Add labels and title
    splot.set_xlabel('分类')
    splot.set_ylabel('数量')
    splot.set_title(title)

def get_half_year(date):
    if int(date[5:7]) <= 6:
        return f'{date[:4]}-H1'
    else:
        return f'{date[:4]}-H2'

def longest_streak(date_strings):
    # Convert the date strings to datetime.date objects
    dates = [datetime.strptime(date_string, '%Y-%m-%d').date() for date_string in date_strings]
    
    # Remove duplicates and sort the dates
    dates = sorted(set(dates))
    
    # Initialize variables to track the longest streak and the current streak
    longest_streak = 0
    current_streak = 1  # Start with a streak of 1 (a single date counts as a streak)
    longest_end = None
    streaks = []

    # Iterate through the sorted list of dates
    for i in range(1, len(dates)):
        if dates[i] == dates[i - 1] + timedelta(days=1):
            # Consecutive date found, increment the streak
            current_streak += 1
        else:
            # Non-consecutive date, update the longest streak if needed
            if current_streak >= 7:
                streaks.append((dates[i - 1], current_streak))
            if longest_streak < current_streak:
                longest_end = dates[i - 1]
            longest_streak = max(longest_streak, current_streak)
            current_streak = 1  # Reset current streak
    
    # Final update for the streak at the end of the list
    if current_streak >= 7:
        streaks.append((dates[-1], current_streak))
    if longest_streak < current_streak:
        longest_end = dates[-1]
    longest_streak = max(longest_streak, current_streak)
    
    return longest_streak, streaks, longest_end

def get_lib_record(account, use_cache = True):
    try:
        if not use_cache:
            raise KeyError("Not using cache") # Maybe there are better solution?
        with open("records.json","r") as f:
            records = json.load(f)
            return records
    except Exception as e:
        url = f"https://seat.lib.tsinghua.edu.cn/user/index/book/status/4/p/1"
        cookie = {
            "userid": account['id'],
            "access_token": account['token']
        }
        response = requests.get(
            url = url,
            cookies = cookie
        )
        if response.status_code != 200:
            print(f"Error when fetching lib record, code {response.status_code}")
            exit(1)
        raw_content = response.text.replace(' ','').replace('\n', '').replace('\t','').replace('\r','')
        records = re.findall(seat_pattern, raw_content)
        page_count = re.search('class="end"href="/user/index/book/status/4/p/([0-9]+)">', raw_content)
        if page_count is None:
            print("读取错误，请尝试刷新token。")
            # print(f"Content :{raw_content}")
            exit(2)
        page_count = int(page_count.group(1))
        print(f"Total pages: {page_count}")
        for i in tqdm(range(2, page_count + 1)):
            # print(f"Fetching page {i}")
            url = f"https://seat.lib.tsinghua.edu.cn/user/index/book/status/4/p/{i}"
            response = requests.get(
                url = url,
                cookies = cookie
            )
            if response.status_code != 200:
                print(f"Error when fetching lib record, code {response.status_code}")
                exit(1)
            raw_content = response.text.replace(' ','').replace('\n', '').replace('\t','').replace('\r','')
            records.extend(re.findall(seat_pattern, raw_content))
        json.dump(records,open("records.json","w"))
        return records

def get_id_and_token():
    try:
        with open("config.json", "r", encoding='utf-8') as f:
            account = json.load(f)
            return account
    except Exception as e:
        print("账户信息读取失败，请重新输入")
        id = input("请输入学号: ")
        token = input("请输入token: ")
        account = {"id": id, "token": token}
        with open("config.json", "w", encoding='utf-8') as f:
            json.dump(account, f, indent=4)
        return account

if __name__ == '__main__':
    account = get_id_and_token()
    fetch_again = input("是否重新从图书馆系统获取数据？[y/n]").lower()
    if fetch_again != 'y' and fetch_again != 'n':
        print("请输入合法选项")
        exit(3)
    records = get_lib_record(account, fetch_again == 'n')

    # Annotate here to check the overall statistics
    # records = [m for m in records if m[5] == '2024']

    if platform.system() == "Darwin":
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']
    elif platform.system() == "Linux":
        plt.rcParams['font.family'] = ['Droid Sans Fallback', 'DejaVu Sans']
    else:
        plt.rcParams['font.sans-serif'] = ['SimHei']
    figs, ((p1, p2), (p3, p4)) = plt.subplots(2, 2, figsize=(30, 30))
    
    print(f"Total Count: {len(records)}")
    seats = [m[0] for m in records]
    seat_counting = collections.Counter(seats)
    print("------Seats by Count------")
    print(seat_counting)
    areas = [m[1] for m in records]
    area_counting = collections.Counter(areas)
    print("------Areas by Count------")
    print(area_counting)
    print("------Areas by Order------")
    print_dict_by_key_order(area_counting)
    plot_pie_chart(dict(area_counting), p1, '区域')
    # libs = [m[2] for m in records]
    libs = [lib_mapping[m[2]] for m in records]
    libs_counting = collections.Counter(libs)
    print("------Libraries by Count------")
    print(libs_counting)
    print("------Libraries by Order------")
    print_dict_by_key_order(libs_counting)
    # plot_pie_chart(dict(libs_counting), p2, '图书馆')
    plot_bar_graph(libs_counting, p2, "图书馆")
    # years = [m[5] for m in records]
    # years_counting = collections.Counter(years)
    # print("------Years by Order------")
    # print_dict_by_key_order(years_counting)
    months = [m[4] for m in records]
    months_counting = collections.Counter(months)
    print("------Months by Count------")
    print(months_counting)
    print("------Months by Order------")
    print_dict_by_key_order(months_counting)
    times = [m[6][:2] for m in records]
    times_counting = collections.Counter(times)
    print("------Times by Count------")
    print(times_counting)
    unique_dates = set(m[3] for m in records)
    print("------Longest Streak------")
    print(longest_streak(set(m[3] for m in records)))
    month_count = collections.defaultdict(int)
    for date in unique_dates:
        year_month = date[:7]
        month_count[year_month] += 1
    print("------Dates in Month------")
    print_dict_by_key_order(month_count)
    for year in range(2022, 2025):
    # for year in range(2024, 2025):
        for month in ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']:
            if not f'{year}-{month}' in month_count:
                month_count[f'{year}-{month}'] = 0
    sorted_months = sorted(month_count.items())
    months, counts = zip(*sorted_months)
    p3.plot(months, counts, marker='o', linestyle='-', color='b')
    # p3.set_xlabel('月份', fontsize=12)
    p3.set_xlabel('半年', fontsize=12)
    p3.set_ylabel('天数', fontsize=12)
    # p3.set_title('每月图书馆签到天数', fontsize=14)
    p3.tick_params(axis='x', rotation=45)  # Rotate x-axis labels for better readability
    p3.grid(axis='y', linestyle='--', alpha=0.7)
    p3.legend()
    half_year_counts = collections.defaultdict(collections.Counter)
    for m in records:
        # Annotate here to check by half_year statistics
        half_year_counts[get_half_year(m[3])][lib_mapping[m[2]]] += 1
        # half_year_counts[m[3][5:7]][lib_mapping[m[2]]] += 1
    
    df = pd.DataFrame(half_year_counts).fillna(0).astype(int)
    df = df.sort_index(axis=1)
    
    df.T.plot(kind="bar", ax=p4, width=0.7)
    p4.set_title('每月图书馆分布')
    p4.set_xlabel("月份")
    p4.set_ylabel("频率")
    p4.tick_params(axis='x', rotation=45)
    
    # plt.tight_layout()
    plt.show()
