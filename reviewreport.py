#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os
import sys
import commands

# 这里import aais 脚本里面的一些方法
from aais.log import Log
from aais.utils import Utils
from aais.sendmail import SendMail
from aais.html import *

COMMENTS_IN_INNER_SQL = """\\"
    SELECT
        patch_comments.line_nbr AS line_nbr,
        patch_comments.author_id AS author_id,
        patch_comments.written_on AS written_on,
        patch_comments.message AS message,
        patch_comments.change_id AS change_id,
        patch_comments.patch_set_id AS patch_set_id,
        patch_comments.file_name AS file_name,
        (SELECT accounts.full_name FROM accounts WHERE accounts.account_id = patch_comments.author_id) AS full_name,
        (SELECT accounts.preferred_email FROM accounts WHERE accounts.account_id = patch_comments.author_id) AS preferred_email,
        patch_sets.revision AS revision,
        patch_sets.created_on AS created_on,
        patch_sets.uploader_account_id AS uploader_account_id,
        patch_sets.change_id AS a_change_id,
        patch_sets.patch_set_id AS a_patch_set_id,
        (SELECT accounts.full_name FROM accounts WHERE accounts.account_id = patch_sets.uploader_account_id) AS uploader_full_name,
        (SELECT accounts.preferred_email FROM accounts WHERE accounts.account_id = patch_sets.uploader_account_id) AS uploader_preferred_email
    FROM
        (patch_comments JOIN patch_sets ON ((patch_comments.change_id = patch_sets.change_id) AND (patch_comments.patch_set_id = patch_sets.patch_set_id)))
    WHERE
        (
            (patch_comments.change_id IN (SELECT changes.change_id FROM changes WHERE (changes.status = 'M'))) AND
            patch_comments.written_on >='%s' AND
            patch_comments.written_on <'%s' AND
            patch_comments.message LIKE '%%%s%%'
        )
    ;

   \\"
   """

COMMENTS_IN_OUTBOX_SQL = """\\"
    SELECT
        change_messages.author_id AS author_id,
        change_messages.written_on AS written_on,
        change_messages.message AS message,
        change_messages.patchset_change_id AS patchset_change_id,
        change_messages.patchset_patch_set_id AS patchset_patch_set_id,
        change_messages.change_id AS change_id,
        change_messages.uuid AS UUID,
        (SELECT accounts.full_name FROM accounts WHERE accounts.account_id = change_messages.author_id) AS author_full_name,
        (SELECT accounts.preferred_email FROM accounts WHERE accounts.account_id = change_messages.author_id) AS author_preferred_email,
        patch_sets.revision AS revision,
        patch_sets.created_on AS created_on,
        patch_sets.uploader_account_id AS uploader_account_id,
        patch_sets.change_id AS a_change_id,
        patch_sets.patch_set_id AS a_patch_set_id,
        (SELECT accounts.full_name FROM accounts WHERE accounts.account_id = patch_sets.uploader_account_id) AS uploader_full_name,
        (SELECT accounts.preferred_email FROM accounts WHERE accounts.account_id = patch_sets.uploader_account_id) AS uploader_preferred_email
    FROM
        (change_messages JOIN patch_sets ON ((change_messages.change_id = patch_sets.change_id) AND (change_messages.patchset_patch_set_id = patch_sets.patch_set_id)))
    WHERE
        ((change_messages.change_id IN (SELECT changes.change_id FROM  changes WHERE (changes.status = 'M'))) AND
        change_messages.written_on >='%s' AND
        change_messages.written_on <'%s'  AND
        change_messages.message LIKE '%%%s%%')
    ;

   \\"
   """

CHANGE_REVIEW_SQL = """\\"
    SELECT
        patch_set_approvals.change_id AS change_id,
        patch_set_approvals.value AS review_value,
        patch_set_approvals.granted AS review_time,
        patch_set_approvals.patch_set_id AS patch_set_id,
        patch_set_approvals.account_id AS reviewer_account_id,
        (SELECT accounts.full_name FROM accounts WHERE accounts.account_id = patch_set_approvals.account_id) AS reviewer_name,
        (SELECT accounts.preferred_email FROM accounts WHERE accounts.account_id = patch_set_approvals.account_id) AS reviewer_email,
        patch_set_approvals.category_id AS category_id,
        changes.created_on AS change_createddate,
        changes.last_updated_on AS change_updatedate,
        changes.subject AS SUBJECT,
        changes.owner_account_id AS owner_account_id,
        (SELECT accounts.full_name FROM accounts WHERE accounts.account_id = changes.owner_account_id) AS change_auther_name,
        (SELECT accounts.preferred_email FROM accounts WHERE accounts.account_id = changes.owner_account_id) AS change_auther_email,
        changes.dest_branch_name AS dest_branch_name,
        changes.current_patch_set_id AS change_patch_sets,
        changes.status AS STATUS
    FROM
        (patch_set_approvals JOIN changes ON ((patch_set_approvals.change_id = changes.change_id)))
    WHERE
        changes.status = 'M' AND
        changes.created_on >='%s' AND
        changes.created_on <'%s'  AND
        patch_set_approvals.category_id LIKE '%%%s%%'
    ;

   \\"
   """

def save_to_file(status, output, output_file):
    if status == 0:
        line_L = output.splitlines()
        new_line_L = []
        for line in line_L:
            temp_L = line.split("|")
            temp_L = [w.strip() for w in temp_L]
            newline = " | ".join(temp_L)
            new_line_L.append("%s\n" % newline)
        with open(output_file, "w") as fd:
            fd.writelines(new_line_L)
    else:
        print status, output


def get_build_environment_html():
    key = "BUILD_URL"
    url = os.environ.get(key, "")
    table_tr = BUILD_TABLE_TH % ("Build Environemnt")

    url_a = BUILD_TABLE_A % (url, url)
    table_tr += BUILD_TABLE_TR % ("build url", url_a)
    url_a = BUILD_TABLE_A % ("%sconsole" % url, "%sconsole" % url)
    table_tr += BUILD_TABLE_TR % ("console output", url_a)
    table_tr += BUILD_TABLE_TR % ("GERRIT_IP", os.environ.get("GERRIT_IP", ""))
    table_tr += BUILD_TABLE_TR % ("view name", os.environ.get("SQL_TYPE", ""))
    table_tr += BUILD_TABLE_TR % ("start date", os.environ.get("SQL_START_DATE", ""))
    table_tr += BUILD_TABLE_TR % ("end date", os.environ.get("SQL_END_DATE", ""))
    table_tr += BUILD_TABLE_TR % ("message_or_category", os.environ.get("SQL_MESSAGE_OR_CATEGORY", ""))
    table_tr += BUILD_TABLE_TR % ("assigner", os.environ.get("ASSIGNER", ""))
    table = BUILD_TABLE_BODY % (table_tr)
    return table

def sendmail(assigner, subject="", attach_file=""):
    subject = "[ReviewReport][success] %s" % (subject)
    body = ""
    body += get_build_environment_html()
    html = HTML % (TABLE_CSS_STYLE, body)
    to = []
    to.extend(assigner.split(","))
    sm = SendMail()
    sm.SendHtmlMailWithAttach(to, subject, html, attach_file)



def main():
    gerrit_ip = os.environ.get("GERRIT_IP", "10.0.12.62")
    sql_type = os.environ.get("SQL_TYPE", "")
    assigner = os.environ.get("ASSIGNER", "")
    if sql_type == "comments_in_inner":
        start_date =  os.environ.get("SQL_START_DATE","")
        end_date =  os.environ.get("SQL_END_DATE","")
        messagelike = os.environ.get("SQL_MESSAGE_OR_CATEGORY","")
        comments_in_inner_sql = COMMENTS_IN_INNER_SQL % (start_date, end_date, messagelike)
        cmd = "ssh -p 29418 %s gerrit gsql -c \"  %s   \"  " % (gerrit_ip, comments_in_inner_sql)
        status, output = commands.getstatusoutput(cmd)

        output_file = "%s.txt" % (sql_type)
        outputzip_file = "%s.zip" % (sql_type)

        save_to_file(status, output, output_file)
        os.system("zip -r %s %s" % (outputzip_file, output_file))

        sendmail(assigner, sql_type, outputzip_file)
    elif sql_type == "comments_in_outbox":
        start_date =  os.environ.get("SQL_START_DATE","")
        end_date =  os.environ.get("SQL_END_DATE","")
        messagelike = os.environ.get("SQL_MESSAGE_OR_CATEGORY","")
        comments_outbox_sql = COMMENTS_IN_OUTBOX_SQL % (start_date, end_date, messagelike)
        cmd = "ssh -p 29418 %s gerrit gsql -c \"  %s   \"  " % (gerrit_ip, comments_outbox_sql)
        status, output = commands.getstatusoutput(cmd)
        output_file = "%s.txt" % (sql_type)
        outputzip_file = "%s.zip" % (sql_type)

        save_to_file(status, output, output_file)
        os.system("zip -r %s %s" % (outputzip_file, output_file))

        sendmail(assigner, sql_type, outputzip_file)
    elif sql_type == "change_review":
        start_date =  os.environ.get("SQL_START_DATE", "")
        end_date =  os.environ.get("SQL_END_DATE", "")
        category_id = os.environ.get("SQL_MESSAGE_OR_CATEGORY", "")
        change_review = CHANGE_REVIEW_SQL % (start_date, end_date, category_id)
        cmd = "ssh -p 29418 %s gerrit gsql -c \"  %s   \"  " % (gerrit_ip, change_review)
        status, output = commands.getstatusoutput(cmd)
        output_file = "%s.txt" % (sql_type)
        outputzip_file = "%s.zip" % (sql_type)

        save_to_file(status, output, output_file)
        os.system("zip -r %s %s" % (outputzip_file, output_file))

        sendmail(assigner, sql_type, outputzip_file)
    return 0



if __name__ == "__main__" :
    # need flush print
    sys.stdout = sys.stderr
    main()
