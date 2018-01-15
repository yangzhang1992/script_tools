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

type = manager.envVars['BUILD_TYPE']
if(type == "DailyBuild" || type == "TimelyBuild"){
    html = getChangeLogHtml("changelog.build.html")
    summary = manager.createSummary("document.png")
    summary.appendText(html, false)
}

if(type == "OndemandBuild"){
    html = getChangeLogHtml("changelog.ondemand.html")
    summary = manager.createSummary("document.png")
    summary.appendText(html, false)

    html = getChangeLogHtml("changelog.build.html")
    summary = manager.createSummary("document.png")
    summary.appendText(html, false)
}
