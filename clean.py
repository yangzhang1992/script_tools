#!/usr/bin/python
# coding:utf-8

from __future__ import print_function


import os
import sys
import shutil
import glob
import pprint
import commands
import re
import datetime
import traceback
import zipfile
import platform
import time

BASE_DAY_AGO = 30 # 默认30天，这里可以调整
DATE_FORMAT = "%Y-%m-%d"  # date to string format
# 下面的几个目录文件是不需要压缩的
BLACKFILE_L = ["build.prop", "symbols_system.zip", "Bins", "debug.zip", "qfil.zip", "cust.zip"]

LOCAL = os.environ.get("AAIS_FILE_SERVER_LOCAL", "").strip()
if  platform.system() == "Linux":
    DAILYBUILD_BASE_PATTERN = "/dailybuild/android/%s/*"
    DAILYBUILD_BASE_DIR = "/dailybuild/android/"
    if LOCAL == "XI":
        DAILYBUILD_BASE_PATTERN = "/dailybuild-xi/android/%s/*"
        DAILYBUILD_BASE_DIR = "/dailybuild-xi/android/"
    if LOCAL == "SZ":
        DAILYBUILD_BASE_PATTERN = "/dailybuild-sz/android/%s/*"
        DAILYBUILD_BASE_DIR = "/dailybuild-sz/android/"
    if LOCAL == "NJ":
        DAILYBUILD_BASE_PATTERN = "/dailybuild-nj/android/%s/*"
        DAILYBUILD_BASE_DIR = "/dailybuild-nj/android/"
elif platform.system() == "Windows":
    # 如果是在 windows 运行就使用这个base路径
    DAILYBUILD_BASE_PATTERN = "D:\\dailybuild\\android\\%s\\*"
    DAILYBUILD_BASE_DIR = "D:\\dailybuild\\android"
    if LOCAL == "XI":
        DAILYBUILD_BASE_PATTERN = "D:\\dailybuild-xi\\android\\%s\\*"
        DAILYBUILD_BASE_DIR = "D:\\dailybuild-xi\\android"
    if LOCAL == "SZ":
        DAILYBUILD_BASE_PATTERN = "D:\\dailybuild-sz\\android\\%s\\*"
        DAILYBUILD_BASE_DIR = "D:\\dailybuild-sz\\android"
    if LOCAL == "NJ":
        DAILYBUILD_BASE_PATTERN = "D:\\dailybuild-nj\\android\\%s\\*"
        DAILYBUILD_BASE_DIR = "D:\\dailybuild-nj\\android"

def delete_path_or_file(pathorfile):
    retry = 0
    while True:
        try:
            if os.path.isdir(pathorfile):
                shutil.rmtree(pathorfile)
                return
            else:
                os.remove(pathorfile)
                return
        except OSError as e:
            try:
                os.chmod(pathorfile, 644)
            except OSError as ee:
                pass
        retry += 1
        time.sleep(2)
        if retry > 10:return

def make_zip(dirname, dstfile, deletesrc=False):
    dstfile = os.path.abspath(dstfile)
    filelist = []
    subdir_L = os.listdir(dirname)
    for subdir in subdir_L:
        if subdir in BLACKFILE_L:
            continue
        newpath = os.path.join(dirname, subdir)
        if os.path.isfile(newpath):
            filelist.append(newpath)
        else:
            for root, dirs, files in os.walk(newpath):
                for name in files:
                    filelist.append(os.path.join(root, name))

    if not os.path.exists(os.path.dirname(dstfile)):
        os.makedirs(os.path.dirname(dstfile))

    zf = zipfile.ZipFile(dstfile, "w", zipfile.ZIP_DEFLATED, True)
    for tar in filelist:
        if tar == dstfile:
            continue
        arcname = tar[len(dirname):]
        zf.write(tar, arcname)
    zf.close()
    if deletesrc:
        for subdir in subdir_L:
            if subdir in BLACKFILE_L:
                continue
            newpath = os.path.join(dirname, subdir)
            delete_path_or_file(newpath)


def clean_dailybuild(platform):
    # 这里删除  60 天以前的 imagedate 目录下面的 所有的子目录，
    dailybuild_path_L = glob.glob(DAILYBUILD_BASE_PATTERN % platform)

    today = datetime.date.today()

    for dailybuild_path in dailybuild_path_L:
        if not os.path.isdir(dailybuild_path):
            # 这中情况估计很少出现
            print("[debug] dailybuild path not is a dir: %s " % dailybuild_path)
            continue
        folder = os.path.basename(dailybuild_path)
        imagedate_L = folder.split("_")
        try:
            imgdt = datetime.datetime.strptime(imagedate_L[0], DATE_FORMAT)
        except:
            print("[debug] image date format invalid: %s" % dailybuild_path)
            continue
        imagedate = datetime.date(imgdt.year, imgdt.month, imgdt.day)
        before_1day_ago = today - datetime.timedelta(1) #1天以前的日期
        before_1xday_ago = today - datetime.timedelta(BASE_DAY_AGO)
        before_2xday_ago = today - datetime.timedelta(BASE_DAY_AGO * 2)
        before_3xday_ago = today - datetime.timedelta(BASE_DAY_AGO * 3)

        flag_file = os.path.join(dailybuild_path, ".release.txt")
        if os.path.isfile(flag_file):
            print("[debug] found release flag file, will clean_1xday_ago this path: %s" % dailybuild_path)
            if imagedate < before_1day_ago:
                clean_1xday_ago(dailybuild_path)
        else:
            # 90 ----  60 ---- 30 ---- 7 ----- now
            if imagedate < before_3xday_ago: # 90天以前的 全删
                clean_3xday_ago(dailybuild_path)
            elif imagedate < before_2xday_ago:# 60天以前的 到 90天以前的 之间的
                clean_2xday_ago(dailybuild_path)
            elif imagedate < before_1xday_ago:# 30天以前的 到 60天以前的 之间的
                clean_1xday_ago(dailybuild_path)
            elif imagedate < before_1day_ago:
                clean_1xday_ago(dailybuild_path)
    # end for


def clean_3xday_ago(dailybuild_path):
    # 3 倍的 日期之前的 所有的debug，qfil ota 目录统统删除
    subdir_L = os.listdir(dailybuild_path) # 列出下面所有的子目录，子文件
    for subdir in subdir_L: # 变量下面所有的文件，目录
        old = os.path.join(dailybuild_path, subdir) # 拼接出来一个完整的路径
        if os.path.isdir(old): # 这里值关心目录，文件不关心,文件不进行删除
            delete_path_or_file(old)


def clean_2xday_ago(dailybuild_path):
    # 2 倍的 日期之前的 删除debug，ota目录 留下刷机目录
    subdir_L = os.listdir(dailybuild_path) # 列出下面所有的子目录，子文件
    for subdir in subdir_L: # 变量下面所有的文件，目录
        old = os.path.join(dailybuild_path, subdir) # 拼接出来一个完整的路径
        if os.path.isdir(old): # 这里值关心目录，文件不关心,文件不进行删除
            debug = os.path.join(old, "debug")
            if os.path.isdir(debug):
                print("will rmtree debug folder: %s" % debug)
                delete_path_or_file(debug)

            ota = os.path.join(old, "ota")
            if os.path.isdir(ota):
                print("will rmtree ota folder: %s" % ota)
                delete_path_or_file(ota)

def clean_1xday_ago(dailybuild_path):
    # 1 倍的 日期之前的 压缩debug，qfil等目录，然后删除原来目录
    subdir_L = os.listdir(dailybuild_path)  # 列出下面所有的子目录，子文件
    for subdir in subdir_L:  # 变量下面所有的文件，目录
        old = os.path.join(dailybuild_path, subdir)  # 拼接出来一个完整的路径
        if os.path.isdir(old):  # 这里值关心目录，文件不关心,文件不进行删除
            debug = os.path.join(old, "debug")
            if os.path.isdir(debug):
                debug_zip = os.path.join(debug, "debug.zip")
                if not os.path.exists(debug_zip):
                    print("will zip  debug folder: %s" % debug)
                    make_zip(debug, debug_zip, True)

            qfil = os.path.join(old, "qfil")
            if os.path.isdir(qfil):
                qfil_zip = os.path.join(qfil, "qfil.zip")
                if not os.path.exists(qfil_zip):
                    print("will zip qfil folder: %s" % qfil)
                    make_zip(qfil, qfil_zip, True)

            flash = os.path.join(old, "flash")
            if os.path.isdir(flash):
                flash_zip = os.path.join(flash, "flash.zip")
                if not os.path.exists(flash_zip):
                    print("will zip flash folder: %s" % flash)
                    make_zip(flash, flash_zip, True)

def main():
    # 清理zl1 目录下面的所有的dailybuild  的image date 目录里面的子目录
    for folder in os.listdir(DAILYBUILD_BASE_DIR):
        if folder != "temp":
            clean_dailybuild(folder)


if __name__ == "__main__":
    # need flush print
    sys.stdout = sys.stderr
    main()
