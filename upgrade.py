#!/usr/bin/python
#coding:utf-8

import xml.dom.minidom
import optparse
import commands
import os
import time

class UpgradeQcom(object):
    def __init__(self, upgrade_xml, qcom_xml,rebase_branch):
        self.upgrade_xml = upgrade_xml
        self.qcom_xml = qcom_xml
        self.rebase_branch = rebase_branch
        self.gerrit_host = "gerrit.ccdomain.com"
        self.gerrit_port = "29418"
        self.manifest_git = "git/android/platform/manifest"
        self.repo_branch = "zeusis-stable"
        self.manifest_branch = "zs_master"
        self.remote = "zsgit"
        self.local_workspace = os.getcwd()

    def DownloadCode(self, manifest, current=True):
        cmd = "repo init -u ssh://%s:%s/%s \
              --repo-url ssh://%s:%s/git/android/tools/repo \
              --repo-branch %s \
              --no-repo-verify \
              -q -b %s -m %s \
              --reference /home/mirror" % (self.gerrit_host,
                                           self.gerrit_port,
                                           self.manifest_git,
                                           self.gerrit_host,
                                           self.gerrit_port,
                                           self.repo_branch,
                                           self.manifest_branch,
                                           manifest)
        print cmd
        status, output = commands.getstatusoutput(cmd)
        if status != 0:
            print "init error"
            return 1
        cmd = "repo sync -j16 -q --force-sync --no-tags"
        if current: cmd += " -c "
        status, output = commands.getstatusoutput(cmd)
        if status != 0:
            print "sync error"
            return 1

    def ProjectLists(self,manifest):
        try:
            tree = xml.dom.minidom.parse(manifest)
        except Exception as e:
            return 1
        projects_L = []
        l_manifest = tree.documentElement
        l_project_list = l_manifest.getElementsByTagName("project")
        for pro in l_project_list:
            project_name = pro.getAttribute("name")
            projects_L.append(project_name)
        return projects_L

    def GetProjectPathDis(self,manifest):
        try:
            tree = xml.dom.minidom.parse(manifest)
        except Exception as e:
            return 1
        project_path_dis = {}
        l_manifest = tree.documentElement
        l_project_list = l_manifest.getElementsByTagName("project")
        for pro in l_project_list:
            project_name = pro.getAttribute("name")
            project_path = pro.getAttribute("path")
            if not project_path:
                project_path = project_name
            project_path_dis[project_name] = project_path
        return project_path_dis

    def MakeRebase(self,manifest,upgrade_and_qcom_project_list,rebase_branch):
        try:
            tree = xml.dom.minidom.parse(manifest)
        except Exception as e:
            return 1
        l_manifest = tree.documentElement
        l_project_list = l_manifest.getElementsByTagName("project")
        default_info = l_manifest.getElementsByTagName("default")
        default_remote = default_info[0].getAttribute("remote")
        default_revision = default_info[0].getAttribute("revision")
        print "default_remote:",default_remote
        print "default_revision:", default_revision
        rebase_success_l = []
        rebase_faile_l = []
        for pro in l_project_list:
            project_name = pro.getAttribute("name")
            if project_name in upgrade_and_qcom_project_list:
                project_path = pro.getAttribute("path")
                if not project_path:
                    project_path = project_name
                os.chdir(project_path)
                updatecmd = "git fetch %s %s --quiet --no-tags" % (default_remote, rebase_branch)
                os.system(updatecmd)
                rebasecmd = "git rebase %s/%s" % (default_remote, rebase_branch)
                status,output = commands.getstatusoutput(rebasecmd)
                if status == 0:
                    print "\nrebase successful: ",project_name
                    cmd = "git push -f zsgit HEAD:%s" % default_revision
                    os.system(cmd)
                    rebase_success_l.append(project_name)
                else:
                    print "\nrebase failed: ",project_name
                    cmd = "git rebase --abort"
                    os.system(cmd)
                    rebase_faile_l.append("name:%s, path:%s" % (project_name,project_path))
                print output
                #print os.getcwd()
                os.chdir(self.local_workspace)
        print "\nrebase_success_l"
        for p in rebase_success_l:
            print "== ",p
        print "\nrebase_faile_l"
        for p in rebase_faile_l:
            print "** ",p

    def Execute(self):
        self.DownloadCode(self.upgrade_xml,current=False)
        local_upgrade_xml = os.path.join(".repo/manifests",self.upgrade_xml)
        local_qcom_xml = os.path.join(".repo/manifests",self.qcom_xml)
        upgrade_project_list = self.ProjectLists(local_upgrade_xml)
        qcom_project_list = self.ProjectLists(local_qcom_xml)
        a = set(upgrade_project_list)
        b = set(qcom_project_list)
        upgrade_and_qcom_project_list = list(a & b)
        self.MakeRebase(local_upgrade_xml, upgrade_and_qcom_project_list, self.rebase_branch)
        qcom_diff_upgrade_project_list = list(b - a)
        print "\nnew git"
        for p in qcom_diff_upgrade_project_list:
            print "++ ",p

def parseages():
    parser = optparse.OptionParser()
    parser.add_option("","--upgrade_xml",dest="upgrade_xml",help="")
    parser.add_option("","--qcom_xml",dest="qcom_xml",help="")
    parser.add_option("","--rebase_branch", dest="rebase_branch", help="")
    (option,args) = parser.parse_args()
    return (option,args)

def main():
    (option, args) = parseages()
    upgrade_xml = option.upgrade_xml.strip()
    qcom_xml = option.qcom_xml.strip()
    rebase_branch = option.rebase_branch.strip()
    up = UpgradeQcom(upgrade_xml,qcom_xml,rebase_branch)
    up.Execute()

if __name__ == "__main__":
    main()
