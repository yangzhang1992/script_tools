#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import sys
import os
import pwd
import psutil
import commands
import pprint
import datetime

# 这里import aais 脚本里面的一些方法
from aais.sendmail import SendMail
from aais.html import *


class DiskReport(object):
    def __init__(self):
        self.work_base_path = "/work"
        self.home_base_path = "/home"
        self.jenkins_base_path = "/home/buildfarm/jenkins"

        self.allinfo_L = []
        self.work_usage_Tuple = (0, 0, 0, 0)
        self.home_usage_Tuple = (0, 0, 0, 0)
        self.jenkins_usage_Tuple = (0, 0, 0, 0)

    def GetAllUser(self):
        return pwd.getpwall()

    def GetAllUserName(self):
        return [user[0] for user in pwd.getpwall()]

    def GetComment(self, name):
        return pwd.getpwnam(name)[4]

    def GetAllNormalUserName(self):
        # 把 buildfarm user 过滤掉
        return [user[0] for user in pwd.getpwall() if user[2] > 1000  and user[2] < 1999 and user[0] != "buildfarm" and user[0] != "user"]

    def GetAllNormalUserEmail(self):
        return [self.GetComment(user)  for user in self.GetAllNormalUserName()]

    def BytesToHuman(self, bytes):
        # 字节单位　转换　人比较容易看懂的单位
        symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
        prefix = {}
        for i, s in enumerate(symbols):
            prefix[s] = 1 << (i+1)*10
        for s in reversed(symbols):
            if bytes >= prefix[s]:
                value = float(bytes) / prefix[s]
                return '%.1f%s' % (value, s)
        return "%sB" % bytes

    def FindRepoDir(self, dir):
        # 查找指定目录下面有多少个.repo　目录，多少个ｒｅｐｏ目录就代表下载了几套
        all_L = []
        for root, dirs, files in os.walk(dir):
            if ".repo" in dirs:
                del dirs[:]
                all_L.append(root)
        return all_L

    def DuDir(self, user_work_path):
        status, output = commands.getstatusoutput("sudo du -sh %s" % user_work_path)
        if status == 0:
            return output.split("\t")[0]
        else:
            return ""

    def GetBuildEnvHtml(self):
        key = "BUILD_URL"
        url = os.environ.get(key, "")
        table_tr = BUILD_TABLE_TH % ("Build Environemnt")

        url_a = BUILD_TABLE_A % (url, url)
        table_tr += BUILD_TABLE_TR % ("build url", url_a)
        url_a = BUILD_TABLE_A % ("%sconsole" % url, "%sconsole" % url)
        table_tr += BUILD_TABLE_TR % ("console output", url_a)

        table_tr += BUILD_TABLE_TR % ("server hostname", os.environ.get("NODE_NAME", ""))

        table = BUILD_TABLE_BODY % (table_tr)
        return table

    def SendPassMail(self, subject=""):
        subject = "[diskusage][success][%s] disk usage report %s" % (os.environ.get("NODE_NAME", ""), datetime.datetime.now())
        body = ""
        body += self.GetDiskUsageHtml()
        body += self.GetBuildEnvHtml()

        html = HTML % (TABLE_CSS_STYLE, body)
        to = []
        assigner = os.environ.get("ASSIGNER", "")
        to.extend(assigner.split(","))
        to.extend(self.GetAllNormalUserEmail())
        sm = SendMail()
        sm.SendHtmlMail(to, subject, html)

    def GetDiskUsageHtml(self):
        html = BR

        totaltable_tr = BUILD_TABLE_TH % ("home dir total usage info")
        totaltable_tr += BUILD_TABLE_TR % ("total:", self.BytesToHuman(self.home_usage_Tuple[0]) )
        totaltable_tr += BUILD_TABLE_TR % ("used:", self.BytesToHuman(self.home_usage_Tuple[1]) )
        totaltable_tr += BUILD_TABLE_TR % ("free:", self.BytesToHuman(self.home_usage_Tuple[2]) )
        totaltable_tr += BUILD_TABLE_TR % ("percent:", self.home_usage_Tuple[3] )
        totaltable = BUILD_TABLE_BODY % (totaltable_tr)
        html += totaltable + BR

        if os.path.exists(self.work_base_path) and os.path.ismount(self.work_base_path):
            totaltable_tr = BUILD_TABLE_TH % ("work dir total usage info")
            totaltable_tr += BUILD_TABLE_TR % ("total:", self.BytesToHuman(self.work_usage_Tuple[0]) )
            totaltable_tr += BUILD_TABLE_TR % ("used:", self.BytesToHuman(self.work_usage_Tuple[1]) )
            totaltable_tr += BUILD_TABLE_TR % ("free:", self.BytesToHuman(self.work_usage_Tuple[2]) )
            totaltable_tr += BUILD_TABLE_TR % ("percent:", self.work_usage_Tuple[3] )
            totaltable = BUILD_TABLE_BODY % (totaltable_tr)
            html += totaltable + BR

        if os.path.exists(self.jenkins_base_path) and os.path.ismount(self.jenkins_base_path):
            totaltable_tr = BUILD_TABLE_TH % ("jenkins dir total usage info")
            totaltable_tr += BUILD_TABLE_TR % ("total:", self.BytesToHuman(self.jenkins_usage_Tuple[0]) )
            totaltable_tr += BUILD_TABLE_TR % ("used:", self.BytesToHuman(self.jenkins_usage_Tuple[1]) )
            totaltable_tr += BUILD_TABLE_TR % ("free:", self.BytesToHuman(self.jenkins_usage_Tuple[2]) )
            totaltable_tr += BUILD_TABLE_TR % ("percent:", self.jenkins_usage_Tuple[3] )
            totaltable = BUILD_TABLE_BODY % (totaltable_tr)
            html += totaltable + BR


        for info in self.allinfo_L:
            table_tr = BUILD_TABLE_TH % ("%s work dir usage info" % info[0])

            table_tr += BUILD_TABLE_TR % ("%s dir size:" % os.path.join(self.work_base_path, info[0]), info[1])
            table_tr += BUILD_TABLE_TR % ("code number:", len(info[2]))
            table_tr += BUILD_TABLE_TR % ("code path:", "<br/>".join(info[2]) )
            table = BUILD_TABLE_BODY % (table_tr)
            html += table + BR

            table_tr = BUILD_TABLE_TH % ("%s home dir usage info" % info[0])

            table_tr += BUILD_TABLE_TR % ("%s dir size:" % os.path.join(self.home_base_path, info[0]), info[3])
            table_tr += BUILD_TABLE_TR % ("code number:", len(info[4]))
            table_tr += BUILD_TABLE_TR % ("code path:", "<br/>".join(info[4]) )
            table = BUILD_TABLE_BODY % (table_tr)
            html += table + BR

        return html


    def Execute(self):
        # 统计　/work 硬盘总的使用情况
        if os.path.exists(self.work_base_path) and os.path.ismount(self.work_base_path):
            self.work_usage_Tuple = psutil.disk_usage(self.work_base_path)
            pprint.pprint(self.work_usage_Tuple)

        if os.path.exists(self.home_base_path):
            self.home_usage_Tuple = psutil.disk_usage(self.home_base_path)
            pprint.pprint(self.home_usage_Tuple)

        if os.path.exists(self.jenkins_base_path) and os.path.ismount(self.jenkins_base_path):
            self.jenkins_usage_Tuple = psutil.disk_usage(self.jenkins_base_path)
            pprint.pprint(self.jenkins_usage_Tuple)

        alluser_L = self.GetAllNormalUserName()
        alluser_L.append("buildfarm")
        for username in alluser_L:  # 遍历所有的用户

            userwork_size = 0
            userworkrepo_L=[]
            userhome_size=0
            userhomerepo_L=[]

            user_work_path = os.path.join(self.work_base_path, username)
            if os.path.exists(user_work_path):
                userworkrepo_L = self.FindRepoDir(user_work_path) # 用户下了多少套代码
                userwork_size = self.DuDir(user_work_path) # 用户的work目录大小

            user_home_path = os.path.join(self.home_base_path, username)
            if os.path.exists(user_home_path):
                userhomerepo_L = self.FindRepoDir(user_home_path)  # 用户home目录下了多少套代码
                userhome_size = self.DuDir(user_home_path)  # 用户的home目录大小

            info = (username, userwork_size, userworkrepo_L, userhome_size, userhomerepo_L)

            pprint.pprint(info)
            self.allinfo_L.append(info)


        pprint.pprint(self.allinfo_L)

        self.SendPassMail()




def main():
    diskreport = DiskReport()
    diskreport.Execute()

if __name__ == "__main__":
    # need flush print
    sys.stdout = sys.stderr
    main()
