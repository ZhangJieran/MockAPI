# 本模块负责将模型的Web问答包装成API调用


## 爬虫
import re
from playwright.sync_api import Playwright, sync_playwright, expect, Page 
# 检查是否符合openai格式
import json
from openai.types.chat import ChatCompletion

import logging
import time
from collections.abc import Callable
from urllib.parse import urlsplit


def WaitForDeepSeekResponse(
    page: Page, send_message: Callable[[], None], timeout: float = 300_000
) -> None:
    """先监听再调用 send_message，阻塞到本次 complete/completion 响应正文接收完毕。

    timeout 单位为毫秒，必须大于 0；网络失败、HTTP 错误或超时会抛出异常。
    必须把发送操作传入本函数，不能在发送后才调用，以免漏掉请求事件。
    """
    if timeout <= 0:
        raise ValueError("timeout must be greater than 0")

    def is_completion(request):
        url = urlsplit(request.url)
        return (
            request.method == "POST"
            and url.hostname == "chat.deepseek.com"
            and url.path.rstrip("/").rsplit("/", 1)[-1] in ("complete", "completion")
        )

    finished = set()
    failed = {}

    def on_finished(request):
        finished.add(request)

    def on_failed(request):
        failed[request] = request.failure

    deadline = time.monotonic() + timeout / 1000
    page.on("requestfinished", on_finished)
    page.on("requestfailed", on_failed)
    try:
        # response 事件只代表响应头已到达；requestfinished 才代表流已读完。
        with page.expect_request(is_completion, timeout=timeout) as request_info:
            send_message()
        request = request_info.value
        while request not in finished:
            if request in failed:
                raise RuntimeError(f"DeepSeek request failed: {failed[request]}")
            remaining = (deadline - time.monotonic()) * 1000
            if remaining <= 0:
                raise TimeoutError(f"DeepSeek stream did not finish within {timeout} ms")
            # Playwright 的等待会分发网络事件，不能用 time.sleep() 替代。
            page.wait_for_timeout(min(100, remaining))

        response = request.response()
        if response is None or not response.ok:
            status = response.status if response is not None else "no response"
            raise RuntimeError(f"DeepSeek completion HTTP error: {status}")
    finally:
        page.remove_listener("requestfinished", on_finished)
        page.remove_listener("requestfailed", on_failed)


def GetCurrentTagPreNum(page:Page)->int:
# 获得当前会话的<pre>标签数量
# 设计原因是希望在给模型发消息前，先获取<pre>数量
# 再把这个数量传给GetLLMResponse的BeforeTagPreNum
# 用于判断模型是否按照预期返回Json代码块
# GetCurrentTagPreNum() ->给模型发消息()->GetLLMResponse()
    TagPre = page.locator("pre")
    return len( TagPre.all() )


def GetLLMResponse(page:Page,BeforeTagPreNum:int)-> None|str:
# 爬虫抓取模型回复
# 系统提示词要求模型模拟api服务，返回json代码块,openai格式
# 系统提示词如下：
# systemPrompt:str = "
#           请你模拟LLM api服务。我将发给你一段api请求调用,
#           你回复我一段json格式，符合openai格式的api应答。
#           请启用严格的格式化输出模式，我只要json，不要给我多余的东西，
#           请返回json代码块，不要返回给我消息
#   "
# 预期模型的回复将只包含一个json代码块
# 当然这是指提示词层面的软约束，因此需要进行校验
#   1.校验模型是否返回Json代码块
#   2.校验该Json代码块是否合法，不报错，符合openai格式
# 本函数仅保证(1)，至于(2),由另一个函数CheckLLMResponse校验

# 输入：page是当前目标页面 是Playwright Page类的实例
#       如何判定模型是否返回Json代码块？根据BeforeTagPreNum参数
#       其语义是当前会话，截止上一轮对话(不算本轮对话产生的<pre>)一共有多少<pre>
#       如果当前页面的TagPreNum和BeforeTagNum一样则模型未按要求返回Json代码块
# 输出：1.模型返回Json代码块：
#           以str形式返回这个Json代码
#       2.模型未返回Json代码块：
#           return None

    # step1 : 检查模型是否按要求返回Json代码块
    #判断标准：<pre>标签数目是否更新
    TagPre = page.locator("pre")
    CurTagPreNum:int = len(TagPre.all())
    if CurTagPreNum == BeforeTagPreNum:
        return None
    
    TagPre = TagPre.last
    # 抓取外层span标签   外层span标签是json代码的一行
    OuterTagSpan = TagPre.locator("span")
    OuterTagSpanList = OuterTagSpan.all()
    JsonCode:str = ""
    for SingleOuterTagSpan in OuterTagSpanList :
        InnerTagSpan = SingleOuterTagSpan.locator("span")
        InnerTagSpanList = InnerTagSpan.all()
        # 拼接出一行json
        OneLineCode:str = ""
        for SingleInnerTagSpan in InnerTagSpanList :
            OneLineCode += SingleInnerTagSpan.text_content() 
        # 拼接出Json代码
        JsonCode += OneLineCode
    return JsonCode

def CheckLLMResponse(Response:None|str)->bool:
# 接收GetLLMResponse的返回值，即Response
# 如果Response合法——非None,通过openai格式校验 return True
# 否则 return False    
    if Response == None :
        logging.warning("CheckLLMResponse : The output of model is invalid")
        return False
    # 1.Json是否合法？不合法无法转成PyJson
    # 2.用openai官方的pydantic模型校验该Json
    # 不合法二者都会抛错，进入except
    try:
        PyJson = json.loads(Response)
        ChatCompletion.model_validate(PyJson)
    except:
        logging.warning("CheckLLMResponse : The output of model is invalid")
        return False
    return True


def MakePrompt(request:str)->str:
    # request是claudecode发出的请求，其经过的链路如下：
    # 1. claudecode发出 
    # 2. cc switch转换openai格式并转发到本项目后端
    # 3. 后端接收后交由本函数做进一步提示词处理
    # 本函数从提示词层面约束模型输出，确保模型正确返回预期格式
    SystemPrompt:str = "    \
        请你模拟LLM API服务。\
        我将发给你一段OpenAI格式的API请求,你回复我API响应\
        要求如下：\
        1.json格式\
        2.符合OpenAI规范API应答。\
        3.请启用严格的格式化输出模式，只要json，不要输出任何无关的字符\
        4.请返回json代码块,且仅返回一个代码块，除此之外无任何多余的东西\
        5.我将把你的回复一字不漏地交给openai pydantic模型(ChatCompletion.model_validate)做校验，请确保能通过\
        模型api请求如下:\
    "
    logging.info("MakePrompt : Change request to Prompt successfully")
    return  SystemPrompt+request


def SendToWebLLM(page:Page,Prompt:str)->bool:
# 用于给模型发送消息，Prompt会直接原样写入输入框发给模型
# 因此Prompt应为加工后的请求，请确保其被 MakePrompt 加工过
# 返回bool表示模型是否成功响应
    try:
        loc = page.locator("textarea")
        loc.fill(Prompt)                    
        WaitForDeepSeekResponse(page, lambda: loc.press("Enter"))
        logging.info("SendToWebLLM : DeepSeek stream has finished")
        return True                      
    except Exception:
        logging.exception("SendToWebLLM : Sending message or waiting for response failed!")
        return False
    


# 本模块唯一对外暴露接口
def APIResponse(
        page    :Page,   
        RowRequest :str,    
        TryTimes:int = 1 
    ) -> str:
# 模拟API调用
# Request：后端接收到的请求
# 期望模型结构化输出，但是提示词层面的软约束，因此很有可能输出不符合预期
# 如果不符合预期，可以重试 
# TryTime 耗尽输出仍然不符合预期，报错
    if TryTimes<=0 :
        raise ValueError("TryTime<=0! You have to try one time at least")
    Prompt:str = MakePrompt(RowRequest)
    while TryTimes:
        BeforeTagPreNum = GetCurrentTagPreNum(page)
        SendToWebLLM(page,Prompt)
        JsonResp:str = GetLLMResponse(page,BeforeTagPreNum)
        IsValid:bool = CheckLLMResponse(JsonResp)
        if IsValid :
            return JsonResp
        else :   
            TryTimes = TryTimes - 1
            # 如果模型输出不符合预期，这里修改一下提示词
            Prompt = "错误！请严格按照我的要求输出！"+MakePrompt(RowRequest)
    raise Exception(
        'The Output of LLM is always invalid, \
        please add "TryTime" or change a better model'
        )

    


