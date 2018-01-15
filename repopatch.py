import sys
import os
import commands

def log_read(filename=""):
    with open(filename,"r") as log_file:
        log_info=log_file.readlines()
        patch={}
        # print log_info
        for i,j  in enumerate(log_info):
            # print i,"++++>>>>",j
            if j.startswith("/") and i !=(len(log_info)-1) :
                single_patch = []
                for k in range(i+1,len(log_info)):

                    if ("[" in log_info[k] and "]" in log_info[k]) or "|" in log_info[k]:
                        single_patch.append(log_info[k])
                    else:
                        if single_patch!=[]:
                            patch[log_info[i]]=single_patch
                            break
                        else:
                            break
        # for m in patch.keys():
        #     print m,"#######",patch[m]
        return patch

def cherry(patch={},branch=""):
    try:
        error_workplace=[]
        error_cherry=[]
        error_push=[]
        for i in patch.keys():
            print type(patch[i])
            print "the workplace is :  ",i.replace("\n","")
            cmd="cd "+i.replace("\n","")
            os.chdir(i.replace("\n",""))
            for j in patch[i][::-1]:
                print "the hash is: ",j[0:7]
                cmd_1="pwd && git cherry-pick "+j[0:7]
                ret_1=os.system(cmd_1)
                if ret_1!=0:
                    cmd_3="git cherry-pick --abort"
                    ret_3=os.system(cmd_3)
                    error_cherry.append(i.replace("\n","")+":"+j)
                cmd_2="git push zsgit HEAD:"+branch
                ret_2=os.system(cmd_2)
                if ret_2!=0:
                    error_push.append(i.replace("\n","")+":"+j)
    except Exception as e:
        print e.message

    if error_workplace !=[]:
        print "the worksplace is error"
        for error_i in error_workplace:
            print error_i
    else:
        print "all worksplace is ok"
    if error_cherry !=[]:
        print "cherry pick is error"
        for error_j in error_cherry:
            print error_j
    else:
        print "all cherry-pick is ok"
    if error_push !=[]:
        print "push is error"
        for error_k in error_push:
            print error_k
    else:
        print "all push is ok"



if __name__=="__main__":
    branch=sys.argv[1]
    patch=log_read("log1.txt")
    cherry(patch,branch)
    #for i in patch.keys():
    #    print i,"===>",patch[i]
