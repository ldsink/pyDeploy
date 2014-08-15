#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# --------------------------------------------
# Author: Zhou Cheng <zhoucheng@ldsink.com>
# Date  : 2014-08-14 16:50:41
# --------------------------------------------

import os
import configparser
import subprocess

CONFIG_FILE = 'deploy.ini'

PROGRESS_PULL = '1'  # pull code
PROGRESS_COMP = '2'  # complie
PROGRESS_SYNC = '3'  # rsync
PROGRESS_EODW = '4'  # end of deployment work

STATUS_NORMAL = '0'
STATUS_FINISH = '1'
STATUS_ERROR = '2'

FIELD_STATUS = 'status'
FIELD_PROGRESS = 'progress'
FIELD_MESSAGE = 'message'


def check_tool(tool_name, tool_path=None):
    is_exist = False
    if not tool_path:
        for cmdPath in os.environ['PATH'].split(':'):
            if os.path.isdir(cmdPath) and tool_name in os.listdir(cmdPath):
                is_exist = True
    elif os.path.isdir(tool_path) and tool_name in os.listdir(tool_path):
        is_exist = True
    return is_exist


def redis_log(host, port, key, field, value):
    cmd = ['redis-cli', '-h', host, '-p', port, 'HSET', key, field, value]
    if subprocess.call(cmd):
        raise Exception('Connect to redis error.')


def rsync(source, dest):
    cmd = ['rsync',
           '-c',  # skip based on checksum, not mod-time & size
           '-r',  # recurse into directories
           '-p',  # preserve permissions
           '--delete-delay',  # find deletions during, delete after
           '--delay-updates',  # put all updated files into place at transfer's end
           source,
           dest
    ]
    return subprocess.call(cmd)


def main():
    if not os.path.isfile(CONFIG_FILE):
        raise Exception('Config file not exist.')
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)

    # 检查必须的工具
    redis_cli_path = config.get('env', 'redis_path')
    if not check_tool('redis-cli', redis_cli_path):
        raise Exception('redis-cli can\'t find.')

    git_path = config.get('env', 'git_path')
    if not check_tool('git', git_path):
        raise Exception('git can\'t find.')

    rsync_path = config.get('env', 'rsync_path')
    if not check_tool('rsync', rsync_path):
        raise Exception('rsync can\'t find.')

    # 检查Redis配置
    redis_host = config.get('redis', 'host')
    redis_port = config.get('redis', 'port')
    redis_key = config.get('redis', 'condition_key')
    if not all((redis_host, redis_port, redis_key)):
        raise Exception('redis config missing.')

    # 初始化记录
    redis_log(redis_host, redis_port, redis_key, FIELD_STATUS, STATUS_NORMAL)

    # 更新代码
    redis_log(redis_host, redis_port, redis_key, FIELD_PROGRESS, PROGRESS_PULL)
    redis_log(redis_host, redis_port, redis_key, FIELD_MESSAGE, 'begin pull new codes.')
    project_path = config.get('env', 'project_path')
    if not project_path:
        msg = 'project_path config missing.'
        redis_log(redis_host, redis_port, redis_key, FIELD_STATUS, STATUS_ERROR)
        redis_log(redis_host, redis_port, redis_key, FIELD_MESSAGE, msg)
        raise Exception(msg)

    redis_log(redis_host, redis_port, redis_key, FIELD_MESSAGE, 'pulling codes.')
    if git_path:
        git_path += '/git'
    else:
        git_path = 'git'
    cmd = [git_path, 'pull']
    if subprocess.call(cmd, cwd=project_path):
        msg = 'git pull error.'
        redis_log(redis_host, redis_port, redis_key, FIELD_STATUS, STATUS_ERROR)
        redis_log(redis_host, redis_port, redis_key, FIELD_MESSAGE, msg)
        raise Exception(msg)

    # 编译代码
    redis_log(redis_host, redis_port, redis_key, FIELD_PROGRESS, PROGRESS_COMP)
    redis_log(redis_host, redis_port, redis_key, FIELD_MESSAGE, 'begin compile.')
    compile_script = config.get('env', 'compile_script')
    if compile_script:
        redis_log(redis_host, redis_port, redis_key, FIELD_MESSAGE, 'compiling.')
        if subprocess.call([compile_script]):
            msg = '编译脚本运行时发生错误。'
            redis_log(redis_host, redis_port, redis_key, FIELD_STATUS, STATUS_ERROR)
            redis_log(redis_host, redis_port, redis_key, FIELD_MESSAGE, msg)
            raise Exception(msg)

    # 同步新代码到网站目录
    redis_log(redis_host, redis_port, redis_key, FIELD_PROGRESS, PROGRESS_SYNC)
    redis_log(redis_host, redis_port, redis_key, FIELD_MESSAGE, 'begin rsync.')
    source_path = config.get('rsync', 'source_path')
    dest_path = config.get('rsync', 'dest_path')
    if not all((source_path, dest_path)):
        msg = 'rsync argus missing.'
        redis_log(redis_host, redis_port, redis_key, FIELD_STATUS, STATUS_ERROR)
        redis_log(redis_host, redis_port, redis_key, FIELD_MESSAGE, msg)
        raise Exception(msg)

    redis_log(redis_host, redis_port, redis_key, FIELD_MESSAGE, 'rsyncing...')
    if rsync(source_path, dest_path):
        msg = 'rsync error.'
        redis_log(redis_host, redis_port, redis_key, FIELD_STATUS, STATUS_ERROR)
        redis_log(redis_host, redis_port, redis_key, FIELD_MESSAGE, msg)
        raise Exception(msg)


'''

    # 同步完成后执行扫尾脚本
    redis_log(redis_host, redis_port, redis_key, 'begin outstanding work.')
    finish_script = config.get('env', 'finish_script')
    if finish_script:
        redis_log(redis_host, redis_port, redis_key, 'executing outstanding work.')
        if subprocess.call([finish_script]):
            raise Exception('扫尾脚本运行时发生错误.')
'''

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print('Error : {}'.format(e))
