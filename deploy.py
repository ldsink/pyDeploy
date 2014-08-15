#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# --------------------------------------------
# Author: Zhou Cheng <zhoucheng@ldsink.com>
# Date  : 2014-08-14 16:50:41
# --------------------------------------------

import os
import configparser
import subprocess

config_file = 'deploy.ini'


def check_tool(tool_name):
    isExist = False
    for cmdPath in os.environ['PATH'].split(':'):
        if os.path.isdir(cmdPath) and tool_name in os.listdir(cmdPath):
            isExist = True
    return isExist


def redis_log(host, port, key, value):
    cmd = ['redis-cli', '-h', host, '-p', port, 'SET', key, value]
    if subprocess.call(cmd):
        raise Exception('Connect to redis error.')


def rsync(source, dest):
    cmd = ['rsync',
           # '-t',  # 快速复制策略（文件的时间戳、大小完全一致，认为文件相同）
           '-I', # 老老实实逐一复制，确保数据的一致性，但是速度上会变慢
           '-r',  # 同步文件夹
           '-p',  # 保持权限一致
           '--delete',  # 目的端删除源端不存在的文件
           source,
           dest
    ]
    if subprocess.call(cmd):
        raise Exception('rsync error.')


if __name__ == "__main__":
    if not os.path.isfile(config_file):
        raise Exception('Config file not exist.')
    config = configparser.ConfigParser()
    config.read(config_file)

    # 检查必须的环境
    tools = config.get('env', 'required_tools')
    if not tools:
        raise Exception('Read Config [env] required_tools error.')
    tools = str(tools).split(':')
    for tool in tools:
        if not check_tool(tool):
            raise Exception('Tool : {} not exist.'.format(tool))

    # 检查Redis配置
    redis_host = config.get('redis', 'host')
    redis_port = config.get('redis', 'port')
    redis_key = config.get('redis', 'condition_key')
    if not redis_host or not redis_key or not redis_key:
        raise Exception('Read Config [redis] error.')

    # 更新代码
    redis_log(redis_host, redis_port, redis_key, 'begin pull new codes.')
    codes_dir = config.get('env', 'source_location')
    if not codes_dir:
        raise Exception('Read Config [env] source_location error.')

    redis_log(redis_host, redis_port, redis_key, 'pulling codes.'.format(codes_dir))
    cmd = ['git', 'pull']
    if subprocess.call(cmd, cwd=codes_dir):
        raise Exception('git pull error.')

    # 编译代码
    redis_log(redis_host, redis_port, redis_key, 'begin compile.')
    compile_script = config.get('env', 'compile_script')
    if compile_script:
        redis_log(redis_host, redis_port, redis_key, 'compiling.')
        if subprocess.call([compile_script]):
            raise Exception('编译脚本运行时发生错误.')

    # 同步新代码到网站目录
    redis_log(redis_host, redis_port, redis_key, 'begin rsync.')
    source_dir = config.get('rsync', 'source_dir')
    dest_dir = config.get('rsync', 'dest_dir')
    if not source_dir or not dest_dir:
        raise Exception('Missing rsync argus.')

    redis_log(redis_host, redis_port, redis_key, 'rsyncing...')
    rsync(source_dir, dest_dir)

    # 同步完成后执行扫尾脚本
    redis_log(redis_host, redis_port, redis_key, 'begin outstanding work.')
    finish_script = config.get('env', 'finish_script')
    if finish_script:
        redis_log(redis_host, redis_port, redis_key, 'executing outstanding work.')
        if subprocess.call([finish_script]):
            raise Exception('扫尾脚本运行时发生错误.')
