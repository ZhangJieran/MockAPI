from fastapi import FastAPI
import uvicorn


LocalServer = FastAPI()

@LocalServer.post("")
def GetClaudeCodePost():
    return 


uvicorn.run(LocalServer, host="127.0.0.1", port=1000)