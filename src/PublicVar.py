from queue import Queue  
from playwright.sync_api import Playwright, sync_playwright, Page 
# 加载配置文件 ../config.json
import json
from pathlib import Path



def InitChromium(playwright:Playwright)->Page:
# 用于初始化浏览器
    browser = playwright.chromium.launch(headless=False,channel = "msedge")
    context = browser.new_context()
    page = context.new_page()
    return page


CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)  


RequestQue  = Queue(maxsize=1)
ResponseQue = Queue(maxsize=1) 

playwright = sync_playwright().start()
page = InitChromium(playwright)
page.goto(config["BaseURL"])
