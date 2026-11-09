import time
from dataclasses import dataclass
from playwright.sync_api import sync_playwright, Page 

from Public import logging


# 建造者模式，构造 ModelCrawlerManager 管理不同模型Web端的爬虫抓取

@dataclass
class CrawlerConfig():
    # playwright对象
    page:Page|None = None
    # 这些是page的相关信息，本来不打算加的，但加了也没错万一以后用得上
    __playwright = None
    __browser    = None
    __context    = None 
    # page.goto()的网址
    BaseUrl:str = ""
    # 记录一个会话窗口的对话次数,发送的总token数，超过阈值切换会话
    CurSessionChat  : int = 0
    CurSessionToken : int = 0
    MaxSessionChat  : int = -1  
    MaxSessionToken : int = -1
    # 记录连续的的对话次数,超过阈值要让等一段时间再发请求
    # 多次连续对话要大休息一轮（time.sleep()）
    CurContinuousChat:int = 0
    MaxContinuousChat:int = -1
    # 每次给模型发prompt的间隔时间（s），防止请求频率太快
    Interval = 0
    # 每次大休息的休息时间(s)
    RestTime = 0





class CrawlerBuilder():
    # 请先使用 `所有SetXXX()`，最后使用 `Build()`
    # `Setxxx()`原本设计返回None,但为了支持链式调用，返回self
    def __init__(self):
        self.config:CrawlerConfig = CrawlerConfig()

    def SetPage(
            self,
            browerArgs  = {"headless":False,"channel":"msedge"},
            contextArgs = {},
        )->"CrawlerBuilder":
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(**browerArgs)
        context = browser.new_context(**contextArgs)
        self.config.page         = context.new_page()
        self.config.__playwright = playwright
        self.config.__browser    = browser
        self.config.__context    = context
        return self
    def SetBaseUrl(self,Url:str)->"CrawlerBuilder":
        self.config.BaseUrl = Url
        return self
    def SetMaxSessionChat(self,MaxSessionChat:int)->"CrawlerBuilder":
        self.config.MaxSessionChat = MaxSessionChat
        return self
    def SetMaxSessionToken(self, MaxSessionToken:int)->"CrawlerBuilder":
        self.config.MaxSessionToken = MaxSessionToken
        return self
    def SetMaxContinuousChat(self,MaxContinuousChat:int)->"CrawlerBuilder":
        self.config.MaxContinuousChat = MaxContinuousChat
        return self
    def SetIntervalTime(self,time:int)->"CrawlerBuilder":
        self.config.Interval = time
    def SetRestTime(self,time:int)->"CrawlerBuilder":
        self.config.RestTime = time
    
    def Build(self)->CrawlerConfig:
        return self.config
        




class CrawlerManager():
    # 顶层基类
    # 对于不同的模型的CrawlerManager，请继承这个基类
    # 唯一对外暴露接口GetAPIResponse():
    # 数据是否>=阈值_IsOver() -- yes -->相关逻辑_DealOver()(请保证执行完该逻辑后page位于一个会话里)
    #           -- no -->给模型发消息_Send()->抓取模型回复_GetResponse()->校验回复_CheckResponse()->更新数据_Update()                        
    # 必须实现以上提及的方法，GetAPIResponse()已经把以上方法组合流程框架搭好
    # 以上所有方法，除了GetAPIResponse()，均实现错误处理逻辑，保证不会报错
    
    # 类级注解：让静态分析器认识 self.page 等属性（不产生运行时属性）
    page         : Page | None
    __playwright : object | None
    __browser    : object | None
    __context    : object | None
    BaseUrl      : str
    CurSessionChat    : int
    CurSessionToken   : int
    MaxSessionChat    : int
    MaxSessionToken   : int
    CurContinuousChat : int
    MaxContinuousChat : int
    IntervalTime      : int
    RestTime          : int
    ManagerName       : str

    def __init__(self,config:CrawlerConfig,ManagerName:str="Unknown"):
        # 传入经Buidler构造过的CrawlerConfig实例
        # 拿到CrawlerConfig里的所有属性
        self.__dict__.update(config.__dict__)
        #给manager取个名，方便看日志的时候区分
        self.ManagerName:str = ManagerName

    def _ResetData(self)->None:
        # 超过阈值后。可以使用本函数重置数据
        self.CurSessionChat    = 0
        self.CurSessionToken   = 0
        self.CurContinuousChat = 0

    def _IsOver(self)->bool:
        return ( 
           self.CurSessionChat       >= self.MaxSessionChat   
           or self.CurSessionToken   >= self.MaxSessionToken  
           or self.CurContinuousChat >= self.MaxContinuousChat 
        )
    
    def _DealOver(self)->None:
        # 如果超过阈值，处理逻辑
        pass
    
    def _Send(self,APIRequest:str)->int:
        # 实现给模型发消息逻辑，返回模型的回复
        # 本函数应返回模型模拟的API response(以字符串json的形式)
        # 返回发给模型的消息的token数量
        # 如果发送失败，返回0
        # 可能会用到的工具函数：MakePrompt
        pass

    def _GetResponse(self)->str|None:
        # 请使用try except处理错误,不要报错终止程序。
        # 如果报错，返回None
        # 否则返回模型回复(API Response 字符串形式的json)
        # 这里可以有一些模型回复粗略检验：
        # 比如在DeepSeek的实现逻辑里
        # 视模型返回只返回一个json代码块为标准情况
        # 非标准情况，如返回多个json代码块，未返回代码块等
        # 这些情况单靠程序死逻辑不好全部覆盖
        # 因此如果遇到非标准情况，不用要硬爬，直接返回None
        # 后续逻辑会要求模型按标准情况重新生成
        pass
    
    def _CheckResponse(self,APIResponse:str)->bool:
        # 用于检验模型输出是否符合预期
        #本
        pass    
    def _Update(self,CurTurnToken:int)->bool:
        # 每轮与模型对话，不管是否成功，都要更新一下
        self.CurContinuousChat += 1
        self.CurSessionChat    += 1
        self.CurSessionToken   += CurTurnToken
        
    def GetAPIResponse(self,APIRequest:str,TryTime:int=5)->str:
        #TryTime：可能GetAPIResponse会失败，比如模型返回的消息未通过_CheckReturn的校验
        #允许重试，重试TryTime后任未通过则终止程序，报错

        # 统计Token,传给self._Update做数据更新
        Token:int = 0
        APIResponse:str|None = None
        while TryTime:
            time.sleep(self.IntervalTime)
            TryTime = TryTime - 1
            APIResponse = None
            # 如果达到阈值先处理阈值
            if self._IsOver():
                logging.info(f"{self.ManagerName}CrawlerManager : Reach threshold")
                logging.info(f"{self.ManagerName}CrawlerManager : Data Reset")
                # 这里先设计DealOver 后 ResetData
                # 因为IsOver没有暴露是哪种阈值超了，DealOver的时候数据还没重置
                # 可以根据这些数据来实现DealOver逻辑
                self._DealOver()
                self._ResetData()
            SendToken:int = self._Send(APIRequest)
            Token += SendToken
            # 如果发送失败，continue
            if SendToken == 0 :
                logging.warning(f"{self.ManagerName}CrawlerManager : Send Request Failed!")
                self._Update(Token)
                Token = 0 
                continue

            APIResponse = self._GetResponse()
            # 如果抓取消息失败,continue
            if APIResponse == None:
                logging.warning(f"{self.ManagerName}CrawlerManager : Get Response Failed!")
                self._Update(Token)
                Token = 0 
                continue
            Token += len(APIResponse)
            # 如果模型返回不符合预期，continue
            if not self._CheckResponse(APIResponse):
                logging.warning(f"{self.ManagerName}CrawlerManager : Unexpected Model Response")
                self._Update(Token)
                Token = 0 
                continue
            return APIResponse
        raise Exception("Tried Too Many Times Without Getting One Expected Answer")
            
        

            





            

        
        
        




