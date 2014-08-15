#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess

print('just for test.')
subprocess.call(['ls', '-al'])
subprocess.call(['uname', '-a'])
subprocess.call(['free'])