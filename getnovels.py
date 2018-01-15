#!/usr/bin/python
# coding:utf-8
import pprint
import re
import os
import sys
import optparse
import commands
import shutil
import glob
import urllib2
import chardet

#http://www.5du5.net/book/0/570/

def HttpPost(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (X11; U; Linux i686)Gecko/20071127 Firefox/2.0.0.11'}
        req = urllib2.Request(url, headers=headers)
        response = urllib2.urlopen(url, timeout=100)  # 发送页面请求
        html = response.read()
        return html  # 获取服务器返回的页面信息
    except Exception, e:
        print str(e)
        return None

def main():
    root_url = "http://www.xxbiquge.com/0_547"
    root_html = HttpPost(root_url)
    alldd_html = re.findall(r"(<dd>.*</dd>)", root_html, re.S)  # 这里是返回一个列表了
    all_a_html = re.findall(r"<dd>(.*?)</dd>", alldd_html[0])


    for a in all_a_html:
        aurl = re.findall(r"<a href=\"(.*)\">(.*)</a>", a)
        #pprint.pprint(url)
        aurl = aurl[0]
        title = aurl[1]
        try:
            num = int(title[0:4])
            if num <= 5128:
                continue
        except ValueError:
            continue
        title = title[4:]
        print num, title

        #print url[0],url[1]
        root_url = "http://www.xxbiquge.com"
        suburl =  root_url + aurl[0]
        subhtml = HttpPost(suburl)
        content = re.findall(r"<div id=\"content\">(.*?)</div>", subhtml)
        if content:
            content = content[0]
            alltxt = "第%s章 %s\n" % (num,title)
            alltxt = """%s
%s
""" % (alltxt, content)
            with open("xiaohua.txt", "a") as fd:
                fd.write(alltxt)

if __name__ == "__main__":
    main()
