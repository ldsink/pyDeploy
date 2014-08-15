pyDeploy
========

A simple python deployment script.

说明
--
运行`deploy.py`执行部署，执行状态将会按配置文件`deploy.ini`的设置写入`Redis`某个key下，可以通过查询`Redis`的键值获得部署情况。

流程
---
1. 检测环境
1. Git pull 同步代码
1. 执行编译脚本
1. rsync 将代码移动到目标目录
1. 执行扫尾脚本

文件
---
**deploy.ini**
> 配置文件。

**deploy.py**
> 部署脚本，根据配置文件的设置执行任务。
