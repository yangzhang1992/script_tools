#!/usr/bin/python
#coding:utf-8
#yangyong1 2017.08.29

import optparse
import sys
import os
import glob
import commands

class SubtreeGit(object):
    def __init__(self,oem_project,oem_branch,oem_tag):
        self.oem_project = oem_project
        self.oem_branch = oem_branch
        self.oem_tag = oem_tag
        self.amss_branch = oem_project.split("/")[-1]
        self.gerrit_host = "gerrit.ccdomain.com"
        self.gerrit_port = "29418"
        self.gerrit_admin = "gerrit2"
        self.manifest_L = []

    # clone amss 代码
    def clonegit(self):
        cmd = "git clone ssh://%s:%s/%s %s -b %s" % (self.gerrit_host,self.gerrit_port,self.oem_project,self.amss_branch,self.oem_branch)
        print "clone cmd:[", cmd, "]"
        os.system(cmd)
        os.chdir(self.amss_branch)
        cmd = "git checkout %s" % (self.oem_tag)
        if self.oem_tag == "news":
            pass
        else:
            try:
                os.system(cmd)
            except:
                print "cannot find tag %s" % (self.oem_tag)
                return 1

    # 获取要分仓到AMSS下的列表,排除LINUX
    def get_amss_list(self):
        sub_amss_list = glob.glob("*/")
        if 'LINUX/' in sub_amss_list:
            sub_amss_list.remove('LINUX/')
        else:
            sub_amss_list = glob.glob("*/*/")
            sub_linux_temp = glob.glob("*/LINUX/")
            sub_amss_list.remove(sub_linux_temp[0])
        print "amss list\n"
        for i in sub_amss_list:
            print "==",i
        return sub_amss_list

    # 获取要分仓到proprietary下的列表
    def get_proprietary_list(self):
        sub_proprietary_list = glob.glob("*/LINUX/android/vendor/qcom/proprietary/*/")
        sub_proprietary_list.extend(glob.glob("LINUX/android/vendor/qcom/proprietary/*/"))
        print "proprietary list\n"
        for i in sub_proprietary_list:
            print "==",i
        return sub_proprietary_list

    # 检查要分的仓是否gerrit已存在,不存在则创建
    def check_gerrit_project(self,project):
        cmd = "ssh -p %s %s@%s gerrit ls-projects | grep ^%s$" % (self.gerrit_port,self.gerrit_admin,self.gerrit_host,project)
        #print "  check cmd:[", cmd, "]"
        status, output = commands.getstatusoutput(cmd)
        if status != 0:
            cmd = "ssh -p %s %s@%s gerrit create-project %s --description \"'auto create project'\" --submit-type \"REBASE_IF_NECESSARY\" --parent \"Permission_parent/All-android\" --empty-commit" % (self.gerrit_port,
                                                                                                                                                                                                         self.gerrit_admin,
                                                                                                                                                                                                         self.gerrit_host,
                                                                                                                                                                                                         project)
            os.system(cmd)

    # AMSS分仓的方法
    def split_amss(self,subamss):
        amss_local_branch = subamss.replace("/","_")
        subamss_gerrit_project = os.path.join("git/android/AMSS/",subamss[:-1])
        self.check_gerrit_project(subamss_gerrit_project)
        cmd = "git subtree split -P %s -b %s" % (subamss,amss_local_branch)
        print "  split cmd: [",cmd,"]"
        status,output = commands.getstatusoutput(cmd)
        cmd = "git push ssh://%s:%s/%s %s:refs/heads/%s" % (self.gerrit_host,self.gerrit_port,subamss_gerrit_project,amss_local_branch,self.amss_branch)
        os.system(cmd)
        manifests = "  <project groups=\"zs_amss\" name=\"AMSS/%s\" path=\"AMSS/%s\" revision=\"%s\" upstream=\"%s\" />" % (subamss[:-1],
                                                                                                                         subamss_gerrit_project.split("/")[-1],
                                                                                                                          output.split()[-1],
                                                                                                                          self.amss_branch)
        self.manifest_L.append(manifests)

    # proprietary分仓的方法
    def split_linux(self,subproprietary):
        proprietary_local_branch = subproprietary.split("/")[-2]
        subproprietary_gerrit_project = os.path.join("git/android/platform/",
                                                  subproprietary[:-1].split("LINUX/android/")[1])
        self.check_gerrit_project(subproprietary_gerrit_project)
        cmd = "git subtree split -P %s -b %s" % (subproprietary, proprietary_local_branch)
        status, output = commands.getstatusoutput(cmd)
        print "  split cmd: [", cmd, "]"
        cmd = "git push ssh://%s:%s/%s %s:refs/heads/%s" % (self.gerrit_host,self.gerrit_port,subproprietary_gerrit_project,proprietary_local_branch,self.amss_branch)
        os.system(cmd)
        manifests = "  <project name=\"%s\" path=\"%s\" revision=\"%s\" upstream=\"%s\" />" % (subproprietary_gerrit_project.replace("git/android/","",1),
                                                                                             subproprietary_gerrit_project.replace("git/android/platform/","",1),
                                                                                             output.split()[-1],
                                                                                             self.amss_branch)
        self.manifest_L.append(manifests)

    # 执行分仓
    def subtreeqcom(self):
        self.clonegit()
        #执行 amss分仓
        amss_list_L = self.get_amss_list()
        for subamss in amss_list_L:
            self.split_amss(subamss)
        #执行 proprietary 分仓
        proprietary_list_L = self.get_proprietary_list()
        for subproprietary in proprietary_list_L:
            self.split_linux(subproprietary)

def parseages():
    parser = optparse.OptionParser()
    parser.add_option("", "--oem_project", dest="oem_project", help="oem project")
    parser.add_option("", "--oem_branch", dest="oem_branch", help="oem branch",default="master")
    parser.add_option("", "--oem_tag", dest="oem_tag", help="oem tag",default="news")
    (option,args) = parser.parse_args()
    return (option,args)

def main():
    (options, args) = parseages()
    oem_project = options.oem_project.strip()
    oem_branch = options.oem_branch.strip()
    oem_tag = options.oem_tag.strip()
    sub = SubtreeGit(oem_project,oem_branch,oem_tag)
    sub.subtreeqcom()
    print "\n\nmanifest:\n"
    for manifest in sub.manifest_L:
        print manifest

if __name__ == '__main__':
    sys.stdout = sys.stderr
    main()