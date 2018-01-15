#!/usr/bin/env python
# -*- coding: utf-8 -*-
#   使用这个脚本来给 员工使用的服务
#    1.添加新的帐号，
#    2.删除帐号
#    3.锁定帐号
#    4.解锁帐号
#    5.重置员工帐号登录密码
#    6.更新员工账号中的commment字典，主要是存放个邮件，方便发邮件通知
#export PYTHONPATH=aais  执行的时候需要先这样一下，才可以使用aais里面的库
#
import os
import sys
import stat
import optparse
import pwd
import traceback
import commands
import datetime

# 这里import aais 脚本里面的一些方法
from aais.log import Log
from aais.utils import Utils
from aais.sendmail import SendMail
from aais.html import *

class ManageUserException(Exception):
    pass

class Type(object):
    ADDUSER = "AddUser"
    DELUSER = "DelUser"
    LOCKUSER = "LockUser"
    UNLOCKUSER = "UnLockUser"
    RESETPW = "ResetPasswd"
    UPDATEUSER = "UpdateUser"

class ManageUser(object):
    def __init__(self, build_type, username, assigner):
        self.build_type = build_type

        self.assigner = assigner

        self.SetUsername(username)

        self.dryrun = True
        self.SetDryRun()

        self.default_mail_list = ["huxiaoqin1@yulong.com",
                                  "yangyong1@yulong.com"]

    def SetUsername(self, username):
        # logingname:email, logingname2: email2, loginname3: email3
        temp_L = [(temp.strip().split(":")[0].strip(), temp.strip().split(":")[1].strip()) if ":" in temp else (temp.strip().split(":")[0].strip(), "")
                      for temp in username.split(",")]
        self.username = temp_L

    def SetDryRun(self, dryrun=""):
        dryrun = os.environ.get("DRY_RUN", "").strip()
        self.dryrun =  True if dryrun == "true" else False

    def GetAllUser(self):
        all_L = pwd.getpwall()
        return all_L

    def GetAllUserName(self):
        all_L = pwd.getpwall()
        return [user[0] for user in all_L]

    def GetComment(self, name):
        comment = pwd.getpwnam(name)[4]
        return comment

    def GetAllNormalUserName(self):
        all_L = pwd.getpwall()
        # 把 buildfarm user 过滤掉
        return [user[0] for user in all_L if user[2] > 1000 and user[0] != "buildfarm" and user[0] != "user"]

    def GetWikiHtml(self):
        status ,output = commands.getstatusoutput("hostname -I")
        ip = ""
        if status == 0:
            ip = output

        pre = """
        帐号都是自己的中文名拼音带数字，ex：yangyong1。
        初始密码都是 123456
        IP是：%s
        HostName是：%s

        请使用 ssh username@IP 这样的方式登录服务器。服务器不支持图形化界面的！
        smb密码也是 123456,windows系统登录smb 使用 \\\\IP\username 这样的方式来登录（不是\\\\IP\home\username）。

        下面列了几个需要特别注意的

        注意 repo init  的时候 加上必须的
            --reference   /home/zeusis-mirror （手机的zl1项目用这个，乐视的项目使用这个）
            --reference   /home/mirror (其他项目用这个)
            加上这个--reference会节省硬盘空间，同时下载代码速度加快。
            另外repo sync时候请使用repo sync -cdj 4 --no-tags


        注意  如果使用了ccache
              # Use ccache default
                export USE_CCACHE=1
                export CCACHE_DIR=${CCACHE_DIR:-${PWD}/.ccache}
            这个CCACHE_DIR的路径一定要是/work/下面的（ /work 这个路径上的空间大，读写速度也快！！！），
            一般用${PWD}/.ccache就可以了。编译建议使用./make_letv.sh或者./build.sh这个脚本。自己单独设置了要注意了。


        注意/tmp目录的使用
            我们直接把内存的一半作为了/tmp目录，这样会加快文件的访问速度的。需要注意的是，自己在这个下面创建的文件要及时的删除。

        注意  /work 目录的使用
            大家把代码放到这个目录下面，可以在这个目录下面再建立自己喜欢的子目录，然后代码下入其中。

        注意 文档 里面有个.ssh/config  里面要配置的。
            访问gerrit的时候，由于登录vm本机的用户名和gerrit上面的用户名不一致。

            请参考01.02 软件VM 配置&Gerrit登入 http://wiki.ccdomain.com:/pages/viewpage.action?pageId=360920

            关于乐视的gerrit：
            请参考01.06.02 乐视gerrit配置http://wiki.ccdomain.com:/pages/viewpage.action?pageId=6717569

        注意 repo相关的使用
            repo sync 的使用，-j后面不要大于4.
            repo sync -cdj 4 --no-tags 推荐使用这个命令
            repo sync -cdj 4 --no-tags platform/build  只更新platform/build这个仓库。
            repo sync -cdj 4 --no-tags  kernel/msm-3.18 只更新kernel仓库。

            只下载android 仓库 在repo init命令后面加上  -g all,-zs_amss  。这里的减号 -zs_amss 就是排除下载amss的代码
             只下载amss的代码在repo init命令后面加上  -g zs_amss,zs_common 。
             android和amss都下载就不要加-g参数了。

        注意.更改下代码url
            方法1
                使用repo下载代码更改方法
                编辑这个文件 .repo/manifests.git/config   把其中的url = ssh://gerrit.ccdomain.com相对应的行改为各个地域的url地址。
                一个简便的方法，在源码顶层目录用命令的方式更改：
                sed -i s/gerrit.ccdomain.com/gerrit.ccdomain.com/g .repo/manifests.git/config   这个是改为上海的从gerrit去下代码
                sed -i s/gerrit.ccdomain.com/gerrit-xi.ccdomain.com/g .repo/manifests.git/config   这个是改为 西安的从gerrit去下代码
                sed -i s/gerrit.ccdomain.com/gerrit-sz.ccdomain.com/g .repo/manifests.git/config   这个是改为深圳的从gerrit去下代码

            方法2
                如果之前已经下载了代码，请把repo init命令修改后重新执行。然后repo sync -cdj4 --no-tags
                repo init -u ssh://gerrit.ccdomain.com:29418/git/android/platform/manifest --repo-url ssh://gerrit.ccdomain.com:29418/git/android/tools/repo --repo-branch stable --no-repo-verify -q -b zs_master -m zeusis/ZSUI_MSM8953_APK_20161109.xml --reference /home/mirror
                替换为
                repo init -u ssh://gerrit.ccdomain.com:29418/git/android/platform/manifest --repo-url ssh://gerrit.ccdomain.com:29418/git/android/tools/repo --repo-branch stable --no-repo-verify -q -b zs_master -m zeusis/ZSUI_MSM8953_APK_20161109.xml --reference /home/mirror
                请把repo init命令修改后重新执行。然后repo sync -cdj4 --no-tags

        注意.work下面代码最好3,4 套代码，基本上控制在500GB以内
            首先使用  repo init -u ssh://gerrit-sz.ccdomain.com:29418/git/android/platform/manifest
            --repo-url ssh://gerrit-sz.ccdomain.com:29418/git/android/tools/repo --repo-branch stable --no-repo-verify -q -b zs_master
            -m zeusis/ZSUI_MSM8953_APK_20161109.xml --reference /home/mirror
            这个时候已经是ZSUI_MSM8953_APK_20161109这个分支了，

            怎么切换分支？？？就是把-m后面的参数换了，然后在代码顶层目录重新执行repo init，然后repo sync，这样就切换分支了。这样可以少下载几套代码。

            如下使用这个命令就会切换到ODM_DEBUG_20170306.xml这个分支上面
            repo init -u ssh://gerrit-sz.ccdomain.com:29418/git/android/platform/manifest -b zs_master -m zeusis/ODM_DEBUG_20170306.xml --repo-url ssh://gerrit-sz.ccdomain.com:29418/git/android/tools/repo --repo-branch stable --no-repo-verify --reference /home/mirror

        有问题vm小群里提问，不要在大群里。。。。
        """ % (ip, os.environ.get("NODE", ""))




        pre = BUILD_PRE % (pre) #最后拼接到 html <pre>标签里面
        return pre

    def SendPassMail(self, subject=""):
        subject = "[%s][success][%s] %s" % (self.build_type, os.environ.get("NODE", ""), datetime.datetime.now())
        body = ""
        body += self.GetBuildEnvHtml()
        html = HTML % (TABLE_CSS_STYLE, body)
        to = []
        to.extend(self.default_mail_list)
        to.extend(self.assigner.split(","))
        sm = SendMail()
        sm.SendHtmlMail(to, subject, html)

    def SendFailMail(self, subject=""):
        subject = "[%s][fail][%s] %s %s" % (self.build_type, os.environ.get("NODE", ""), subject, datetime.datetime.now())
        body = ""
        body += self.GetBuildEnvHtml()
        html = HTML % (TABLE_CSS_STYLE, body)
        to = []
        to.extend(self.default_mail_list)
        to.extend(self.assigner.split(","))
        sm = SendMail()
        sm.SendHtmlMail(to, subject, html)

    def GetBuildEnvHtml(self):
        key = "BUILD_URL"
        url = os.environ.get(key, "")
        table_tr = BUILD_TABLE_TH % ("Build Environemnt")
        table_tr += BUILD_TABLE_TR % ("build type", os.environ.get("BUILD_TYPE", ""))
        url_a = BUILD_TABLE_A % (url, url)
        table_tr += BUILD_TABLE_TR % ("build url", url_a)
        url_a = BUILD_TABLE_A % ("%sconsole" % url, "%sconsole" % url)
        table_tr += BUILD_TABLE_TR % ("console output", url_a)

        table_tr += BUILD_TABLE_TR % ("server hostname", os.environ.get("NODE", ""))
        table_tr += BUILD_TABLE_TR % ("user name", os.environ.get("NEW_USERNAME", ""))

        table_tr += BUILD_TABLE_TR % ("assigner", os.environ.get("ASSIGNER", ""))
        table_tr += BUILD_TABLE_TR % ("dry run or not", os.environ.get("DRY_RUN", ""))
        table = BUILD_TABLE_BODY % (table_tr)
        return table

class UnLockUser(ManageUser):
    def __init__(self, build_type, username, assigner):
        super(UnLockUser, self).__init__(build_type, username, assigner)

    def Execute(self):
        try:
            for (account, email) in self.username:
                Log.Blue("\n===============================================================\n")
                if account not in self.GetAllNormalUserName() or email not in self.GetComment(account):
                    Log.Error("%s is not exists" % (account))
                    raise ManageUserException("%s not exists" % account)
                cmd = "sudo bash -c \"usermod -U %s\"" % (account)
                Log.Info("unlock user cmd: [%s]" % cmd)
                if not self.dryrun and os.system(cmd) != 0: raise ManageUserException("unlock user fail")
            Log.Info("will send pass mail")
            self.SendPassMail()
        except Exception as e:
            Log.Error("unlock user fail: %s, will send fail  mail" % e)
            traceback.print_exc()
            self.SendFailMail("%s" % (e))
            return 1
        return 0

class LockUser(ManageUser):
    def __init__(self, build_type, username, assigner):
        super(LockUser, self).__init__(build_type, username, assigner)

    def Execute(self):
        try:
            for (account, email) in self.username:
                Log.Blue("\n===============================================================\n")
                if account not in self.GetAllNormalUserName() or email not in self.GetComment(account):
                    Log.Error("%s is not exists" % (account))
                    raise ManageUserException("%s not exists" % account)
                cmd = "sudo bash -c \"usermod -L %s\"" % (account)
                Log.Info("lock user cmd: [%s]" % cmd)
                if not self.dryrun and os.system(cmd) != 0: raise ManageUserException("lock user fail")
            Log.Info("will send pass mail")
            self.SendPassMail()
        except Exception as e:
            Log.Error("lock user fail: %s, will send fail mail" % e)
            traceback.print_exc()
            self.SendFailMail("%s" % (e))
            return 1
        return 0

class UpdateUser(ManageUser):
    def __init__(self, build_type, username, assigner):
        super(UpdateUser, self).__init__(build_type, username, assigner)

    def Execute(self):
        try:
            for (account, email) in self.username:
                # 这里的account 就是 登陆时候的账号，email就是这个员工的邮箱地址
                Log.Blue("\n===============================================================\n")
                if not self.dryrun: self.default_mail_list.append(email)
                cmd = "sudo bash -c \"usermod -c %s %s\"" % (email, account)
                Log.Info("lock user cmd: [%s]" % cmd)
                if not self.dryrun and os.system(cmd) != 0: raise ManageUserException("update user comment fail")
            Log.Info("will send pass mail")
            self.SendPassMail()
        except Exception as e:
            Log.Error("update user comment fail: %s, will send fail mail" % e)
            traceback.print_exc()
            self.SendFailMail("%s" % (e))
            return 1

        return 0



class DelUser(ManageUser):
    def __init__(self, build_type, username, assigner):
        super(DelUser, self).__init__(build_type, username, assigner)

    def Execute(self):
        try:
            default_work = "/work"
            for (account, email) in self.username:
                Log.Blue("\n===============================================================\n")
                if account not in self.GetAllNormalUserName() or email not in self.GetComment(account):
                    Log.Error("%s is not exists" % (account))
                    raise ManageUserException("%s not exists" % account)
                cmd = "sudo bash -c \"userdel -r %s\"" % (account)
                Log.Info("delete user cmd: [%s]" % cmd)
                if not self.dryrun and os.system(cmd) != 0: raise ManageUserException("delete user fail")
                cmd = "sudo bash -c \"rm -rf %s\"" % (os.path.join(default_work, account))
                Log.Info("delete user work dir cmd: [%s]" % cmd)
                if not self.dryrun and os.system(cmd) != 0: raise ManageUserException("delete user work folder fail")
            Log.Info("will send pass mail")
            self.SendPassMail()
        except Exception as e:
            Log.Error("delete user fail: %s, will send fail mail" % e)
            traceback.print_exc()
            self.SendFailMail("%s" % (e))
            return 1
        return 0

class ResetPasswd(ManageUser):
    def __init__(self, build_type, username, assigner):
        super(ResetPasswd, self).__init__(build_type, username, assigner)
        self.success_mail_list = []

    def GetBuildEnvHtml(self):
        table_tr = BUILD_TABLE_TH % ("[%s] success list, 不在下面表格中的账号表示重置密码失败的!" % self.build_type)
        for index, success in enumerate(self.success_mail_list):
            table_tr += BUILD_TABLE_TR % (index+1, success)
        table = BUILD_TABLE_BODY % (table_tr)
        table += BR
        table += self.GetWikiHtml()
        table += BR
        table += super(ResetPasswd, self).GetBuildEnvHtml()
        return table

    def Execute(self):
        try:
            default_passwd = "123456"

            for (account, email) in self.username:
                Log.Blue("\n===============================================================\n")
                if not self.dryrun: self.default_mail_list.append(email)
                #判断一下这个帐号是不是已经存在了，存在就打印错误，继续下一个
                if account not in self.GetAllNormalUserName() or email not in self.GetComment(account):
                    # 判断是否在 用户列表中， 还要判断全名是否在这个用户的comment字段下面
                    Log.Error("%s not exists" % (account))
                    raise ManageUserException("%s not exists" % account)

                # 设置帐号密码
                cmd = "sudo bash -c \"echo -ne %s:%s | chpasswd\"" % (account, default_passwd)
                Log.Info("reset passwd cmd: [%s]" % cmd)
                if not self.dryrun and os.system(cmd) != 0:  raise ManageUserException("reset passwd fail")

                # 重置密码就要发邮件给 用户了
                self.success_mail_list.append(email)
            # end for结束遍历
            Log.Info("will send pass mail")
            self.SendPassMail()
        except Exception as e:
            Log.Error("reset passwd fail: %s, will send fail mail" % e)
            traceback.print_exc()
            self.SendFailMail("%s" % (e))
            return 1
        return 0

class AddUser(ManageUser):
    def __init__(self, build_type, username, assigner):
        super(AddUser, self).__init__(build_type, username, assigner)
        self.success_mail_list = []


    def GetBuildEnvHtml(self):
        table_tr = BUILD_TABLE_TH % ("[%s] success list, 不在下面表格中的账号是添加失败的!" % self.build_type)
        for index, success in enumerate(self.success_mail_list):
            table_tr += BUILD_TABLE_TR % (index+1, success)
        table = BUILD_TABLE_BODY % (table_tr)
        table += BR
        table += self.GetWikiHtml()
        table += BR
        table += super(AddUser, self).GetBuildEnvHtml()
        return table

    def Execute(self):
        try:
            default_passwd = "123456"
            default_work = "/work"

            for (account, email) in self.username:
                Log.Blue("\n===============================================================\n")
                if not self.dryrun: self.default_mail_list.append(email)
                #判断一下这个帐号是不是已经存在了，存在就打印错误，继续下一个
                all_username_L = self.GetAllUserName()
                if account in all_username_L:
                    Log.Error("%s is already exists" % (account))
                    raise ManageUserException("%s is already exists" % account)

                #add user
                cmd = "sudo bash -c \"useradd -m -s /bin/bash -c %s %s\" " % (email, account)
                Log.Info("adduser cmd: [%s]" % cmd)
                if not self.dryrun and os.system(cmd) != 0: raise ManageUserException("adduser fail")

                # 设置帐号密码
                cmd = "sudo bash -c \"echo -ne %s:%s | chpasswd\"" % (account, default_passwd)
                Log.Info("set passwd cmd: [%s]" % cmd)
                if not self.dryrun and os.system(cmd) != 0: raise ManageUserException("set passwd fail")

                # 设置smb的帐号密码
                cmd = "sudo bash -c 'echo -ne \"%s\\n%s\\n\" |smbpasswd -a -s %s'" % (default_passwd, default_passwd, account)
                Log.Info("set smb passwd cmd: [%s]" % cmd)
                if not self.dryrun and os.system(cmd) != 0: raise ManageUserException("set smb passwd fail")

                # 创建连接 work 文件
                user_work = os.path.join(default_work, account)
                link_work = "/home/%s/work" % (account)
                cmd = "sudo bash -c \"mkdir -p %s && chown %s:%s %s -R\"" % (user_work, account, account, user_work)
                Log.Info("create work path cmd: [%s]" % cmd)
                if not self.dryrun and os.system(cmd) != 0: raise ManageUserException("create user work path fail")

                # 创建连接 work的文件
                cmd = "sudo bash -c \"ln -s %s %s && chown %s:%s %s -h\"" % (user_work, link_work, account, account, link_work)
                Log.Info("create link work file cmd: [%s]" % cmd)
                if not self.dryrun and os.system(cmd) != 0: raise ManageUserException("create link work file fail")

                # 添加新的用户也是要发邮件给 用户了
                self.success_mail_list.append(email)
            # end for
            Log.Info("will send pass mail")
            self.SendPassMail()
        except Exception as e:
            Log.Error("adduser fail: %s, will send fail mail" % e)
            traceback.print_exc()
            self.SendFailMail("%s" % (e))
            return 1
        return 0

def parseargs():
    usage = "usage: %prog [options] arg1 arg2"
    parser = optparse.OptionParser(usage=usage)

    optiongroup = optparse.OptionGroup(parser, "common options")
    optiongroup.add_option("-t", "--type", dest="buildtype",
                                  help="build type [adduser, deluser, lockuser, unlockuser, resetpasswd， updateuser]", default="")
    parser.add_option_group(optiongroup)

    adduseroptiongroup = optparse.OptionGroup(parser, "add user options")
    adduseroptiongroup.add_option("-u", "--username-email", dest="username",
                                  help="user name and email", default="")
    adduseroptiongroup.add_option("-a", "--assigner", dest="assigner",
                                  help="assigner email address", default="")
    parser.add_option_group(adduseroptiongroup)
    (options, args) = parser.parse_args()

    return (options, args)

def main():
    (options, args) = parseargs()
    buildtype = options.buildtype.strip()
    username = options.username.strip().lower()
    assigner = options.assigner.strip()

    if buildtype == Type.ADDUSER:
        #add user
        add = AddUser(buildtype, username, assigner)
        ret = add.Execute()
    elif buildtype == Type.DELUSER:
        dele = DelUser(buildtype, username, assigner)
        ret = dele.Execute()
    elif buildtype == Type.LOCKUSER:
        lock = LockUser(buildtype, username, assigner)
        ret = lock.Execute()
    elif buildtype == Type.UNLOCKUSER:
        unlock = UnLockUser(buildtype, username, assigner)
        ret = unlock.Execute()
    elif buildtype == Type.RESETPW:
        reset = ResetPasswd(buildtype, username, assigner)
        ret = reset.Execute()
    elif buildtype == Type.UPDATEUSER:
        update = UpdateUser(buildtype, username, assigner)
        ret = update.Execute()
    else:
        Log.Error("invalid type %s " % buildtype)
        return 1

    return ret

if __name__ == "__main__" :
    # need flush print
    sys.stdout = sys.stderr
    main()
