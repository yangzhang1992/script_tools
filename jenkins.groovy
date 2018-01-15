import java.util.regex.Matcher
import java.util.regex.Pattern

manifest_file = manager.envVars['MANIFEST_FILE']
manifest_file = new File(manifest_file)

def getChangeLogHtml(filename){
        Pattern pattern = Pattern.compile("<body>(.*)</body>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL);
        //这里是把,build的change log 显示出来。
        htmlfile = new File(manifest_file.getParent(), filename)
        if(htmlfile.exists()){
            Matcher matcher = pattern.matcher(htmlfile.text);
            while(matcher.find()){
                body = matcher.group(1)
            }
            return body
        } else {
            return  ""
        }
}

def getBuildFailLogHtml(filename){
        Pattern pattern = Pattern.compile("(<pre>.*</pre>)", Pattern.CASE_INSENSITIVE | Pattern.DOTALL);
        htmlfile = new File(manifest_file.getParent(), filename)
        if(htmlfile.exists()){
            Matcher matcher = pattern.matcher(htmlfile.text);
            while(matcher.find()){
                body = matcher.group(1)
            }
            return body
        } else {
            return ""
        }
}

//这里是把,ondemand 的change log 显示出来。
html = getChangeLogHtml("changelog.ondemand.html")
summary = manager.createSummary("notepad.png")
summary.appendText(html, false)

//这里显示gerrit相关的变量
gerrit_file = new File(manifest_file.getParent(), "gerrit.cfg")
gerrit_file.eachLine{ line ->
    if (line.contains("GERRIT_PATCHSET_UPLOADER_EMAIL")){
        email = "$line"
        email = email.split("=")[1]
        manager.addShortText(email, "grey", "white", "0px", "white")
    }
}

// 显示上游job的build url地址
summary = manager.createSummary("orange-square.png")
jenkins_file = new File(manifest_file.getParent(), "jenkins.cfg")
jenkins_file.eachLine{ line ->
    url = "$line"
    url = url.split("=")[1]
    summary.appendText("<bre><a href=\"" + url + "\">upstream job build url</a></bre>", false)
}


//显示编译错误log
product = manager.envVars['PRODUCT']
variant = manager.envVars['VARIANT']
carrier = manager.envVars['CARRIER']
imagemode = manager.envVars['IMAGEMODE']
failfile = "." + product + "_" + variant + "_" + carrier + "_" + imagemode + ".fail"
html = getBuildFailLogHtml(failfile)
summary = manager.createSummary("notepad.png")
summary.appendText(html, false)

