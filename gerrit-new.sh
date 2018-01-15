#!/bin/bash
# Helper script to ease the task of pushing commits to gerrit server

##################
# Global variables
##################
progname=$(basename "$0")

# Port number of gerrit ssh server, typically 29418
g_port=29418

# Gerrit host name like "gerrit.zeusis.com"
g_gerrit_host=

# Gerrit remote name, zsgit, letv, etc.
g_remote=

# Gerrit project name like "ssh://gerrit.zeusis.com:29418/git/android/platform/manifest"
g_project=

# Default email host
g_email_host=

##################
# Functions
##################

# Ensure that git envionment is ready
check_git_env()
{
    local remotes
    local no_use

    no_use=$(git config --get user.name)
    if [ $? -ne 0 ]; then
        echo "Error: No git user name configured."
        echo "Add it by \"git config --global user.name <your name>\"."
        usage
    fi

    no_use=$(git config --get user.email)
    if [ $? -ne 0 ]; then
        echo "Error: No git email configured."
        echo "Add it by \"git config --global user.email xxx@yyy.zzz\"."
        usage
    fi

    remotes=$(git remote)
    if [ $? -ne 0 ]; then
        echo "Error: git repository not found or no remote server found."
        usage
    fi
}

# Parse "git remote -v" output, use specified remote to match and find correct remote and project name
get_gerrit_info_from_remote()
{
    local remote_str
    local py_git_remote_re
    local port

    remote_str=$(git remote -v | grep "(push)" | grep -P "^${g_remote}[\s]+" | head -1)
    if [ "$remote_str" == "" ]; then
        echo "Error: No matching remote server found."
        usage
    fi

    g_project=$(echo "$remote_str" | awk '{print $2}')
    if [ "$g_project" == "" ]; then
        echo "Error: No correct project name found."
        usage
    fi

    #FIXME: We only support ssh protocol for now
    # Consider more verbose re match like this one "((git|ssh|http(s)?)|(git@[\w\.]+))(:(//)?)([\w\.@\:/\-~]+)(\.git)(/)?"
    # on https://www.debuggex.com/r/H4kRw1G0YPyBFjfm
    #
    # Currently we support these gerrit host names:
    # dianar:/ruby/platform/system/core
    # ssh://10.5.11.13:29418/git/yulong/qualcomm/frameworks/base
    # ssh://gerrit.zeusis.com:29418/git/android/platform/manifest
    py_git_remote_re="'^(ssh://)?([\w\.]+@)?(?P<host>[\w\.]+)(:(?P<port>[\d]*))?/[\w]+'"

    g_gerrit_host=$(echo $g_project | python -c "import re,sys; print re.search(r$py_git_remote_re, sys.stdin.read()).group('host')")

    port=$(echo $g_project | python -c "import re,sys; print re.search(r$py_git_remote_re, sys.stdin.read()).group('port') or ''")
    if [ "$port" != "" ]; then
        g_port=$port
    fi
}

# Get git remote name
# Selection order:
# 1. If only one remote, just use it
# 2. If more remotes found, try to use git remote that repo uses ("m/")
# 3. If no repo is used, let user choose git remote
get_git_remote()
{
    remote_count=$(git remote | wc -l)
    if [ $remote_count -eq 0 ]; then
        echo "Error: No git remote found."
        usage
    elif [ $remote_count -eq 1 ]; then
        g_remote=$(git remote)
    else
        g_remote=$(git branch -r | grep "^ *m/" |head -1 | perl -p -e 's#^.+-> (.+)/.+#\1#g')
        if [ "$g_remote" == "" ]; then
            echo "Found $remote_count git remotes:"
            git remote -v |grep "(push)" |cat -n

            selection=""
            while [[ ! "$selection" =~ ^[1-$remote_count]$ ]]; do
                echo -e "Please select one (1-${remote_count}):"
                read selection
            done
            g_remote=$(git remote -v | grep "(push)" | awk '{print $1}' | sed "${selection}q;d")
            echo "git remote selected: $g_remote"
        fi
    fi
}

# Config several global variables according to remote option
config_gerrit_variables()
{
    g_remote=$remote_opt

    # If not specified, we try to get remote from current dir
    if [ "$g_remote" == "" ]; then
        get_git_remote
    fi

    get_gerrit_info_from_remote

    if [ "$g_gerrit_host" == "gerrit.zeusis.com" ]; then
        g_email_host="coolpad.com"
    elif [ "$g_gerrit_host" == "dianar" ]; then
        g_email_host="le.com"
    else
        g_email_host="yulong.com"
    fi
}

usage()
{
    cat <<EOF

Usage: $progname [-vfqD] [-g remote] [-c value] [-r email1,email2,...] [-m message] [branch name]

If no "branch name" specified, this script will automatically find the branch specified by repo
manifest file.

Options:
    -m  Specify comments
    -t  Specify Gerrit "topic" name
    -r  Set reviewer email list separated by comma, like 'john@foo.com,tom@bar.com'
        If no '@host.name' specified, default email hosts are used for different git remote(-g):
        '@coolpad.com' for 'gerrit.zeusis.com'
        '@le.com' for 'dianar'
        '@yulong.com' for other git remotes
    -d  Push as drafts instead
    -c  Set Code-Review as 'value', valid values are: 1, 2, +1, +2, -1, may need corresponding
        permission settings in Gerrit
    -v  Set Verified +1
    -D  Dry run: set --dry-run in git push
    -f  Force to continue reviewer and other actions even if commits push failed
    -q  Set to 'quiet' mode: no confirmation before pushing commits
    -g  Specify git remote like zsgit, yl.nj, letv, etc. (default: auto detect)
    -h  This help message

EOF
    exit 1
}

check_code_review_option()
{
    # Verify Code Review values are valid
    if [ "$code_review" == "1" -o "$code_review" == "2" ]; then
        code_review=+$code_review
    fi

    if [ "$code_review" != "+1" -a "$code_review" != "+2" -a "$code_review" != "-1" ]; then
        echo "Error: Bad Code Review value: $code_review"
        usage
    fi
}

##################
# Main entry
##################
export PATH=/bin:/sbin/:/usr/bin:$PATH

reviewers=
remote_opt=
code_review=
dry_run=
force_continue=false
quiet=false
verified=false
drafts=false
message=
topic=
while getopts :r:g:c:vdDfqhm:t: opt; do
    case $opt in
        r)
            reviewers="$OPTARG"
            ;;
        g)
            remote_opt="$OPTARG"
            ;;
        c)
            code_review="$OPTARG"
            check_code_review_option
            ;;
        v)
            verified=true
            ;;
        d)
            drafts=true
            ;;
        D)
            dry_run="--dry-run "
            ;;
        f)
            force_continue=true
            ;;
        q)
            quiet=true
            ;;
        m)
            message="$OPTARG"
            ;;
        t)
            topic="$OPTARG"
            ;;
        h|\?)
            usage
            ;;
    esac
done

shift $((OPTIND-1))

if [ "$1" == "--help" ]; then
    usage
fi

check_git_env

config_gerrit_variables

# Get branch to push to
if [ $# -lt 1 ]; then
    branch=$(git branch -r | grep "^ *m/" | head -1 | perl -p -e 's#^.+/##g')
else
    branch="$1"
fi

if [ "$branch" == "" ]; then
    echo "Error: No remote branch specified and no default branch found!"
    usage
fi

echo Project: $g_project
echo Branch: $branch
echo

#FIXME: user prefix is basically not working now, enable it later if there is requirement
user_prefix=
#Overwrite user name from env variables if set
if [ "$GERRIT_USER" != "" ]; then
    user_prefix="${GERRIT_USER}@"
fi

#################################################
# Build up final git push command line below
#################################################

# Push as 'drafts' or not?
if $drafts; then
    push_target="drafts"
else
    push_target="for"
fi

cmd="git push --no-thin $dry_run $g_remote HEAD:refs/$push_target/$branch"

if [ "$topic" != "" ]; then
    cmd="$cmd/$topic"
fi

echo $cmd

# Review commits to push
commits_count=$(git log --oneline "$g_remote"/$branch.. | wc -l)
commit_ids=$(git log --format=%h "$g_remote"/$branch..)
if [ $commits_count -eq 0 ]; then
    echo "Error: No commits found, possibly wrong branch name $branch?"
    exit 1
fi
echo commits count: $commits_count
git log --oneline "$g_remote"/$branch..

#Find Change-Id info
change_ids=
for commit_id in $commit_ids; do
    change_id=$(git show --format=%b -s $commit_id |tac |grep -P '^Change-Id: ' |head -1 |sed 's/Change-Id: //g')
    if [ "$change_id" == "" ]; then
        echo "Error: commit $commit_id has no Change-Id. Detailed info for this commit:"
        git show -s $commit_id
        cat <<EOF

Please check this and fix this commit.
It's possible that you don't have correct commit-msg hook. In that case get
commit-msg by "scp -p -P $g_port $g_gerrit_host:hooks/commit-msg .git/hooks/"
and commit again by "git commit --amend"
EOF
        exit 1
    fi
    change_ids="$change_ids $change_id"
done

# Need extra confirm before pushing large set of commits, unless 'quiet' option set
if [ "$quiet" != "true" ] && [ $commits_count -gt 2 ]; then
    echo -n "Push these commits? [y/n]: "
    read ans
else
    ans=Y
fi

# Push commits
case "${ans}" in
    "y"|"Y")
        ${cmd}
        if [ $? -eq 0 ]; then
            echo "Push commit done!"
        elif $force_continue; then
            echo "Push commits failed but forced to continue..."
        else
            echo "Error pushing commits"
            exit 1
        fi
        ;;
    *)
        echo "Push commit abort!"
        exit 1
        ;;
esac

#################################################
# Extra steps below after commits pushed
#################################################

# For lazy error handling
set -e

# Set reviewers
if [ "$reviewers" != "" ]; then
    IFS=';,' read -ra reviewers_array <<< "$reviewers"
    reviewers_arg=
    for reviewer in "${reviewers_array[@]}"; do
        if [[ $reviewer != *"@"* ]]; then
            reviewer="${reviewer}@${g_email_host}"
        fi
        reviewers_arg="$reviewers_arg -a $reviewer"
    done
    echo "Setting reviewers to $reviewers:"

    for commit_id in $commit_ids; do
        echo ssh ${user_prefix}$g_gerrit_host -p $g_port gerrit set-reviewers $reviewers_arg $commit_id
        ssh ${user_prefix}$g_gerrit_host -p $g_port gerrit set-reviewers $reviewers_arg $commit_id
    done
fi

# Set other options
for commit_id in $commit_ids; do
    if $verified; then
        echo "Commit $commit_id Verified +1"
        ssh ${user_prefix}$g_gerrit_host -p $g_port gerrit review --verified +1 $commit_id
    fi

    if [ "$message" != "" ]; then
        # Note that gerrit review command requires special quoting of message string
        echo "Commit $commit_id add comment: $message"
        ssh ${user_prefix}$g_gerrit_host -p $g_port gerrit review -m "'$message'" $commit_id
    fi

    if [ "$code_review" != "" ]; then
        echo "Commit $commit_id Code Review $code_review"
        ssh ${user_prefix}$g_gerrit_host -p $g_port gerrit review --code-review "$code_review" $commit_id
    fi
done
