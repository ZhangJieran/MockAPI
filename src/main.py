import uvicorn
from PythonScripts.src.Crawler.DeepseekCrawlerManager import *
import threading
from PythonScripts.src.Public import RequestQue,ResponseQue,config
from BackendService import LocalService


def BackendServiceFunc():
    #启动后端服务
    uvicorn.run(LocalService, host="127.0.0.1", port=config["BackendPort"])


def main():
    # 这里需要给后端单开一个线程
    # 原本计划是后端里直接调用APIResponse
    # 但是后端有一个事件循环，playwright也会有一个事件循环(playwright的同步API底层是异步的)
    # 两层事件循环报错，因此不得不再给后端开一个线程
    StartBackendService = threading.Thread( target=BackendServiceFunc,daemon=True ) 
    StartBackendService.start()
    
    while True:
        # 等待后端发来请求，没有就阻塞等待
        RequestJson = RequestQue.get()
        # APIResponse处理结果返回给后端
        Response = GetAPI(RequestJson,config["TryTime"])
        ResponseQue.put(Response)


if __name__=="__main__":    
    main()