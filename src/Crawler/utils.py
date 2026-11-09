def MakePrompt(request:str)->str:
    # request是claudecode发出的请求，其经过的链路如下：
    # 1. claudecode发出 
    # 2. cc switch转换openai格式并转发到本项目后端
    # 3. 后端接收后交由本函数做进一步提示词处理
    # 本函数从提示词层面约束模型输出，确保模型正确返回预期格式
    SystemPrompt:str = "请你模拟LLM API服务。我将发给你一段OpenAI格式的API请求，请以Json代码块的形式回复我API响应，要求如下：\
1.仅包含json代码块。\
2.符合OpenAI规范API应答。\
3.请启用严格的格式化输出模式.\
4.我将把你的回复一字不漏地交给OpenAI pydantic模型(ChatCompletion.model_validate)做校验，请确保能通过。\
5.我会把你的响应转给agent,请确保agent能正常工作。\
6.你可以使用工具函数，我会把你的请求转交给agent\
模型API请求如下:" 
    return  SystemPrompt+request


