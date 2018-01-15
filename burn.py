#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import stat
import optparse
import shutil
import zipfile
import threading
import time
import tempfile
import platform
import ctypes
import fnmatch
import filecmp
import ftplib
import urllib2
import re
import StringIO
import pprint


__version__ = "1.0"

#父类 Burn class
class Burn(object):
    def __init__(self, imagedate="", product="", bif="", local="", destpath=""):
        #os的类型，Linux还是windows
        self.systemtype = platform.system()

        self.imagedate = imagedate
        self.product = product
        self.bif = bif # burm info file,表示烧录手机的相关的信息的文件

        #是否打印输出log
        self.quiet = False

        self.copyforce = False

        #print all image name if set this option
        self.listimage = False

        #默认是当前路径
        self.destpath = ""
        self.onlyburn = False
        self.onlycopy = False

        #是否擦写
        self.eraseflash = False
        #是否只是擦写
        self.onlyeraseflash = False
        #是否烧写后自动重启
        self.resetafterburning = False

        #softwaredownloader name
        if self.systemtype == "Linux":
            self.swdlname = "fastboot_flash.sh"
            self.dailybuildpath = os.path.join("/","dailybuild")
        elif self.systemtype == "Windows":
            self.swdlname = "fastboot_flash.bat"
            self.dailybuildpath = os.path.join("\\\\10.0.12.12","dailybuild")
        else:
            self.swdlname = ""
            self.dailybuildpath = ""

        # dailybuild + android = 默认的dailybuild images的路径
        self.androidpath = "android"

        #local path,where source image are
        self.local = local
        self.destpath = destpath

        self.Image_Enable_pattern = "Image_Enable"
        self.Image_ID_Name_pattern = "Image_ID_Name"
        self.Image_Tim_Included_partten = "Image_Tim_Included"
        self.Image_Path_pattern = "Image_Path"
        self.Erase_All_Flash = "Erase_All_Flash"
        self.UE_Boot_Option = "UE_Boot_Option"

        self.printcolor = PrintColor()

        #bif 里的image name
        self.bifimagename_L = []

        #不烧写的image
        self.disableimage_L = []
        #只烧写的image
        self.enableimage_L = []

        #image enable or disable num -->0/1 enable/disable
        self.bifimageable_D = {}

        #bif 里的image num --> name
        self.bifimagenum_D = {}

        #bif 里的image id name --> num 映射
        self.bifimageidname_D = {}

        #bif 里的image num --> tim included,这个TIM不知道干啥的
        self.bifimagetimincluded_D = {}

        #local目录下的image path
        self.localimagefile_L = []

        #local路径下的bif路径/绝对路径
        self.localbifpath = "" #只有路径
        self.localbiffile= "" #路径+bif文件名

        #目的路径下的bif路径/绝对路径
        self.destbifpath = "" #只有路径
        self.destbiffile= "" #路径+bif文件名

        #local路径下的swdl路径/绝对路径
        self.localswdlpath = "" #只有路径
        self.localswdlfile= "" #路径+swdl文件名

        #目的路径下的swdl路径/绝对路径
        self.destswdlpath = "" #只有路径.烧image时要切入这个目录中
        self.destswdlfile = ""

        self.swdldriver = SwdlDriver()

        self.findfile = FindFile()

        self.printlistmax = 20

        #线程池的个数
        self.jobsnum = 0
    def start(self):
        return 0

    #父类 Burn class -> prepare_copy_swdl(), 这里的swdl是fastboto脚本
    def prepare_copy_swdl(self, local="", swdlname=""):
        return 0

    #父类 Burn class -> prepare_copy_images()
    def prepare_copy_images(self, local="", bif=""):
        local = self.local if local == "" else local
        bif = self.bif if bif == "" else bif



        #1.(1)先精确的查找bif在local下的位置, k2的是download.zip 压缩包
        if not self.findfile.exists(self.localbiffile):
            if self.find_local_bif(local, bif, None) != 0:
                #(2)没找到这个bif文件时，尝试通配搜索其他的bif文件
                self.printcolor.printwarning("try to search other burn info file")
                pattern = "*fastboot.*"
                if self.systemtype == "Linux":pattern = "*fastboot_flash.sh"
                if self.systemtype == "Windows":pattern = "*fastboot_flash.bat"

                if self.find_local_bif(local, pattern, pattern) != 0:
                    #没bif文件我怎么知道你需要copy哪些image啊？！
                    if self.find_local_zip() != 0:
                        return 1

                if self.find_local_bif("", bif, None) != 0:
                    return 1



        #2.然后根据bif找image文件了.有了bif文件才好知道需要哪些image
        self.bifimagename_L = self.get_bifimagename_L() #这个有可能有重名的image
        self.bifimageable_D = self.get_bifimageable_D()
        self.bifimagenum_D = self.get_bifimagenum_D()
        self.bifimageidname_D = self.get_bifimageidname_D()
        self.bifimagetimincluded_D = self.get_bifimagetimincluded_D()
        self.localimagefile_L = self.get_localimagefile_L()

        #3.destpath没设置，直接返回
        if self.destpath == "":
            #image date 有的话就在当前目录下建立个imagedate的目录
            if self.imagedate:#local mode这里没有imagedate
                #有product的情况下
                if self.product:#local mode这里没有product
                    self.destpath =os.path.join(os.path.join(".", self.imagedate), self.product)
                    self.printcolor.printinfo("will create a folder: %s" % self.destpath)
                #没有product的情况下
                else:
                    self.destpath = os.path.join(".", self.imagedate)
                    self.printcolor.printerror("not set product,will create a temp folder: %s" % self.destpath)
            #没有的话创建临时的目录
            else:#local mode这里没有imagedate
                self.destpath = tempfile.mkdtemp()
                self.printcolor.printerror("will create a temp folder: %s" % self.destpath)

        #4.destpath设置了，判断存在与否和设置的对不对，不能是个文件吧？！
        if not os.path.exists(self.destpath):
            self.printcolor.printinfo("%s not exist,create it" % self.destpath)
            os.makedirs(self.destpath)

        if os.path.isdir(self.destpath):
            #这个就是之后放swdl的目录

            #在destpath目录下找swdl
            if self.find_dest_swdl(self.destpath) != 0:
                #准备swdl。查找设置swdl的一些路径
                self.prepare_copy_swdl()#这个方法子类里面会重写
                #再次在destpath目录里查找swdl，这次应该是有的
                if self.find_dest_swdl(self.destpath) != 0:
                    return 1

            #(1)然后创建在里面创建个 bif的目录用来存放bif文件,destswdlpath会在find_dest_swdl()里面设置
            self.destbifpath = self.destswdlpath

            #(2)bif转换为绝对路径
            self.destbiffile = os.path.abspath(os.path.join(self.destbifpath, self.bif))
            if os.path.exists(self.destbiffile):
                #存在
                if self.is_difffile(self.localbiffile, self.destbiffile):
                    #不一样的文件
                    if self.copyforce:
                        #强制覆盖
                        self.findfile.download(self.localbiffile, self.destbiffile)
                    else:
                        self.printcolor.printwarning("%s exists, if you want force copy use --force" % self.destbiffile)
                else:
                    self.printcolor.printwarning("%s is same, no need to copy" % self.bif)
            else:
                #不存在
                self.printcolor.printinfo("copy bif %s --> %s" % (self.localbiffile, self.destbifpath))
                self.findfile.download(self.localbiffile, self.destbiffile)

            #(3)修改bif文件
            self.modify_destbiffile(self.destbiffile)

        else:
            #这里估计是走不到的
            self.printcolor.printwarning("%s is a file not a dir, use --dest-path" % self.destpath)
            return 1

        return 0

    #Burn class -> start_copy_images()
    def start_copy_images(self):
        if self.jobsnum > 0:
            #use mutil thread
            threadpool = ThreadPool(self.jobsnum)
            for local_image in self.localimagefile_L:
                threadpool.queueTask(self.copy, (local_image, self.destbifpath), None)
            threadpool.joinAll()
        else:
            #not use mutil thread
            for local_image in self.localimagefile_L:
                self.copy((local_image, self.destbifpath))

    #父类Burn class -> copy()
    def copy(self, data):
        srcfile = data[0]#源文件路径+名字
        srcfilename = os.path.basename(srcfile)

        destpath = data[1]#目的路径、或者路径+名字
        destfile = os.path.join(destpath, srcfilename)

        if os.path.exists(destfile):
            if self.is_difffile(srcfile, destfile):
                if self.copyforce:
                    self.printcolor.printinfo("download %s --> %s" % (srcfile, destpath))
                    self.findfile.download(srcfile, destfile)#samba mode 会是真正的下载，其他的是重写了download()方法，里面是用的shutil.copy()
                else:
                    self.printcolor.printwarning("%s exists, if you want force copy use --force options" % destfile)
            else:
                self.printcolor.printwarning("%s, %s same, no need to copy" % (srcfile, destfile))
        else:
            self.printcolor.printinfo("download %s --> %s" % (srcfile, destpath))
            #samba mode 会是真正的下载，其他的是重写了download()方法，里面是用的shutil.copy()
            self.findfile.download(srcfile, destfile)

    #父类Burn class -> find_dest_swdl() 在destpath里面寻找 swdl，之后会.设置self.destswdlfile, self.destswdlpat
    def find_dest_swdl(self, dest="", swdlname=""):
        dest = self.destswdlpath if dest == "" else dest
        swdlname = self.swdlname if swdlname == "" else swdlname

        #精确查找,这时候就需要findfile.localfile(),因为文件已经复制到本地了，而不是findfile.findfile()了,
        #samba模式findfile会被重写这里就不能用了。其他模式localfile（）和findfile（）是一样的
        destswdl_L = self.findfile.localfile(dest, swdlname, None)
        destswdl_L_len = len(destswdl_L)
        if not destswdl_L:
            #不可能吧？没找到
            self.printcolor.printwarning("not found %s in [%s]" % (swdlname, dest))
            return 1
        elif destswdl_L_len > 1:
            #不可能吧？找到多个
            self.printcolor.printinfo("found more %s ,which do you want? [%s - %s] or exit?" % (swdlname, 0, destswdl_L_len - 1))
            if destswdl_L_len > self.printlistmax:
                for i in range(0, destswdl_L_len):
                    print "[%s]" % i, destswdl_L[i]
                self.printcolor.printwarning("so many %s! I cann't list all, just list top %s" % (swdlname, self.printlistmax))
                return 1
            for i in range(0, destswdl_L_len):
                print "[%s]" % i, destswdl_L[i]
            choice = raw_input("please input [0 - %s] " % (destswdl_L_len -1))
            try:
                index = int(choice)
            except ValueError as e:
                self.printcolor.printinfo("exit")
                sys.exit(1)
            if index > destswdl_L_len - 1 or index < 0:
                self.printcolor.printerror("[%s]out of index" % index)
                sys.exit(1)

            self.destswdlfile = destswdl_L[index]#路径+文件名
            self.destswdlpath = os.path.dirname(self.destswdlfile)#只有路径
        else:
            #只找到一个
            self.destswdlfile = destswdl_L[0]#路径+文件名
            self.destswdlpath = os.path.dirname(self.destswdlfile)#只有路径
        return 0

    def find_local_zip(self, local="", zipanme = "flash.zip", pattern="*flash.zip"):
        local = self.local if local == "" else local

        zip_L = self.findfile.findfile(local, zipanme, pattern)
        zip_L_len = len(zip_L)
        if not zip_L:
            #没用在local路径里找到bif文件，直接return
            self.printcolor.printwarning("not found this zip: %s" % zipanme)
            return 1
        elif zip_L_len > 1:
            #找到多个zip文件
            self.printcolor.printinfo("found more zip[%s] file,which do you want? [%s - %s] or exit?" % (zipanme, 0, zip_L_len-1))
            if zip_L_len > self.printlistmax:
                for i in range(0, self.printlistmax):
                    print "[%s]" % i, (zip_L[i].replace(local, ""))
                self.printcolor.printwarning("so many bif files! I cann't list all, just list top %s" % self.printlistmax)
                return 2
            for i in range(0, zip_L_len):
                print "[%s]" % i, (zip_L[i].replace(local, ""))
            choice = raw_input("please input [0 - %s] " % (zip_L_len - 1))
            try:
                index = int(choice)
            except ValueError as e:
                self.printcolor.printinfo("exit")
                sys.exit(1)
            if index > zip_L_len - 1 or index < 0:
                self.printcolor.printerror("[%s]out of index" % index)
                sys.exit(1)
            localzip = zip_L[index]
        else:
            localzip = zip_L[0]

        #3.destpath没设置，直接返回
        if self.destpath == "":
            #image date 有的话就在当前目录下建立个imagedate的目录
            if self.imagedate:#local mode这里没有imagedate
                #有product的情况下
                if self.product:#local mode这里没有product
                    self.destpath =os.path.join(os.path.join(".", self.imagedate), self.product)
                    self.printcolor.printinfo("will create a folder: %s" % self.destpath)
                #没有product的情况下
                else:
                    self.destpath = os.path.join(".", self.imagedate)
                    self.printcolor.printerror("not set product,will create a temp folder: %s" % self.destpath)
            #没有的话创建临时的目录
            else:#local mode这里没有imagedate
                self.destpath = tempfile.mkdtemp()
                self.printcolor.printerror("will create a temp folder: %s" % self.destpath)

        #4.destpath设置了，判断存在与否和设置的对不对，不能是个文件吧？！
        if not os.path.exists(self.destpath):
            self.printcolor.printinfo("%s not exist,create it" % self.destpath)
            os.makedirs(self.destpath)


        destzip = os.path.join(self.destpath, os.path.basename(localzip))
        self.printcolor.printinfo("download %s --> %s" % (localzip, destzip))
        self.findfile.download(localzip, destzip)

        self.printcolor.printinfo("unzip %s --> %s" % (destzip, self.destpath))
        self.findfile.unzip(destzip, self.destpath)
        self.local  = self.destpath
        return 0



    #父类Burn class -> ()
    #精确的查找bif，通配搜索
    def find_local_bif(self, local="", bif="", pattern=None):
        local = self.local if local == "" else local
        bif = self.bif if bif == "" else bif

        #local path 里的bif
        bif_L = self.findfile.findfile(local, bif, pattern)
        bif_L_len = len(bif_L)
        if not bif_L:
            #没用在local路径里找到bif文件，直接return
            self.printcolor.printwarning("not found this bif: %s" % bif)
            return 1
        elif bif_L_len > 1:
            #找到多个bif文件
            self.printcolor.printinfo("found more bif[%s] file,which do you want? [%s - %s] or exit?" % (bif,0, bif_L_len-1))
            if bif_L_len > self.printlistmax:
                for i in range(0, self.printlistmax):
                    print "[%s]" % i, (bif_L[i].replace(local, ""))
                self.printcolor.printwarning("so many bif files! I cann't list all, just list top %s" % self.printlistmax)
                return 2
            for i in range(0, bif_L_len):
                print "[%s]" % i, (bif_L[i].replace(local, ""))
            choice = raw_input("please input [0 - %s] " % (bif_L_len - 1))
            try:
                index = int(choice)
            except ValueError as e:
                self.printcolor.printinfo("exit")
                sys.exit(1)
            if index > bif_L_len - 1 or index < 0:
                self.printcolor.printerror("[%s]out of index" % index)
                sys.exit(1)

            self.localbiffile = bif_L[index]#路径+bif
            #通配搜索的情况下需要重设bif名字
            self.bif = os.path.basename(self.localbiffile)
            self.localbifpath = os.path.dirname(self.localbiffile) #只有路径
            # #这里重新设置一下self.local 吧
            self.local = self.localbifpath
        else:
            #找到了一个bif文件
            self.localbiffile = bif_L[0]#路径+bif

            #通配搜索的情况下需要重设bif名字
            searchbif = os.path.basename(self.localbiffile)
            if searchbif != self.bif:
                print "[0]", bif_L[0].replace(local, "")
                choice = raw_input("This bif you want? please input [0] " )
                try:
                    index = int(choice)
                except ValueError as e:
                    self.printcolor.printinfo("exit")
                    sys.exit(1)
                if index != 0:
                    self.printcolor.printwarning("exit")
                    sys.exit(1)
                self.bif = searchbif
                self.printcolor.printinfo("your choice: %s" % self.bif)

            self.localbifpath = os.path.dirname(self.localbiffile) #只有路径
            # #这里重新设置一下self.local 吧
            self.local = self.localbifpath
        return 0

    #父类Burn class -> ()
    def list_allimagename(self, local="", bif=""):
        local = self.local if local == "" else local
        bif = self.bif if bif == "" else bif
        #1.(1)先精确的查找bif在local下的位置
        if self.find_local_bif(local, bif, None) != 0:
            #(2)没找到这个bif文件时，尝试通配搜索其他的bif文件
            self.printcolor.printwarning("try to search other burn info file")
            pattern = "**fastboot.*.*"
            if self.systemtype == "Linux":pattern = "*fastboot_flash.sh"
            if self.systemtype == "Windows":pattern = "*fastboot_flash.bat"

            if self.find_local_bif(local, pattern, pattern) != 0:
                #(3)没bif文件我怎么知道烧写image啊
                if self.find_local_zip()!= 0:
                    return 1
            if self.find_local_bif("", bif, None) != 0:
                return 1

        self.bifimagenum_D = self.get_bifimagenum_D()

        self.bifimageidname_D = self.get_bifimageidname_D()
        self.bifimageable_D = self.get_bifimageable_D()

        self.bifimagetimincluded_D = self.get_bifimagetimincluded_D()

        num_L = self.bifimagenum_D.keys()
        num_L.sort()
        self.printcolor.printinfo("list all image [ID:?] = name in bif: %s" % (self.bif))
        for num in num_L:
            print "[ID: %2s] = %s" % (num, self.bifimagenum_D[num])
        self.printcolor.printinfo("list all image [ID:?] = name in bif: %s" % (self.bif))


    #父类Burn class -> ()
    #burn images, linux use swdl_linux, windows use .exs
    def start_burn_images(self):
        if self.systemtype == "Linux":
            os.chmod(self.destswdlfile, stat.S_IRWXU + stat.S_IRWXG + stat.S_IRWXO)
            destswdlabspath = os.path.abspath(self.destswdlpath)
            os.chdir(self.destswdlpath)
            command = "sudo bash ./%s" % (self.swdlname)
            ret = os.system(command)
            self.printcolor.printinfo("biffile: [%s]" % (self.destbiffile))
            self.printcolor.printinfo("swdlpath:[%s]" % (destswdlabspath))
            self.printcolor.printinfo("command: [cd %s && %s]" % (destswdlabspath, command))
        elif self.systemtype == "Windows":
            destswdlabspath = os.path.abspath(self.destswdlpath)
            os.chdir(self.destswdlpath)
            command = "%s" % (self.swdlname)
            ret = os.system(command)
            self.printcolor.printinfo("biffile: [%s]" % (self.destbiffile))
            self.printcolor.printinfo("swdlpath:[%s]" % (destswdlabspath))
            self.printcolor.printinfo("command: [cd %s && %s]" % (destswdlabspath, command))
        return 0


    #父类Burn class -> modify_destbiffile()
    def modify_destbiffile(self, destbiffile=""):
        #修改目的路径下的bif文件
        destbiffile = self.destbiffile if destbiffile =="" else destbiffile
        fd = open(destbiffile, "r")
        lines_L = fd.readlines()
        lines_L_len = len(lines_L)
        fd.close()

        if self.disableimage_L:
            #If you disable this item,other items that have same value in Tim column will be disabled automatically
            #Since they have same Tim include property and they should have same status to ensure after burning flash successfully.
            newbifname = "%s_disable" % self.bif

            #先整理一下需要disabled的image对应的num，得到一个list
            disableimagenum_L = []
            for num_or_id in self.disableimage_L:
                #获取所有的disable的num是一个list
                num_L = self.get_disable_enable_imagenum_L(num_or_id)
                disableimagenum_L.extend(num_L)
            #去重
            disableimagenum_L = list(set(disableimagenum_L))
            #处理tim之后的num的list
            disableimagenum_tim_L = []
            for num in disableimagenum_L:
                #获取tim include的数，大于0的需要处理一下
                timincluded = self.bifimagetimincluded_D.get(num, -1)
                if timincluded == "0":
                    disableimagenum_tim_L.append(num)
                else:
                    for (numkey, timvalue) in self.bifimagetimincluded_D.items():
                        if timvalue == timincluded:
                            disableimagenum_tim_L.append(numkey)
            #再次把新的的处理过tim的list去重
            disableimagenum_L = list(set(disableimagenum_tim_L))

            for i in range(0, lines_L_len):
                #遍历所有需要disabled的image对应的num的list
                for num in disableimagenum_L:
                    pattern = "%s_%s" % (num, self.Image_Enable_pattern)
                    if pattern == lines_L[i].split("=")[0].strip():
                        lines_L[i] = "%s = %s\r\n" % (pattern, 0)
                        #remove bifimagename in the bif name.IOError 36, File name too long.
                        newbifname = "%s_%s" % (newbifname, num)
                        self.printcolor.printinfo("will disable image: [%2s]%s" % (num, self.bifimagenum_D[num]))
            newbifname = "%s.bif" % (newbifname)
            newbiffile = os.path.join(self.destbifpath, newbifname)

            self.printcolor.printinfo("will write to new bif file(disable images):\n %s" % (newbiffile))
            fd = open(newbiffile, "w")
            fd.writelines(lines_L)
            fd.close()

            self.bif = newbifname
            self.destbiffile = os.path.abspath(newbiffile)

        if self.enableimage_L:
            newbifname = "%s_enable" % self.bif

            #先整理一下需要enabled的image对应的num，得到一个list
            enableimagenum_L = []
            for num_or_id in self.enableimage_L:
                #获取所有的enable的num是一个list
                num_L = self.get_disable_enable_imagenum_L(num_or_id)
                enableimagenum_L.extend(num_L)
            #去重
            enableimagenum_L = list(set(enableimagenum_L))
            #处理tim之后的num的list
            enableimagenum_tim_L = []
            for num in enableimagenum_L:
                #获取tim include的数，大于0的需要处理一下
                timincluded = self.bifimagetimincluded_D.get(num, -1)
                if timincluded == "0":
                    enableimagenum_tim_L.append(num)
                else:
                    for (numkey, timvalue) in self.bifimagetimincluded_D.items():
                        if timvalue == timincluded:
                            enableimagenum_tim_L.append(numkey)
            #再次把新的的处理过tim的list去重
            enableimagenum_L = list(set(enableimagenum_tim_L))

            for i in range(0, lines_L_len):
                #遍历所有需要disabled的image对应的num的list
                for num in enableimagenum_L:
                    pattern = "%s_%s" % (num, self.Image_Enable_pattern)
                    if pattern == lines_L[i].split("=")[0].strip():
                        lines_L[i] = "%s = %s\r\n" % (pattern, 1)
                        #remove bifimagename in the bif name.IOError 36, File name too long.
                        newbifname = "%s_%s" % (newbifname, num)
                        self.printcolor.printinfo("will enable image: [%2s]%s" % (num, self.bifimagenum_D[num]))
            newbifname = "%s.bif" % (newbifname)
            newbiffile = os.path.join(self.destbifpath, newbifname)

            self.printcolor.printinfo("will write to new bif file(enable images):\n %s" % (newbiffile))
            fd = open(newbiffile, "w")
            fd.writelines(lines_L)
            fd.close()

            self.bif = newbifname
            self.destbiffile = os.path.abspath(newbiffile)

        if self.eraseflash:
            newbifname = "%s_erase_all_flash" % self.bif
            for i in range(0, lines_L_len):
                pattern = "%s" % (self.Erase_All_Flash)
                if pattern in lines_L[i].split("=")[0].strip():
                    lines_L[i] = "%s = %s\r\n" % (pattern, 1)
                    self.printcolor.printinfo("Erase All Flash.")
            newbifname = "%s.bif" % (newbifname)
            newbiffile = os.path.join(self.destbifpath, newbifname)

            self.printcolor.printinfo("will write to new bif file(Erase All Flash):\n %s" % (newbiffile))
            fd = open(newbiffile, "w")
            fd.writelines(lines_L)
            fd.close()

            self.bif = newbifname
            self.destbiffile = os.path.abspath(newbiffile)

        if self.onlyeraseflash:
            newbifname = "%s_only_erase_all_flash" % self.bif
            for i in range(0, lines_L_len):
                pattern = "%s" % (self.Erase_All_Flash)
                if pattern == lines_L[i].split("=")[0].strip():
                    lines_L[i] = "%s = %s\r\n" % (pattern, 2)
                    self.printcolor.printinfo("Only Erase All Flash.")
            newbifname = "%s.bif" % (newbifname)
            newbiffile = os.path.join(self.destbifpath, newbifname)

            self.printcolor.printinfo("will write to new bif file(Only Erase All Flash):\n %s" % (newbiffile))
            fd = open(newbiffile, "w")
            fd.writelines(lines_L)
            fd.close()

            self.bif = newbifname
            self.destbiffile = os.path.abspath(newbiffile)

        if self.resetafterburning:
            newbifname = "%s_reset_after_burning" % self.bif
            for i in range(0, lines_L_len):
                pattern = "%s" % (self.UE_Boot_Option)
                if pattern == lines_L[i].split("=")[0].strip():
                    lines_L[i] = "%s = %s\r\n" % (pattern, 1)
                    self.printcolor.printinfo("ResetUE After Burning.")
            newbifname = "%s.bif" % (newbifname)
            newbiffile = os.path.join(self.destbifpath, newbifname)

            self.printcolor.printinfo("will write to new bif file(ResetUE After Burning):\n %s" % (newbiffile))
            fd = open(newbiffile, "w")
            fd.writelines(lines_L)
            fd.close()

            self.bif = newbifname
            self.destbiffile = os.path.abspath(newbiffile)

        return 0

    #父类Burn class -> ()
    def get_disable_enable_imagenum_L(self, num_or_id):
        try:
            #如果是整数
            num = int(num_or_id)
            num_L = [num]
        except ValueError:
            #image的idname可能对应多个num值
            num_L = []
            for num,idname in self.bifimageidname_D.iteritems():
                #都转换为大写
                if idname == num_or_id.upper():
                    num_L.append(num)
        return num_L

    def is_samefile(self, f1, f2):
        return filecmp.cmp(f1,f2)

    def is_difffile(self, f1, f2):
        return not self.is_samefile(f1,f2)

    #获取通过local，和bif 获取image的路径
    def get_localimagefile_L(self, local="", bif=""):
        bif = self.localbiffile if bif == "" else bif
        local = self.local if local=="" else local
        local_image_L = []
        for imagename in self.get_bifimagename_L(bif):
            local_image_L.extend(self.findfile.findfile(local, imagename))
        local_image_L = list(set(local_image_L))
        return local_image_L

    #通过bif文件获得image的名字
    def get_bifimagename_L(self, bif=""):
        bif = self.localbiffile if bif == "" else bif
        local_image_L = []

        lines_L = self.findfile.get_file_lines_L(bif)
        if bif.endswith(".sh"):
            str = "".join(lines_L)
            find_all_L = re.findall(r"images=\(.*?\)", str, re.S)
            if not find_all_L:
                local_image_L = []
            else:
                all_images = find_all_L[0].replace("images=(", "").replace(")", "").replace("\"", "")
                local_image_L = all_images.split(" ")
                local_image_L = [image.strip() for image in local_image_L if image.strip() != ""]
        elif bif.endswith(".bat"):
            for line in lines_L:
                if "FASTBOOTFAILED" in line and "call" in line:
                    local_image_L.append(line.strip().replace("||", " ").split(" ")[3].strip())
        local_image_L = list(set(local_image_L))
        return local_image_L

    def get_bifimagenum_D(self, bif=""):
        bif = self.localbiffile if bif == "" else bif
        image_num_D = {}
        imagename_L = self.get_bifimagename_L(bif)
        for index,name in enumerate(imagename_L):
            image_num_D[index] = name
        return image_num_D

    def get_bifimageidname_D(self, bif=""):
        bif = self.localbiffile if bif == "" else bif
        image_idname_D = {}
        lines_L = self.findfile.get_file_lines_L(bif)
        for line in lines_L:
            if self.Image_ID_Name_pattern in line:
                # 25_Image_ID_Name = CACH
                imagenum = int(line.split("_")[0].strip())
                id_name = line.split("=")[1].strip()
                image_idname_D.setdefault(imagenum, id_name)
        return image_idname_D

    def get_bifimageable_D(self, bif=""):
        bif = self.localbiffile if bif == "" else bif
        image_able_D = {}
        lines_L = self.findfile.get_file_lines_L(bif)
        for line in lines_L:
            if self.Image_Enable_pattern in line:
                # 1_Image_Enable = 1
                imagenum = int(line.split("_")[0].strip())
                able = line.split("=")[1].strip()
                image_able_D.setdefault(imagenum, able)
        return image_able_D

    def get_bifimagetimincluded_D(self, bif=""):
        bif = self.localbiffile if bif == "" else bif
        tim_num_D = {}
        lines_L = self.findfile.get_file_lines_L(bif)
        for line in lines_L:
            #1_Image_Tim_Included = 1
            if self.Image_Tim_Included_partten in line:
                imagenum = int(line.split("_")[0].strip())
                tim_included = line.split("=")[1].strip()
                tim_num_D.setdefault(imagenum, tim_included)
        return tim_num_D

    def set_disableimage(self, d):
        #分割字符串，获得image num
        d_L = d.split(",")
        disableimage_L = []
        for index, item in enumerate(d_L):
            try:
                disableimage_L.append(item)
            except ValueError as e:
                pass
        self.disableimage_L = disableimage_L

    def set_enableimage(self, d):
        #分割字符串，获得image num
        d_L = d.split(",")
        enableimage_L = []
        for index, item in enumerate(d_L):
            try:
                enableimage_L.append(item)
            except ValueError as e:
                pass
        self.enableimage_L = enableimage_L

    def set_destpath(self, path):
        self.destpath=path

    def set_dailybuildpath(self, dailybuildpath):
        self.dailybuildpath = dailybuildpath

    def set_androidpath(self, androidpath):
        self.androidpath = androidpath
        print self.androidpath

    def set_swdlname(self, swdlname):
        self.swdlname = swdlname

    def set_onlycopy(self, onlycopy):
        self.onlycopy=onlycopy

    def set_onlyburn(self, onlyburn):
        self.onlyburn=onlyburn

    def set_copyforce(self, f):
        self.copyforce = f

    def set_listimage(self, l):
        self.listimage = l

    def set_eraseflash(self, eraseornot):
        self.eraseflash = eraseornot

    def set_onlyeraseflash(self, onlyeraseornot):
        self.onlyeraseflash = onlyeraseornot

    def set_resetafterburning(self, reset):
        self.resetafterburning = reset

    def set_printlistmax(self, m):
        self.printlistmax = m

    def set_quiet(self, quiet):
        self.quiet = quiet
        self.printcolor.set_quiet(quiet)

    def set_jobsnum(self, num):
        self.jobsnum = num

    def set_username(self, username):
        pass

    def set_password(self, password):
        pass
#end class Burn()

#父类，继承Burn()类，专门为daily image准备的
class DailyBurn(Burn):
    def __init__(self, imagedate="", product="", bif=""):
        super(DailyBurn, self).__init__(imagedate=imagedate, product=product, bif=bif)

        #image base path
        self.platformpath = ""

    #daily build burn class -> start()
    def start(self):
        if self.listimage:
            if self.prepare_imagedate_product() != 0:
                return 1
            self.list_allimagename()
            return 0

        if self.onlycopy and self.onlyburn:
            self.printcolor.printerror('onlycopy or onlyburn?')
            return 1

        #1,copy images and burn images,daily dailybuild 需要imagedate的folder名字和product的folder名字
        if self.prepare_imagedate_product() != 0:
            return 1
        #2.prepare copy images.准备destpath路径。复制bif文件／修改bif文件,prepare_copy_images()使用父类的
        if self.prepare_copy_images() != 0:
            return 1

        if self.onlycopy:
            #3.start copy images
            self.start_copy_images()
        else:
            #3.start copy images
            self.start_copy_images()
            #4.start burn images
            self.start_burn_images()

        return 0

    #daily build burn class -> ()
    #preepare imagedtae and product
    def prepare_imagedate_product(self):
        if not self.imagedate and not self.product:
            #imagedate 和 product 都没有,先选择 platformpath 例如：/dailybuild/android/pxa988
            if self.select_platformpath() != 0:
                return 1
            #接下来选择imagedate的目录
            if self.select_imagedate() != 0:
                return 1
            #imagedate设置好了就在imagedate里找不同的product的目录
            if self.select_product() != 0:
                return 1
        elif self.imagedate and not self.product:
            #imagedate 有了要在不同的platform 目录下搜索这个imagedate的folder
            if self.find_imagedate() != 0:
                return 1
            #imagedate设置好了就在imagedate找不同的product的目录
            if self.select_product() != 0:
                return 1
        elif not self.imagedate and self.product:
            #product 有了要在不同的platform/imagedate 目录下搜索这个product的folder
            #确定platform
            if self.find_product() != 0:
                return 1
            #选择imagedate
            if self.select_imagedate() != 0:
                return 1
        else:
            #都有的情况,有了imagedate要在不同的platform目录下搜索这个imagedate的folder
            if self.find_imagedate() != 0:
                return 1

            if self.find_product() != 0:
                return 1

        #到此 "imagedate:", "platform:", "product:"这三个都有了, 然后设置一下local
        self.local = os.path.join(self.platformpath, self.imagedate, self.product)

        return 0

    #daily build burn class -> ()
    def find_product(self,dailybuildpath="", platformpath="", imagedate="", product=""):
        #/dailybuild
        dailybuildpath = self.dailybuildpath if dailybuildpath == "" else dailybuildpath
        platformpath = self.platformpath if platformpath == "" else platformpath
        imagedate = self.imagedate if imagedate == "" else imagedate
        product = self.product if product == "" else product

        #/dailybuild/android
        androidpath = os.path.join(dailybuildpath, self.androidpath)

        if not self.findfile.isdir(androidpath):
            self.printcolor.printerror("[%s]is not a dir!" % (androidpath))
            return 1

        #哪个platform中有此product
        platform_has_product_L = []

        if platformpath:
            if imagedate:
                platformimagedatepath = os.path.join(platformpath, imagedate)
                platformimagedateproductpath = os.path.join(platformimagedatepath, product)
                if self.findfile.isdir(platformimagedateproductpath):
                    platform_has_product_L.append(platformpath)
            else:
                idate_L = self.findfile.listdir(platformpath)
                for idate in idate_L:
                    platformimagedatepath = os.path.join(platformpath, idate)
                    platformimagedateproductpath = os.path.join(platformimagedatepath, product)
                    if self.findfile.isdir(platformimagedateproductpath):
                        platform_has_product_L.append(platformpath)
        else:
            platform_L = self.findfile.listdir(androidpath)
            for platformfolder in platform_L:
                platformpath = os.path.join(androidpath, platformfolder)
                if imagedate:
                    platformimagedatepath = os.path.join(platformpath, imagedate)
                    platformimagedateproductpath = os.path.join(platformimagedatepath, product)
                    if self.findfile.isdir(platformimagedateproductpath):
                        platform_has_product_L.append(platformpath)
                else:
                    idate_L = self.findfile.listdir(platformpath)
                    for idate in idate_L:
                        platformimagedatepath = os.path.join(platformpath, idate)
                        platformimagedateproductpath = os.path.join(platformimagedatepath, product)
                        #samba 模式判断isdir()会出现MemoryError的错误？？？？怎么破？？？
                        #重新改写了smbisdir（）函数，用open打开来判断是否是一个目录。
                        #opendir打开会出现MemoryError
                        if self.findfile.isdir(platformimagedateproductpath):
                            platform_has_product_L.append(platformpath)

        platform_has_product_L = list(set(platform_has_product_L))
        platform_has_product_L_len = len(platform_has_product_L)

        if not platform_has_product_L:
            self.printcolor.printerror("not found product: '%s' in [%s]" % (product, os.path.join(platformpath, imagedate)))
            return 1
        elif platform_has_product_L_len > 1:
            self.printcolor.printinfo("found product:'%s' in different platform path,which do you want? [%s - %s] or exit?" % (product, 0, platform_has_product_L_len - 1))
            if platform_has_product_L_len > self.printlistmax:
                for i in range(0, self.printlistmax):
                    print "[%4s]" % i,(platform_has_product_L[i])
                self.printcolor.printwarning("so many %s! I cann't list all, just list top %s" % (product, self.printlistmax))
                return 1
            for i in range(0, platform_has_product_L_len):
                print "[%4s]" % i,(platform_has_product_L[i])

            choice = raw_input("please input [%s - %s]" % (0, platform_has_product_L_len - 1))
            try:
                index = int(choice)
            except ValueError as e:
                self.printcolor.printwarning("exit")
                sys.exit(1)
            if index > platform_has_product_L_len - 1 or index < 0:
                self.printcolor.printerror("[%s]out of index" % index)
                sys.exit(1)

            self.platformpath = platform_has_product_L[index]
        else:
            self.platformpath = platform_has_product_L[0]
        return 0

    #daily build burn class -> find_imagedate()
    def find_imagedate(self,dailybuildpath="", platformpath="", imagedate="", product=""):
        #/dailybuild
        dailybuildpath = self.dailybuildpath if dailybuildpath == "" else dailybuildpath
        platformpath = self.platformpath if platformpath == "" else platformpath
        imagedate = self.imagedate if imagedate == "" else imagedate
        product = self.product if product == "" else product

        #/dailybuild/android
        androidpath = os.path.join(dailybuildpath, self.androidpath)

        if not self.findfile.isdir(androidpath):
            self.printcolor.printerror("[%s]is not a dir or not exist!" % (androidpath))
            return 1

        #platformpath + imagedate
        imagedatepath_L = []
        if platformpath:
            imagedatepath = os.path.join(platformpath, imagedate)
            if product:
                productpath = os.path.join(imagedatepath, product)
                if self.findfile.isdir(productpath):
                    imagedatepath_L.append(imagedatepath)
            else:
                if self.findfile.isdir(imagedatepath):
                    imagedatepath_L.append(imagedatepath)
        else:
            platform_L = self.findfile.listdir(androidpath)
            for platformfolder in platform_L:
                platformpath = os.path.join(androidpath, platformfolder)
                imagedatepath = os.path.join(platformpath, imagedate)
                if product:
                    productpath = os.path.join(imagedatepath, product)
                    if self.findfile.isdir(productpath):
                        imagedatepath_L.append(imagedatepath)
                else:
                    if self.findfile.isdir(imagedatepath):
                        imagedatepath_L.append(imagedatepath)
        imagedatepath_L_len = len(imagedatepath_L)

        if not imagedatepath_L:
            #没有找到指定的imagedate的folder
            self.printcolor.printwarning("no '%s' '%s' in [%s]" % (imagedate, product, androidpath))
            self.printcolor.printwarning("will try to search '%s' '%s' in [%s]" % (imagedate, product, androidpath))
            platform_L = self.findfile.listdir(androidpath)

            #存放类似/dailybuild/android/pxa988/2014-06-12_pxa988-kk4.4_T7_beta2的一个list
            platformimagedatepath_L = []
            for platformfolder in platform_L:
                platformpath = os.path.join(androidpath, platformfolder)
                idate_L = self.findfile.listdir(platformpath)
                for idate in idate_L:
                    if idate == imagedate or idate in imagedate or imagedate in idate:
                        platformimagedatepath = os.path.join(platformpath, idate)
                        if self.findfile.isdir(platformimagedatepath):
                            if product:
                                productpath = os.path.join(platformimagedatepath, product)
                                if self.findfile.isdir(productpath):
                                    platformimagedatepath_L.append(platformimagedatepath)
                            else:
                                platformimagedatepath_L.append(platformimagedatepath)
                    else:
                        #来个相似搜索
                        pass
            platformimagedatepath_L_len = len(platformimagedatepath_L)
            if not platformimagedatepath_L:
                self.printcolor.printerror("not search out '%s' in [%s]" % (imagedate, androidpath))
                return 1
            elif platformimagedatepath_L_len >= 1:
                self.printcolor.printinfo("found more '%s' in [%s],which do you want? [%s - %s] or exit?" % (imagedate, androidpath, 0, platformimagedatepath_L_len - 1))
                if platformimagedatepath_L_len > self.printlistmax:
                    for i in range(0, self.printlistmax):
                        print "[%4s]%10s %s" % (i,os.path.basename(os.path.dirname(platformimagedatepath_L[i])), os.path.basename(platformimagedatepath_L[i]))
                    self.printcolor.printwarning("so many '%s'! I cann't list all, just list top %s" % (imagedate, self.printlistmax))
                    return 1

                for i in range(0, platformimagedatepath_L_len):
                    print "[%4s]%10s %s" % (i,os.path.basename(os.path.dirname(platformimagedatepath_L[i])), os.path.basename(platformimagedatepath_L[i]))
                choice = raw_input("please input [%s - %s]" % (0, platformimagedatepath_L_len - 1))
                try:
                    index = int(choice)
                except:
                    self.printcolor.printwarning("exit")
                    sys.exit(1)
                if index > platformimagedatepath_L_len - 1 or index < 0:
                    self.printcolor.printerror("[%s]out of index" % index)
                    sys.exit(1)

                self.platformpath = os.path.dirname(platformimagedatepath_L[index])
                self.imagedate = os.path.basename(platformimagedatepath_L[index])
                self.printcolor.printinfo("your choice is [%s], %s, %s" % (index, self.platformpath, self.imagedate))
        elif imagedatepath_L_len > 1:
            #找到了多个imagedate的folder
            self.printcolor.printinfo("found more '%s' in [%s],which do you want? [%s - %s] or exit?" % (imagedate, androidpath, 0, imagedatepath_L_len - 1))
            if imagedatepath_L_len > self.printlistmax:
                for i in range(0, self.printlistmax):
                    print "[%4s]" % i, imagedatepath_L[i]

                self.printcolor.printwarning("so many '%s'! I cann't list all, just list top %s" % (imagedate, self.printlistmax))
                return 1
            for i in range(0, imagedatepath_L_len):
                print "[%4s]" % i, imagedatepath_L[i]

            choice = raw_input("please input [%s - %s]" % (0, imagedatepath_L_len - 1))
            try:
                index = int(choice)
            except ValueError as e:
                self.printcolor.printwarning("exit")
                sys.exit(1)
            if index > imagedatepath_L_len - 1 or index < 0:
                self.printcolor.printerror("[%s]out of index" % index)
                sys.exit(1)

            self.platformpath = os.path.dirname(imagedatepath_L[index])
            self.imagedate = os.path.basename(imagedatepath_L[index])
        else:
            #找到了1个imagedate的folder
            self.platformpath = os.path.dirname(imagedatepath_L[0])
            self.imagedate = os.path.basename(imagedatepath_L[0])

        return 0


    #mount daily build burn class -> ()
    def select_product(self, platformpath="", imagedate=""):
        platformpath = self.platformpath if platformpath == "" else platformpath
        imagedate = self.imagedate if imagedate == "" else imagedate

        #platformpath + imagedate
        platformimagedatepath = os.path.join(platformpath, imagedate)

        product_L = self.findfile.listdir(platformimagedatepath)
        product_L_len = len(product_L)

        productfolder_L = []
        for i in range(0, product_L_len):
            #platformpath + imagedate + product
            platformimagedateproductpath = os.path.join(platformimagedatepath, product_L[i])
            #判断是否是个目录不是就pass了
            if self.findfile.isdir(platformimagedateproductpath):
                productfolder_L.append(product_L[i])
        productfolder_L_len = len(productfolder_L)

        if not productfolder_L:
            self.printcolor.printerror("not found any product in [%s]" % (platformimagedatepath))
            return 1
        elif productfolder_L_len > 1:
            self.printcolor.printinfo("found more product in [%s], which do you want? [%s - %s] or exit?" % (platformimagedatepath, 0, productfolder_L_len-1) )
            if productfolder_L_len > self.printlistmax:
                for i in range(0,  self.printlistmax):
                    print "[%2s]" % i,productfolder_L[i]

                self.printcolor.printwarning("so many product! I cann't list all, just list top %s" % (self.printlistmax))
                return 1
            for i in range(0, productfolder_L_len):
                print "[%2s]" % i,productfolder_L[i]
            choice = raw_input("please input [%s - %s]" % (0, productfolder_L_len - 1))
            try:
                index = int(choice)
            except ValueError as e:
                self.printcolor.printwarning("exit")
                sys.exit(1)
            if index > productfolder_L_len -1 or index < 0:
                self.printcolor.printerror("[%s]out of index" % index)
                sys.exit(1)
            self.product = productfolder_L[index]
            self.printcolor.printinfo("your choice product [%s]" % self.product)
        else:
            self.product = productfolder_L[0]
            self.printcolor.printinfo("your choice product [%s]" % self.product)
        return 0

    #imagedate and product 都没设置的话先选择 platform的路径s    然后设置选择imagedate
    def select_imagedate(self, platformpath="", product=""):
        #/dailybuild/android/pxa988这是platform路径
        platformpath = self.platformpath if platformpath == "" else platformpath

        product = self.product if product == "" else product

        imagedate_L = self.findfile.listdir(platformpath)
        imagedate_L_len = len(imagedate_L)

        imagedatefolder_L = []
        for i in range(0, imagedate_L_len):
            platformimagedate = os.path.join(platformpath, imagedate_L[i])
            if self.findfile.isdir(platformimagedate):
                if product:
                    platformimagedateproduct = os.path.join(platformimagedate, product)
                    if self.findfile.isdir(platformimagedateproduct):
                        imagedatefolder_L.append(imagedate_L[i])
                else:
                    imagedatefolder_L.append(imagedate_L[i])

        imagedatefolder_L_len = len(imagedatefolder_L)
        imagedatefolder_L.sort(reverse = True)
        if not imagedatefolder_L:
            self.printcolor.printerror("not found any imagedate in [%s]" % (platformpath))
            return 1
        elif imagedatefolder_L_len > 1:
            self.printcolor.printinfo("found %s imagedate folder in path [%s], which do you want? [%s - %s] or exit?" % (imagedatefolder_L_len, platformpath, 0, imagedatefolder_L_len-1) )
            if imagedatefolder_L_len > self.printlistmax:
                for i in range(0, self.printlistmax):
                    print "[%4s]" % i,imagedatefolder_L[i]
                self.printcolor.printwarning("so many imagedate! I cann't list all, just list top %s" % (self.printlistmax))
                return 1
            for i in range(0, imagedatefolder_L_len):
                print "[%4s]" % i,imagedatefolder_L[i]

            choice = raw_input("please input [%s - %s]" % (0, imagedatefolder_L_len - 1))
            try:
                index = int(choice)
            except ValueError as e:
                self.printcolor.printwarning("exit")
                sys.exit(1)
            if index > imagedatefolder_L_len -1 or index < 0:
                self.printcolor.printerror("[%s]out of index" % index)
                sys.exit(1)
            self.imagedate = imagedatefolder_L[index]
            self.printcolor.printinfo("your choice imagedate [%s]" % self.imagedate)
        else:
            self.imagedate = imagedatefolder_L[0]
            self.printcolor.printinfo("your choice imagedate [%s]" % self.imagedate)

        return 0


    #daily build burn class -> select_platformpath()
    #imagedate and product 都没设置的话先选择 platform的路径 然后设置选择imagedate
    def select_platformpath(self, dailybuildpath = ""):
        dailybuildpath = self.dailybuildpath if dailybuildpath == "" else dailybuildpath
        androidpath = os.path.join(dailybuildpath, self.androidpath)

        #判断是否是个folder，并且也判断了是否存在了
        if not self.findfile.isdir(androidpath):
            self.printcolor.printerror("[%s]is not a dir or not exist!" % (androidpath))
            return 1

        #列出androidpath目录下的所有的文件，包括文件夹。暂时没有过滤。目前应该都是文件夹。
        platform_L = self.findfile.listdir(androidpath)
        platform_L_len = len(platform_L)

        if not platform_L:
            self.printcolor.printerror("not found any platform in [%s]s" % (androidpath))
            return 1
        else:
            self.printcolor.printinfo("found %s platform, which do you want? [%s - %s] or exit?" % (platform_L_len, 0, platform_L_len - 1) )
            for i in range(0, platform_L_len):
                #这里没有过滤是否是个folder。暂时不过滤了。目前应该都是folder。
                print "[%2s]" % i, platform_L[i]

            choice = raw_input("please input [%s - %s] " %(0, platform_L_len - 1))
            try:
                index = int(choice)
            except ValueError as e:
                self.printcolor.printwarning("exit")
                sys.exit(1)
            if index > platform_L_len-1 or index < 0:
                self.printcolor.printerror("[%s]out of index" % index)
                sys.exit(1)
            self.platformpath = os.path.join(androidpath, platform_L[index])
            self.printcolor.printinfo("your choice platform [%s]" % self.platformpath)
        return 0



#ftp daily build burn
class FtpDailyBurn(DailyBurn):
    def __init__(self, imagedate, product, bif):
        #数据在class Burn()s里初始化
        super(FtpDailyBurn,self).__init__(imagedate=imagedate, product=product, bif=bif)

        if self.systemtype == "Linux":
            self.dailybuildpath= os.path.join("/","dailybuild")
        elif self.systemtype == "Windows":
            self.dailybuildpath= "\\dailybuild"
        else:
            self.dailybuildpath = ""


        self.host = "10.0.12.12"
        self.username = "autotest"
        self.password = "zeusis123"

        self.findfile = FindFtpFile(self.host, self.username, self.password)  # 这里会覆盖父类的这个变量


    #子类的ftp daily build burn class -> prepare_copy_swdl()
    def prepare_copy_swdl(self, local="", swdlname=""):
        self.localswdlfile = self.localbiffile
        self.localswdlpath = self.localbifpath
        self.swdlname = os.path.basename(self.localswdlfile)

        self.destswdlfile = os.path.join(self.destpath, self.swdlname)
        self.destswdlpath = self.destpath

        self.printcolor.printinfo("download(ftp) %s --> %s" % (self.localswdlfile, self.destpath))
        self.findfile.download(self.localswdlfile, self.destswdlfile)


    def is_samefile(self, f1, f2):
        #return filecmp.cmp(f1,f2)
        return False

    def is_difffile(self, f1, f2):
        return not self.is_samefile(f1,f2)

    def set_host(self, host):
        self.host = host
        self.findfile.set_host(host)

    def set_username(self, username):
        self.username = username
        self.findfile.set_username(username)

    def set_password(self, password):
        self.password = password
        self.findfile.set_password(password)


#http daily build burn
class HttpDailyBurn(DailyBurn):
    def __init__(self, imagedate, product, bif):
        #数据在class Burn()s里初始化
        super(HttpDailyBurn, self).__init__(imagedate=imagedate, product=product, bif=bif)

        if self.systemtype == "Linux":
            self.dailybuildpath= os.path.join("/","dailybuild")
        elif self.systemtype == "Windows":
            self.dailybuildpath= "\\dailybuild"
        else:
            self.dailybuildpath = ""

        self.host = "10.0.12.12"
        self.username = "autotest"
        self.password = "zeusis123"

        self.findfile = FindHttpFile()
        self.findfile.set_host(self.host)
        self.findfile.set_username(self.username)
        self.findfile.set_password(self.password)

    #子类的ftp daily build burn class -> prepare_copy_swdl()
    def prepare_copy_swdl(self, local="", swdlname="", swdlzipname=""):
        self.localswdlfile = self.localbiffile
        self.localswdlpath = self.localbifpath
        self.swdlname = os.path.basename(self.localswdlfile)

        self.destswdlfile = os.path.join(self.destpath, self.swdlname)
        self.destswdlpath = self.destpath

        self.printcolor.printinfo("download(http) %s --> %s" % (self.localswdlfile, self.destswdlfile))
        self.findfile.download(self.localswdlfile, self.destswdlfile)

    def is_samefile(self, f1, f2):
        #return filecmp.cmp(f1,f2)
        return False

    def is_difffile(self, f1, f2):
        return not self.is_samefile(f1,f2)

    def set_host(self, host):
        self.host = host
        self.findfile.set_host(host)

    def set_username(self, username):
        self.username = username
        self.findfile.set_username(username)

    def set_password(self, password):
        self.password = password
        self.findfile.set_password(password)

#samba daily build burn class
class SambaDailyBurn(DailyBurn):
    def __init__(self, imagedate, product, bif):
        #数据在class Burn()s里初始化
        super(SambaDailyBurn, self).__init__(imagedate=imagedate, product=product, bif=bif)

        if self.systemtype == "Linux":
            self.dailybuildpath= os.path.join("/","dailybuild")
        elif self.systemtype == "Windows":
            self.dailybuildpath= "\\dailybuild"
        else:
            self.dailybuildpath = ""


        self.host = "10.0.12.12"
        self.username = "autotest"
        self.password = "zeusis123"

        self.findfile = FindSambaFile(self.host, self.username, self.password)

    #end __init__()

    #子类的SambaDailyBurn class -> prepare_copy_swdl()
    def prepare_copy_swdl(self, local="", swdlname=""):
        self.localswdlfile = self.localbiffile
        self.localswdlpath = self.localbifpath
        self.swdlname = os.path.basename(self.localswdlfile)

        self.destswdlfile = os.path.join(self.destpath, self.swdlname)
        self.destswdlpath = self.destpath

        self.printcolor.printinfo("download(samba) %s --> %s" % (self.localswdlfile, self.destswdlfile))
        self.findfile.download(self.localswdlfile, self.destswdlfile)

    def is_samefile(self, f1, f2):
        #return filecmp.cmp(f1,f2)
        return False

    def is_difffile(self, f1, f2):
        return not self.is_samefile(f1,f2)

    def set_host(self, host):
        self.host = host
        self.findfile.set_host(host)

    def set_username(self, username):
        self.username = username
        self.findfile.set_username(username)

    def set_password(self, password):
        self.password = password
        self.findfile.set_password(password)

#end samba daily burn class

#mount daily build burn class
class MountDailyBurn(DailyBurn):
    def __init__(self, imagedate, product, bif):
        #数据在这里初始化
        super(MountDailyBurn, self).__init__(imagedate=imagedate, product=product, bif=bif)

        self.findfile = FindLocalFile()#mount也用findlocalfile类,因为都是本地的文件的操作，不像samba
    #end __init__()

    #子类的mount daily build burn class -> prepare_copy_swdl()
    def prepare_copy_swdl(self, local="", swdlname=""):
        self.localswdlfile = self.localbiffile
        self.localswdlpath = self.localbifpath
        self.swdlname = os.path.basename(self.localswdlfile)

        self.destswdlfile = os.path.join(self.destpath, self.swdlname)
        self.destswdlpath = self.destpath

        self.printcolor.printinfo("download(mount) %s --> %s" % (self.localswdlfile, self.destswdlfile))
        self.findfile.download(self.localswdlfile, self.destswdlfile)

#end class MountDailyBurn()

#local build burn class
class LocalBurn(Burn):
    def __init__(self, bif, local, destpath=""):
        super(LocalBurn, self).__init__(bif=bif,local=local,destpath=destpath)
        self.findfile = FindLocalFile()#localburn就用findlocalfile类,是本地的文件的操作，不像samba
    #end __init__()

    #local build burn class -> start()
    def start(self):
        if self.listimage:
            #print all image name in bif.
            self.list_allimagename()#pass
            return 0

        if self.onlycopy and self.onlyburn:
            self.printcolor.printerror('onlycopy or onlyburn?')
            return 1
        #1,这里就不需要准备imagedate和product了
        #if self.prepare_imagedate_product() != 0:
        #    return 1

        #2.准备 copy images，准备destpath路径。复制bif文件/修改bif文件，准备swdl。
        if self.prepare_copy_images() != 0:
            return 1

        if self.onlycopy:
            self.start_copy_images()
        else:
            self.start_copy_images()
            self.start_burn_images()
        return 0

    #local build burn class -> prepare_copy_swdl()
    #子类里重写的方法
    def prepare_copy_swdl(self, local="", swdlname="", swdlzipname=""):
        local = self.local if local == "" else local
        swdlname = self.swdlname if swdlname == "" else swdlname
        swdlzipname = self.swdlzipname if swdlzipname == "" else swdlzipname

        swdl_L = self.findfile.findfile(local, swdlname)
        swdl_L_len = len(swdl_L)
        #1先找swdl位置、没找到的话找swdl.zip的位置
        if not swdl_L:
            #(1).not found swdl, then find swdlzip/
            self.printcolor.printwarning("not found %s, then will try to find %s" % (swdlname, swdlzipname))
            swdlzip_L = self.findfile.findfile(local, swdlzipname)
            swdlzip_L_len = len(swdlzip_L)
            if not swdlzip_L:
                #(1.1) swdl.zip 也没找到的话估计是没法烧image了
                self.printcolor.printwarning("not found %s" % swdlzipname)
                return 1
            elif swdlzip_L_len > 1:
                #(1.2)找到了多个swdl.zip文件
                self.printcolor.printinfo("found more %s ,which do you want? [%s - %s] or exit?" % (swdlzipname, 0, swdlzip_L_len - 1))
                if swdlzip_L_len > self.printlistmax:
                    for i in range(0, self.printlistmax):
                        print "[%s]" % i, swdlzip_L[i]
                    return 1
                for i in range(0, swdlzip_L_len):
                    print "[%s]" % i, swdlzip_L[i]
                choice = raw_input("please input [%s - %s] " %(0, swdlzip_L_len - 1))
                try:
                    index = int(choice)
                except ValueError as e:
                    self.printcolor.printwarning("exit")
                    sys.exit(1)
                if index > swdlzip_L_len -1 or index < 0:
                    self.printcolor.printerror("[%s]out of index" % index)
                    sys.exit(1)
                self.localswdlzipfile = swdlzip_L[index]
                self.localswdlzippath = os.path.dirname(self.localswdlzipfile)
            else:
                #(1.3)只找到一个zip，这个就好办了
                self.printcolor.printwarning("found 1 %s" % (swdlzipname))
                self.localswdlzipfile = swdlzip_L[0]
                self.localswdlzippath = os.path.dirname(self.localswdlzipfile)
            #到此是没找到swdl bin 文件 而是 找到swdl.zip 文件了，

            #unzip swdl.zip to this folder
            self.findfile.unzip(self.localswdlzipfile, self.destpath)

            #到这来我们把swdl.zip解压到destpath里，之后后find_dest_path()来设置destswdlpath,
            #destswdlpath里面或建bif目录。

            return 0
        #2.找到多个swdl文件，一般情况应该不会找到多个吧
        elif swdl_L_len > 1:
            self.printcolor.printinfo("found more %s ,which do you want? [%s - %s] or exit?" % (self.swdlname, 0, swdl_L_len - 1))
            if swdl_L_len > self.printlistmax:
                for i in range(0, self.printlistmax):
                    print "[%s]" % i, swdl_L[i]
                self.printcolor.printwarning("so many %s! I cann't list all, just list top %s" % (self.swdlname, self.printlistmax))
                return 1
            for i in range(0, swdl_L_len):
                print "[%s]" % i, swdl_L[i]
            choice = raw_input("please input [%s - %s] " %(0, swdl_L_len - 1))
            try:
                index = int(choice)
            except ValueError as e:
                self.printcolor.printinfo("exit")
                sys.exit(1)
            if index > swdl_L_len - 1 or index < 0:
                self.printcolor.printerror("[%s]out of index" % index)
                sys.exit(1)

            self.localswdlfile = swdl_L[index] #路径+swdl文件名
            self.localswdlpath = os.path.dirname(self.localswdlfile) #只有路径

            self.printcolor.printinfo("your choice: %s" % self.localswdlfile)

            self.destswdlpath = self.destpath
            self.destswdlfile = os.path.abspath(os.path.join(self.destswdlpath, self.swdlname))

            shutil.copy(self.localswdlfile, self.destswdlpath)
        #找到一个,这有可能就是上次烧过image的目录，之后判断bif文件，image的位置是否正确
        else:
            self.printcolor.printinfo("only found 1 %s" % self.swdlname)

            self.localswdlfile = swdl_L[0] #路径+swdl文件名
            self.localswdlpath = os.path.dirname(self.localswdlfile) #只有路径

            self.destswdlpath = self.destpath
            self.destswdlfile = os.path.abspath(os.path.join(self.destswdlpath, self.swdlname))

            shutil.copy(self.localswdlfile, self.destswdlpath)
        return 0

#end class LocalBurn()


#class FindFile() 父类
class FindFile(object):
    def __init__(self):
        #os的类型，Linux还是windows
        self.systemtype = platform.system()

        self.path = ""
        self.filename = ""

    def set_path(self,path):
        self.path=path

    def set_filename(self,filename):
        self.filename=filename

    #find the file, 子类会重写此方法
    def findfile(self, path = "", filename = "", pattern = None):
        path = self.path if path == "" else path
        filename = self.filename if filename == "" else filename
        filepath_L = []
        if pattern is None:
            for root, dirs, files in os.walk(path):
                for f in files:
                    if f == filename:
                        filepath_L.append(os.path.join(root, f))
        else:
            for root, dirs, files in os.walk(path):
                for f in files:
                    if fnmatch.fnmatch(f, pattern):
                        filepath_L.append(os.path.join(root, f))
        return filepath_L

    #find the local file,这里确实需要一个localfile方法来查找destpath目录下的文件
    def localfile(self, path = "", filename = "", pattern = None):
        path = self.path if path == "" else path
        filename = self.filename if filename == "" else filename
        filepath_L = []
        if pattern is None:
            for root, dirs, files in os.walk(path):
                for f in files:
                    if f == filename:
                        filepath_L.append(os.path.join(root, f))
        else:
            for root, dirs, files in os.walk(path):
                for f in files:
                    if fnmatch.fnmatch(f, pattern):
                        filepath_L.append(os.path.join(root, f))
        return filepath_L

    #download file from if local will use copy
    def download(self, srcfile, destfile):
        shutil.copy(srcfile, destfile)
        return 0

    #to check is a dir
    def isdir(self, mpath):
        mpath = self.path if mpath == "" else mpath
        return os.path.isdir(mpath)

    #to check is a common file
    def isfile(self, path):
        path = self.path if path == "" else path
        return os.path.isfile(path)

    #判断文件或者目录是否存在
    def exists(self, path):
        path = self.path if path == "" else path
        return os.path.exists(path)

    #给定一个samba路径(像这样的：/dailybuild/android/)，列出所有的文件，文件夹，出去.和.."""
    def listdir(self, path):
        path = self.path if path == None else path

        return os.listdir(path)

    #
    #读取一个文件，一般会是bif文件。
    #可以是smb服务器上的,这样只能用read()，然后需要split()获取一个行内容的list
    #如果是本地的文件，就直接readlines(),然后直接获得了一个行内容的list
    #
    def get_file_lines_L(self, path):
        path = self.path if path == None else path

        fd = open(path, "r")
        lines_L = fd.readlines()
        fd.close()
        return lines_L


    #unzip zip file to dest folder
    def unzip(self, zpfile, destDir):
        zfile = zipfile.ZipFile(zpfile)
        for name in zfile.namelist():
            (dirName, fileName) = os.path.split(name)
            #check if the directory exists
            newDir = os.path.join(destDir, dirName)
            if not os.path.exists(newDir):
                os.makedirs(newDir)
            if not fileName == '':
                #file
                fd = open(os.path.join(destDir, name), 'wb')
                fd.write(zfile.read(name))
                fd.flush()
                fd.close()
        zfile.close()
#end class FindFile()

class FindLocalFile(FindFile):
    def __init__(self):
        super(FindLocalFile, self).__init__()

#end class FindLocalFile(FindFile)

class FindHttpFile(FindFile):
    def __init__(self):
        super(FindHttpFile, self).__init__()

        self.host = ""
        self.username = ""
        self.password = ""

        self.isdir_L = []
        self.isfile_L = []

    def set_host(self, host):
        self.host = host

    def set_username(self, username):
        self.username = username

    def set_password(self, password):
        self.password = password

    def findfile(self, httppath="", filename="", pattern=None):
        filehttppath_L = []

        if self.systemtype=="Windows":
            httppath = httppath.replace("\\", "/")

        httpfile_L = self.listdir(httppath)
        for httpfile in httpfile_L:
            if httppath[-1] == "/":
                httpfilepath="%s%s" % (httppath,httpfile)
            else:
                httpfilepath="%s/%s" % (httppath,httpfile)
            if self.isdir(httpfilepath):
                filehttppath_L.extend(self.findfile(httpfilepath, filename, pattern))
            else:
                if pattern is None:
                    if httpfile == filename:
                        filehttppath_L.append(httpfilepath)
                else:
                    if fnmatch.fnmatch(httpfile, pattern):
                        filehttppath_L.append(httpfilepath)

        return filehttppath_L


    def download(self,httpfile, destfile):
        httpfile = self.path_to_httppath(httpfile)
        f=urllib2.urlopen(httpfile)
        fd=open(destfile,"wb")
        while True:
            data=f.read(1024*1024)
            if data:
                fd.write(data)
            else:
                break


    def path_to_httppath(self,httppath):
        if self.systemtype=="Windows":
            httppath = httppath.replace("\\", "/")

        if httppath[0:6] == "http://":
            pass
        else:
            if httppath[0] == "/":
                httppath = "http://%s%s" % (self.host, httppath)
            else:
                httppath = "http://%s/%s" % (self.host, httppath)

        return httppath

    def isdir(self,httppath):
        if httppath == "":return False
        if fnmatch.fnmatch(httppath, "*.img"): return False
        if fnmatch.fnmatch(httppath, "*img"): return False
        if fnmatch.fnmatch(httppath, "*.tgz"): return False
        if fnmatch.fnmatch(httppath, "*.mdb"): return False
        if fnmatch.fnmatch(httppath, "*.txt"): return False
        if fnmatch.fnmatch(httppath, "*uImage"): return False
        if fnmatch.fnmatch(httppath, "*vmlinux"): return False
        if fnmatch.fnmatch(httppath, "*.bin"): return False
        if fnmatch.fnmatch(httppath, "*.map"): return False
        if fnmatch.fnmatch(httppath, "*.zip"): return False

        httppath = self.path_to_httppath(httppath)
        if httppath in self.isdir_L:
            return True
        if httppath in self.isfile_L:
            return False

        httppathdirname = os.path.dirname(httppath)
        httppathbasename = os.path.basename(httppath)
        try:
            html = urllib2.urlopen(httppathdirname).read()
            html_L = html.split("<br>")
            for hl in html_L:
                if httppathbasename in hl:
                    if "&lt;dir&gt;" in hl:
                        self.isdir_L.append(httppath)
                        return True
                    else:
                        return False
                else:
                    try:
                        html = urllib2.urlopen(httppath).read()
                    except urllib2.HTTPError as e:
                        return False
                    if "[To Parent Directory]" in html:
                        self.isdir_L.append(httppath)
                        return True
                    else:
                        return False
        except urllib2.HTTPError as e:
            return False

    def isfile(self,httppath):
        if httppath == "":return False

        httppath = self.path_to_httppath(httppath)

        if httppath in self.isfile_L:
            return True

        if httppath in self.isdir_L:
            return False

        try:
            html = urllib2.urlopen(httppath).read()
        except urllib2.HTTPError as e:
            return False

        if "&lt;dir&gt;" in html and "[To Parent Directory]" in html:
            return False
        else:
            return True

    def exists(self,httppath):
        if self.isdir(httppath) or self.isfile(httppath):
            return True
        else:
            return False

    def listdir(self,httppath):
        httppath = self.path_to_httppath(httppath)

        html = urllib2.urlopen(httppath).read()
        html_L=html.split("<br>")
        file_L = [re.findall("<A.*?>(.*?)</A>", h) for h in html_L]
        file_L = [f[0] for f in file_L if len(f)==1 and f[0] != "[To Parent Directory]"]

        #把目录和普通文件的路径存下来。以空间来换取时间加快判断。
        folder_L = [re.findall("<A.*?>(.*?)</A>", h) for h in html_L if "&lt;dir&gt;" in h]
        folder_L = [f[0] for f in folder_L if len(f)==1]
        self.isdir_L = ["%s/%s" % (httppath, f) for f in folder_L]

        #把目录和普通文件的路径存下来。以空间来换取时间加快判断。
        normalfile_L = [re.findall("<A.*?>(.*?)</A>", h) for h in html_L if "&lt;dir&gt;" not in h]
        normalfile_L = [f[0] for f in normalfile_L if len(f)==1]
        self.isfile_L =  ["%s/%s" % (httppath, f) for f in normalfile_L]

        return file_L

    def get_file_lines_L(self,httppath):
        httppath = self.path_to_httppath(httppath)

        html = urllib2.urlopen(httppath).read()
        filelines_L=html.splitlines()
        return filelines_L

class FindFtpFile(FindFile):
    def __init__(self, host="", username="", password=""):
        super(FindFtpFile, self).__init__()

        self.host = host
        self.username = username
        self.password = password

        self.isdir_L = []
        self.isfile_L = []

        self.ftp = ftplib.FTP(self.host,self.username,self.password,timeout=300)

    def set_host(self, host):
        self.host = host
        self.set_ftp()

    def set_username(self, username):
        self.username = username
        self.set_ftp()

    def set_password(self, password):
        self.password = password
        self.set_ftp()

    def set_ftp(self):
        self.ftp.connect(self.host)
        self.ftp.login(self.username, self.password)

    def findfile(self, path = "", filename = "", pattern = None):
        #注意windows模式下，路径需要转换为ftp的统一的路径
        if self.systemtype == "Windows":
            path = path.replace("\\","/")
        #最后返回的结果，是一个list
        fileftppath_L = []

        ftpfile_L = self.ftp.nlst(path)

        for ftpfile in ftpfile_L:
            ftpfilename = os.path.basename(ftpfile)
            if self.isdir(ftpfile) and ftpfilename != "debug" and ftpfilename != "ota":
                #递归调用
                fileftppath_L.extend(self.findfile(ftpfile, filename, pattern))
            else:
                if pattern is None:
                    if ftpfilename == filename:
                        fileftppath_L.append(ftpfile)
                else:
                    if fnmatch.fnmatch(ftpfilename, pattern):
                        fileftppath_L.append(ftpfile)

        return fileftppath_L

    #download file from ftp server
    def download(self,ftpfile, destfile):
        #注意windows模式下，路径需要转换为ftp的统一的路径
        if self.systemtype == "Windows":
            ftpfile = ftpfile.replace("\\","/")

        #多线程下不能用self.ftp，需要重新建立一个ftp对象
        #ftp = ftplib.FTP(self.host,self.username,self.password, timeout=300)
        fd_local = open(destfile, "wb")
        #这里得是retrbinary，二进制模式
        self.ftp.retrbinary("RETR %s" % ftpfile, fd_local.write)
        fd_local.close()
        return 0

    def isdir(self,ftppath):
        #注意windows模式下，路径需要转换为ftp的统一的路径
        if self.systemtype == "Windows":
            ftppath = ftppath.replace("\\","/")

        if ftppath in self.isfile_L:
            return False
        if ftppath in self.isdir_L:
            return True

        isdir = False
        try:
            file_L = []
            self.ftp.dir(ftppath, file_L.append)
            file_L_len = len(file_L)
            if not file_L:
                isdir = False
            elif file_L_len > 1:
                isdir = True
            else:
                if file_L[0].startswith("d"):
                    isdir = True
                else:
                    isdir = False
        except ftplib.error_perm:
            pass
        return isdir

    def isfile(self,ftppath):
        #注意windows模式下，路径需要转换为ftp的统一的路径
        if self.systemtype == "Windows":
            ftppath = ftppath.replace("\\","/")

        if ftppath in self.isfile_L:
            return True
        if ftppath in self.isdir_L:
            return False

        file_L = []
        self.ftp.nlst(ftppath, file_L.append)

        file_L_len = len(file_L)
        if not file_L:
            #不存在此文件或者是个空目录
            return False
        elif file_L_len > 1:
            return False
        else:
            if file_L[0].startswith("-"):
                return True
            else:
                return False

    def exists(self,ftppath):
        if not ftppath:
            return False
        #注意windows模式下，路径需要转换为ftp的统一的路径
        if self.systemtype == "Windows":
            ftppath = ftppath.replace("\\","/")

        file_L = self.ftp.nlst(ftppath)
        file_L_len = len(file_L)
        if not file_L:
            #是个空目录
            return False
        elif file_L_len > 0:
            return True

    def listdir(self,ftppath):
        #注意windows模式下，路径需要转换为ftp的统一的路径
        if self.systemtype == "Windows":
            ftppath = ftppath.replace("\\","/")

        #把目录和普通文件的路径存下来。以空间来换取时间加快判断。
        dirs_L = []
        self.ftp.dir(ftppath, dirs_L.append)
        for line in dirs_L:
            if line.startswith("d"):
                folder = line.split(" ")[-1]
                self.isdir_L.append("%s/%s" % (ftppath, folder))
            elif line.startswith("-"):
                folder = line.split(" ")[-1]
                self.isfile_L.append("%s/%s" % (ftppath, folder))

        file_L = self.ftp.nlst(ftppath)
        return [os.path.basename(f) for f in file_L]

    def get_file_lines_L(self,ftppath):
        #注意windows模式下，路径需要转换为ftp的统一的路径
        if self.systemtype == "Windows":
            ftppath = ftppath.replace("\\","/")

        stringio=StringIO.StringIO()
        cmd = "RETR %s" % ftppath
        self.ftp.retrbinary(cmd, stringio.write)
        stringio.seek(0)
        filelines_L = stringio.readlines()
        return filelines_L

class FindSambaFile(FindFile):
    def __init__(self, host="", username="", password=""):
        super(FindSambaFile, self).__init__()

        self.isdir_L = []
        self.isfile_L = []

        self.smbdomain = ""

        self.host = host
        self.username = username
        self.password = password

    def set_smbdomain(self,domain):
        self.smbdomain=domain

    def set_host(self, host):
        self.host = host

    def set_username(self, username):
        self.username = username

    def set_password(self, password):
        self.password = password

    def __do_auth(self, server, security, workgroup, username, password):
        return (self.smbdomain, self.username, self.password)

    #find smb file
    def findfile(self, path = "", filename = "", pattern = None):
        #这个是带smb://的path
        smbpath = self.path if path == "" else path
        #这个是正常的path
        path = self.path if path == "" else path

        filename = self.filename if filename == "" else filename

        filesmbpath_L = []
        if filename.strip() == "" and pattern is None:
            return filesmbpath_L

        #如果是windows系统就不能用samba这种方式了
        if self.systemtype == "Windows":
            #window下路径要加上host，这是为了统一
            path = "\\\\%s\\%s" % (self.host, path)

            filepath_L = []
            if pattern is None:
                if os.path.exists(os.path.join(path, filename)):
                    root = path.replace("\\\\%s\\" % (self.host), "")
                    filepath_L.append(os.path.join(root, filename))
                else:
                    for root, dirs, files in os.walk(path):
                        #window下要把host去掉，这是为了统一
                        if "debug" in dirs: dirs.remove("debug") # 这里优化一下，过滤掉 debug 和 ota目录
                        if "ota" in dirs: dirs.remove("ota")
                        root = root.replace("\\\\%s\\" % (self.host), "")
                        if filename in files:
                            filepath_L.append(os.path.join(root, filename))
            else:
                for root, dirs, files in os.walk(path):
                    #window下要把host去掉，这是为了统一
                    if "debug" in dirs: dirs.remove("debug")
                    if "ota" in dirs: dirs.remove("ota")
                    root = root.replace("\\\\%s\\" % (self.host), "")
                    for f in files:
                        if fnmatch.fnmatch(f, pattern):
                            filepath_L.append(os.path.join(root, f))
            return filepath_L
        else:
            #try to import smbc,貌似ubutnu默认安装这个了
            try:
                import smbc
            except ImportError as e:
                print e
                return filesmbpath_L

        #smbpath做一些特殊的处理和判断，path就不用
        if smbpath[0:5] == "smb://":
            pass
        else:
            if smbpath[0] == "/":
                smbpath = "smb://%s%s" % (self.host, smbpath)
            else:
                smbpath = "smb://%s/%s" % (self.host, smbpath)

        filesmbpath_L = []
        ctx = smbc.Context(debug=0, auth_fn=self.__do_auth)
        try:
            #这里只能打开smbpath
            fd = ctx.opendir(smbpath)
        except smbc.NoEntryError as e:
            print e,smbpath
        except smbc.TimedOutError as e:
            print e,smbpath
        else:
            entries = fd.getdents()
            for entry in entries:
                if path[-1] == "/":
                    #这里只要path，都统一一下
                    smbfilepath = path + entry.name
                else:
                    smbfilepath = path + "/" + entry.name
                # smbc_type == 7 this is a dir
                if entry.smbc_type == 7 and entry.name != "." and entry.name != ".." and entry.name != "debug" and entry.name != "ota":
                    filesmbpath_L.extend(self.findfile(smbfilepath, filename, pattern))
                # smbc_type == 8 this is a file
                elif entry.smbc_type == 8:
                    #pattern is None就需要精确匹配
                    if pattern is None:
                        if entry.name == filename:
                            filesmbpath_L.append(smbfilepath)
                    else:
                        if fnmatch.fnmatch(entry.name, pattern):
                            filesmbpath_L.append(smbfilepath)

        return filesmbpath_L


    #download file from samba server
    def download(self, smbfile, destfile):
        #如果是windows系统就不能用samba这种方式了
        if self.systemtype == "Windows":
            smbfile = "\\\\%s\\%s" % (self.host, smbfile)
            shutil.copy(smbfile, destfile)
            return 0
        else:
            #try to import smbc,貌似ubutnu默认安装这个了
            try:
                import smbc
            except ImportError as e:
                print e
                return False
        if smbfile[0:5] == "smb://":
            pass
        else:
            if smbfile[0] == "/":
                smbfile = "smb://%s%s" % (self.host, smbfile)
            else:
                smbfile = "smb://%s/%s" % (self.host, smbfile)

        ctx = smbc.Context(auth_fn=self.__do_auth)
        try:
            fd_smb = ctx.open(smbfile)
        except smbc.NoEntryError as e:
            return 1
        except smbc.TimedOutError as e:
            return 1
        else:
            fd_local = open(destfile , "w")
            fd_local.write(fd_smb.read())
            fd_local.close()
        return 0

    def isdir(self, smbpath):
        smbpath = self.path if smbpath == "" else smbpath

        #如果是windows系统就不能用samba这种方式了
        if self.systemtype == "Windows":
            smbpath = "\\\\%s\\%s" % (self.host, smbpath)
            #windows 返回
            return os.path.isdir(smbpath)

        try:
            import smbc
        except ImportError as e:
            print e
            return False

        if smbpath[0:5] == "smb://":
            pass
        else:
            if smbpath[0] == "/":
                smbpath = "smb://%s%s" % (self.host, smbpath)
            else:
                smbpath = "smb://%s/%s" % (self.host, smbpath)

        if smbpath in self.isdir_L:
            return True
        if smbpath in self.isfile_L:
            return False

        ctx = smbc.Context(debug=0, auth_fn=self.__do_auth)
        try:
            fd = ctx.open(smbpath)
        except smbc.NoEntryError as e:
            return False
        except RuntimeError as e:
            #(21, 'Is a directory')
            if e[0] == 21:
                return True
            else:
                return False
        except ValueError as e:
            #很奇怪为什么会报这个错误？？
            return False
        else:
            fd.close()
            return False

    def isfile(self, path):
        smbpath = self.path if path == "" else path

        #如果是windows系统就不能用samba这种方式了
        if self.systemtype == "Windows":
            smbpath = "\\\\%s\\%s" % (self.host, smbpath)
            return os.path.isfile(smbpath)
        else:
            #try to import smbc,貌似ubutnu默认安装这个了
            try:
                import smbc
            except ImportError as e:
                print e
                return False
        if smbpath[0:5] == "smb://":
            pass
        else:
            if smbpath[0] == "/":
                smbpath = "smb://%s%s" % (self.host, smbpath)
            else:
                smbpath = "smb://%s/%s" % (self.host, smbpath)

        if smbpath in self.isdir_L:
            return False
        if smbpath in self.isfile_L:
            return True

        ctx = smbc.Context(debug=0, auth_fn=self.__do_auth)
        try:
            fd = ctx.open(smbpath)
        except smbc.NoEntryError as e:
            #(2, 'No such file or directory')
            return False
        except RuntimeError as e:
            #(21, 'Is a directory')
            return False
        except ValueError as e:
            #很奇怪为什么会报这个错误？？
            return False
        else:
            fd.close()
            return True

    #判断文件或者目录是否存在
    def exists(self, path):
        smbpath = self.path if path == "" else path

        #如果是windows系统就不能用samba这种方式了
        if self.systemtype == "Windows":
            smbpath = "\\\\%s\\%s" % (self.host, smbpath)
            return os.path.exists(smbpath)
        else:
            #try to import smbc,貌似ubutnu默认安装这个了
            try:
                import smbc
            except ImportError as e:
                print e
                return False
        if smbpath[0:5] == "smb://":
            pass
        else:
            if smbpath != "" and smbpath[0] == "/":
                smbpath = "smb://%s%s" % (self.host, smbpath)
            else:
                smbpath = "smb://%s/%s" % (self.host, smbpath)

        ctx = smbc.Context(debug=0, auth_fn=self.__do_auth)
        try:
            fd = ctx.open(smbpath)
        except smbc.NoEntryError as e:
            #(2, 'No such file or directory')
            return False
        except RuntimeError as e:
            #(21, 'Is a directory')
            if e[0] == 21:
                return True
            else:
                return False
        except ValueError as e:
            #很奇怪为什么会报这个错误？？
            return False
        else:
            fd.close()
            return True

    #给定一个samba路径(像这样的：/dailybuild/android/)，列出所有的文件，文件夹，出去.和..
    def listdir(self, path):
        smbpath = self.path if path == None else path

        #只包含文件夹的名字，不带路径
        filesmbpath_L = []

        #如果是windows系统就不能用samba这种方式了
        if self.systemtype == "Windows":
            smbpath = "\\\\%s\\%s" % (self.host, smbpath)
            return os.listdir(smbpath)
        else:
            #try to import smbc,貌似ubutnu默认安装这个了
            try:
                import smbc
            except ImportError as e:
                print e
                return False
        if smbpath[0:5] == "smb://":
            pass
        else:
            if smbpath[0] == "/":
                smbpath = "smb://%s%s" % (self.host, smbpath)
            else:
                smbpath = "smb://%s/%s" % (self.host, smbpath)


        ctx = smbc.Context(debug=0, auth_fn=self.__do_auth)
        try:
            fd = ctx.opendir(smbpath)
        except smbc.NoEntryError as e:
            return filesmbpath_L
        except RuntimeError as e:
            return filesmbpath_L
        else:
            entries = fd.getdents()
            for entry in entries:
                #把目录和普通文件的路径存下来。以空间来换取时间加快判断。
                if entry.smbc_type == 7:
                    self.isdir_L.append("%s/%s" % (smbpath, entry.name))
                if entry.smbc_type == 8:
                    self.isfile_L.append("%s/%s" % (smbpath, entry.name))

                #暂时不过滤目录smbc_type == 7 ，舍去.和..目录
                if entry.name != "." and entry.name != "..":
                    filesmbpath_L.append(entry.name)

        return filesmbpath_L


    #读取一个文件，一般会是bif文件。
    #可以是smb服务器上的,这样只能用read()，然后需要split()获取一个行内容的list
    #如果是本地的文件，就直接readlines(),然后直接获得了一个行内容的list
    def get_file_lines_L(self, path):
        smbpath = self.path if path == None else path
        if self.systemtype == "Windows":
            smbpath = "\\\\%s\\%s" % (self.host, smbpath)
            fd = open(smbpath, "r")
            lines_L = fd.readlines()
            fd.close()
            return lines_L
        else:
            #try to import smbc,貌似ubutnu默认安装这个了
            try:
                import smbc
            except ImportError as e:
                print e
                return False
        if smbpath[0:5] == "smb://":
            pass
        else:
            if smbpath[0] == "/":
                smbpath = "smb://%s%s" % (self.host, smbpath)
            else:
                smbpath = "smb://%s/%s" % (self.host, smbpath)

        ctx = smbc.Context(debug=0, auth_fn=self.__do_auth)
        try:
            fd = ctx.open(smbpath)
        except smbc.NoEntryError as e:
            #(2, 'No such file or directory')
            return []
        except RuntimeError as e:
            #(21, 'Is a directory')
            return []
        except ValueError as e:
            #很奇怪为什么会报这个错误？？
            return []
        else:
            #读取文件，并分割
            lines_L = fd.read().split("\n")
            fd.close()
            return lines_L

#end class FindSambaFile(FindFile)

class SwdlDriver():
    def __init__(self):
        self.systemtype = platform.system()
        self.host = "10.38.120.30"
        self.username = "anonymous"
        self.password = ""

        self.wtptpdriverzipname = "wtptp_driver.zip"
        self.wtptpdriverzippath = "/share"
        self.wtptpdriverzipfile = os.path.join(self.wtptpdriverzippath, self.wtptpdriverzipname)

        self.findfile = FindFile()

        self.localwtptpdriverzipfile = ""
        self.localwtptpdriverzippath = ""


    def get_ftp_driver_zip(self, ftpfile = ""):
        ftpfile = self.wtptpdriverzipfile if ftpfile == "" else ftpfile
        if self.systemtype == "Linux":
            tmppath = tempfile.mkdtemp()
            tmpfile = os.path.join(tmppath, self.wtptpdriverzipname)

            localfile = open(tmpfile, "wb")
            ftp = ftplib.FTP(self.host, self.username, self.password, timeout=30)
            ftp.retrbinary("RETR %s" % ftpfile, localfile.write)
            ftp.quit()
            localfile.close()

            self.localwtptpdriverzipfile = tmpfile
            self.localwtptpdriverzippath = tmppath

            return 0
        elif self.systemtype == "Windows":
            return 0
        else:
            return 0

    def make_wtptp_driver(self):
        #判断存在
        if os.path.exists(self.localwtptpdriverzipfile):
            #解压zip文件
            self.findfile.unzip(self.localwtptpdriverzipfile, self.localwtptpdriverzippath)
            makefile_L = self.findfile.localfile(self.localwtptpdriverzippath, "Makefile")

            if not makefile_L:
                return 1
            else :
                makefilefile = makefile_L[0]
                makefilepath = os.path.dirname(makefilefile)

                oldcwd = os.getcwd()

                os.chdir(makefilepath)
                ret = os.system("make")
                if ret == 0:
                    self.installdriver("./wtptp.ko")

                os.chdir(oldcwd)
            return 0
        else:
            return 1

    def installdriver(self, driverko = ""):
        if self.systemtype == "Linux":
            if self.checkdriver():
                return 0
            else:
                if driverko:
                    ret = os.system("sudo insmod %s" % driverko)
                else:
                    #先下载zip文件
                    if self.get_ftp_driver_zip() != 0:
                        return 1
                    ret = self.make_wtptp_driver()

                return ret
        elif self.systemtype == "Windows":
            return 0
        else:
            return 1

    def reinstalldriver(self, driverko = ""):
        if self.systemtype == "Linux":
            if self.checkdriver():
                self.uninstalldriver()
            if driverko:
                ret = os.system("sudo insmod %s" % driverko)
            else:
                #先下载zip文件
                if self.get_ftp_driver_zip() != 0:
                    return 1
                ret = self.make_wtptp_driver()
            return ret
        elif self.systemtype == "Windows":
            return 0
        else:
            return 1

    def uninstalldriver(self, driverko="wtptp"):
        if self.systemtype == "Linux":
            ret = os.system("sudo rmmod %s" % driverko)
        elif self.systemtype == "Windows":
            pass
        else:
            pass

    def checkdriver(self, driverko="wtptp"):
        if self.systemtype == "Linux":
            ret = os.system("lsmod|grep '%s' 1>/dev/null 2>/dev/null" % driverko)
            return True if ret == 0 else False
        elif self.systemtype == "Windows":
            return os.path.exists("C:\\Windows\\System32\\drivers\\WTPTP.sys")
        else:
            return False
#end class SwdlDriver()

class PrintColor():
    def __init__(self, level="", color="", quiet=False):
        self.quiet = quiet
        self.level = level
        self.color = color
        self.systemtype = platform.system()
        if self.systemtype == "Windows":
            self.STD_INPUT_HANDLE = -10
            self.STD_OUTPUT_HANDLE= -11
            self.STD_ERROR_HANDLE = -12

            self.FOREGROUND_BLACK  = 0x0
            self.FOREGROUND_BLUE   = 0x01 # text color contains blue
            self.FOREGROUND_GREEN  = 0x02 # text color contains green
            self.FOREGROUND_CYAN   = 0x03 # text color contains cyan
            self.FOREGROUND_RED    = 0x04 # text color contains red
            self.FOREGROUND_PINK   = 0x05 # text color contains pink
            self.FOREGROUND_YELLOW = 0x06 # text color contains yellow
            self.FOREGROUND_WHITE  = 0x07 # text color contains red
            self.FOREGROUND_GRAY   = 0x08 # text color contains red

            self.FOREGROUND_HBLUE   = 0x09 # text color contains highlight blue
            self.FOREGROUND_HGREEN  = 0x0a # text color contains highlight green
            self.FOREGROUND_CYAN    = 0x0b # text color contains cyan
            self.FOREGROUND_HRED    = 0x0c # text color contains highlight red
            self.FOREGROUND_HPINK   = 0x0d # text color contains highlight pink
            self.FOREGROUND_HYELLOW = 0x0e # text color contains highlight yellow
            self.FOREGROUND_HWHITE  = 0x0f # text color contains highlight white
            self.std_out_handle = ctypes.windll.kernel32.GetStdHandle(self.STD_OUTPUT_HANDLE)
        elif self.systemtype == "Linux":
            self.FOREGROUND_BLACK   = 30 # black
            self.FOREGROUND_HBLUE   = 34 # text color contains highlight blue
            self.FOREGROUND_HGREEN  = 32 # text color contains highlight green
            self.FOREGROUND_CYAN    = 36 # text color contains cyan
            self.FOREGROUND_HRED    = 31 # text color contains highlight red
            self.FOREGROUND_HPINK   = 35 # text color contains highlight pink
            self.FOREGROUND_HYELLOW = 33 # text color contains highlight yellow
            self.FOREGROUND_HWHITE  = 37 # text color contains highlight white
        else:
            self.FOREGROUND_BLACK   = 0
            self.FOREGROUND_HBLUE   = 0
            self.FOREGROUND_HGREEN  = 0
            self.FOREGROUND_CYAN    = 0
            self.FOREGROUND_HRED    = 0
            self.FOREGROUND_HPINK   = 0
            self.FOREGROUND_HYELLOW = 0
            self.FOREGROUND_HWHITE  = 0
    def set_color(self, color):
        if self.systemtype == "Linux":
            sys.stdout.write("\033[1;%sm" % (color))
        elif self.systemtype == "Windows":
            ctypes.windll.kernel32.SetConsoleTextAttribute(self.std_out_handle, color)
        else:
            return
    def reset_color(self):
        if self.systemtype == "Linux":
            sys.stdout.write("\033[0m")
        elif self.systemtype == "Windows":
            self.set_color(self.FOREGROUND_RED | self.FOREGROUND_GREEN | self.FOREGROUND_BLUE)
        else:
            return

    def get_pink_string(self,s):
        if self.systemtype == "Linux":
            return "\033[1;%sm%s\033[0m" % (self.FOREGROUND_HPINK, s)
        elif self.systemtype == "Windows":
            return s
        else:
            return s

    def printpink(self, print_text):
        self.set_color(self.FOREGROUND_HPINK)
        sys.stdout.write(print_text)
        self.reset_color()


    def get_cyan_string(self,s):
        if self.systemtype == "Linux":
            return "\033[1;%sm%s\033[0m" % (self.FOREGROUND_CYAN, s)
        elif self.systemtype == "Windows":
            return s
        else:
            return s

    def printcyan(self, print_text):
        self.set_color(self.FOREGROUND_CYAN)
        sys.stdout.write(print_text)
        self.reset_color()

    def get_black_string(self,s):
        if self.systemtype == "Linux":
            return "\033[1;%sm%s\033[0m" % (self.FOREGROUND_BLACK, s)
        elif self.systemtype == "Windows":
            return s
        else:
            return s

    def printblack(self, print_text):
        self.set_color(self.FOREGROUND_HBLACK)
        sys.stdout.write(print_text)
        self.reset_color()

    def get_blue_string(self, s):
        if self.systemtype == "Linux":
            return "\033[1;%sm%s\033[0m" % (self.FOREGROUND_HBLUE, s)
        elif self.systemtype == "Windows":
            return s
        else:
            return s

    def printblue(self, print_text):
        self.set_color(self.FOREGROUND_HBLUE)
        sys.stdout.write(print_text)
        self.reset_color()

    def get_green_string(self, s):
        if self.systemtype == "Linux":
            return "\033[1;%sm%s\033[0m" % (self.FOREGROUND_HGREEN, s)
        elif self.systemtype == "Windows":
            return s
        else:
            return s

    def printgreen(self, print_text):
        self.set_color(self.FOREGROUND_HGREEN)
        sys.stdout.write(print_text)
        self.reset_color()

    def get_red_string(self, s):
        if self.systemtype == "Linux":
            return "\033[1;%sm%s\033[0m" % (self.FOREGROUND_HRED, s)
        elif self.systemtype == "Windows":
            return s
        else:
            return s

    def printred(self, print_text):
        self.set_color(self.FOREGROUND_HRED)
        sys.stdout.write(print_text)
        self.reset_color()

    def get_yellow_string(self, s):
        if self.systemtype == "Linux":
            return "\033[1;%sm%s\033[0m" % (self.FOREGROUND_HYELLOW, s)
        elif self.systemtype == "Windows":
            return s
        else:
            return s

    def printyellow(self, print_text):
        self.set_color(self.FOREGROUND_HYELLOW)
        sys.stdout.write(print_text)
        self.reset_color()

    def get_white_string(self, s):
        if self.systemtype == "Linux":
            return "\033[1;%sm%s\033[0m" % (self.FOREGROUND_HYELLOW, s)
        elif self.systemtype == "Windows":
            return s
        else:
            return s

    def printwhite(self, print_text):
        self.set_color(self.FOREGROUND_HWHITE)
        sys.stdout.write(print_text)
        self.reset_color()

    def printcolor(self, msg, level="", color=""):
        if self.quiet:
            return

        level = self.level if level=="" else level
        color = self.color if color=="" else color
        if color == "green":
            self.printgreen(level)
            print msg
        elif color == "red":
            self.printred(level)
            print msg
        elif color == "blue":
            self.printblur(level)
            print msg
        elif color == "yellow":
            self.printyellow(level)
            print msg
        elif color == "white":
            self.printwhite(level)
            print msg
        else:
            print "%s%s" %(level, msg)

    def printinfo(self, msg):
        if self.quiet:
            return
        self.printgreen("[   info]")
        print msg

    def printwarning(self, msg):
        if self.quiet:
            return
        self.printyellow("[warning]")
        print msg

    def printerror(self, msg):
        if self.quiet:
            return
        self.printred("[  error]")
        print msg

    def set_quiet(self, q):
        self.quiet = q

#end class PrintColor()

class ThreadPool:
    """Flexible thread pool class.  Creates a pool of threads, then
    accepts tasks that will be dispatched to the next available
    thread."""

    def __init__(self, numThreads):

        """Initialize the thread pool with numThreads workers."""

        self.__threads = []
        self.__resizeLock = threading.Condition(threading.Lock())
        self.__taskLock = threading.Condition(threading.Lock())
        self.__tasks = []
        self.__isJoining = False
        self.setThreadCount(numThreads)

    def setThreadCount(self, newNumThreads):

        """ External method to set the current pool size.  Acquires
        the resizing lock, then calls the internal version to do real
        work."""

        # Can't change the thread count if we're shutting down the pool!
        if self.__isJoining:
            return False

        self.__resizeLock.acquire()
        try:
            self.__setThreadCountNolock(newNumThreads)
        finally:
            self.__resizeLock.release()
        return True

    def __setThreadCountNolock(self, newNumThreads):

        """Set the current pool size, spawning or terminating threads
        if necessary.  Internal use only; assumes the resizing lock is
        held."""

        # If we need to grow the pool, do so
        while newNumThreads > len(self.__threads):
            newThread = ThreadPoolThread(self)
            self.__threads.append(newThread)
            newThread.start()
        # If we need to shrink the pool, do so
        while newNumThreads < len(self.__threads):
            self.__threads[0].goAway()
            del self.__threads[0]

    def getThreadCount(self):

        """Return the number of threads in the pool."""

        self.__resizeLock.acquire()
        try:
            return len(self.__threads)
        finally:
            self.__resizeLock.release()

    def queueTask(self, task, args=None, taskCallback=None):

        """Insert a task into the queue.  task must be callable;
        args and taskCallback can be None."""

        if self.__isJoining == True:
            return False
        if not callable(task):
            return False

        self.__taskLock.acquire()
        try:
            self.__tasks.append((task, args, taskCallback))
            return True
        finally:
            self.__taskLock.release()

    def getNextTask(self):

        """ Retrieve the next task from the task queue.  For use
        only by ThreadPoolThread objects contained in the pool."""

        self.__taskLock.acquire()
        try:
            if self.__tasks == []:
                return (None, None, None)
            else:
                return self.__tasks.pop(0)
        finally:
            self.__taskLock.release()

    def joinAll(self, waitForTasks = True, waitForThreads = True):

        """ Clear the task queue and terminate all pooled threads,
        optionally allowing the tasks and threads to finish."""

        # Mark the pool as joining to prevent any more task queueing
        self.__isJoining = True

        # Wait for tasks to finish
        if waitForTasks:
            while self.__tasks != []:
                time.sleep(.1)

        # Tell all the threads to quit
        self.__resizeLock.acquire()
        try:
            # Wait until all threads have exited
            if waitForThreads:
                for t in self.__threads:
                    t.goAway()
                for t in self.__threads:
                    t.join()
                    del t

            self.__setThreadCountNolock(0)
            self.__isJoining = True

            # Reset the pool for potential reuse
            self.__isJoining = False
        finally:
            self.__resizeLock.release()

class ThreadPoolThread(threading.Thread):
    """ Pooled thread class. """

    threadSleepTime = 0.1

    def __init__(self, pool):

        """ Initialize the thread and remember the pool. """

        threading.Thread.__init__(self)
        self.__pool = pool
        self.__isDying = False

    def run(self):

        """ Until told to quit, retrieve the next task and execute
        it, calling the callback if any.  """

        while self.__isDying == False:
            cmd, args, callback = self.__pool.getNextTask()
            # If there's nothing to do, just sleep a bit
            if cmd is None:
                time.sleep(ThreadPoolThread.threadSleepTime)
            elif callback is None:
                cmd(args)
            else:
                callback(cmd(args))

    def goAway(self):

        """ Exit the run loop next time through."""

        self.__isDying = True
#end class ThreadPoolThread(threading.Thread)

def parseargs():
    example = """

simple use:
    python %%prog  [-d %s] [-b bif] [-p product]

    python %%prog --local /home/mamh/myimagepath -b biffilename
    python %%prog --local /home/mamh/myimagepath -b biffilename -S SYSY,USRY

mount command:
    sudo mount.cifs //10.0.12.12/dailybuild/ /dailybuild -o user=yourusername,pass=yourpasswd
or
    sudo mount -t cifs //10.0.12.12/dailybuild/ /dailybuild -o user=yourusername,pass=yourpasswd
    """ % (time.strftime("%Y-%m-%d"))

    usage = "%prog [options] args" + example

    parser = optparse.OptionParser(usage)

    parser.add_option("-d", "--image-date",dest="imagedate",
            help="image date folder name", default="")
    parser.add_option("-p", "--product",dest="product",
            help="product", default="")
    parser.add_option("-b", "--bif",dest="bif",
            help="bif file name", default="")

    parser.add_option("-D",   "--dest-path",  dest="destpath",
            help="the path where you want to save images", default="")

    parser.add_option("", "--only-copy",   dest="onlycopy",
            help="enable this optons, it will not burn image", default=False, action="store_true")
    parser.add_option("", "--only-burn",   dest="onlyburn",
            help="enable this optons, it will only burn image", default=False, action="store_true")

    burnoptiongroup=optparse.OptionGroup(parser,"About burn options")
    burnoptiongroup.add_option("-S", "--disable-image",   dest="disableimage",
            help="disable some images not to burn. Can be a comma seperated list of ID_Names or index", default="")
    burnoptiongroup.add_option("-N", "--enable-image",   dest="enableimage",
            help="enable some images not to burn. Can be a comma seperated list of ID_Names or index", default="")
    burnoptiongroup.add_option("-E", "--erase-flash",   dest="eraseflash",
            help="erase all flash images", default=False, action="store_true")
    burnoptiongroup.add_option("-e", "--only-erase-flash",   dest="onlyeraseflash",
            help="only erase all flash images", default=False, action="store_true")
    burnoptiongroup.add_option("-R", "--reset-after-burning",   dest="resetafterburning",
            help="resetUE after burning", default=False, action="store_true")
    parser.add_option_group(burnoptiongroup)

    parser.add_option("-L", "--list-image",   dest="listimage",
            help="print all images name in bif file", default=False, action="store_true")

    parser.add_option("-q", "--quiet",   dest="quiet",
            help="will not print log", default=False, action="store_true")

    parser.add_option("-F", "--force",   dest="force",
            help="force copy file", default=False, action="store_true")

    parser.add_option("-j",   "--jobs",   dest="jobsnum",
            help="set max threadpoool num", default=0)
    parser.add_option("",   "--max",   dest="printlistmax",
            help="set max print list num", default="")

    parser.add_option("",   "--swdl",   dest="swdlname",
            help="set swdl app name", default="")

    swdldrivergroup=optparse.OptionGroup(parser,"About SoftwareDownloader Driver options")
    swdldrivergroup.add_option("", "--check-driver",   dest="checkdriver",
            help="check driver", default=False, action="store_true")
    swdldrivergroup.add_option("", "--install-driver",   dest="installdriver",
            help="install SWDownloader driver", default=False, action="store_true")
    swdldrivergroup.add_option("", "--reinstall-driver",   dest="reinstalldriver",
            help="reinstall SWDownloader driver", default=False, action="store_true")
    swdldrivergroup.add_option("", "--uninstall-driver", dest="uninstalldriver",
            help="install SWDownloader driver", default=False, action="store_true")
    parser.add_option_group(swdldrivergroup)

    mountgroup=optparse.OptionGroup(parser, "Mount options")
    mountgroup.add_option("-m", "--mount",      dest="mount",
            help="use mount mode if you mount dailybuild", default=False, action="store_true")
    parser.add_option_group(mountgroup)

    ftpgroup=optparse.OptionGroup(parser, "Ftp options")
    ftpgroup.add_option("-f", "--ftp",      dest="ftp",
            help="use ftp mode to download file", default=False, action="store_true")
    parser.add_option_group(ftpgroup)

    httpgroup=optparse.OptionGroup(parser, "http options")
    httpgroup.add_option("-H", "--http",      dest="http",
            help="use http mode to download file", default=False, action="store_true")
    parser.add_option_group(httpgroup)

    localburnoptiongroup=optparse.OptionGroup(parser,"Local images burn options")
    localburnoptiongroup.add_option("-l",   "--local",  dest="local",
            help="the path where your source images", default="")
    parser.add_option_group(localburnoptiongroup)

    servergroup=optparse.OptionGroup(parser, "samba/ftp/http server options")
    servergroup.add_option("",   "--host",   dest="host",
            help="", default="")
    servergroup.add_option("",   "--username",   dest="username",
            help="", default="")
    servergroup.add_option("",   "--password",   dest="password",
            help="", default="")
    servergroup.add_option("",   "--dailybuild-path", dest="dailybuildpath",
            help="dailybuild path", default="")
    servergroup.add_option("",   "--android-path", dest="androidpath",
            help="android path", default="")
    parser.add_option_group(servergroup)

    (options, args) = parser.parse_args()

    return (options, args)

def rundailyburn(options, dailyburn):

    #目的路径，用来存放复制过来的images
    destpath = options.destpath

    #dailbuild dailybuild 的base路径,可以改为其他的，例如odvb
    dailybuildpath = options.dailybuildpath
    androidpath = options.androidpath

    #只复制image
    onlycopy = options.onlycopy
    #直接烧image
    onlyburn = options.onlyburn

    #安静模式，不输出print的信息
    quiet = options.quiet
    #当模糊搜索到多个时，列出最多个数给用户
    printlistmax=options.printlistmax
    #多线程，0的时候禁用多线程，>0 线程池的最大个数
    jobsnum = options.jobsnum
    force = options.force

    #不烧写哪些image： 数字，用逗号分开
    disableimage = options.disableimage
    #只烧写哪些image
    enableimage = options.enableimage
    #是否擦写
    eraseflash = options.eraseflash
    #只擦写不烧写
    onlyeraseflash = options.onlyeraseflash
    #烧写后是否重启
    resetafterburning = options.resetafterburning
    #print image name list
    listimage = options.listimage

    swdlname = options.swdlname

    #host/ip
    host = options.host
    #username 账户名
    username = options.username
    #password 密码
    password = options.password

    if quiet:
        dailyburn.set_quiet(True)
    if force:
        dailyburn.set_copyforce(True)
    if printlistmax:
        try:
            plmax = int(printlistmax)
        except ValueError as e:
            dailyburn.set_printlistmax(20)
        else:
            dailyburn.set_printlistmax(plmax)
    if jobsnum:
        try:
            jobsnum = int(jobsnum)
        except ValueError as e:
            dailyburn.set_jobsnum(10)
        else:
            if jobsnum < 0:
                jobsnum = 0
            dailyburn.set_jobsnum(jobsnum)
    if destpath:
        dailyburn.set_destpath(destpath)

    if onlycopy:
        dailyburn.set_onlycopy(True)

    if onlyburn:
        dailyburn.set_onlyburn(True)

    if dailybuildpath:
        dailyburn.set_dailybuildpath(dailybuildpath)
    if androidpath:
        dailyburn.set_androidpath(androidpath)

    if listimage:
        dailyburn.set_listimage(True)

    #这两个不能同时出现
    if disableimage and enableimage:
        pass
    elif disableimage:
        dailyburn.set_disableimage(disableimage)
    elif enableimage:
        dailyburn.set_enableimage(enableimage)

    #擦写flash的选项，这两个也不能同时出现
    if eraseflash and onlyeraseflash:
        pass
    elif eraseflash:
        dailyburn.set_eraseflash(True)
    elif onlyeraseflash:
        dailyburn.set_onlyeraseflash(True)

    if resetafterburning:
        dailyburn.set_resetafterburning(True)

    if swdlname:
        dailyburn.set_swdlname(swdlname)

    if host:
        dailyburn.set_host(host)
    if username:
        dailyburn.set_username(username)
    if password:
        dailyburn.set_password(password)

    dailyburn.start()

def runlocalburn(options, localburn):
    #目的路径，用来存放复制过来的images
    destpath = options.destpath

    #只复制image
    onlycopy = options.onlycopy
    #直接烧image
    onlyburn = options.onlyburn

    #安静模式，不输出print的信息
    quiet = options.quiet
    #当模糊搜索到多个时，列出最多个数给用户
    printlistmax=options.printlistmax
    #多线程，0的时候禁用多线程，>0 线程池的最大个数
    jobsnum = options.jobsnum
    force = options.force

    #不烧写哪些image： 数字，用逗号分开
    disableimage = options.disableimage
    #只烧写哪些image
    enableimage = options.enableimage
    #是否擦写
    eraseflash = options.eraseflash
    #只擦写不烧写
    onlyeraseflash = options.onlyeraseflash
    #烧写后是否重启
    resetafterburning = options.resetafterburning
    #print image name list
    listimage = options.listimage

    swdlname = options.swdlname

    if quiet:
        localburn.set_quiet(True)
    if force:
        localburn.set_copyforce(True)

    if printlistmax:
        try:
            plmax = int(printlistmax)
        except ValueError as e:
            localburn.set_printlistmax(20)
        else:
            localburn.set_printlistmax(plmax)

    if jobsnum:
        try:
            jobsnum = int(jobsnum)
        except ValueError as e:
            localburn.set_jobsnum(10)
        else:
            if jobsnum < 0:
                jobsnum = 0
            localburn.set_jobsnum(jobsnum)
    if destpath:
        localburn.set_destpath(destpath)

    if onlycopy:
        localburn.set_onlycopy(True)

    if onlyburn:
        localburn.set_onlyburn(True)

    if listimage:
        localburn.set_listimage(True)

    #这两个不能同时出现
    if disableimage and enableimage:
        pass
    elif disableimage:
        localburn.set_disableimage(disableimage)
    elif enableimage:
        localburn.set_enableimage(enableimage)

    if eraseflash and onlyeraseflash:
        pass
    elif eraseflash:
        localburn.set_eraseflash(True)
    elif onlyeraseflash:
        localburn.set_onlyeraseflash(True)

    if resetafterburning:
        localburn.set_resetafterburning(True)

    if swdlname:
        localburn.set_swdlname(swdlname)

    localburn.start()

def main():
    (options, args) = parseargs()

    checkdriver = options.checkdriver    #检查驱动
    reinstalldriver = options.reinstalldriver#安装驱动
    installdriver = options.installdriver   #安装驱动
    uninstalldriver = options.uninstalldriver    #卸载驱动，一般不会用到吧

    imagedate = options.imagedate    #包含日期的 image folder名字
    product = options.product    #product名，也是folder的名字
    bif = options.bif    #bif文件名字

    local = options.local    #local模式用到的一个路径
    mount = options.mount    #mount模式
    ftp = options.ftp    #ftp模式下载images
    http = options.http    #ftp模式下载images


    swdldriver = SwdlDriver()
    if checkdriver:
        #检查驱动是否有
        if swdldriver.checkdriver():
            PrintColor().printinfo("installed driver")
        else:
            PrintColor().printerror("Not install driver")
        return 0
    #reinstall-driver选项装驱动
    if reinstalldriver:
        swdldriver.reinstalldriver()
        return 0
    #install-driver选项装驱动
    if installdriver:
        swdldriver.installdriver()
        return 0
    #uninstall-driver 卸载驱动用处不大吧
    if uninstalldriver:
        swdldriver.uninstalldriver()
        return 0

    #local模式，指定一个local的路径，一个bif文件名字
    if local:
        localburn = LocalBurn(bif, local)
        runlocalburn(options, localburn)
        return 0

    #mount模式daily burn模式
    if mount:
        dailyburn = MountDailyBurn(imagedate, product, bif)
        rundailyburn(options, dailyburn)
        return 0
    #http模式daily burn
    if http:
        dailyburn = HttpDailyBurn(imagedate, product, bif)
        rundailyburn(options, dailyburn)
        return 0
    #ftp模式daily burn
    if ftp:
        dailyburn = FtpDailyBurn(imagedate, product, bif)
        rundailyburn(options, dailyburn)
        return 0
    #默认smb模式
    dailyburn = SambaDailyBurn(imagedate, product, bif)
    rundailyburn(options, dailyburn)

    return 0

if __name__ == '__main__':
    main()
