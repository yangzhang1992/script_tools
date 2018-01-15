#!/usr/bin/python
# coding:utf-8

import os
import sys
import optparse


# 这里import aais 脚本里面的一些方法
from aais.log import Log
from aais.utils import Utils


def parseargs():
    usage = "usage: %prog [options] arg1 arg2"
    parser = optparse.OptionParser(usage=usage)

    optiongroup = optparse.OptionGroup(parser, "common options")
    optiongroup.add_option("", "--src-path", dest="srcpath", 
            help="dailybuild server windows source path,like:\n E:\\dailybuild\\android", default="")
    optiongroup.add_option("", "--dst-path", dest="dstpath", 
            help="verbaseline server winodws dest path,like:\n  Z:\\test_ver\\mobile\\ZL1", default="")

    optiongroup.add_option("", "--assigner", dest="assigner", help="assigner email address", default="")
    parser.add_option_group(optiongroup)

    (options, args) = parser.parse_args()

    return (options, args)

def main():
    (options, args) = parseargs()
    srcpath = options.srcpath.strip() # 需要复制的源路径
    dstpath = options.dstpath.strip() # 复制的目的路径
    assigner = options.assigner.strip()

    ignore_folder = os.environ.get("XD_FOLDER", "").strip() # 忽略不复制的子目录名称

    dry_run = os.environ.get("DRY_RUN", "").strip()
    dry_run = True if dry_run == "true" else False

    if not dry_run:
        release_flog_file = os.path.join(srcpath, ".release.txt")
        mode = "a" if os.path.isfile(release_flog_file) else "w"
        with open(release_flog_file, mode) as fd:
            fd.write("release to: %s" % dstpath)

    if ignore_folder != "": # 忽略复制的目录
        xd_option = " /xd %s " % ignore_folder
    else:
        xd_option = ""

    robocopy_cmd = "robocopy %s %s /e /v /mt:32 %s" % (srcpath, dstpath, xd_option)
    Log.Info("copy cmd: [%s]" % robocopy_cmd)
    if not dry_run:
        os.system(robocopy_cmd)

    if not dry_run:
        release_flog_file = os.path.join(dstpath, ".release.txt")
        mode = "a" if os.path.isfile(release_flog_file) else "w"
        with open(release_flog_file, mode) as fd:
            fd.write("release from: %s" % srcpath)

if __name__ == "__main__":
    # need flush print
    sys.stdout = sys.stderr
    main()
