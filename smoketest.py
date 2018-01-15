#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import urllib2
import json
import pprint
import sys

# 这里import aais 脚本里面的一些方法
from aais.log import Log
from aais.utils import Utils

class SmokeTestException(Exception):
    pass

class SmokeTest(object):
    URL = 'http://10.0.81.33:8080/task/importtask'

    def __init__(self, build_type, platform, branch, product, variant, carrier, manifest, workspace, assigner):
        self.build_type = build_type
        self.platform = platform
        self.branch = branch
        self.product = ""  # this build task will run this android target product
        self.SetProduct(product)  # current product list in this build
        self.variant = ""
        self.SetVariant(variant)
        self.carrier = ""  # 这个是和通信制式相关的一个变量，有移动，联通，电信等
        self.SetCarrier(carrier)

        # 暂时，目前为止，这个参数是用来区分正常版本的image和工厂烧片版本image的
        self.imagemode = ""

        self.source_manifest_file = ""
        self.SetSourceManifest(manifest)

        self.workspace = ""  # first init empty then use SetWorkspace to init it
        self.SetWorkspace(workspace)

        self.assigner = assigner

    def SetBuildType(self, build_type):
        self.build_type = build_type

    def SetAssigner(self, assigner):
        self.assigner = assigner

    def SetBranch(self, branch):
        self.branch = branch

    def SetPlatform(self, platform):
        self.platform = platform

    def SetSourceManifest(self, manifest):
        ip, manifest = Utils.WindowsPathToLinuxPath(manifest)
        self.source_manifest_file = manifest

    def SetProduct(self, product):
        self.product = product

    def SetVariant(self, variant):
        self.variant = variant

    def SetCarrier(self, carrier):
        self.carrier = carrier

    def SetImageMode(self, imagemode):
        self.imagemode = imagemode

    def SetWorkspace(self, workspace):
        self.workspace = workspace

    def HttpPost(self, values):
        try:
            url = self.URL
            jdata = json.dumps(values)             # 对数据进行JSON格式化编码
            req = urllib2.Request(url, jdata)       # 生成页面请求的完整数据
            response = urllib2.urlopen(req, timeout=10)       # 发送页面请求
            return response.read()                    # 获取服务器返回的页面信息
        except Exception, e:
            print str(e)
            return None

    def Execute(self):
        publish_path = os.path.dirname(self.source_manifest_file)
        imsagedate = os.path.basename(publish_path)

        folers_L = os.listdir(publish_path)
        for folder in folers_L:
            product_path = os.path.join(publish_path, folder)
            if not os.path.isdir(product_path):
                continue

            if "_userdebug_" not in folder:
                # 只测试userdebug的版本
                continue

            image_path = os.path.join(product_path, "flash")
            if not os.path.isdir(image_path):
                Log.Warning("%s path not exists" % image_path)
                continue

            image_path = "\\\\%s%s" % ("10.0.12.12", image_path.replace("/", "\\"))
            jsondata = {
                "TaskName": "[%s]-%s-%s" % ( self.build_type, imsagedate, folder),
                "Policy": "%s.xml" % folder,
                "Execute": True,
                "RecoveryPath": image_path,
                "Uname": self.build_type
            }
            Log.Info("json: \n%s" % jsondata)
            self.HttpPost(jsondata)

if __name__ == "__main__":
    build_type = os.environ.get("BUILD_TYPE")
    platform = os.environ.get("ANDROID_PLATFORM")
    branch = os.environ.get("BRANCHc")
    product = os.environ.get("PRODUCT")
    variant = os.environ.get("VARIANT")
    carrier = os.environ.get("CARRIER")
    imagemode = os.environ.get("IMAGEMODE")

    manifest = os.environ.get("MANIFEST_FILE")
    assigner = os.environ.get("ASSIGNER")

    st = SmokeTest(build_type, platform, branch, product, variant, carrier, manifest, os.getcwd(), assigner)
    st.SetImageMode(imagemode)
    ret = st.Execute()
    sys.exit(ret)


