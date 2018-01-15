#!/usr/bin/python
# coding:utf-8

from jira import JIRA
import sys
import datetime

#搜单
def searchjira(project,buildtime):
    jira = JIRA('http://jira.ccdomain.com',basic_auth=('jira', 'jira@2017~!@'))
    sql = 'project="%s" and issuetype="缺陷" and status="组织测试" and updated <= "%s"' %(project,buildtime)
    jiraall = jira.search_issues(sql,maxResults=10000)
    jiralen = len(jiraall)
    jiralist = []
    for a in range(jiralen):
        jiralist.append(jiraall[a].key)
    print "There are %s jira founded totally " %(jiralen)
    print jiralist
    return jiralist

def searchjirareq(project,buildtime):
    jira = JIRA('http://jira.ccdomain.com:80/',basic_auth=('jira', 'jira@2017~!@'))
    sql = 'project="%s" and issuetype="软件需求" and status="组织测试" and updated <= "%s"' %(project,buildtime)
    jiraall = jira.search_issues(sql,maxResults=10000)
    jiralen = len(jiraall)
    jiralist = []
    for a in range(jiralen):
        jiralist.append(jiraall[a].key)
    print "There are %s jira founded totally " %(jiralen)
    print jiralist
    return jiralist

#跟releasenotes中得到的jira做比较，现在暂时不需要
def comparelist(project,buildtime,releasejira):
    jiralist_a = searchjira(project,buildtime)
    # releaenote 中得到的jira单
    jiralist_b = releasejira.split(" ")
    print "releasejira list is : %s" %(jiralist_b)
    jiralist = list(set(jiralist_a).intersection(set(jiralist_b)))
    print "The finally result is: %s " %(len(jiralist))
    print jiralist
    return jiralist

#判断jira单特性(开发，量产，送测...)
def judgelist(project,buildtime,judgement):
    jira = JIRA('http://jira.ccdomain.com',basic_auth=('jira', 'jira@2017~!@'))
    jiraall = searchjira(project,buildtime)
    jiralist = []
    loseversion = []
    for jirad in jiraall:
        issue = jira.issue(jirad)
        version = issue.fields.versions
        if len(version) == 0:
            loseversion.append(jirad)
        else:
            effversion = version[0].name
            if judgement in str(effversion):
                jiralist.append(jirad)

    jiradifference = list(set(jiraall).difference(set(jiralist)))
    print "Can't find effect version:"
    print loseversion
    print "The left is %s " %(len(jiradifference))
    print jiradifference
    print "The real lenth is %s ,these jira will flow to test" %(len(jiralist))
    print jiralist
    return jiralist

#转单
def changejira(project,buildtime,judgement,newversion,releasejira):
    jira = JIRA('http://jira.ccdomain.com',basic_auth=('jira', 'jira@2017~!@'))
    if releasejira == "":
        jiralist = judgelist(project,buildtime,judgement)
    else:
        jiralist = comparelist(project,buildtime,releasejira)
    jirareq_list= searchjirareq(project,buildtime)
    #创建version:
    curTime = datetime.date.today()
    curTime = curTime.strftime("%Y-%m-%d")
    try:
        jira.create_version(newversion,project,description="Pollux %s 版本转测试" %newversion,startDate=curTime)
    except BaseException:
        print "create version %s error,maybe it's existed" %(newversion)
    #将所有组织测试的单转成回归测试
    for a in jiralist:
        print "start to change bug %s to 回归测试" %(str(a))
        try:
            issue = jira.issue(a)
            #修改 jira 单中的修复版本：
            issue_dict = {
                'fixVersions':[{'name':newversion}]
            }
            issue.update(fields=issue_dict)
            #修改 jira 单状态：
            jira.transition_issue(issue,'191',comment="自动回归测试")
            #修改指向人
            newassign = str(issue.fields.reporter.name)
            jira.assign_issue(issue,newassign)
        except BaseException:
            print "change fail in %s" %(str(a))
    for b in jirareq_list:
        print "start to change req %s to 回归测试" %(str(b))
        try:
            issue = jira.issue(b)
            #修改 jira 单中的修复版本：
            issue_dict = {
                'fixVersions':[{'name':newversion}]
            }
            issue.update(fields=issue_dict)
            #修改 jira 单状态：
            jira.transition_issue(issue,'21',comment="需求自动回归测试")
        except BaseException:
            print "change fail in %s" %(str(b))

if __name__ == "__main__":
    #changejira("POL","2017-01-16 14:52","DP","PUXSCN000100DP003_2")
    changejira(sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5])
