#!/usr/bin/python
# coding:utf-8

import re
import os
import sys
import optparse
import commands
import shutil
import glob

# 这里import aais 脚本里面的一些方法
from aais.log import Log
from aais.utils import Utils

def main():
    cmd = "ssh -p 29418 gerrit.zeusis.com gerrit  ls-projects|grep \"git/android\""
    status, output = commands.getstatusoutput(cmd)
    all_projects_L = output.splitlines()
    #print  all_projects_L
    #curl -n --digest -X GET http://gerrit.zeusis.com:8080/a/projects/$pp/parent 2>/dev/null
    for project in all_projects_L:
        projectid = project.replace("/", "%2F")
        cmd = "curl -n --digest -X GET http://gerrit.zeusis.com:8080/a/projects/%s/parent 2>/dev/null" % projectid
        status, output = commands.getstatusoutput(cmd)
        temp_L = output.splitlines()
        parent_project = temp_L[1]
        if parent_project == "\"All-Projects\"" and project.startswith("git/android/platform/vendor"):
            print project, parent_project
            cmd = "ssh -p 29418 gerrit.zeusis.com gerrit set-project-parent --parent Permission_parent/All-android  %s" % project
            os.system(cmd)

if __name__ == "__main__":
    #sys.stdout = sys.stderr
    main()