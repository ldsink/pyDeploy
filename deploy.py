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

PROGRESS_NULL = '0'  # no task
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


def cmd_call(cmd, cwd=None):
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
    returncode = proc.wait()
    for line in proc.stdout.readline():
        pass
    for line in proc.stderr.readline():
        pass
    return returncode


class RedisLog():
    def __init__(self, path, host, port, key):
        self.path = path
        self.host = host
        self.port = port
        self.key = key

    def log(self, field, value):
        if field == FIELD_MESSAGE:
            print('INFO : {}'.format(value))
        cmd = [self.path, '-h', self.host, '-p', self.port, 'HSET', self.key, field, value]
        if cmd_call(cmd):
            raise Exception('Connect to redis error.')


def check_tool(tool_name, tool_path=None):
    is_exist = False
    if not tool_path:
        for cmdPath in os.environ['PATH'].split(':'):
            if os.path.isdir(cmdPath) and tool_name in os.listdir(cmdPath):
                is_exist = True
    elif os.path.isfile(tool_path):
        is_exist = True
    return is_exist


def rsync(rsync_path, source, dest, ignore):
    cmd = [rsync_path,
           '-c',  # skip based on checksum, not mod-time & size
           '-r',  # recurse into directories
           '-p',  # preserve permissions
           '--delete-delay',  # find deletions during, delete after
           '--delay-updates'  # put all updated files into place at transfer's end
    ]
    if ignore:  # ignore file and directory
        ignore = str(ignore).strip().split(',')
        for file in ignore:
            cmd.append('--exclude={}'.format(file.strip()))
    cmd.extend([source, dest])
    return cmd_call(cmd)


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
    if not redis_cli_path:
        redis_cli_path = 'redis-cli'
    redis_host = config.get('redis', 'host')
    redis_port = config.get('redis', 'port')
    redis_key = config.get('redis', 'condition_key')
    if not all((redis_cli_path, redis_host, redis_port, redis_key)):
        raise Exception('redis config missing.')

    # 初始化记录
    log = RedisLog(redis_cli_path, redis_host, redis_port, redis_key)
    log.log(FIELD_STATUS, STATUS_NORMAL)

    # 更新代码
    log.log(FIELD_PROGRESS, PROGRESS_PULL)
    log.log(FIELD_MESSAGE, 'begin pull new codes.')
    project_path = config.get('env', 'project_path')
    if not project_path:
        msg = 'project_path config missing.'
        log.log(FIELD_STATUS, STATUS_ERROR)
        log.log(FIELD_MESSAGE, msg)
        raise Exception(msg)

    log.log(FIELD_MESSAGE, 'pulling codes.')
    if not git_path:
        git_path = 'git'
    cmd = [git_path, 'pull']
    if cmd_call(cmd, cwd=project_path):
        msg = 'git pull error.'
        log.log(FIELD_STATUS, STATUS_ERROR)
        log.log(FIELD_MESSAGE, msg)
        raise Exception(msg)

    # 编译代码
    log.log(FIELD_PROGRESS, PROGRESS_COMP)
    log.log(FIELD_MESSAGE, 'begin compile.')
    compile_script = config.get('env', 'compile_script')
    if compile_script:
        log.log(FIELD_MESSAGE, 'compiling.')
        if cmd_call([compile_script]):
            msg = '编译脚本运行时发生错误。'
            log.log(FIELD_STATUS, STATUS_ERROR)
            log.log(FIELD_MESSAGE, msg)
            raise Exception(msg)

    # 同步新代码到网站目录
    log.log(FIELD_PROGRESS, PROGRESS_SYNC)
    log.log(FIELD_MESSAGE, 'begin rsync.')
    if not rsync_path:
        rsync_path = 'rsync'
    source_path = config.get('rsync', 'source_path')
    dest_path = config.get('rsync', 'dest_path')
    if not all((rsync_path, source_path, dest_path)):
        msg = 'rsync argus missing.'
        log.log(FIELD_STATUS, STATUS_ERROR)
        log.log(FIELD_MESSAGE, msg)
        raise Exception(msg)

    sync_ignore = config.get('rsync', 'sync_ignore')
    log.log(FIELD_MESSAGE, 'rsyncing...')
    if rsync(rsync_path, source_path, dest_path, sync_ignore):
        msg = 'rsync error.'
        log.log(FIELD_STATUS, STATUS_ERROR)
        log.log(FIELD_MESSAGE, msg)
        raise Exception(msg)

    # 同步完成后执行扫尾脚本
    log.log(FIELD_PROGRESS, PROGRESS_EODW)
    log.log(FIELD_MESSAGE, 'begin outstanding work.')
    finish_script = config.get('env', 'finish_script')
    if finish_script:
        log.log(FIELD_MESSAGE, 'executing outstanding work.')
        if cmd_call([finish_script]):
            msg = '扫尾脚本运行时发生错误。'
            log.log(FIELD_STATUS, STATUS_ERROR)
            log.log(FIELD_MESSAGE, msg)
            raise Exception(msg)

    log.log(FIELD_STATUS, STATUS_FINISH)
    log.log(FIELD_MESSAGE, 'Finished')
    log.log(FIELD_PROGRESS, PROGRESS_NULL)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print('Error : {}'.format(e))
