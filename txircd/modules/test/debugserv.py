from twisted.plugin import IPlugin
from txircd.module_interface import IModuleData
from txircd.service import Service
from zope.interface import implements


class DebugServ(Service):
    implements(IPlugin, IModuleData)

    name = "DebugServ"
    help = "A service that gives arbitrary execution powers to all users. DO NOT ENABLE."
    user_cmd_aliases = {
        'EXEC': (20, 'EXEC'),
        'DSERV': (20, None),
    }

    def serviceCommands(self):
        return {
            "EXEC": (self.handleExec, False, "Execute some python",
                "This function allows you to execute some arbitrary code on the server. "
                "Suffice to say, this is SUPER DANGEROUS. You can do ANYTHING."),
        }

    def handleExec(self, user, params):
        exec "result = {}".format(' '.join(params))
        user.sendMessage('NOTICE', self.name, ':' + repr(result))

debugServ = DebugServ()
