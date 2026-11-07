import time

from GetWebDeepSeekAnswer import *


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(
        headless=False,
        channel = "msedge"
    )

    # 添加cookie
    context = browser.new_context()

    page = context.new_page()
    page.goto("https://chat.deepseek.com/a/chat/s/cb1340af-0501-4fcd-ace4-1ad23022f0e6")
    #-----------------------


    loc = page.locator("textarea")
    loc.first.wait_for(state="visible")
    Num:int = 0
    while True:
        systemPrompt:str = "请你模拟LLM api服务。我将发给你一段api请求调用,你回复我一段json格式，符合openai格式的api应答。请启用严格的格式化输出模式，我只要json，不要给我多余的东西，请返回json代码块，不要返回给我消息"
        prompt:str = input("prompt:")
        
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


with sync_playwright() as playwright:
    run(playwright)


