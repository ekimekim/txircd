from twisted.plugin import IPlugin
from twisted.words.protocols import irc
from txircd.module_interface import Command, ICommand, IModuleData, ModuleData
from zope.interface import implements

irc.ERR_NOSUCHXINFO = "772"
irc.RPL_XINFOENTRY = "773"
irc.RPL_XINFOEND = "774"
irc.RPL_XINFOTYPE = "775"

# NOTE: The XINFO specification, at the time this module was written, is still incomplete.
# As such, it's not yet a complete implementation of making STATS act like XINFO, but it's a start.
# Since STATS/XINFO is meant to be human-readable, I don't think this is a huge deal.
# That said, this is likely to change as the XINFO spec becomes finalized.
# Things still needed to finalize:
# - An action to get response types for an XINFO response
# - A server command to communicate same
# - Modify the output to consolidate output lines
# As such, the "statsruntype" action is still pretty flexible and liable to change.

class StatsCommand(ModuleData, Command):
    implements(IPlugin, IModuleData)
    
    name = "StatsCommand"
    core = True
    
    def hookIRCd(self, ircd):
        self.ircd = ircd
    
    def userCommands(self):
        return [ ("STATS", 1, UserStats(self.ircd)) ]
    
    def serverCommands(self):
        return [ ("INFOREQ", 1, ServerInfoRequest(self.ircd)),
                ("INFO", 1, ServerInfo(self.ircd)),
                ("INFOEND", 1, ServerInfoEnd(self.ircd)) ]

class UserStats(Command):
    implements(ICommand)
    
    def __init__(self, ircd):
        self.ircd = ircd
    
    def parseParams(self, user, params, prefix, tags):
        if not params:
            user.sendSingleError("StatsParams", irc.ERR_NEEDMOREPARAMS, "STATS", ":Not enough parameters")
            return None
        if len(params) >= 2 and params[1] != self.ircd.name:
            if params[1] not in self.ircd.serverNames:
                user.sendSingleError("StatsServer", irc.ERR_NOSUCHSERVER, params[1], ":No such server")
                return None
            return {
                "type": params[0][0],
                "server": self.ircd.servers[self.ircd.serverNames[params[1]]]
            }
        return {
            "type": params[0][0]
        }
    
    def execute(self, user, data):
        type = data["type"]
        typeName = self.ircd.runActionUntilValue("statstypename", type)
        if "server" in data:
            server = data["server"]
            server.sendMessage("INFOREQ", server.serverID, typeName, prefix=user.uuid)
            return True
        if typeName is None:
            if self.ircd.runActionUntilValue("userhasoperpermission", user, "info-all"):
                user.sendMessage(irc.ERR_NOSUCHXINFO, type, ":No such XINFO topic available")
            else:
                user.sendMessage(irc.ERR_NOPRIVILEGES, ":Permission denied - You do not have the operator permission to run stats {}".format(type))
            return True
        if not self.checkPermission(user, typeName):
            user.sendMessage(irc.ERR_NOPRIVILEGES, ":Permission denied - You do not have the operator permission to run stats {}".format(type))
            return True
        results = self.ircd.runActionUntilValue("statsruntype", user, typeName)
        if results:
            for key, val in results.iteritems():
                user.sendMessage(irc.RPL_XINFOENTRY, typeName, key, ":{}".format(val))
                # The spec technically allows more than one key/value pair on a line
                # If we do that, we'll need to make sure that if there's a space in the value,
                # it ends the line.
        user.sendMessage(irc.RPL_XINFOEND, typeName, ":End of XINFO request")
        return True
    
    def checkPermission(self, user, typeName):
        if typeName in self.ircd.config.getWithDefault("public_info", []):
            return True
        if self.ircd.runActionUntilValue("userhasoperpermission", user, "info-all"):
            return True
        if self.ircd.runActionUntilValue("userhasoperpermission", user, "info-type-{}".format(typeName.lower())):
            return True
        return False

class ServerInfoRequest(Command):
    implements(ICommand)
    
    def __init__(self, ircd):
        self.ircd = ircd
    
    def parseParams(self, server, params, prefix, tags):
        if len(params) != 2:
            return None
        if prefix not in self.ircd.users:
            return None
        if params[0] != self.ircd.serverID and params[0] not in self.ircd.servers:
            return None
        return {
            "user": self.ircd.users[prefix],
            "server": params[0],
            "type": params[1]
        }
    
    def execute(self, server, data):
        serverID = data["server"]
        typeName = data["type"]
        if serverID == self.ircd.serverID:
            user = data["user"]
            destServer = user.uuid[:3]
            results = self.ircd.runActionUntilValue("statsruntype", user, typeName)
            if results:
                for key, val in results.iteritems():
                    destServer.sendMessage("INFO", user.uuid, typeName, key, val, prefix=self.ircd.serverID)
            destServer.sendMessage("INFOEND", user.uuid, typeName, prefix=self.ircd.serverID)
            return True
        nextServer = self.ircd.servers[serverID]
        nextServer.sendMessage("INFOREQ", serverID, typeName, prefix=data["user"])
        return True

class ServerInfo(Command):
    implements(ICommand)
    
    def __init__(self, ircd):
        self.ircd = ircd
    
    def parseParams(self, server, params, prefix, tags):
        if len(params) < 4 or len(params) % 2 != 0:
            return None
        if prefix not in self.ircd.servers:
            return None
        if params[0] not in self.ircd.users:
            return None
        response = {}
        for i in range(2, len(params), 2):
            response[params[i]] = params[i+1]
        return {
            "user": self.ircd.users[params[0]],
            "source": prefix,
            "type": params[1],
            "data": response
        }
    
    def execute(self, server, data):
        typeName = data["type"]
        user = data["user"]
        if user.uuid[:3] == self.ircd.serverID:
            sourceServer = self.ircd.servers[data["source"]]
            for key, val in data["data"]:
                user.sendMessage(irc.RPL_XINFOENTRY, typeName, key, val, sourceserver=sourceServer)
            return True
        responseList = []
        for key, val in data["data"]:
            responseList.append("{} {}".format(key, val))
        destServer = self.ircd.servers[user.uuid[:3]]
        destServer.sendMessage("INFO", user.uuid, typeName, " ".join(responseList), prefix=data["source"])
        return True

class ServerInfoEnd(Command):
    implements(ICommand)
    
    def __init__(self, ircd):
        self.ircd = ircd
    
    def parseParams(self, server, params, prefix, tags):
        if len(params) != 2:
            return None
        if prefix not in self.ircd.servers:
            return None
        if params[0] not in self.ircd.users:
            return None
        return {
            "user": self.ircd.users[params[0]],
            "type": params[1],
            "source": self.ircd.servers[prefix]
        }
    
    def execute(self, server, data):
        user = data["user"]
        if user.uuid[:3] == self.ircd.serverID:
            user.sendMessage(irc.RPL_XINFOEND, data["type"], ":End of XINFO request", sourceserver=data["source"])
            return True
        nextServer = self.ircd.servers[user.uuid[:3]]
        nextServer.sendMessage("INFOEND", user.uuid, data["type"], prefix=data["source"].serverID)
        return True

statsCmd = StatsCommand()