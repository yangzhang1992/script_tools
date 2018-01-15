#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import glob
import sys
import re

# 这里import aais 脚本里面的一些方法
from aais.log import Log
from aais.utils import Utils
from aais.html import *

class UpdateHtmlException(Exception):
    pass

class UpdateHtml(object):
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
            return None
        with open(buildprop, 'r') as f:
            text = f.read()
        build_id = re.findall('ro.build.id=.*', text)
        build_id = build_id[0].split('=')[-1]
        return build_id

    def Execute(self):
        publish_path = os.path.dirname(self.source_manifest_file)
        platform_path = os.path.dirname(publish_path)

        html_file = os.path.join(platform_path, "LAST_BUILD.%s.html" % self.platform)
        table = ""
        all_globpattern = "*_*"
        all_paths = glob.glob(os.path.join(platform_path, all_globpattern))
        all_paths = list(reversed(all_paths))
        for imagedate_path in all_paths:
            if os.path.isdir(imagedate_path):
                folders_L = os.listdir(imagedate_path)
                for folder in folders_L:
                    product_path = os.path.join(imagedate_path, folder)
                    if os.path.isdir(product_path):
                        version = self.GetBuildId(product_path)
                        Log.Info("imagepath: %s, %s, version: %s " % (imagedate_path, folder, version))
                        imdatedate = os.path.basename(imagedate_path)
                        ip = os.environ.get("FILE_SERVER_IP", "10.0.12.12")
                        smb_path = "\\\\%s%s" % (ip, imagedate_path.replace("/", "\\"))
                        table += "<tr align=\"left\"><td width=\"50%%\"><a href=\"%s\"> %s </a></td><td width=\"25%%\">%s</td><td width=\"25%%\">%s</td></tr>\n" \
                                 % (imdatedate, smb_path,folder, version)

        body = """
        <br/>
        <br/>
        <table table width=\"80%%\" class=\"altrowstable\" border=\"1\">
            %s
        </table>
        <br/>
        <br/>
        """ % table

        html = HTML % (TABLE_CSS_STYLE, body)
        with open(html_file, "w") as fd:
            fd.write(html)


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

    uh = UpdateHtml(build_type, platform, branch, product, variant, carrier, manifest, os.getcwd(), assigner)
    uh.SetImageMode(imagemode)
    ret = uh.Execute()
    sys.exit(ret)

if __name__ == "__main__":
    sys.stdout = sys.stderr
    main()

