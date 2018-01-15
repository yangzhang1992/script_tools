#!/bin/bash
#添加员工帐号的脚本

PASS="123456"
BASE_WORK="/work"
for n in $1
do
    if [[ $n =~ "wx_" ]];then
        LOGIN=$(echo $n|awk -F "." '{print $1}'|awk -F "_" '{print $2}')
    else
        LOGIN=$(echo $n|awk -F "." '{print $1}')
    fi
    echo "cmd =useradd -m -s /bin/bash $LOGIN -c $n="
    useradd -m -s /bin/bash $LOGIN -c $n

    echo "cmd =echo $LOGIN:$PASS | chpasswd="
    echo $LOGIN:$PASS | chpasswd

    echo "cmd =echo -ne $PASS\n$PASS\n | smbpasswd -a -s $LOGIN="
    echo -ne "$PASS\n$PASS\n" | smbpasswd -a -s $LOGIN

    USER_WORK=$BASE_WORK/$LOGIN
    LINK_WORK=/home/$LOGIN/work

    mkdir $USER_WORK && chown $LOGIN:$LOGIN $USER_WORK -R
    ln -s $USER_WORK $LINK_WORK && chown $LOGIN:$LOGIN $LINK_WORK -h
done

