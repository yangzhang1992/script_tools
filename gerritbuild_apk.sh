#!/bin/bash -x
#apk gerrit build

#日志函数
function printcolor() {
	printf "\033[1;33m[debugshell]\033[0m \033[1;32m[`date "+%Y-%m-%d %H:%M:%S"`]\033[0m \033[1;31m$*\n\033[0m"
}

#签名文件
function f_signapk() {
	local signapk_jar=/dailybuild-sz/share/signapk/signapk.jar
	local platform_x509_pem=build_sign/target/product/security/platform.x509.pem
	local platform_pk8=build_sign/target/product/security/platform.pk8
	local input_apk=$1
	local output_apk=$2
	if [ -d build_sign ];then rm -rf build_sign; fi
	git clone ssh://gerrit.ccdomain.com:29418/git/android/platform/build build_sign -b  msm8996_nougat_r01055_20161021 || exit 1
	printcolor "apk signed"
	echo "java -Xmx2048m -jar ${signapk_jar} ${platform_x509_pem} ${platform_pk8} ${input_apk} ${output_apk}"
	java -Xmx2048m -jar ${signapk_jar} ${platform_x509_pem} ${platform_pk8} ${input_apk} ${output_apk} || ( echo "sign apk error" && exit 1 )
}

#签名并拷贝apk函数
function sign_and_cp_apk() {
	local apk_project=$1
	local out_apk=$2
	local outputpath=$3
	apk_basename=$(basename "$out_apk")
	apk_dirname=$(dirname "$out_apk")
	apk_releasename=$(echo $apk_basename | sed 's/unsigned/signed/g' | sed "s/^app/${apk_project}/g")
	if [ ! -d "$outputpath" ];then mkdir -p ${outputpath}; fi

	if [ "`echo "$apk_basename" | grep unsigned`" = "" ];then
		#不需要签名的apk，直接拷贝
		cp -v ${out_apk} ${outputpath}/${apk_releasename}
	else
		cd ${apk_dirname}
		#签名apk
		f_signapk ${apk_basename} ${apk_releasename}
		cp -v ${apk_releasename} ${outputpath}/${apk_releasename}
		cd - > /dev/null 2>&1
	fi
}

#apk工作目录
cd ${GERRIT_PROJECT}_${GERRIT_BRANCH}

#环境变量
export GRADLE_HOME=/opt/gradle/gradle-2.14.1
export PATH=${GRADLE_HOME}/bin:$PATH
export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64

#apk 输出路径
currentdate=$(date +%Y-%m-%d)
outputpath=/dailybuild-sz/share/app_output/${GERRIT_BRANCH}/${currentdate}

#apk 编译
printcolor "build ${GERRIT_PROJECT} ${GERRIT_BRANCH}"
echo "#" > local.properties
echo "sdk.dir=/opt/android-sdk-linux" >> local.properties
echo "ndk.dir=/opt/android-ndk-r10b" >> local.properties
gradle clean
gradle assembleRelease --info
if [ $? -eq 0 ]; then
	printcolor "build successfully"
	ssh -p 29418 buildfarm@gerrit.ccdomain.com gerrit review \
		--message '"build success: '${BUILD_URL}'"' \
		--verified 1 --code-review 1 ${GERRIT_CHANGE_NUMBER},${GERRIT_PATCHSET_NUMBER}
else
	printcolor "build error"
	ssh -p 29418 buildfarm@gerrit.ccdomain.com gerrit review \
		--message '"build fail：'${BUILD_URL}'"' \
		--verified -1 --code-review -1 ${GERRIT_CHANGE_NUMBER},${GERRIT_PATCHSET_NUMBER}
	exit 1
fi

#将apk编译结果签名并拷贝至dailybuild-sz下
apk=$(echo $GERRIT_PROJECT | awk -F / '{print $NF}')
apk_list=`find . -name outputs | xargs -i find {} -name "*unsigned.apk" -o -name "app-release.apk"`
echo -e "output apks:\n$apk_list"
for i in $apk_list
do
	sign_and_cp_apk "$apk" "$i" "$outputpath"
done

printcolor "\\\\\\\\172.16.3.136$(echo $outputpath | sed 's/\//\\\\/g')"
