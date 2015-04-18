from buildslave.commands import base
from twisted.internet.defer import inlineCallbacks
import treq

class Command(base.Command):
    header = "nexus upload"
    requiredArgs = ['host','cred','repo','artifact','file']

    @inlineCallbacks
    def start(self):
        host = "http://%(host)s"%(self.args)
        res = "/nexus/service/local/artifact/maven/content"
        artifact = self.args["artifact"]
        fileName = self.args["file"]
        fileName = os.path.join(self.builder.basedir,fileName)
        g,a,v,e = artifact.split(":")
        params = {
          'r': self.args["repo"],
          'g': g,
          'a': a,
          'v': v,
          'e': e,
          'p': e}
        print "posting",host+res, params, fileName,self.args["cred"]
        res = yield treq.post(
          host+res,
          data = params,
          files = {'file':open(fileName,"rb")},
          auth=self.args["cred"])
        print "res",res
        output = yield treq.content(res)
        print "info", res.code, output
        self.sendStatus({'info':(res.code,output)})
        self.sendStatus({'rc': 0 if res.code == 201 else 1})

def commandFactory():
    return Command
