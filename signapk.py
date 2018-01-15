#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import optparse

# 这里import aais 脚本里面的一些方法
from aais.log import Log
from aais.utils import Utils
from aais.sendmail import SendMail
from aais.html import *

def parseargs():
    usage = "usage: %prog [options] arg1 arg2"
    parser = optparse.OptionParser(usage=usage)

    optiongroup = optparse.OptionGroup(parser, "common options")
    optiongroup.add_option("", "--src-path", dest="srcpath",
            help="apk source path,like:", default="")
    optiongroup.add_option("", "--sign-jar-path", dest="signjarpath",
            help="", default="")

    optiongroup.add_option("", "--product", dest="product", help="product", default="")
    optiongroup.add_option("", "--keytype", dest="keytype", help="keytype", default="platform")

    optiongroup.add_option("", "--assigner", dest="assigner", help="assigner email address", default="")
    parser.add_option_group(optiongroup)

    (options, args) = parser.parse_args()

    return (options, args)


def sendmail(assigner, subject=""):
    subject = "[SignAPK][success] %s" % (subject)
    body = ""
    html = HTML % (TABLE_CSS_STYLE, body)
    to = []
    to.extend(assigner.split(","))
    sm = SendMail()
    sm.SendHtmlMail(to, subject, html)

def main():
    (options, args) = parseargs()
    srcpath = options.srcpath.strip()
    signjarpath = options.signjarpath.strip()
    product = options.product.strip()
    assigner = options.assigner.strip()
    keytype = options.keytype.strip()

    if not os.path.isfile(srcpath):
        Log.Error("src apk path not exists")
        return 1
    if not os.path.isfile(signjarpath):
        Log.Error("sign.jar path not exists")
        return 1
    if srcpath.endswith(".apk"):
        dstpath = srcpath + "_signed.apk"
    elif srcpath.endswith(".zip"):
        dstpath = srcpath + "_signed.zip"
    else:
        dstpath = srcpath + ".signed"


    cmd = "git clone ssh://gerrit.zeusis.com:29418/git/private/product_key"
    ret = os.system(cmd)
    if ret != 0:
        Log.Error("git clone key fail")
        return 1

    wipe = os.environ.get("WIPE_USER_DATA", "").strip()
    wipe_user_data = True if wipe == "true" else False
    cmd = "java -Xmx2048m -jar %s " % (signjarpath)
    if wipe_user_data:
        cmd += " -w "
    cmd += " ./product_key/%s_key/%s.x509.pem ./product_key/%s_key/%s.pk8 %s %s" % (
                    product, keytype, product, keytype, srcpath, dstpath)
    Log.Info("sign apk/zip cmd: [%s]" % cmd)
    ret = os.system(cmd)
    if ret != 0:
        Log.Error("sign apk fail")
        return 1
    sendmail(assigner, dstpath)

if __name__ == "__main__":
    # need flush print
    sys.stdout = sys.stderr
    main()
