#!/usr/bin/python
# coding:utf-8
import os
import hashlib
import base64
import time
import pprint
import re
import optparse
import shutil
import commands
import sys  

class UPC(object):

    def __init__(self, source_swv,dest_swv,hardware,hwversion,ota_file,description = '',priority = 'Optional',full_package = 'false'):
        self.full_package = full_package
        self.hardware = hardware
        self.hwversion = hwversion
        self.source_swv = source_swv
        self.dest_swv = dest_swv
        self.priority = priority
        self.ota_file = ota_file
        self.description = description

    def GetMD5(self):
        with open(self.ota_file, 'rb') as file:
            rf=file.read()
            md5 = hashlib.md5()
            md5.update(rf)
        return str.upper(md5.hexdigest())
    def GetBase64(self):
        with open(self.ota_file, 'rb') as file:
            rf = file.read()
            b64encode= base64.b64encode(rf)
        return b64encode
    def GetSize(self):
        with open(self.ota_file, 'rb') as file:
            rf = file.read()
            size=len(rf)
        return str(size)
    def MakeUPC(self):
        self.CheckConfigParameters()
        if not self.CheckFile(self.ota_file):
            raise IOError('%s is not exist!' % self.ota_file)
        localtime=time.localtime()
        xml_str = '<?xml version="1.0" encoding="utf-8" ?>'
        xml_str += '<update-package>'
        xml_str += '<creation-date>'
        xml_str += time.strftime("%Y/%m/%d %H:%M:%S", localtime)  # 2016/10/27 11:46:18
        xml_str += '</creation-date>'
        xml_str += '<hw>'
        xml_str += self.hardware
        xml_str += '</hw>'
        xml_str += '<hwv>'
        xml_str += self.hwversion
        xml_str += '</hwv>'
        xml_str += '<src_swv>'
        # if(!bool_is_fullCPB) xml_str += T2A(str_src_swv); # 完整包，这个节点无效
        xml_str += self.source_swv
        xml_str += '</src_swv>'
        xml_str += '<dst_swv>'
        xml_str += self.dest_swv
        xml_str += '</dst_swv>'
        xml_str += '<description><![CDATA['
        # xml_str += convert_utf8(str_description.GetBuffer(0));
        xml_str += self.description
        xml_str += ']]></description>'
        xml_str += '<size>'
        xml_str += self.GetSize()
        xml_str += "</size>"
        xml_str += "<priority>"
        xml_str += self.priority
        xml_str += '</priority> '
        xml_str += '<md5>'
        xml_str += self.GetMD5()     #MD5_string
        xml_str += '</md5>'
        xml_str += '<binary>'
        xml_str += self.GetBase64()  # base64_string;
        xml_str += '</binary>'
        xml_str += "</update-package>"
        
        #修改输出UPC的文件名 UPC_{hardware}_{hwversion}_{src_version}-{dest_version}
        src_version=re.match(r'\d.\d.(\d{3}).*',self.source_swv).groups()[0]
        dest_version=re.match(r'\d.\d.(\d{3}).*',self.dest_swv).groups()[0]
        filename='UPC_'+ self.hardware + '_' + self.hwversion + '_' + src_version + '-' + dest_version + r'.xml'
        if self.full_package=='true':
		filename='UPC_'+ self.hardware + '_' + self.hwversion + '_' + dest_version + '_' + 'FULL' + r'.xml'
        with  open(filename,'w') as xmlfile:
            xmlfile.write(xml_str)
    #输出配置属性
    def dump(self):
        #for (key, value) in self.__dict__.items():
        #    pprint.pprint("%s: %s" %(key, value))
        print 'full_package:',self.full_package
        print 'hardware:    ',self.hardware
        print 'hwversion:   ',self.hwversion
        print 'source_swv:  ',self.source_swv
        print 'dest_swv:    ',self.dest_swv
        print 'priority:    ',self.priority
        print 'ota_file:    ',self.ota_file
        print 'description: ',self.description
    #检查文件是否存在
    def CheckFile(self, config_file):
        if not os.path.exists(config_file) or not os.path.isfile(config_file):
            return False
        return True
    #根据UPC规则检查各参数是否符合要求
    def CheckConfigParameters(self):
        pass
        
def parseargs():
    parser = optparse.OptionParser()
    
    ota_option_group = optparse.OptionGroup(parser, "ota options")
    ota_option_group.add_option("-f", "--ota-file", dest="ota_file",
                                    help="ota filename", default="")
    ota_option_group.add_option("-x", "--description", dest="description",
                                    help="ota description", default="")
    ota_option_group.add_option("-o", "--priority", dest="priority",
                                    help="ota priority", default="")
    ota_option_group.add_option("-t","--ota-type",dest="ota_type",
                                    help="ota type",default="")
    ota_option_group.add_option("-b","--build",dest="build",
                                    help="build",default="")
    ota_option_group.add_option("-p", "--platform", dest="platform",
                                help="platform", default="")

    (options, args) = parser.parse_args()
    return (options, args)

if __name__ == "__main__":
    (options, args) = parseargs()
    ota_file = options.ota_file.strip()
    description = options.description.strip()
    priority = options.priority.strip()
    ota_type = options.ota_type.strip()
    build=options.build.strip()
    platform = options.platform.strip()
    print 'build:',build
    root = '/dailybuild-sz/android/%s' % (platform)
    #print ota_file
    if build:
        strlist=re.match('(.*)---(.*\d{8})\..*',ota_file)
        src=strlist.groups()[0]
        dest=strlist.groups()[1]
        dest_son=re.match('(\d{4}-\d{2}-\d{2}_\d{1})',dest)
        if dest_son is None:
            src=re.sub('\d{4}-\d{2}-\d{2}',src,dest)
        else:
            src=re.sub('\d{4}-\d{2}-\d{2}_\d{1}',src,dest)
        path=build
    else:
        strlist=re.match('(.*)---(.*_\d{8}).(.*)\.\d.*',ota_file)
        src=strlist.groups()[0]
        dest=strlist.groups()[1]
        path=strlist.groups()[2]
         

    if src>dest:
	tmp=src
        src=dest
        dest=tmp
    print "src:",src
    print "dest:",dest
    src_path = root + '/' + src + '/' + path + '/ota'
    dest_path = root + '/' + dest + '/' + path + '/ota'
    print src_path
    print dest_path
    #sys.exit(0)
    upgrade_zip = None
    downgrade_zip = None
    full_zip = None
    up_file_name=None
    down_file_name=None
    full_file_name=None
    if build:
        for name in os.listdir(src_path):
            if re.match(re.findall('\d{4}-\d{2}-\d{2}',src)[0] + r'.*' + dest + r'.*',name):
                downgrade_zip = src_path + '/' + name
                down_file_name = name
            elif re.match(r'.*-ota-.*',name):
                full_zip = dest_path + '/' + name
                full_file_name = name
            
        for name in os.listdir(dest_path):
            if  re.match(re.findall('\d{4}-\d{2}-\d{2}',dest)[0] + r'.*' + src + r'.*',name):
                upgrade_zip = dest_path + '/' + name
                up_file_name = name
                break;
    else:
        for name in os.listdir(dest_path):
            if re.match(dest + r'.*' + src + r'.*',name):
                upgrade_zip = dest_path + '/' + name
                up_file_name = name
            elif re.match(r'.*-ota-.*',name):
                full_zip = dest_path + '/' + name
                full_file_name = name
                                                            
        for name in os.listdir(src_path):
            if  re.match(src + r'.*' + dest + r'.*',name):
                downgrade_zip = src_path + '/' + name
                down_file_name = name
                break;

    print '************************OTA file**************************'
    print 'upgrade_zip:   ',upgrade_zip
    print 'downgrade_zip: ',downgrade_zip
    print 'full_zip:      ',full_zip
    
    buildprop = root + '/' + src + '/' + path + '/debug/build.prop'
    with open(buildprop,'r') as f:
        fr=f.read()
    #source_swv=re.findall(r'\d\.\d\.\d{3}\.\w{2}\.\d{6}\.\w+',fr)[0]
    source_swv=re.findall(r'ro.yulong.version.software=(\S+)',fr)[0]
    src_swv=re.findall(r'ro.build.id=(\S+)',fr)[0]
    #src_swv=re.match(r'ro.build.id=(\w+)',src_swv).groups()[0]
    print 'source_swv:    ',source_swv
    print 'src_swv   :    ',src_swv
    with open('src','w') as wf:
	wf.write(src_swv)
    buildprop = root + '/' + dest + '/' + path + '/debug/build.prop'
    with open(buildprop,'r') as f:
        fr=f.read()
    dest_swv=re.findall(r'ro.yulong.version.software=(\S+)',fr)[0]
    dst_swv=re.findall(r'ro.build.id=(\S+)',fr)[0]
    hardware=re.findall(r'ro.product.model=(\S+)',fr)[0]
    print 'dest_swv  :    ',dest_swv    
    print 'dst_swv   :    ',dst_swv
    with open('dest','w') as wf:
    	wf.write(dst_swv)
    #with open('description.txt','r') as f:
    #    description = f.read()
    m = re.match(r'\d\.\d\.\d{3}\.(\w{2})\.\d{6}\.(\w+)',dest_swv)
    hwversion = m.groups()[0]
    #hardware = m.groups()[1]
    print 'hwversion :    ',hwversion
    print 'hardware  :    ',hardware
    print 'description:   '
    print description
    dsp=description.split('\n')
    desc=r'\n'.join(dsp)
    description=desc
    print '************************Make UPC**************************'
    print 'OTA TYPE:', ota_type
    for type in ota_type.split(','):
	#做升级包
	if  type.strip()=='upgrade':
		print 'copy upgrade_zip to workspace........'
		shutil.copy(upgrade_zip,'.')         
		upc=UPC(source_swv,dest_swv,hardware,hwversion,up_file_name,description,priority)
		print 'make upgrade upc........'
		upc.MakeUPC()
		upc.dump()
		print 'make upgrade upc done.'
	#做降级包
	elif type.strip()=='downgrade':
		print 'copy downgrade_zip to workspace........'
		shutil.copy(downgrade_zip,'.')
		upc=UPC(dest_swv,source_swv,hardware,hwversion,down_file_name,description,priority)
		print 'make downgrade upc........'
		upc.MakeUPC()
		upc.dump()
		print 'make downgrade upc done.'
	#做全包    
	elif type.strip()=='full':
		print 'copy full_zip to workspace........'
		shutil.copy(full_zip,'.')
		upc=UPC(source_swv,dest_swv,hardware,hwversion,full_file_name,description,priority,'true')
		print 'make full upc........'
		upc.MakeUPC()
		upc.dump()
		print 'make full upc done.'
	else:
		print 'ota type is invalid'
