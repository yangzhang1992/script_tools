#!/usr/bin/python
# coding:utf-8
import sys
import os
import commands
import json
import optparse
import xml.dom.minidom



def printcolor(msg):
    print "\033[1;32m[debug]\033[0m\033[1;31m%s\033[0m" % msg


def printgreencolor(msg):
    print "\033[1;32m[debug]\033[0m\033[1;32m%s\033[0m" % msg


def printbluecolor(msg):
    print "\033[1;32m[debug]\033[0m\033[1;34m%s\033[0m" % msg


def get_make_android_shell(product):
    make_android_shell = """
#!/bin/bash

function printcolor(){
    printf "\e[1;33m[debug]\e[0m\e[1;31m$1\n\e[0m"
}

function prepare(){
    # Use ccache default
    export USE_CCACHE=1
    export CCACHE_DIR=${CCACHE_DIR:-${PWD}/.ccache}
    prebuilts/misc/linux-x86/ccache/ccache -M 10G

    . build/envsetup.sh
    chooseproduct """ + product + """  && choosevariant userdebug
}

function main(){
    start_time=$(date +%s)
    printcolor "********************************************************************"

    cpu_num=$(grep -c processor /proc/cpuinfo)
    cpu_num=$[cpu_num*2]

    if [ $# -eq 1 ];then
        if [ "$1" = "all" ];then
            printcolor "make all android"
            prepare
            make -j$cpu_num
            MAKERES=$?
        elif [ "$1" = "allB" ];then
            printcolor "make all android -B"
            prepare
            make -j$cpu_num -B
            MAKERES=$?
        else
            printcolor "mmm only one project:[$1]"
            prepare
            mmm -j$cpu_num $1
            MAKERES=$?
        fi
    elif [ $# -eq 2 ];then
        if [ "$2" == "-B" ];then
            printcolor "mmm -B only one project:[$1] [$2]"
            prepare
            mmm -j$cpu_num $1 -B
            MAKERES=$?
        elif [ "$2" == "-a" ];then
            printcolor "mmma only one project:[$1] [$2]"
            prepare
            mmma -j$cpu_num $1
            MAKERES=$?
        elif [ "$2" == "-aB" ];then
            printcolor "mmma -B only one project:[$1] [$2]"
            prepare
            mmma -j$cpu_num $1 -B
            MAKERES=$?
        fi
    else
        MAKERES=1
    fi

        end_time=$(date +%s)
        time_elapse=$((end_time-start_time))

        printcolor "********************************************************************"
        printcolor "building finished,make result: $MAKERES cost $time_elapse s -- $((time_elapse/60)) min"
        printcolor "********************************************************************"
}
main $*

if [ $MAKERES -ne 0 ]; then
    exit 1
fi

exit 0
"""
    return make_android_shell


def get_repoinit_shell(manifestbranch, manfiest_xml):
    repoinit = "repo init -u ssh://gerrit.zeusis.com:29418/m0/manifest --repo-url ssh://gerrit.zeusis.com:29418/m0/tools/repo --repo-branch stable --no-repo-verify -q -b %s -m %s --reference /home/zeusis-mirror" % (manifestbranch, manfiest_xml)
    return repoinit


def get_reposync_shell():
    reposync = "repo sync -d -c -q --jobs=8 --no-tags"
    return reposync

def get_name_to_path_dirt(manifest):
    DOMTree = xml.dom.minidom.parse(manifest)
    root = DOMTree.documentElement
    projects = root.getElementsByTagName("project");
    name_to_path = {}
    for pro in projects:
        path = pro.getAttribute("path")
        name = pro.getAttribute("name")
        if path and name:
            name_to_path[name] = path

    return name_to_path


def get_android_mk_path_list(flist, rootdir):
    android_mk_list = []
    for ftemp in flist:
        flisttemp = os.path.split(ftemp)
        p = flisttemp[0]  # 路径
        f = flisttemp[1]  # 文件
        path = os.path.join(rootdir, p)
        makefile = os.path.join(path, "Android.mk")
        if os.path.exists(path) and os.path.isfile(makefile):
            android_mk_list.append(path)
        elif p != "":
            # 如果此路径下没有Android.mk
            android_mk_list.extend(get_android_mk_path_list([p], rootdir))
    # 去重复的path
    android_mk_list = list(set(android_mk_list))
    return android_mk_list


def make_project():
    reposync = get_reposync_shell()
    repoinit = get_repoinit_shell(options.manifestbranch, options.manifestxml)

    product = options.product

    gerritproject = options.gerritproject
    gerritbranch = options.gerritbranch
    gerritchangeid = options.gerritchangeid
    gerritchangenumber = options.gerritchangenumber  # repo download use this value.
    gerritpatchsetnumber = options.gerritpatchsetnumber  # repo download use this value.

    # repo init here.
    printbluecolor("repo init: [%s]" % repoinit)
    ret = os.system(repoinit)

    # parse the manifest.xml to get the project name and path
    name = ""
    path = ""
    name_to_path = get_name_to_path_dirt("./.repo/manifest.xml")
    for key in name_to_path.keys():
        if gerritproject.endswith(key):
            name = key
            path = name_to_path.get(key, "")
            printbluecolor("name=%s, path=%s" % (name, path))

    # repo sync.
    reposyncproject = "%s %s" % (reposync, name)
    printbluecolor("repo sync one project: [%s]" % reposyncproject)
    ret = os.system(reposyncproject)

    # repo download
    repodownload = "repo download %s %s/%s" % (name, gerritchangenumber, gerritpatchsetnumber)
    printbluecolor("repo download: [%s]" % repodownload)
    ret = os.system(repodownload)

    query = "--format=JSON project:%s branch:%s --current-patch-set %s --patch-sets --files" % (
        options.gerritproject, gerritbranch, gerritchangeid)
    gerrithost = "gerrit.zeusis.com"
    command = "ssh -p 29418 %s gerrit query %s" % (gerrithost, query)
    printcolor(command)

    status, output = commands.getstatusoutput(command)
    jsonstr = output.split("\n")
    json_D = json.loads(jsonstr[0])

    files_list = []
    if json_D.has_key("patchSets"):
        patchsetlist = json_D.get('patchSets', "")
        for patchset in patchsetlist:
            if patchset.get("number", "") == gerritpatchsetnumber:
                currentpatchset = patchset
                filestemp = currentpatchset.get('files', '')
                for ftemp in filestemp:
                    f = ftemp.get('file', '')
                    if f != "/COMMIT_MSG":  # ignore this.
                        files_list.append(f)
    else:
        printcolor(json_D)
        sys.exit(1)

    android_mk_list = get_android_mk_path_list(files_list, path)
    printbluecolor("Android.mk list: %s" % android_mk_list)

    result = 0
    make_android_shell = get_make_android_shell(product)
    if android_mk_list:
        printcolor("found Android.mk file, then will make only this project.")
        for p in android_mk_list:
            make = "bash -c '%s' make_android_shell.sh %s" % (make_android_shell, p)
            ret = os.system(make)
            printcolor("the first make result: %s " % (ret))
            if ret != 0:
                # if first make fail,then repo sync all project
                printbluecolor("repo sync all: %s" % reposync)
                os.system(reposync)
                # repo download
                printbluecolor("retry 1 repo download : [%s]" % repodownload)
                os.system(repodownload)
                newmake = "%s -B" % (make)
                ret = os.system(newmake)
                printcolor("retry 1 make result: %s" % (ret))
            if ret != 0:
                # if first make fail,then repo sync all project
                printbluecolor("repo sync all: %s" % reposync)
                os.system(reposync)
                # repo download
                printbluecolor("retry 2 repo download : [%s]" % repodownload)
                os.system(repodownload)
                newmake = "%s -a" % (make)
                ret = os.system(newmake)
                printcolor("retry 2 make result: %s" % (ret))
            if ret != 0:
                # if first make fail,then repo sync all project
                printbluecolor("repo sync all: %s" % reposync)
                os.system(reposync)
                # repo download
                printbluecolor("retry 3 repo download : [%s]" % repodownload)
                os.system(repodownload)
                newmake = "%s -aB" % (make)
                ret = os.system(newmake)
                printcolor("retry 3 make result: %s" % (ret))

            result += ret

        if result != 0:
            printcolor("will retry make all")
            printbluecolor("repo sync all: %s" % reposync)
            os.system(reposync)
            # repo download
            printbluecolor("repo download : [%s]" % repodownload)
            os.system(repodownload)
            # make all android
            make = "bash -c '%s' make_android_shell.sh all" % (make_android_shell)
            result = os.system(make)
    else:
        printcolor("not found Android.mk file, then will make all.")
        printbluecolor("repo sync all: %s" % reposync)
        os.system(reposync)
        # repo download
        printbluecolor("repo download : [%s]" % repodownload)
        os.system(repodownload)
        # make all android
        make = "bash -c '%s' make_android_shell.sh all" % (make_android_shell)
        result = os.system(make)

    if result != 0:
        printcolor("will retry make all -b")
        printbluecolor("repo sync all: %s" % reposync)
        os.system(reposync)
        # repo download
        printbluecolor("repo download : [%s]" % repodownload)
        os.system(repodownload)
        # make all android
        make = "bash -c '%s' make_android_shell.sh allB" % (make_android_shell)
        result = os.system(make)

    printcolor("make result: %s" % result)
    if result != 0:
        sys.exit(1)


def main():
    printcolor("options %s" % options)
    make_project()


parser = optparse.OptionParser()
parser.add_option("", "--product", dest="product", help="set product", default="")
parser.add_option("", "--manifest-branch", dest="manifestbranch", help="set repo init branch pass to repo -b", default="")
parser.add_option("", "--manifest-xml", dest="manifestxml", help="set repo init branch pass to repo -m", default="")

parser.add_option("", "--gerrit-event-type", dest="gerriteventtype", help="set gerrit event type", default="")
parser.add_option("", "--gerrit-project", dest="gerritproject", help="set gerrit project", default="")
parser.add_option("", "--gerrit-branch", dest="gerritbranch", help="set gerrit branch", default="")
parser.add_option("", "--gerrit-change-id", dest="gerritchangeid", help="set gerrit change id", default="")
parser.add_option("", "--gerrit-change-number", dest="gerritchangenumber", help="set gerrit change number", default="")
parser.add_option("", "--gerrit-patchset-number", dest="gerritpatchsetnumber", help="set gerrit patchset number",
                  default="")
parser.add_option("", "--gerrit-refspec", dest="gerritrefspec", help="set gerrit refspec", default="")
parser.add_option("", "--gerrit-patch-revision", dest="gerritpatchrevision", help="set gerrit patchset revision",
                  default="")

(options, args) = parser.parse_args()
if __name__ == "__main__":
    sys.stdout = sys.stderr
    main()
