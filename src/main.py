import uvicorn
import threading
from .Public import RequestQue,ResponseQue
from .BackendService import LocalService
from .Crawler.DeepseekCrawlerManager import *

def BackendServiceFunc():
    #启动后端服务
    uvicorn.run(LocalService, host="127.0.0.1", port=1000)


def main():
    # 这里需要给后端单开一个线程
    # 原本计划是后端里直接调用APIResponse
    # 但是后端有一个事件循环，playwright也会有一个事件循环(playwright的同步API底层是异步的)
    # 两层事件循环报错，因此不得不再给后端开一个线程
    StartBackendService = threading.Thread( target=BackendServiceFunc,daemon=True ) 
    StartBackendService.start()


    # 实例化 DeepseekCrawlerManager
    DeepseekBuilder = DeepseekCrawlerBuilder()
    DeepseekBuilder.SetPage()
    DeepseekBuilder.SetBaseUrl("https://chat.deepseek.com")
    DeepseekBuilder.SetMaxSessionChat(5)
    DeepseekBuilder.SetMaxSessionToken(1000000)
    DeepseekBuilder.SetMaxContinuousChat(5)
    DeepseekBuilder.SetIntervalTime(2)
    DeepseekBuilder.SetRestTime(10)
    DeepseekBluePrint = DeepseekBuilder.Build()
    Deepseek = DeepseekCrawlerManager(DeepseekBluePrint)
    # 这一步暂时这样，后面并入GetAPIResponse逻辑
    Deepseek.page.goto(Deepseek.BaseUrl)
    
    while True:
        # 等待后端发来请求，没有就阻塞等待
        RequestJson = RequestQue.get()
        # APIResponse处理结果返回给后端
        Response = Deepseek.GetAPIResponse(RequestJson,5)
        ResponseQue.put(Response)


if __name__=="__main__":    
    main()