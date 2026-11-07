from fastapi import FastAPI,Response,Request
import uvicorn
from GetWebDeepSeekAnswer import APIResponse

LocalServer = FastAPI()

@LocalServer.post("/")
async def GetClaudeCodePost(request:Request):
    body_bytes = await request.body()
    body:str = body_bytes.decode("utf-8")
    from main import page
    JSON:str = APIResponse(page,body,5)
    return Response(content=JSON, media_type="application/json")

uvicorn.run(LocalServer, host="127.0.0.1", port=1000)