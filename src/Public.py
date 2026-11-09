from queue import Queue  
from Crawler.DeepseekCrawlerManager import *
# 加载配置文件 ../config.json
import json
import logging


# 设置日志打印
logging.basicConfig(
    leval=logging.INFO
)

RequestQue  = Queue(maxsize=1)
ResponseQue = Queue(maxsize=1) 

