import java.util.regex.Matcher
import java.util.regex.Pattern

def getChangeLogHtml(filename){
    Pattern pattern = Pattern.compile("<body>(.*)</body>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL);

    if(manager.build.workspace.isRemote()){ // 这里是workspace在远端的情况
        channel = manager.build.workspace.channel;
        fp = new hudson.FilePath(channel, manager.build.workspace.toString() + "/" + filename)
        if(fp != null){
            if (fp.exists()){
                html = fp.readToString(); //reading from file 这里是把,build的change log 显示出来。

                Matcher matcher = pattern.matcher(html);
                while(matcher.find()){
                    body = matcher.group(1)
                }
                return "<h1>Change Log</h1>" + body
            }else{
                return "<p>" + filename + " not exists</p>"
            }
        } else{
            return "<p>" + filename + " not exists</p>"
        }
    } else {
        //这里是把,build的change log 显示出来。
        htmlfile = new File(manager.build.workspace.toString(), filename)
        if(htmlfile.exists()){
            Matcher matcher = pattern.matcher(htmlfile .text);
            while(matcher.find()){
                body = matcher.group(1)
            }
            return "<h1>Change Log</h1>" + body
        } else {
            return  "<p>" + filename + " not exists</p>"
        }
    }

}

def getDowloadUrl(){
    def map = [:]
    pattern = ~/.*jobname:(.*)url:(.*)/
    manager.build.logFile.eachLine { line ->
        matcher = pattern.matcher(line)
        if(matcher.matches()) {
            jobname = matcher.group(1)
            tempurl = matcher.group(2)
            map[jobname] = tempurl
        }
    }
    def html = "<h1>Download stream url 下游项目的链接</h1>"
    if(map.size() > 0) {
        map.each {
            html += "<br/> <b>$it.key</b><a href=\"$it.value\">$it.value</a><br/>"
        }
    }
    return html
}

if (manager.build.getResult().toString() == "SUCCESS"){
    // 构建成功的
    html = getDowloadUrl()
    summary = manager.createSummary("document.png")
    summary.appendText(html , false)

    type = manager.envVars['BUILD_TYPE']
    if(type == "TriggerDailyBuild" || type == "TriggerTimelyBuild"){
        html = getChangeLogHtml("changelog.build.html")
        summary = manager.createSummary("document.png")
        summary.appendText(html, false)
    }
    if(type == "TriggerOndemandBuild"){
        html = getChangeLogHtml("changelog.ondemand.html")
        summary = manager.createSummary("document.png")
        summary.appendText(html, false)

        html = getChangeLogHtml("changelog.build.html")
        summary = manager.createSummary("document.png")
        summary.appendText(html, false)
    }
    if(type == "TriggerGerritBuild"){
        html = getChangeLogHtml("changelog.ondemand.html")
        summary = manager.createSummary("document.png")
        summary.appendText(html, false)
    }

    if(type == "TriggerDailyBuild" ){
        build_id = manager.envVars['AAIS_ANDROID_BUILD_ID']
        if (build_id != "" && build_id != null){
            manager.addShortText("release")
            manager.addBadge("/images/16x16/yellow.gif", "icon from Jenkins")
        }
    }
} else {
    if(manager.logContains(".*no change no build.*")){
        manager.addShortText("no change no build", "red", "white", "1px", "white")
    }
}





