#!/bin/bash

username=shen-buildfarm
password=


function mount_smb(){
    local L_MOUNTNAME=$1
    local L_MOUNTPOINT="/$L_MOUNTNAME"

    if mountpoint $L_MOUNTPOINT ;then
        echo "this is mount point, no need mount any"
    else
        sudo mount -t cifs //10.1.11.82/$L_MOUNTNAME $L_MOUNTPOINT -o guest,uid=$USER,gid=$USER,dir_mode=0755,file_mode=0644
    fi
}

DAILYBUILD="/dailybuild-sz"
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
    echo "will mount dailybuild server to /dailybuild-sz"
    sudo mount.cifs  //10.1.11.60/dailybuild-sz /dailybuild-sz -o credentials="$PWD/$0",uid=buildfarm,gid=buildfarm,dir_mode=0755,file_mode=0644,domain=xx
fi

mount_smb "opt"

