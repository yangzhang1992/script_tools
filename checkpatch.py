#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import re


def main():
    title=os.environ.get("GERRIT_CHANGE_SUBJECT")
    change_number=os.environ.get("GERRIT_CHANGE_NUMBER")
    patchset_number=os.environ.get("GERRIT_PATCHSET_NUMBER")
    project=os.environ.get("GERRIT_PROJECT")
    commit_message=os.environ.get("GERRIT_CHANGE_COMMIT_MESSAGE")
    commit_message_L=commit_message.splitlines()

    msg = []
    try:
        unicode(title, "ascii")
    except Exception:
        msg.append("git commit 标题不允许有中文！")

    if len(title) > 100 :
        msg.append("git commit 标题不要超过100个字符长度！")

    if title.endswith("."):
        msg.append("git commit 标题不要点号结尾！")

    if len(title) > len(commit_message_L[0]):
        msg.append("git commit 标题后面要空一行的！")

    # androi/ 和 letv/下面的需要检验 jira单号
    if project.startswith("git/android/") or  project.startswith("git/letv/"):
        all_L = re.findall("\[[A-Za-z]+-[0-9]+\]", title)
        if not all_L:
            msg.append("git commit 的标题中没有jira单号!")
        else:
            for jiraidstr in all_L:
                jiraid = jiraidstr.replace("[", "").replace("]", "")
                jiranum = jiraid.split("-")[1]
                try:
                    if int(jiranum) <= 0:
                        msg.append("jira id %s 单号不对,怎么能等于零!" % jiraidstr)
                except:
                    msg.append("jira id %s 单号不对!" % jiraidstr)
    if msg :
        message = " ".join(msg)
        message = """Error.
        %s""" % message
        cmd = "ssh -p 29418 jira@gerrit.zeusis.com gerrit review --message '\"%s\"' --verified -1 --code-review -2 %s,%s" % (message, change_number, patchset_number)
        print "cmd : %s" % (cmd)
        os.system(cmd)
        ret = 1
    else:
        # 说明是合法的标题
        msg = """Good.
        第一行不要超过100个字符长度！
        第一行之后要空一行的！
        第一行不允许有中文！
        第一行不允许点号结尾！
        jira单号规范参考这里：http://wiki.zeusis.com:8090/pages/viewpage.action?pageId=1999652
        """
        cmd = "ssh -p 29418 jira@gerrit.zeusis.com gerrit review --message '\"%s\"' --verified 0 --code-review +1 %s,%s" % (msg, change_number, patchset_number)
        print "cmd : %s" % (cmd)
        os.system(cmd)
        ret = 0

    sys.exit(ret)

if __name__ == "__main__" :
    # need flush print
    sys.stdout = sys.stderr
    main()
