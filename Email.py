#!/usr/bin/python
# coding:utf-8
import sys
import os
curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)
import smtplib
import optparse
from email.mime.text import MIMEText
#from email.mime.multipart import MIMEMultipart

class email(object):
    def __init__(self, sender, receiver, CC, subject, content, host='172.16.2.66', port='25', user='zhangwanliang',
                 password='Email_123450'):
        self.sender = sender
        self.receiver = receiver
        self.CC = CC
        self.subject = subject
        self.content = content
        self.host = host
        self.port = port
        self.user = user
        self.password = password

    def SendMail(self):
        msg = self.GetMsg()
        try:
  	    receiver=self.receiver + ',' +  self.CC
            receiver=receiver.split(',')
            #receiver 是真正的接收邮件，是物理的连接；这些邮件的分类显示则是在message里控制，message里的都是控制显示的格式而已
            smtp = smtplib.SMTP()
            smtp.connect(self.host, self.port)
            smtp.login(self.user, self.password)
            smtp.sendmail(self.sender, receiver, msg.as_string())
            print "邮件发送成功"
        except smtplib.SMTPException:
            print "Error: 无法发送邮件"

    def GetMsg(self):
        message = MIMEText(self.content,'html','utf-8')
        message['From'] = self.sender
        if len(self.receiver.split(','))>1:
	    message['To'] = ','.join(self.receiver.split(','))
	else:
	    message['To'] = self.receiver
   
        if len(self.CC.split(','))>1:
            message['CC'] = ','.join(self.CC.split(','))
 	else:
	    message['CC'] = self.CC
        message['Subject'] = self.subject

        ''''#text = "Hi!\nHow are you?\nHere is the link you wanted:\nhttps://www.python.org"
        html = """\
        <html>
          <head></head>
          <body>
            <p>Hi!<br>
               How are you?<br>
               Here is the <a href="https://www.python.org">link</a> you wanted.
            </p>
          </body>
        </html>
        """
        part1 = MIMEText(text, 'plain')
        part2 = MIMEText(html, 'html')

        message.attach(part1)
        message.attach(part2)'''
        return message

def parseargs():
    parser = optparse.OptionParser()

    ota_option_group = optparse.OptionGroup(parser, "email options")
    ota_option_group.add_option("-s", "--sender", dest="sender",
                                help="email sender", default="zhangwanliang@yulong.com")
    ota_option_group.add_option("-r", "--receiver", dest="receiver",
                                help="email receiver", default="")
    ota_option_group.add_option("-c", "--cc", dest="CC",
                                help="CC", default="")
    ota_option_group.add_option("-j", "--subject", dest="subject",
                                help="email subject", default="")
    ota_option_group.add_option("-t", "--content", dest="content",
                                help="email content", default="")
    (options, args) = parser.parse_args()
    return (options, args)


if __name__ == "__main__":
    (options, args) = parseargs()
    sender = options.sender.strip()
    receiver = options.receiver.strip()
    CC = options.CC.strip()
    subject = options.subject.strip()
    content = options.content.strip()
    print 'receiver:',receiver
    print 'CC      :',CC
    '''
    sender = 'zhangwanliang@yulong.com'
    receiver = 'zhangwanliang@yulong.com'
    CC = 'zhangwanliang@yulong.com'
    subject = '这是一个测试'
    content = '周瑶:&nbsp&nbsp&nbsp请将这个upc部署到<font color=red size=5><b>预测试服务器</b></font>'
    '''
    em = email(sender, receiver, CC, subject, content)
    em.SendMail()

