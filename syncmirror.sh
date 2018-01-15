#!/bin/bash -x

ssh  -o StrictHostKeyChecking=no -p 29418 gerrit-sh.zeusis.com gerrit version
ssh  -o StrictHostKeyChecking=no -p 29418 gerrit-sz.zeusis.com gerrit version
ssh  -o StrictHostKeyChecking=no -p 29418 gerrit-xi.zeusis.com gerrit version

REPO_URL="ssh://gerrit-sh.zeusis.com:29418/git/android/tools/repo"
MANIFEST_URL="ssh://gerrit-sh.zeusis.com:29418/git/android/platform/manifest"
MANIFEST_FILE="zeusis/MSM8953_3701A_20170224.xml"
MANIFEST_BRANCH="zs_master"

REPO_INIT="repo init"
REPO_SYNC="repo sync"
REPO_INIT_OTHEROPT=" --repo-branch stable --no-repo-verify --mirror"

cd /home/mirror


echo ${NODE_NAME}
NUMBER=${NODE_NAME##*-}
NUMBER=`expr $NUMBER % 2`
if [ "${NUMBER}" = "0" ];then
    MANIFEST_URL="ssh://gerrit-sh.zeusis.com:29418/git/android/platform/manifest"
else
    MANIFEST_URL="ssh://gerrit.zeusis.com:29418/git/android/platform/manifest"
fi

rm -rf .repo
MANIFEST_FILE="zeusis/MSM8953_3701A_20170224.xml"
$REPO_INIT -u "$MANIFEST_URL"  -b "$MANIFEST_BRANCH" -m "$MANIFEST_FILE" --repo-url "$REPO_URL" "$REPO_INIT_OTHEROPT"
$REPO_SYNC


exit 0

rm -rf .repo
MANIFEST_FILE="zeusis/ZSUI_MSM8953_APK_20161109.xml"
$REPO_INIT -u "$MANIFEST_URL"  -b "$MANIFEST_BRANCH" -m "$MANIFEST_FILE" --repo-url "$REPO_URL" "$REPO_INIT_OTHEROPT"
$REPO_SYNC



if [ "$RUN_GIT_GC" = "true" ];then
	find . -name "*.git" -type d -exec bash -c 'src="{}"; echo "=$src="; git -C "$src" gc' \;
fi

#########################################################################################################################################

