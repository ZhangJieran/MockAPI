from Serve import *
from GetWebDeepSeekAnswer import *

def InitChromium(playwright:Playwright)->Page:
# 用于初始化浏览器
    browser = playwright.chromium.launch(headless=False,channel = "msedge")
    context = browser.new_context()
    page = context.new_page()
    return page





playwright = sync_playwright().start()
page = InitChromium(playwright)
uvicorn.run(LocalServer, host="127.0.0.1", port=1000)
playwright.stop()


