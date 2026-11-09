## 项目简介绍

网页版deepseek模拟API调用达到白嫖token的目的😁👍

技术栈 : Python Playwright爬虫 + FastAPI后端


<br><br><br>

## 环境配置

>[!IMPORTANT]请确保设备上有 Edge浏览器 和 CC Switch
>👉<a href="https://github.com/farion1231/cc-switch">CC Switch</a><br>



**step1 : 安装python环境**

```bash
uv sync
```

**step2 : CC Switch开启本地路由**


**step3 : CC Switch ClaudeCode配置**

|配置项|配置方法
|---|---
|请求地址|http://localhost:xxxx<br>请把"请求地址"指向本项目后端服务，端口号与后端服务端口一致（1000）<br>
|高级选项->上游格式|Open Chat Completions(需开启路由)
|高级选项->完整URL|开启

<br>
未提及配置项可以随便填<br>

**运行 `./src/main.py` 启动本项目** 

<br><br><br>

>[!CAUTION]注意事项
***请勿随意滚动浏览器窗口:***  <br>&emsp;
DeepSeek Web端采用惰性加载机制：页面在滚动时可能不加载可视区域外内容，或重排DOM。



<br><br><br>

## 原理解析

```
ClaudeCode --- Anthropic格式API请求 --> CC Switch 
    CC Switch将 ClaudeCode 请求转为 OpenAI 格式

CC Switch --- OpenAI格式API请求 --> 本项目后端  
    启动爬虫,将请求包装为Prompt发送给网页版DeepSeek
    要求DeepSeek模拟API响应，返回OpenAI格式API响应

本项目后端 --- OpenAI格式API响应 --> CC Switch
    CC Switch 转换为 Anthropic格式API响应

CC Switch --- Anthropic格式API响应 --> ClaudeCode
```
问：为什么不直接让DeepSeek生成 Anthropic格式API响应？免得中间多一层CC Switch转换。<br>
答：也可以这么干😅😅😅但是在模型生成API响应需要校验是否合法，OpenAI格式的可以直接使用OpenAI库<br>
利用 pydantic 校验，方便校验一点

<br><br><br>




## 更新日志

---

### 2026/11/9 架构升级，增强可扩展性

 <br>

分为爬虫`./src/Crawler/` 和 后端`./src/BackendService/` 两部分<br>
重点更改爬虫部分：<br>
采用建造者设计模式构建爬虫实例，增加基类 `./src/Crawler/CrawlerManager.py`:

- `CrawlerConfig` 
- `CrawlerBuilder`
- `CrawlerManager`

并实现Deepseek特化版本`DeepseekCrawlerManager`


<br><br>
一些边角改动，增强程序稳定性<br>
计划未来适配更多模型Web端

---

### 2026/11/8

项目第一版demo上线
