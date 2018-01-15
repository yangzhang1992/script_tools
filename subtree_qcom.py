#!/usr/bin/env python
# coding:utf-8

import os
import commands
import sys
import shutil
import optparse

# 这里import aais 脚本里面的一些方法
from aais.log import Log
from aais.utils import Utils


class SubtreeGitError(Exception):
    pass


class SubtreeGit(object):
    def __init__(self, basepath, srcbranch, targetpath, targetbranch):
        dry_run = os.environ.get("DRY_RUN", "true").strip()
        dry_run = True if dry_run == "true" else False
        self.dryrun = dry_run

        self.basepath = basepath
        self.srcbranch = srcbranch

        self.targetpath = targetpath
        self.targetbranch = targetbranch

        self.qcom_base = os.path.basename(basepath)

        self.proprietary_project = "git/android/platform/vendor/qcom/proprietary"
        self.gerrit_host = "gerrit.zeusis.com"
        self.gerrit_port = "29418"

    def CloneGit(self):
        if os.path.exists(self.qcom_base) and os.path.isdir(self.qcom_base):
            cmd = "cd %s && git fetch --all --tags && git checkout %s" % (self.qcom_base, self.srcbranch)
        else:
            cmd = "git clone ssh://%s:%s/%s %s && cd %s && git checkout %s" % (self.gerrit_host, self.gerrit_port,
                                                                               self.basepath, self.qcom_base,
                                                                               self.qcom_base, self.srcbranch)

        Log.Info("will clone/fetch base git and checkout to branch: %s, cmd: %s" % (self.srcbranch, cmd))
        ret = os.system(cmd)
        if ret != 0:
            raise SubtreeGitError("git clone/fetch/checkout fail")

    # 列出分仓列表
    def GetRepertory(self, config=""):
        if config == "":
            repertory_L = os.listdir(self.qcom_base)  # 列出当前目录下面的所有内容
            repertory_L = [basedir.strip() for basedir in repertory_L if
                           os.path.isdir(os.path.join(self.qcom_base, basedir))
                           and not basedir.startswith(".")]
            repertory_D = dict(zip(repertory_L, repertory_L))
            return repertory_D
        else:
            repertory_D = Utils.StringToDict(config, firstreg=",|;", sedondreg=":")  # 字符串转换为字典
            return repertory_D

    def CreatePropject(self, targetpath, targetbranch, repertory_L):
        # 获取gerrit上相关仓库
        cmd = "ssh -p %s %s gerrit ls-projects | grep -E \"%s|%s\"  " % (self.gerrit_port, self.gerrit_host,
                                                                         targetpath, self.proprietary_project)
        Log.Info("list project on gerrit: %s" % cmd)

        status, output = commands.getstatusoutput(cmd)
        if status == 0:
            project_L = output.splitlines()

            create_L = []
            for repertory in repertory_L:
                project = os.path.join(targetpath, repertory)
                if repertory == "LINUX" or repertory == "proprietary":
                    project = self.proprietary_project
                if project not in project_L:
                    create_L.append(project)

            for basedir in create_L:
                cmd = "ssh -p %s %s gerrit create-project %s --empty-commit --parent Permission_parent/All-bsp " \
                      "--submit-type REBASE_IF_NECESSARY --branch %s" % (
                      self.gerrit_port, self.gerrit_host, basedir, targetbranch)
                Log.Info("will create project: %s" % cmd)
                if not self.dryrun and os.system(cmd) != 0:
                    Log.Error("crate %s failed" % (basedir))
                    raise SubtreeGitError("create project fail")

    # print each repertory log for manifest
    def PrintGitLog(self, repertory_L):

        Log.Info("The repertory info list is:")
        manifest_str = ""
        for repertory in repertory_L:
            if repertory == "LINUX" or repertory == "proprietary":
                log_cmd = "git log -1 -b proprietary_master --pretty=\"%H<gitlog>%s\""
            else:
                local_branch = repertory.replace("/", "__")
                log_cmd = "git log -1 -b %s_master --pretty=\"%%H<gitlog>%%s\"" % (local_branch)
            status, output = commands.getstatusoutput(log_cmd)

            if status == 0:
                temp_L = output.strip().split("<gitlog>")
                Log.Red("%25s %s\n" % (repertory, temp_L))
                git_commit_id = temp_L[0]

                if self.qcom_base == "proprietary": # 表明是proprietary需要分仓
                    manifest_str += "  <project name=\"platform/vendor/qcom/proprietary/%s\" path=\"vendor/qcom/proprietary/%s\" revision=\"%s\" />\n" % (
                        repertory, repertory, self.targetbranch)
                else:
                    #　其他的表示 高通的大仓库需要分仓
                    if repertory == "LINUX" or repertory == "proprietary":
                        manifest_str += "  <project name=\"platform/vendor/qcom/proprietary\" path=\"vendor/qcom/proprietary\" revision=\"%s\" />\n" % (
                        git_commit_id)
                    else:
                        manifest_str +="  <project name=\"AMSS/%s\" path=\"AMSS/%s\" revision=\"%s\" />\n" % (
                        repertory, repertory, git_commit_id)

        Log.Blue("\n%s\n" % manifest_str)

    # 分仓
    def SubtreeRepertory(self, config=""):
        self.CloneGit()

        repertory_D = self.GetRepertory(config)
        self.CreatePropject(self.targetpath, self.targetbranch, repertory_D.keys())

        os.chdir(self.qcom_base)

        for (repertory, basedir) in repertory_D.items():
            # sepcial for proprietary and build 对于特殊的LINUX目录需要特殊处理
            if repertory == "LINUX" or repertory == "proprietary":
                if repertory == "LINUX":  # 这里等于LINUX的时候表明是没有填写配置文件的
                    basedir = "LINUX/android/vendor/qcom/proprietary"
                cmd = "git subtree split -P %s -b proprietary_master" % (basedir)
                Log.Info("subtree proprietary cmd: %s" % cmd)
                os.system(cmd)

                cmd = "git push ssh://%s:%s/%s proprietary_master:%s -f" % (
                self.gerrit_host, self.gerrit_port, self.proprietary_project, self.targetbranch)
                Log.Info("will proprietary push to gerrit: %s" % cmd)
                if not self.dryrun and os.system(cmd) != 0:
                    raise SubtreeGitError("push proprietary to gerrit fail")
            else:
                local_branch = repertory.replace("/", "__")
                cmd = "git subtree split -P %s -b %s_master" % (basedir, local_branch)
                Log.Info("subtree cmd: %s" % cmd)
                os.system(cmd)

                cmd = "git push ssh://%s:%s/%s/%s  %s_master:%s -f" % (
                self.gerrit_host, self.gerrit_port, self.targetpath, repertory, local_branch, self.targetbranch)
                Log.Info("will push to gerrit: %s" % cmd)
                if not self.dryrun and os.system(cmd) != 0:
                    raise SubtreeGitError("push to gerrit fail")

        self.PrintGitLog(repertory_D.keys())


def parseargs():
    usage = "usage: [options] arg1 arg2"
    parser = optparse.OptionParser(usage=usage)

    optiongroup = optparse.OptionGroup(parser, "common options")
    optiongroup.add_option("", "--base-path", dest="basepath", help="git base path", default="")
    optiongroup.add_option("", "--target-path", dest="targetpath", help="git push target path", default="")

    optiongroup.add_option("", "--src-branch", dest="srcbranch", help="srcbranch", default="")
    optiongroup.add_option("", "--target-branch", dest="targetbranch", help="targetbranch", default="")

    optiongroup.add_option("", "--config", dest="config", help="config", default="")

    parser.add_option_group(optiongroup)

    (options, args) = parser.parse_args()

    return (options, args)


def main():
    (options, args) = parseargs()
    basepath = options.basepath.strip()
    srcbranch = options.srcbranch.strip()  # 源仓库 git分支

    targetpath = options.targetpath.strip()  # 最后需要push到哪个仓库下面
    targetbranch = options.targetbranch.strip()  # 最后需要push到哪个分支上面

    config = options.config.strip()

    sub = SubtreeGit(basepath, srcbranch, targetpath, targetbranch)

    sub.SubtreeRepertory(config)


if __name__ == "__main__":
    # need flush print
    sys.stdout = sys.stderr
    main()
