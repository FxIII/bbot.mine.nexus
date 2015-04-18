from buildbot.process import buildstep 
from buildbot.process import remotecommand 
from buildbot.status.results import FAILURE 
from buildbot.status.results import SUCCESS
from twisted.internet.defer import inlineCallbacks
import sourcecache
reload(sourcecache)
from sourcecache import SourceCachePackage
from jinja2 import Template
import pprint
import re

dtemplate = """
<!DOCTYPE html>
<html>
  <head>
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.4/css/bootstrap.min.css">
    <meta charset="utf-8">
    <title>JS Bin</title>
  </head>
  <body class="container">
    <table class="table">
      <thead>
        <tr>
          <th></th>
          <th>artifact</th>
          <th>info</th>
        </tr>
      </thead>
      <tbody>
        {% for success,artifact,filter,dest,info in infos %}
        <tr class="{{ "success" if success else "danger"}}">
          <th scope="row">{{ "&#x2713;" if success else "&#x2717;" }}</th>
          <td>{{ artifact }}</td>
          <td><pre>{{info}}</pre></td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </body>
</html>
"""


class NexusDownload(buildstep.BuildStep):
    name = 'Nexus Download'
    pkgName = "mine.nexus.download"
    renderables = ['host','cred','repo','artifacts']
    haltOnFailure = True
    flunkOnFailure = True
   
    def __init__(self,artifacts,repo="releases",host="localhost:8081",
                 cred="admin:admin123",**k):
        buildstep.BuildStep.__init__(self,**k)
        self.artifacts = artifacts
        self.repo = repo
        self.host = host
        self.cred = tuple(cred.split(":"))

    @inlineCallbacks
    def start(self):
        pkg = SourceCachePackage(self.pkgName)
        cmd = remotecommand.RemoteCommand('wrapCache',{
            '_package':pkg,
            'host':self.host,
            'cred':self.cred,
            'repo':self.repo,
            'artifacts':self.artifacts})
        d = self.runCommand(cmd)
        d.addErrback(self.failed)
        res = yield d
        t = Template(dtemplate)
        infos = []
        for artifact,success,info in cmd.updates["info"]:
           artifact,filter,dest = re.findall("([^|>]+)(\|[^>]*)?(>.*)?",artifact)[0]
           info = pprint.pformat(info)
           infos.append([success,artifact,filter,dest,info])
            
        yield self.addHTMLLog('info',t.render(infos=infos))        
        self.commandComplete(cmd)

    def commandComplete(self, cmd):
        #self.step_status.setText(str(cmd.updates["info"]))
        for info in cmd.updates["info"]:
            self.step_status.setStatistic(info[0],str(info[2]))
        if cmd.didFail():
            self.descriptionDone = ["Download failed"]
            self.finished(FAILURE)
            return
        self.finished(SUCCESS)
utemplate = """
<!DOCTYPE html>
<html>
  <head>
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.4/css/bootstrap.min.css">
    <meta charset="utf-8">
    <title>JS Bin</title>
  </head>
  <body class="container">
    <dl>
      <dt>Code</dt>
      <dd>{{ info[0] }}</dd>
      <dt>Response</dt>
      <dd><pre>{{ info[1] }}</pre></dd>
    </dl>
  </body>
</html>
"""

class NexusUpload(buildstep.BuildStep):
    name = 'Nexus Upload'
    pkgName = "mine.nexus.upload"
    renderables = ['host','cred','repo','artifact']
    haltOnFailure = True
    flunkOnFailure = True
    
    def __init__(self,file,artifact,repo="releases",host="localhost:8081",
                 cred="admin:admin123",**k):
        buildstep.BuildStep.__init__(self,**k)
        self.artifact = artifact
        self.repo = repo
        self.host = host
        self.cred = tuple(cred.split(":"))
        self.file = file
    
    @inlineCallbacks
    def start(self):
        pkg = SourceCachePackage(self.pkgName)
        cmd = remotecommand.RemoteCommand('wrapCache',{
            '_package':pkg,
            'host':self.host,
            'cred':self.cred,
            'repo':self.repo,
            'artifact':self.artifact,
            'file':self.file})
        d = self.runCommand(cmd)
        d.addErrback(self.failed)
        res = yield d
        t = Template(utemplate)
        yield self.addHTMLLog('info',t.render(info=cmd.updates["info"][0]))        
        self.commandComplete(cmd)
    
    def commandComplete(self, cmd):
        if cmd.didFail():
            self.descriptionDone = ["Upload failed"]
            self.finished(FAILURE)
            return
        self.finished(SUCCESS)
