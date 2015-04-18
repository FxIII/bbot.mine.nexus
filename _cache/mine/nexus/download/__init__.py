from buildslave.commands import base
from twisted.internet.defer import inlineCallbacks
import treq
import os,errno
import re
from distutils.dir_util import mkpath
import tempfile
from twisted.internet import defer, reactor
import zipfile
from pprint import pprint
artre = re.compile("([^:]+):([^:]+):([^:]+):([^:\|\>]+)(?:\|([^>]*))?(?:>(.*))?")


class Command(base.Command):
    header = "nexus download"
    requiredArgs = ['host','cred','repo','artifacts',]

    def copy(self,artifact,d,done,info):
        g,a,v,e,f,dest = artre.findall(artifact)[0]
        if dest == "":
            dest= "%s-%s.%s"%(a,v,e)
        fileName = os.path.join(self.builder.basedir,dest)
        dirName = os.path.abspath(os.path.dirname(fileName))
        #result = mkpath(dirName,verbose=True)
        try:
          result = os.makedirs(dirName)
        except Exception,e:
            pass
        file = open(fileName,"wb")
        reading = treq.collect(d, file.write)
        reading.addBoth(lambda _: file.close())
        reading.addCallback(lambda _:done.callback(info))
        reading.addErrback(done.errback)
        
    def filter_unzip(self,artifact,url,done,info):
        g,a,v,e,f,dest = artre.findall(artifact)[0]
        dest = os.path.join(self.builder.basedir,dest)
        tmp = tempfile.SpooledTemporaryFile(8*2048) # 16KiB
        def handleUnzipping():
            try:
                mkpath(os.path.abspath(dest))
                zip = zipfile.ZipFile(tmp)
                result = zip.extractall(dest)
                done.callback(info)
            except Exception,e:
                done.errback(e)
        reading = treq.collect(url, tmp.write)
        reading.addCallback(lambda _:reactor.callInThread(handleUnzipping))
        reading.addErrback(done.errback)

    @inlineCallbacks
    def handleArtifact(self,artifact,done):
        try:
           info = {}
           g,a,v,e,f,dest = artre.findall(artifact)[0]
           args = "?r=%s&g=%s&a=%s&v=%s&e=%s"%(self.args["repo"],g,a,v,e)
           url = self.host+self.res+args
           res = yield treq.get(url,auth=self.args["cred"])
           if res.code != 200:
              done.errback(Exception(res.code))
           else:
              info["version"]=res.previousResponse.headers.getRawHeaders("location")[0].split("/")[-2]
              filter = getattr(self,"filter_"+f,self.copy)
              filter(artifact,res,done,info)
        except Exception,e:
           done.errback(e)
        
     
    @inlineCallbacks
    def start(self):
        self.host = "http://%(host)s"%(self.args)
        self.res = "/nexus/service/local/artifact/maven/redirect"
        ds = []
        for artifact in self.args["artifacts"]:
            done = defer.Deferred()
            reactor.callLater(0,self.handleArtifact,artifact,done)
            ds.append(done)
        dl = defer.DeferredList(ds)
        try:
          res = yield dl
        except Exception,e:
          print "got exception on DL",e
          
        allOk = True
        for artifact,(success,result) in zip(self.args["artifacts"],res):
            self.sendStatus({'info':(artifact,success,result)})
            if not success:
              allOk=False
        pprint(("results:",zip(res,self.args["artifacts"])))
        self.sendStatus({'rc': 0 if allOk else 1})

def commandFactory():
    return Command
