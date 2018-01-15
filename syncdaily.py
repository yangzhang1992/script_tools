#!/usr/bin/env python
# -*- coding: utf-8 -*-
#export PYTHONPATH=aais-zeusis 执行的时候需要先这样一下，才可以使用aais里面的库
#python -u xxx.py
#
import os
import sys
import datetime
import glob

def robocopy(srcpath, dstpath, branch):
    ignore_folder = os.environ.get("XD_FOLDER", "") # 忽略不复制的子目录名称
    robocopy = "robocopy %s %s /e /v /mt:32 /xd debug ota config " + ignore_folder

    date_format = "%Y-%m-%d"  # date to string format
    today = datetime.date.today().strftime(date_format)  # date format
    globpattern = "%s*%s" % (today, branch)
    folders = glob.glob(os.path.join(srcpath, globpattern))
    for folder in folders:
        src = os.path.join(srcpath, folder)
        dst = os.path.join(dstpath, os.path.basename(folder))
        cmd = robocopy % (src, dst)
        print cmd
        os.system(cmd)


def main():
    from_local = os.environ.get("FROM_LOCAL", "")

    dstbasepath = os.environ.get("DST_DAILYBUILD_PATH", "")
    dstbasepath = os.path.join(dstbasepath, from_local)  # 例如 D:\\dailybuild-xi\\shanghai

    if from_local == "shanghai":
        srcbasepath = "\\\\10.0.12.12\\dailybuild"
        netuse = "net use %s \"zeusis123\" /user:\"autotest\"" % (srcbasepath)
        os.system(netuse)
    elif from_local == "xian":
        srcbasepath = "\\\\192.168.38.174\\dailybuild-xi"
        netuse = "net use %s \"zeusis123\" /user:\"autotest\"" % (srcbasepath)
        os.system(netuse)
    elif from_local == "nanjing":
        srcbasepath = "\\\\10.5.11.12\\dailybuild-nj"
        netuse = "net use %s \"ZEUsis123\" /user:\"autotest\"" % (srcbasepath)
        os.system(netuse)
    elif from_local == "shenzhen":
        srcbasepath = "\\\\172.16.3.136\\dailybuild-sz"
        netuse = "net use %s \"zeusis123\" /user:\"autotest\"" % (srcbasepath)
        os.system(netuse)
    else:
        return 1

    android_platform_branch = os.environ.get("ANDROID_PLATFORM_BRANCH", "")
    android_platform_branch_L = android_platform_branch.split(";")
    for android_pb in android_platform_branch_L:
        android_pb_L = android_pb.strip().split(",")
        android = android_pb_L[0].strip()
        platfrom = android_pb_L[1].strip()
        branch = android_pb_L[2].strip()

        srcpath = os.path.join(srcbasepath, android,platfrom)
        dstpath = os.path.join(dstbasepath, android, platfrom)
        robocopy(srcpath, dstpath, branch)

if __name__ == "__main__":
    # need flush print
    sys.stdout = sys.stderr
    main()
