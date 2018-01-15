#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import datetime
import shutil
import commands
import operator
import re
import pprint

# 这里import aais 脚本里面的一些方法
from aais.log import Log
from aais.utils import Utils
from aais.sendmail import SendMail
from aais.html import *

GERRIT_LOG_PATH="/work/gerrit2/review_site/logs"
GERRIT_IP="gerrit.zeusis.com"
SQL_ACCOUNT = """\\"
    select
        account_external_ids.external_id,
        accounts.preferred_email,
        accounts.full_name
    from
        account_external_ids,accounts
    where
        account_external_ids.account_id = accounts.account_id and
        (%s)
        ;
   \\"
   """

WIKI_HTML_PRE="""
<pre>
统计上百次的同学使用用命令检查一下：

find 代码目录的路径 -name ".repo" -type d -exec bash -c 'src="{}"; echo =$src/manifests.git=; git -C "$src/manifests.git" remote -v ' \;

例如:

    查找/work/bright路径下面的:
find /work/bright -name ".repo" -type d -exec bash -c 'src="{}"; echo =$src/manifests.git=; git -C "$src/manifests.git" remote -v ' \;

    查找当前路径下面的:
find . -name ".repo" -type d -exec bash -c 'src="{}"; echo =$src/manifests.git=; git -C "$src/manifests.git" remote -v ' \;


请切换下代码地址

请参考这个配置，01.02 上海/深圳/西安gerrit读写分离的一些配置
http://wiki.zeusis.com/pages/viewpage.action?pageId=45121572

更改下代码url
方法1
使用repo下载代码更改方法
编辑这个文件 .repo/manifests.git/config   把其中的url = ssh://gerrit.zeusis.com相对应的行改为各个地域的url地址。
一个简便的方法，在源码顶层目录用命令的方式更改：
sed -i s/gerrit.zeusis.com/gerrit-sh.zeusis.com/g .repo/manifests.git/config   这个是改为上海的gerrit去下代码
sed -i s/gerrit.zeusis.com/gerrit-xi.zeusis.com/g .repo/manifests.git/config   这个是改为西安的gerrit去下代码
sed -i s/gerrit.zeusis.com/gerrit-sz.zeusis.com/g .repo/manifests.git/config   这个是改为深圳的gerrit去下代码


</pre>
"""

def main():
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    date_format = "%Y-%m-%d"  # date to string format
    #sshd_log.2017 - 03 - 19. gz
    ssh_log_file_name = "sshd_log.%s.gz" % (yesterday.strftime(date_format))
    ssh_log_file = os.path.join(GERRIT_LOG_PATH, ssh_log_file_name)
    if os.path.isfile(ssh_log_file):
        shutil.copy(ssh_log_file, ssh_log_file_name)
        os.system("gzip -df %s" % (ssh_log_file_name))

    ssh_log_file_name = "sshd_log.%s" % (yesterday.strftime(date_format))
    ssh_log_file = os.path.join(GERRIT_LOG_PATH, ssh_log_file_name)
    if os.path.isfile(ssh_log_file):
        shutil.copy(ssh_log_file, ssh_log_file_name)

    account_D = {}
    ssh_log_file_name = "sshd_log.%s" % (yesterday.strftime(date_format))
    if os.path.isfile(ssh_log_file_name):
        with open(ssh_log_file_name, "r") as fd:
            for line in fd:
                if "git-upload-pack" in line:
                    temp_L = line.split(" ")
                    account = temp_L[4]
                    if account_D.has_key(account):
                        account_D[account] += 1
                    else:
                        account_D.setdefault(account, 1)
    account_L = sorted(account_D.items(), key=operator.itemgetter(1), reverse=True)

    sql = ""
    for (account, download) in account_L:
        if download >= 50:
            sql += "account_external_ids.external_id = 'username:%s' or " % (account)
    sql += " 2=1 "
    sql = SQL_ACCOUNT % (sql)
    cmd = "ssh -p 29418 %s gerrit gsql -c \"  %s   \"  " % (GERRIT_IP, sql)
    status, output = commands.getstatusoutput(cmd)
    email_L = []
    username_D = {}
    for line in output.splitlines():
        if "username:" in line:
            temp_L = line.split("|")
            email_L.append(temp_L[1].strip())
            username = temp_L[0].split(":")[1].strip()
            if username_D.has_key(username):
                username_D[username] = temp_L[2].strip()
            else:
                username_D.setdefault(username, temp_L[2].strip())
    table = """
    <tr>
        <th width=\"10%\">gerrit全名</th>
        <th width=\"10%\">gerrit账号</th>
        <th width=\"5%\">下载次数统计</th>
    </tr>
    """
    for (account, download) in account_L:
        if download >= 50:
            table += "<tr><td width=\"5%%\">%s</td><td width=\"5%%\">%s</td><td width=\"5%%\">%s</td></tr>" % (username_D.get(account, ""), account, download)

    subject = "[Gerrit][success][%s] 下代码人员统计" % (yesterday.strftime(date_format))
    body = WIKI_HTML_PRE
    body += """
    <br/>
    <table table width=\"40%%\" class=\"altrowstable\" border=\"1\">
        %s
    </table>
    <br/>
    """ % table

    html = HTML % (TABLE_CSS_STYLE, body)
    sm = SendMail()
    to = ["bright.ma@coolpad.com"]
    assigner = os.environ.get("ASSIGNER", "scm@coolpad.com").strip().split(",")
    to.extend(assigner)
    to.extend(email_L)
    Log.Info("will send email to: %s" % to)
    sm.SendHtmlMail(to, subject, html)

    return

if __name__ == "__main__" :
    # need flush print
    sys.stdout = sys.stderr
    main()
