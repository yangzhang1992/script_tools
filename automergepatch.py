#!/usr/bin/env python
# -*- coding: utf-8 -*-
# export PYTHONPATH=aais-zeusis 执行的时候需要先这样一下，才可以使用aais里面的库
# python -u xxx.py
#
import os
import sys
import datetime
import glob
import commands
import json
import pprint

def main():
    git_port = "29418"
    git_server = "gerrit.zeusis.com"
    commit_id = os.environ.get("GERRIT_PATCHSET_REVISION")
    querycmd = "ssh -p %s %s gerrit query --format=JSON --current-patch-set  --all-approvals --all-reviewers  %s" % (
        git_port, git_server, commit_id)
    status, output = commands.getstatusoutput(querycmd)
    jsonstr_L = output.splitlines()  # 这里有可能查询出多个，这里分割之后就会是个数组了
    jsonstr_L.pop()  # 删除数组最后一个元素
    json_d = {}
    try:
        json_d = json.loads(jsonstr_L[0])
    except ValueError as e:
        pass
    isDraft = json_d.get("currentPatchSet").get("isDraft")
    status = json_d.get("status")
    if isDraft:
        print "is draft"
        return 1
    if status != "NEW":
        print "patch status is not new"
        return 1

    approvals_L = json_d.get("currentPatchSet").get("approvals")
    approvals_D = {}
    for approvals in approvals_L:
        approvals_username = approvals.get("by").get("username")
        approvals_type = approvals.get("type")
        approvals_value = int(approvals.get("value"))
        if approvals_type == "Code-Review":
            if approvals_D.has_key(approvals_username):
                approvals_D[approvals_username] = approvals_value
            else:
                approvals_D.setdefault(approvals_username, approvals_value)

    reviewers_L = json_d.get("allReviewers")
    reviewers_L = [reviewer.get("username") for reviewer in reviewers_L]

    print(reviewers_L)
    print "\n"
    print(approvals_D)

    if len(reviewers_L) != len(approvals_D.keys()):
        print "not all reviewers approval"
        return 1
    if len(reviewers_L) < 4:
        print "reviewer number less 4, < 4"
        return 1
    if approvals_D.get("jenkins", -1) < 1:
        print "jenkins review -1"
        return 1
    if approvals_D.get("jira", -1) < 1:
        print "jira review -1"
        return 1

    for value in approvals_D.values(): # 有人打了减一
        if value < 1:
            print "someone review -1"
            return 1

    approvals_add_1 = 0 #　所有加１　的人个数
    for value in approvals_D.values(): # 有人打了减一
        if value >= 1:approvals_add_1 += 1

    print "all review +1 number: %s" % approvals_add_1

    if approvals_add_1 == len(reviewers_L):
        print "will merge patch"
        change_number = os.environ.get("GERRIT_CHANGE_NUMBER")
        patchset_number = os.environ.get("GERRIT_PATCHSET_NUMBER")
        cmd = "ssh -p %s %s gerrit review --submit  --code-review +2 --verified +1 %s,%s" % (git_port, git_server, change_number, patchset_number)
        print "submit cmd: %s" % cmd
        os.system(cmd)

if __name__ == "__main__":
    # need flush print
    sys.stdout = sys.stderr
    sys.exit(main())
