# 本模块负责将模型的Web问答包装成API调用
# 检查是否符合openai格式
import json
from openai.types.chat import ChatCompletion 
from PublicVar import page
import logging


def IsModelReturnJson()->bool:
    # 模型返回的是气泡还是Json代码块？
    # 判断标准就是DS回复里有没有<pre>
    # 文字是<span>,代码块是<pre>
    # 当然代码块里的代码不一定是json,这个在CheckLLMResponse会校验
    # 因此本函数仅校验是否返回代码块，当且仅当代码块数量为1 return True
    TagDSResponse = page.locator(".ds-markdown.ds-assistant-message-main-content").last
    print(f"TagDSResponse:{len(TagDSResponse.all())}")
    TagPre = TagDSResponse.locator("pre")
    if TagPre.count() == 1 :
        return True
    else : 
        return False

    


def GetLLMResponse()-> None|str:
# 爬虫抓取模型回复
# 系统提示词要求模型模拟api服务，返回json代码块,openai格式
# 系统提示词如下：
# systemPrompt:str = "
#           请你模拟LLM API服务。我将发给你一段OpenAI格式的API请求，请以Json代码块的形式回复我API响应，要求如下：
#           1.仅包含json代码块。
#           2.符合OpenAI规范API应答。
#           3.请启用严格的格式化输出模式。
#           4.我将把你的回复一字不漏地交给OpenAI pydantic模型(ChatCompletion.model_validate)做校验，请确保能通过。
#           5.我会把你的响应转给agent,请确保agent能正常工作。
#           模型API请求如下:" 
#   "
# 预期模型的回复将只包含一个json代码块
# 当然这是指提示词层面的软约束，因此需要进行校验
#   1.校验模型是否返回Json代码块
#   2.校验该Json代码块是否合法，不报错，符合openai格式
# 本函数仅保证(1)，至于(2),由另一个函数CheckLLMResponse校验

# 输入：page是当前目标页面 是Playwright Page类的实例
#       如何判定模型是否返回代码块？IsModelReturnJson()
# 输出：1.模型返回代码块：
#           以str形式返回这个Json代码
#       2.模型未返回代码块：
#           return None

    global page
    # step1 : 检查模型是否按要求返回1个代码块
    if not IsModelReturnJson():
        print("模型未返回或返回多个Jsno块")
        return None
    print("模型返回Jsno块")
    TagDSResponse = page.locator(".ds-markdown.ds-assistant-message-main-content").last
    TagPre = TagDSResponse.locator("pre").last
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

def CheckLLMResponse(Response:None|str)->str|None:
    print(f"模型返回：{Response}")
# 接收GetLLMResponse的返回值，即Response
# 如果Response合法——非None,通过openai格式校验 return None
# 否则 return 字符串,该字符串将拼接进Prompt，用来修正模型输出
    if Response == None :
        logging.warning(
            "CheckLLMResponse : Model have not response\n " \
            "please add WaitTime or check your Internet"
            )
        # 模型输出太慢,WaitTime设置太小了，无需修正提示词
        return ""
    # 1.Json是否合法？不合法无法转成PyJson
    # 2.用openai官方的pydantic模型校验该Json
    # 不合法二者都会抛错，进入except
    try:
        # TODO:为提高成功率，可以加一个先清理json的逻辑
        # 可以让模型输出，再人为拼接成openai格式，而不是一次性让模型输出全部
        PyJson = json.loads(Response)
        ChatCompletion.model_validate(PyJson)
    except json.JSONDecodeError:
        logging.warning("CheckLLMResponse : The output of model is not valid Json")
        return "不是合法Json,请重新输出"
    except Exception:
            logging.warning("CheckLLMResponse : The output of model is not valid OpenAI response")
            return "未通过OpenAI响应格式校验，请重新输出"
    return None


def MakePrompt(request:str)->str:
    # request是claudecode发出的请求，其经过的链路如下：
    # 1. claudecode发出 
    # 2. cc switch转换openai格式并转发到本项目后端
    # 3. 后端接收后交由本函数做进一步提示词处理
    # 本函数从提示词层面约束模型输出，确保模型正确返回预期格式
    SystemPrompt:str = "请你模拟LLM API服务。我将发给你一段OpenAI格式的API请求，请以Json代码块的形式回复我API响应，要求如下：\
1.仅包含json代码块。\
2.符合OpenAI规范API应答。\
3.请启用严格的格式化输出模式。\
4.我将把你的回复一字不漏地交给OpenAI pydantic模型(ChatCompletion.model_validate)做校验，请确保能通过。\
5.我会把你的响应转给agent,请确保agent能正常工作。\
模型API请求如下:" 
    return  SystemPrompt+request


def __predictate(request)->bool:
    # page.wait_for_event()的predictate参数
    # 如果该请求是completion请求，返回True
    if "/api/v0/chat/completion" in request.url:
        return True
    else :
        return False

def SendToWebLLM(Prompt:str)->bool:
# 用于给模型发送消息，Prompt会直接原样写入输入框并按'Enter'键发给模型
# 因此Prompt应为加工后的请求，请确保其被 MakePrompt 加工过
# 返回bool表示模型是否成功响应
# 本函数保证消息发出且模型已经回复消息,至于返回了什么,交给CheckLLMResponse检验
    global page
    try:
        loc = page.locator("textarea")
        loc.fill(Prompt)                    
        loc.press("Enter")
        # 等待completion请求响应体
        page.wait_for_event("requestfinished",__predictate)
        print("deepseek已回复")
        return True                      
    except Exception:
        logging.exception("SendToWebLLM : Sending message or waiting for response failed!")
        return False
    


# 本模块唯一对外暴露接口
def APIResponse(  
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
        # step1 保证消息发出并且模型已经回复
        if not SendToWebLLM(Prompt):
            TryTimes -= 1
            continue
        # step2 保证模型回复的消息符合预期
        JsonResp:str = GetLLMResponse()
        IsValid:None|str = CheckLLMResponse(JsonResp)
        # IsValid为None说明模型返回的API响应通过
        # 否则，根据错误类型修正提示词。让模型重新生成
        if IsValid==None :
            return JsonResp
        else :   
            TryTimes = TryTimes - 1
            # 如果模型输出不符合预期，这里修改一下提示词
            Prompt = IsValid + MakePrompt(RowRequest)
    raise Exception(
        'The Output of LLM is always invalid, \
        please add "TryTime" or change a better model'
        )

    


