from fastapi import FastAPI,Response,Request
from PublicVar import RequestQue,ResponseQue

import logging



LocalServer = FastAPI()

@LocalServer.post("/")
async def GetClaudeCodePost(request:Request):
    # 拿到请求体
    body_bytes = await request.body()  
    body:str = body_bytes.decode("utf-8")
    # 把请求放入请求队列，交给爬虫处理
    RequestQue.put(body)
    # 阻塞等待爬虫完成，并拿到响应
    JSON = ResponseQue.get()
    logging.info("后端请求发送")
    return Response(content=JSON, media_type="application/json")



