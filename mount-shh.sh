#!/bin/bash
username=srv-buildfarm
password=

DAILYBUILD="/dailybuild"
if mountpoint $DAILYBUILD ;then
    echo "this is mount point, no need mount any"
else
    echo "not mount point"
    if [ -d $DAILYBUILD ];then
        echo "dailybuild is exists"
    else
        echo "dailybuild is not exists,will create it"
        sudo mkdir $DAILYBUILD && sudo chown $USER:$USER $DAILYBUILD 
    fi
    echo "will mount dailybuild server to /dailybuild"
    sudo mount -t cifs  //10.0.12.12/dailybuild /dailybuild -o credentials="$PWD/$0",uid=$USER,gid=$USER,dir_mode=0755,file_mode=0644
fi

OPT="/opt"
if mountpoint $OPT ;then
    echo "this is mount point, no need mount any"
else
    echo "not mount point"
    echo "will mount android sdk to /opt "
    sudo mount -t cifs //jenkins.zeusis.com/opt /opt -o guest,uid=$USER,gid=$USER,dir_mode=0755,file_mode=0644
fi
