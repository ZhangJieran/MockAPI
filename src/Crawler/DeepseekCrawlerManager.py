import json
import time
from openai.types.chat import ChatCompletion
from ..Public import logging
from .CrawlerManager import *
from .utils import MakePrompt


# deepseek没有新增新的config配置，直接继承基类的
class DeepseekCrawlerConfig(CrawlerConfig):
    pass
class DeepseekCrawlerBuilder(CrawlerBuilder):
    pass


class DeepseekCrawlerManager(CrawlerManager):
    def __init__(self,config:CrawlerConfig):
        super().__init__(config)
        self.ManagerName = "DeepSeek"

    def __create_new_chat_session(self)->None:
    # DeepSeek 网页版可以ctrl+j开启新会话
        self.page.keyboard.press("Control+j")
        logging.info(f"{self.ManagerName}CrawlerManager : Create New Chat Session")

    def _DealOver(self):
        self.__create_new_chat_session()
        # 如果连续请求太多了，这里sleep 10s
        if self.CurContinuousChat>self.MaxContinuousChat:
            time.sleep(self.RestTime)
    
    def __predictate(self,request)->bool:
        # page.wait_for_event()的predictate参数
        # 如果该请求是completion请求，返回True
        if "/api/v0/chat/completion" in request.url:
            return True
        else :
            return False

    def _Send(self,Request)->int:
        time.sleep(3)
        # 用于给模型发送消息，Prompt会直接原样写入输入框并按'Enter'键发给模型
        # 因此Prompt应为加工后的请求，请确保其被 MakePrompt 加工过
        Prompt:str = MakePrompt(Request)
        try:
            loc = self.page.locator("textarea")
            loc.fill(Prompt)                    
            loc.press("Enter")
            # 等待completion请求响应体
            self.page.wait_for_event("requestfinished", predicate=self.__predictate)
            logging.info(f"{self.ManagerName}CrawlerManager : Have Sent to Model")
            return len(Prompt)                    
        except Exception as e:
            print(e)
            logging.warning(f"{self.ManagerName}CrawlerManager : Sending Prompt to Model Failed!")
            return 0

    def _GetResponse(self)->str|None:
        # 爬虫抓取模型回复
        # 系统提示词要求模型模拟api服务，返回json代码块,openai格式
        # 系统提示词大致如下：
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

        # step1 : 检查模型是否按要求返回1个代码块
        def __IsModelReturnJson()->bool:
            # 模型返回的是气泡还是Json代码块？
            # 判断标准就是DS回复里有没有<pre>
            # 文字是<span>,代码块是<pre>
            # 当然代码块里的代码不一定是json,这个在CheckLLMResponse会校验
            # 因此本函数仅校验是否返回代码块，当且仅当代码块数量为1 return True
            TagDSResponse = self.page.locator(".ds-markdown.ds-assistant-message-main-content").last
            TagPre = TagDSResponse.locator("pre")
            if TagPre.count() == 1 :
                return True
            else : 
                return False

        if not __IsModelReturnJson():
            logging.warning(f"{self.ManagerName}CrawlerManager : Model Output Invalid Num of Json Block")
            return None
        logging.info(f"{self.ManagerName}CrawlerManager : Model Output Json Block")
        TagDSResponse = self.page.locator(".ds-markdown.ds-assistant-message-main-content").last
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

    def _CheckResponse(self,APIResponse:str)->bool:
        # 如果APIResponse合法——非None,通过openai格式校验 return None
        # 否则 return 字符串,该字符串将拼接进Prompt，用来修正模型输出
            # 1.Json是否合法？不合法无法转成PyJson
            # 2.用openai官方的pydantic模型校验该Json
            # 不合法二者都会抛错，进入except
        try:
            # TODO:为提高成功率，可以加一个先清理json的逻辑
            # 可以让模型输出，再人为拼接成openai格式，而不是一次性让模型输出全部
            PyJson = json.loads(APIResponse)
            ChatCompletion.model_validate(PyJson)
        except json.JSONDecodeError:
            logging.warning(f"{self.ManagerName}CrawlerManager: The output of model is not valid Json")
            return False
        except Exception:
                logging.warning(f"{self.ManagerName}CrawlerManager : The output of model is not valid OpenAI response")
                return False
        logging.info(f"{self.ManagerName}CrawlerManager : Pass Reply Check")
        return True