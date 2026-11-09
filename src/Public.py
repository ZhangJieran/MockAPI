# 为解决循环导入问题创建本模块，存放一些共用的变量
# 本模块严禁导入其他模块，只能被导入
from queue import Queue  
import logging




# 设置日志打印
logging.basicConfig(
    level=logging.WARNING
)

#爬虫与FastAPI后端的通信通道
RequestQue  = Queue(maxsize=1)
ResponseQue = Queue(maxsize=1) 




