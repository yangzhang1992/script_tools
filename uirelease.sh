#!/bin/bash

apklist=$1
basebranch=$2
relbranch=$3
zsuitype=$4

printcolor() {
    printf "\033[1;33m[debugshell]\033[0m \033[1;32m[`date "+%Y-%m-%d %H:%M:%S"`]\033[0m \033[1;31m$*\n\033[0m"
}

#mkdir zsui/date to save apk
currentdate=$(date +%Y-%m-%d)
apkpath=/dailybuild-sz/apk/$basebranch/$currentdate

if [ ! -d "$apkpath" ];then
    mkdir -p $apkpath
fi
printcolor "apklist is $apklist"
printcolor "apkpath is $apkpath"
printcolor "relbranch is $relbranch"

export GRADLE_HOME=/opt/gradle/gradle-2.14.1
export PATH=$GRADLE_HOME/bin:$PATH
export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64

export -p

basepath=$(pwd)

for apk in ${apklist[@]}
do
    cd $basepath
    git clone --depth=100 ssh://gerrit.ccdomain.com:29418/git/android/platform/vendor/zeusis/zui/app/$apk -b $basebranch && scp -p -P 29418 gerrit.ccdomain.com:hooks/commit-msg $apk/.git/hooks/

    #获取源码分支最新的commitID
    cd $basepath/$apk
    newid=$(git --no-pager log --pretty="%H" -1)
    git clone --depth=1 ssh://gerrit.ccdomain.com:29418/git/android/platform/vendor/zeusis/zui/app/$apk $apk-$relbranch -b $relbranch && scp -p -P 29418 gerrit.ccdomain.com:hooks/commit-msg $apk-$relbranch/.git/hooks/

    #获取release分支上次release的commit信息
    cd $basepath/$apk/$apk-$relbranch
    lastcomid=$(git --no-pager log --author=Buildfarm --pretty="%s " -1 | cut -d "|" -f 2 | sed -e s/[[:space:]]//g)

    #回源码仓库获取log信息
    cd $basepath/$apk
    reg='[a-z0-9]{40}'
    if [[ "$lastcomid" =~ $reg ]];then
        #commitbody=$(git --no-pager log --date=short --pretty="%H -- %an -- %ad -- %s |" $lastcomid...)
        commitbody=$(git log --pretty='format: %<(15,trunc)%an  %<(25,trunc)<gitlog> %ae <gitlog> %H  %<(20)<gitlog>  %ci  <gitlog>  %s' $lastcomid...)
        if [ $? != 0 ]; then
            printcolor "$lastcomid missing,maybe because of different branch"
            commitbody=$(git log --pretty='format: %<(15,trunc)%an  %<(25,trunc)<gitlog> %ae <gitlog> %H  %<(20)<gitlog>  %ci  <gitlog>  %s' -5)
        fi
    #在新拉源码分支log很多的情况下，取最新5条
    else
        printcolor "$apk is firstly release"
        #commitbody=$(git --no-pager log --date=short --pretty="%H -- %an -- %ad -- %s |" -5)
        commitbody=$(git log --pretty='format: %<(15,trunc)%an  %<(25,trunc)<gitlog> %ae <gitlog> %H  %<(20)<gitlog>  %ci  <gitlog>  %s' -5)
    fi


    if [ -z "$commitbody" ];then
        printcolor "no need update apk $apk"
        echo "$apk" >> $basepath/noupdate.txt
        continue
    fi

    # start to build apk
    printcolor "start to build $apk"
    echo "#" > local.properties
    echo "sdk.dir=/opt/android-sdk-linux$zsuitype" >> local.properties
    echo "ndk.dir=/opt/android-ndk-r10b" >> local.properties

    gradle clean
    gradle assembleRelease

    if [ $? -eq 0 ]; then
        printcolor "$apk build successfully,start to commit"
    else
        printcolor "$apk build error,skip and continue"
        echo "$apk" >> $basepath/fail.txt
        continue
    fi

    if [ $apk = "ZsPhoneManager" ];then
        gradle assembleDebug
        if [ $? -eq 0 ]; then
            printcolor "$apk assembleDebug build successfully,start to commit"
        else
            printcolor "$apk assembleDebug build error,skip and continue"
            echo "$apk" >> $basepath/fail.txt
            continue
        fi
    fi
    if [ $apk = "I19tService" ];then
        gradle makeDexJar
        if [ $? -eq 0 ]; then
            printcolor "$apk makeJar build successfully,start to commit"
        else
            printcolor "$apk makeJar build error,skip and continue"
            echo "$apk" >> $basepath/fail.txt
            continue
        fi
    fi

    #special for email
    if [ $apk = "Email" ];then
        #copy email
        cp -rv $basepath/$apk/CP_Email/build/outputs/apk/CP_Email-release-unsigned.apk $basepath/$apk/$apk-$relbranch/Email-unsigned.apk
        cp -rv $basepath/$apk/CP_Email/build/outputs/apk/CP_Email-release-unsigned.apk $apkpath/Email-unsigned.apk
        #copy exchange
        cp -rv $basepath/$apk/Exchange/build/outputs/apk/Exchange-release-unsigned.apk $basepath/$apk/$apk-$relbranch/Exchange-unsigned.apk
        cp -rv $basepath/$apk/Exchange/build/outputs/apk/Exchange-release-unsigned.apk $apkpath/Exchange-unsigned.apk
        apkname="Email-unsigned.apk Exchange-unsigned.apk"
    elif [ $apk = "ZsEmail" ];then
        #copy email
        cp -rv $basepath/$apk/app/build/outputs/apk/app-release-unsigned.apk $basepath/$apk/$apk-$relbranch/ZsEmail-unsigned.apk
        cp -rv $basepath/$apk/app/build/outputs/apk/app-release-unsigned.apk $apkpath/ZsEmail-unsigned.apk
        #copy exchange
        cp -rv $basepath/$apk/exchange/build/outputs/apk/exchange-release-unsigned.apk $basepath/$apk/$apk-$relbranch/ZsExchange-unsigned.apk
        cp -rv $basepath/$apk/exchange/build/outputs/apk/exchange-release-unsigned.apk $apkpath/ZsExchange-unsigned.apk
        apkname="ZsEmail-unsigned.apk ZsExchange-unsigned.apk"
    elif [ $apk = "ZsPhoneManager" ];then
        #copy ZsPhoneManager-release-unsigned.apk for Release Key
        cp -rv $basepath/$apk/build/outputs/apk/ZsPhoneManager-release-unsigned.apk $basepath/$apk/$apk-$relbranch/ZsPhoneManager-release-unsigned.apk
        cp -rv $basepath/$apk/build/outputs/apk/ZsPhoneManager-release-unsigned.apk $apkpath/ZsPhoneManager-release-unsigned.apk
        #copy sPhoneManager-debug.apk for Test Key
        cp -rv $basepath/$apk/build/outputs/apk/ZsPhoneManager-debug.apk $basepath/$apk/$apk-$relbranch/ZsPhoneManager_unsigned.apk
        cp -rv $basepath/$apk/build/outputs/apk/ZsPhoneManager-debug.apk $apkpath/ZsPhoneManager-debug.apk
        apkname="ZsPhoneManager_unsigned.apk ZsPhoneManager-release-unsigned.apk"
    elif [ $apk = "Zs3DNotepad" ];then
        cp -rv $basepath/$apk/app/build/outputs/apk/app-release.apk $basepath/$apk/$apk-$relbranch/Zs3DNotepad_release.apk
        cp -rv $basepath/$apk/app/build/outputs/apk/app-release.apk $apkpath/Zs3DNotepad_release.apk
        apkname="Zs3DNotepad_release.apk"
    elif [ $apk = "ZsAssistantapi" ];then
        cp -rv $basepath/$apk/assistantservice/build/outputs/apk/assistantservice-release-unsigned.apk $basepath/$apk/$apk-$relbranch/ZsAssistantapi-unsigned.apk
        cp -rv $basepath/$apk/assistantservice/build/outputs/apk/assistantservice-release-unsigned.apk $apkpath/ZsAssistantapi-unsigned.apk
        #copy aar
        cp -rv $basepath/$apk/assistantapi/build/outputs/aar/assistantapi-release.aar $basepath/$apk/$apk-$relbranch/assistantapi-release.aar
        apkname="ZsAssistantapi-unsigned.apk assistantapi-release.aar"
    elif [ $apk = "Messaging" ];then
        cp -rv $basepath/$apk/messaging/build/outputs/apk/* $basepath/$apk/$apk-$relbranch/
        cp -rv $basepath/$apk/messaging/build/outputs/apk/* $apkpath/
        apkname=`ls $basepath/$apk/messaging/build/outputs/apk/`
    elif [ $apk = "PNInfoProvider" ];then
        cp -rv $basepath/$apk/build/outputs/apk/PNInfoProvider-teddyVersion-release-unsigned.apk $basepath/$apk/$apk-$relbranch/PNInfoProvider-teddyVersion-release-unsigned.apk
        cp -rv $basepath/$apk/build/outputs/apk/PNInfoProvider-teddyVersion-release-unsigned.apk $apkpath/PNInfoProvider-teddyVersion-release-unsigned.apk
        cp -rv $basepath/$apk/build/outputs/apk/PNInfoProvider-unioncastVersion-release-unsigned.apk $basepath/$apk/$apk-$relbranch/PNInfoProvider-unioncastVersion-release-unsigned.apk
        cp -rv $basepath/$apk/build/outputs/apk/PNInfoProvider-unioncastVersion-release-unsigned.apk $apkpath/PNInfoProvider-unioncastVersion-release-unsigned.apk
        cp -rv $basepath/$apk/build/outputs/apk/PNInfoProvider-yuloreVersion-release-unsigned.apk $basepath/$apk/$apk-$relbranch/PNInfoProvider-yuloreVersion-release-unsigned.apk
        cp -rv $basepath/$apk/build/outputs/apk/PNInfoProvider-yuloreVersion-release-unsigned.apk $apkpath/PNInfoProvider-yuloreVersion-release-unsigned.apk
        apkname="PNInfoProvider-teddyVersion-release-unsigned.apk PNInfoProvider-unioncastVersion-release-unsigned.apk PNInfoProvider-yuloreVersion-release-unsigned.apk"
    elif [ $apk = "Dialer" ];then
        cp -rv $basepath/$apk/build/outputs/apk/Dialer-teddyVersion-release-unsigned.apk $basepath/$apk/$apk-$relbranch/Dialer-teddyVersion-release-unsigned.apk
        cp -rv $basepath/$apk/build/outputs/apk/Dialer-teddyVersion-release-unsigned.apk $apkpath/Dialer-teddyVersion-release-unsigned.apk
        cp -rv $basepath/$apk/build/outputs/apk/Dialer-unioncastVersion-release-unsigned.apk $basepath/$apk/$apk-$relbranch/Dialer-unioncastVersion-release-unsigned.apk
        cp -rv $basepath/$apk/build/outputs/apk/Dialer-unioncastVersion-release-unsigned.apk $apkpath/Dialer-unioncastVersion-release-unsigned.apk
        apkname="Dialer-teddyVersion-release-unsigned.apk Dialer-unioncastVersion-release-unsigned.apk"
    elif [ $apk = "CoolM7" ];then
        cp -rv $basepath/$apk/build/outputs/apk/* $basepath/$apk/$apk-$relbranch/
        cp -rv $basepath/$apk/build/outputs/apk/* $apkpath/
        apkname=`ls $basepath/$apk/build/outputs/apk/`
    elif [ $apk = "I19tService" ];then
        cp -rv $basepath/$apk/dispatcher/build/outputs/apk/dispatcher-release-unsigned.apk $basepath/$apk/$apk-$relbranch/I19tService_unsigned.apk
        cp -rv $basepath/$apk/dispatcher/build/outputs/apk/dispatcher-release-unsigned.apk $apkpath/I19tService_unsigned.apk
        cp -rv $basepath/$apk/i19tsdk/build/outputs/jar/i19tsdk.jar $basepath/$apk/$apk-$relbranch/i19tsdk.jar
        cp -rv $basepath/$apk/i19tsdk/build/outputs/jar/i19tsdk_compile.jar $basepath/$apk/$apk-$relbranch/i19tsdk_compile.jar
        apkname="I19tService_unsigned.apk i19tsdk.jar i19tsdk_compile.jar"
    elif [ $apk = "MobileVoc" ];then
        cp -rv $basepath/$apk/app/build/outputs/apk/app-release.apk $basepath/$apk/$apk-$relbranch/MobileVoc_release.apk
        cp -rv $basepath/$apk/app/build/outputs/apk/app-release.apk $apkpath/MobileVoc_release.apk
        apkname="MobileVoc_release.apk"
    elif [ $apk = "RROApps" ];then
        cp -rv $basepath/$apk/journeyui_overlay_message_64/build/outputs/apk/journeyui_overlay_message_64-release-unsigned.apk        $basepath/$apk/$apk-$relbranch/
        cp -rv $basepath/$apk/journeyui_overlay_launcher_64/build/outputs/apk/journeyui_overlay_launcher_64-release-unsigned.apk      $basepath/$apk/$apk-$relbranch/
        cp -rv $basepath/$apk/journeyui_overlay_settings_64/build/outputs/apk/journeyui_overlay_settings_64-release-unsigned.apk      $basepath/$apk/$apk-$relbranch/
        cp -rv $basepath/$apk/journeyui_overlay_dialer_64/build/outputs/apk/journeyui_overlay_dialer_64-release-unsigned.apk          $basepath/$apk/$apk-$relbranch/
        apkname="RROApps_release.apk"
    else
        #find correct apkpath and rename apk
        apk_outputs=$(find ./ -path "./$apk-$relbranch" -a -prune -o -name "*unsigned.apk" -print)
        correctpath=$(dirname "$apk_outputs")
        printcolor "correctpath is $correctpath"
        cd $correctpath

        apkname="$apk"_unsigned.apk
        printcolor "apkname is $apkname"

        mv *unsigned.apk $apkname
        if [ $? -eq 0 ]; then
            printcolor "$apk named correcttly,start to rename"
         else
            printcolor "$apk named error,skip and continue"
            echo "$apk" >> $basepath/fail.txt
            continue
        fi

        #copy apk to dailybuild
        cp -rv $apkname $apkpath

        # clone zsui_apk
        cp -rv $apkname $basepath/$apk/$apk-$relbranch
    fi

    # commit
    cd $basepath/$apk/$apk-$relbranch

    git add $apkname
    git commit -m"update $apk $currentdate |$newid" -m"$commitbody"
    git push origin HEAD:refs/for/$relbranch%submit

done

#列出apk的编译结果
cd $basepath
if [ -f noupdate.txt ];then
    noupdate=$(cat noupdate.txt)
    printcolor "No need update apklist is:"
    printcolor $noupdate
fi
if [ -f fail.txt ];then
    failapk=$(cat fail.txt)
    printcolor "Build fail apklist is:"
    printcolor $failapk
fi








