import time
from GetWebDeepSeekAnswer import *



def InitChromium(playwright:Playwright)->Page:
# 用于初始化浏览器
    browser = playwright.chromium.launch(headless=False,channel = "msedge")
    context = browser.new_context()
    page = context.new_page()
    return page






def run(playwright: Playwright) -> None:
    

    page = InitChromium(playwright)

    page.goto("https://chat.deepseek.com/a/chat/s/cb1340af-0501-4fcd-ace4-1ad23022f0e6")
    #-----------------------


    loc = page.locator("textarea")
    loc.first.wait_for(state="visible")
    Num:int = 0
    while True:
        
        loc.fill(systemPrompt+prompt)         # 1. 填入内容
        loc.press("Enter")                    # 2. 按回车发送

        # 抓回复
        time.sleep(3)
        resp = GetLLMResponse(page,Num)
        isValid = CheckLLMResponse(resp)
        if isValid==True:
            print(resp)
            Num = Num + 1
        else :
            print("is not valid")
        
    # ---------------------
    context.close()
    browser.close()


playwright = sync_playwright().start()
InitChromium(playwright)


run(playwright)
playwright.stop()      


