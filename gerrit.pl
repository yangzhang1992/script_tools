#!/usr/bin/perl

use Getopt::Long;
use Data::Dumper;
use POSIX;



my $version="1.0";
my $prog="gerrit.pl";

sub usage{
    printf "$prog [--branch | -b] branch

general options:
    --help          | -h    usage message
    --version       | -v    version number and copyright
    --branch        | -b    gerrit git project branch name
    --reviewer      | -r    add reviewer email
    --drafts        | -d    push to drafts
\n\n";
}

sub print_hex {
    my ($str) = @_;
    my @arr = split //, $str;
    for my $c (@arr) {
        printf "<%x>", ord($c);
    }
    printf "\n";
}
sub main{
    my $cimsg = `git log -n 1`;
    if($cimsg =~ /Change-Id:/){

    }else{
        print "No Change-Id in commit message!\n";
        print "Get commit-msg by \"scp -p -P 29418 gerrit host:hooks/commit-msg .git/hooks/\".\n";
        print "Git commit again.\n";
        return 1;
    }

    my $project = "";
    my $remote = `git remote -v`;
    if($remote){
        my @temp = split(" ", $remote);
        $project = $temp[1];
    }else{
        print "No git project in current directory!\n";
        return 1;
    }
    if($project){

    }else{
        print "No git project in remote server!\n";
        return 1;
    }

    my $user = `git config --get user.name`;
    if($user){

    }else{
        print "No git user, add your git email by \"git config --global user.email xxx\@yyy.com\".";
        return 1;
    }
    if($branch){
        my $cmd = "git push ${project}  HEAD:refs/for/$branch";
        if($draft){#推送为草稿类型
            $cmd = "git push ${project}  HEAD:refs/drafts/$branch";
        }
        if($reviewer){
            $cmd = "$cmd"."%r=$reviewer";
        }
        print "$cmd\n";
        my $res = `$cmd`;
    }else{
        my $remotebranch = `git branch -a`;
        print "==未指定branch===================\n$remotebranch=================================\n";
        return 1;
    }

    return 0;
}#end main

unless (GetOptions(
    "help|h"               => sub{&usage(); exit RET_OK;},
    "version|v"            => sub{&version(); exit RET_OK;},
    "branch|b=s"           => \$branch,
    "reviewer|r=s"         => \$reviewer,
    "drafts|d"             => \$draft
    )){
    &usage();
    exit RET_INVALID_CALL;
}
main();
