#!/usr/bin/python
# coding:utf-8

import re
import os
import sys
import optparse
import commands
import shutil
import glob

# 这里import aais 脚本里面的一些方法
from aais.log import Log
from aais.utils import Utils


class MakeCpbException(Exception):
    pass


class MakeCpb(object):
    CONFIG = """
        [Combin]
            Devicename=%s
            SoftVersion=%s
            srcdir=./flash
            dstdir=%s

        [NET]
            IF_NAME=em1
            IP_ADDR=10.3.11.123
    """

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

    # 读版本号
    def GetBuildId(self, version_path):
        buildprop = os.path.join(version_path, 'debug', 'build.prop')
        if not os.path.exists(buildprop):
            Log.Red('Error:Can not find build id!')
            raise MakeCpbException("get build id fail")
        with open(buildprop, 'r') as f:
            text = f.read()
        build_id = re.findall('ro.build.id=.*', text)
        build_id = build_id[0].split('=')[-1]
        return build_id

    def Execute(self):
        publish_path = os.path.dirname(self.source_manifest_file)
        folers_L = os.listdir(publish_path)
        for folder in folers_L:
            product_path = os.path.join(publish_path, folder)
            if not os.path.isdir(product_path):
                continue

            if folder.startswith("civic") and folder.endswith('_factory'):
                Log.Info("only support civic factory")
            if folder.startswith("victor") and folder.endswith('_factory'):
                Log.Info("only support victor factory")
            elif folder.endswith('_factory'):
                Log.Warning("not support factory")
                continue
            elif folder.endswith("_amss"):
                Log.Warning("not support amss folder")
                continue

            Log.Info("product path: %s" % product_path)

            if folder.startswith("pollux"):
                device_name = "POL-A0"
                soft_version = "%s-%s" % (device_name, self.GetBuildId(product_path))
            elif folder.startswith("alchemy"):
                device_name = "3701A"
                soft_version = "7.1.%s" % (self.GetBuildId(product_path))
            elif folder.startswith("civic"):
                device_name = "CVC-A0"
                soft_version = "%s-%s" % (device_name, self.GetBuildId(product_path))
            elif folder.startswith("victor"):
                device_name = "VCR-A0"
                soft_version = "%s" % (self.GetBuildId(product_path))
            elif folder.startswith("cp_ares"):
                device_name = "C105"
                soft_version = "%s-%s" % (device_name, self.GetBuildId(product_path))
            elif folder.startswith("ares_in"):
                device_name = "C105-I0"
                soft_version = "%s-%s" % (device_name, self.GetBuildId(product_path))
            elif folder.startswith("ares"):
                device_name = "C105-E0"
                soft_version = "%s-%s" % (device_name, self.GetBuildId(product_path))
            elif folder.startswith("grover"):
                device_name = "301A"
                soft_version = "%s-%s" % (device_name, self.GetBuildId(product_path))
            elif folder.startswith("clover"):
                device_name = "COR-I0"
                soft_version = "%s-%s" % (device_name, self.GetBuildId(product_path))
            elif folder.startswith("cp302a"):
                device_name = "302A"
                soft_version = "%s-%s" % (device_name, self.GetBuildId(product_path))
            elif self.product in ["c1"] :
                if self.carrier in ["ru_open", "india"] :
                    device_name = "C103"
                elif self.carrier == "id_open":
                    device_name = "R116"
                elif self.carrier in ["open", "cu", "ctc", "cmcc", "openNonCA"] :
                    device_name = "C106"
                else:
                    device_name = "C103"
                soft_version = "%s-%s" % (device_name, self.GetBuildId(product_path))
            elif folder.startswith("c107"):
                device_name = "C107"
                soft_version = "C107-%s" % (self.GetBuildId(product_path))
            else:
                Log.Warning("not support this product: %s" % folder)
                continue

            # 最后存放cpb文件的目录，路径
            cpb_path = os.path.join(product_path, "CPB")
            if os.path.exists(cpb_path):
                cpb_file_L = os.listdir(cpb_path)
                if cpb_file_L:
                    continue
                else:
                    # 空目录，这里先删除
                    Utils.DeletePathOrFile(cpb_path)
            else:
                Log.Info("will mkdir cpb_path: %s" % cpb_path)
                os.mkdir(cpb_path)

            Log.Info("product path: %s" % product_path)

            Utils.DeletePathOrFile("flash")
            Utils.DeletePathOrFile("flash.zip")

            if folder.endswith("_factory"):
                Log.Info("factory will copy %s qfil.zip" % product_path)
                shutil.copy(os.path.join(product_path, 'qfil/qfil.zip'), './flash.zip')
            else:
                Log.Info("factory will copy %s flash.zip" % product_path)
                shutil.copy(os.path.join(product_path, 'flash/flash.zip'), './flash.zip')
            os.system('unzip flash.zip -d flash')

            # cpb配置文件
            config = self.CONFIG % (device_name, soft_version, cpb_path )

            with open("Cpbtool.cfg", "w") as fd:
                fd.write(config)

            #打包cpb
            os.system('./MakeCpb yl29158')

def main():
    build_type = os.environ.get("BUILD_TYPE")
    platform = os.environ.get("ANDROID_PLATFORM")
    branch = os.environ.get("BRANCHc")
    product = os.environ.get("PRODUCT")
    variant = os.environ.get("VARIANT")
    carrier = os.environ.get("CARRIER")
    imagemode = os.environ.get("IMAGEMODE")

    manifest = os.environ.get("MANIFEST_FILE")
    assigner = os.environ.get("ASSIGNER")

    cpb = MakeCpb(build_type, platform, branch, product, variant, carrier, manifest, os.getcwd(), assigner)
    cpb.SetImageMode(imagemode)
    ret = cpb.Execute()
    sys.exit(ret)


if __name__ == "__main__":
    sys.stdout = sys.stderr
    main()
