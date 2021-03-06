from twisted.plugin import IPlugin
from twisted.words.protocols import irc
from txircd.module_interface import Command, ICommand, IModuleData, ModuleData
from zope.interface import implements

class ConnectCommand(ModuleData, Command):
    implements(IPlugin, IModuleData, ICommand)
    
    name = "ConnectCommand"
    core = True
    
    def hookIRCd(self, ircd):
        self.ircd = ircd
    
    def actions(self):
        return [ ("commandpermission-CONNECT", 1, self.canConnect) ]
    
    def userCommands(self):
        return [ ("CONNECT", 1, self) ]
    
    def canConnect(self, user, command, data):
        if not self.ircd.runActionUntilValue("userhasoperpermission", "command-connect"):
            user.sendMessage(irc.ERR_NOPRIVILEGES, ":Permission denied - You do not have the correct operator privileges")
            return False
        return None
    
    def parseParams(self, user, params, prefix, tags):
        if not params:
            user.sendSingleError("ConnectParams", irc.ERR_NEEDMOREPARAMS, "CONNECT", ":Not enough parameters")
            return None
        return {
            "server": params[0]
        }
    
    def execute(self, user, data):
        serverName = data["server"]
        if serverName in self.ircd.serverNames:
            user.sendMessage("NOTICE", ":*** Server {} is already on the network".format(serverName))
        elif self.ircd.connectServer(serverName):
            user.sendMessage("NOTICE", ":*** Connecting to {}".format(serverName))
        else:
            user.sendMessage("NOTICE", ":*** Failed to connect to {}".format(serverName))
        return True

connectCmd = ConnectCommand()