# -*- encoding: utf-8 -*-
'''
@File    :   1loume_download.py
@Time    :   2025/07/08 17:01:57
@Author  :   leanfly 
@Version :   1.0
@Contact :   ningmuyu@live.com
'''

# here put the import lib
from curl_cffi import requests
from bs4 import BeautifulSoup
import re
import qbittorrentapi
from dotenv import load_dotenv
import os
from fastapi import FastAPI
import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler
from pathlib import Path


cur_file_abspath = os.path.abspath(__file__)

# 加载环境变量
load_dotenv()


# movie 栏目链接
movie_api = "https://www.1lou.me/forum-3-1.htm?tagids=959___"


def upload_download(torrent_path):
    ## 配置qbit ##
    qbit_conn = dict(
        host= os.getenv("QBITHOST"),
        port= os.getenv("QBITPORT"),
        username= os.getenv("QBITUSER"),
        password= os.getenv("QBITPASS"),
    )

    qbt_client = qbittorrentapi.Client(**qbit_conn)
    save_path = os.getenv("SAVEPATH")
    try:
        qbt_client.auth_log_in(**qbit_conn)
        qbt_client.torrents_add(torrent_files=torrent_path, save_path=save_path, category="")
    except Exception as e:
        print("任务添加失败：", str(e))
        pass

def extract_core_title(title):
    """提取影片核心名称（去除版本、格式等后缀）"""
    # 分割标题中的特殊标记（如[高码版]、[杜比视界]等）
    
    # 先移除所有方括号及内部内容（如[高码版]、[国语配音]等）
    clean_title = re.sub(r'\[.*?\]', '', title)
    # 再移除年份及之后的格式信息（如2025.2160p.WEB-DL...）
    # 匹配年份（4位数字）及后续内容
    core_title = re.split(r'\d{4}\.', clean_title, 1)[0].strip()
    # 处理可能的英文名称干扰（保留中文核心名称）
    # 提取中文部分作为核心名称（如果有）
    chinese_part = re.findall(r'[\u4e00-\u9fa5]+', core_title)
    if chinese_part:
        return ''.join(chinese_part)
    # 如果无中文，使用英文核心名称（去除特殊符号）
    return re.sub(r'[^\w\s]', '', core_title).strip()


def main_hanle():
    # 请求
    resp = requests.get(movie_api, impersonate="chrome131")
    # BeautifulSoup 处理
    soup = BeautifulSoup(resp.text, "html.parser")
    # 获取全部的子项
    title_list = soup.find_all(name="a", attrs={"class": "text-title"})
    link_title_list = [(i.get("href"), i.text) for i in title_list]

    # 去重逻辑：保留每个影片的第一个出现的版本
    seen = set()
    unique_movies = []
    for item in link_title_list:
        url, title = item
        core = extract_core_title(title)
        if core not in seen:
            seen.add(core)
            unique_movies.append(item)

    # 遍历请求，获取下载链接
    for movie in unique_movies:
        # 先检查一下是否已添加过同名内容
        with open("add.txt", "r", encoding="utf-8") as fadd:
            added_list = fadd.readlines()
            if movie[1] in added_list:
                continue

        resp1 = requests.get(f"https://www.1lou.me/{movie[0]}", impersonate="chrome131")

        download_id = re.findall(r'li aid="(\d+)">', resp1.text)
        if not download_id:
            continue

        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36 Edg/137.0.0.0",
            "Cookie": os.getenv("COOKIE"),
    
            # "bbs_sid=f3g5fbe0p2kcu6h34rpdcdggov; cf_clearance=5.v4sY8oTG25XnpYaqmyqTB54dy.zTXKYZ6RJtmpdNw-1751597789-1.2.1.1-30wv6KjiAd4V8lQUi7RfevffKqqFCHxu5QffAKix3fdHXD2_L_fPcB49PCAU5m5msYrUb2nw_cbNd4_6zEBIltcomfkRLmBvLX948VPuEToLs5__8LIIvhSvZPGbWe8_mQXNzK8L6sy7yA8JKgPZs09ynnW6ujjlRSbA3V0J.6TiJECn3.t25AomahYskFR72AgEO_YnE8Kx2jiyM2zOMrVXETnfz57ggMmLvRJcNTo"
        }

        download_link = f"https://www.1lou.me/attach-download-{download_id}.htm"

        respd = requests.get(download_link, impersonate="chrome131", headers=headers, allow_redirects=True)

        if respd.status_code != 200:
            continue
        save_path = f"{download_id}.torrent"
        with open(save_path, 'wb') as f:
            f.write(respd.content)
        print(f"torrent文件已成功下载至：{save_path}")

        # 上传下载
        upload_download(save_path)

        # 名字写入本地
        with open("add.txt", "a+", encoding="utf-8") as f:
            f.writelines(f"{movie[1]}\n")


# 创建定时任务
scheduler = BackgroundScheduler()
scheduler.add_job(
    func=main_hanle,
    trigger='interval',
    hours=12
)



def lifespan(app: FastAPI):
    scheduler.start()
    print("********** 1loume 任务已启动 **********")
    print(scheduler.get_jobs()[0])
    yield

    scheduler.shutdown()
    print("********** 1loume 任务已停止 **********")


app = FastAPI(title="1loume 下载")

@app.get("/1loume")
async def root():
    return {"message": "1loume 任务"}


if __name__ == "__main__":
    app_name = Path(cur_file_abspath).stem
    uvicorn.run(app=f"{app_name}:app", host="0.0.0.0", port=13312)
