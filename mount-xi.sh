#!/bin/bash

username=xi-buildfarm
password=


function mount_smb(){
    local L_MOUNTNAME=$1
    local L_MOUNTPOINT="/home/$L_MOUNTNAME"

    if mountpoint $L_MOUNTPOINT ;then
        echo "this is mount point, no need mount any"
    else
        [ -d $L_MOUNTPOINT ] || sudo mkdir -p "$L_MOUNTPOINT"
        sudo mount -t cifs //192.168.38.176/$L_MOUNTNAME $L_MOUNTPOINT -o guest,uid=$USER,gid=$USER,dir_mode=0755,file_mode=0644
    fi
}

DAILYBUILD="/dailybuild-xi"
if mountpoint $DAILYBUILD ;then
    echo "this is mount point, no need mount any"
else
    echo "not mount point"
    if [ -d $DAILYBUILD ];then
        echo "dailybuild is exists"
    else
        echo "dailybuild is not exists,will create it"
        sudo mkdir -p $DAILYBUILD && sudo chown $USER:$USER $DAILYBUILD
    fi
    echo "will mount dailybuild server to /dailybuild"
    #sudo mount -t cifs  //192.168.38.174/dailybuild-xi /dailybuild-xi -o username=xi-buildfarm,password=XIserver2016^,uid=$USER,gid=$USER,dir_mode=0755,file_mode=0644,domain=xx
    sudo mount.cifs  //192.168.38.174/dailybuild-xi /dailybuild-xi -o credentials="$PWD/$0",uid=buildfarm,gid=buildfarm,dir_mode=0755,file_mode=0644,domain=xx
fi

mount_smb "mirror"
mount_smb "zeusis-mirror"
mount_smb "qcom"

