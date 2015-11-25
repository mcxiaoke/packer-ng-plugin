#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: mcxiaoke
# @Date:   2015-11-25 14:30:02
import subprocess
import os

with open('huge_markets.txt','w+') as f:
    for i in range(1000):
        f.write("Test Market %s#test market %s\n" % (i,i))
        f.write("中文:MARKET%s#test market %s\n" % (i,i))

subprocess.call(["./gradlew", "-Pmarket=huge_markets.txt", "clean", "archiveApkRelease"])
os.remove('huge_markets.txt')
