from twisted.plugin import IPlugin
from twisted.words.protocols import irc
from txircd.module_interface import Command, ICommand, IModuleData, ModuleData
from zope.interface import implements

class MessageCommands(ModuleData):
    implements(IPlugin, IModuleData)
    
    name = "MessageCommands"
    core = True
    
    def hookIRCd(self, ircd):
        self.ircd = ircd
    
    def actions(self):
        return [ ("sendchannelmessage-PRIVMSG", 1, self.sendChannelPrivmsg),
                ("sendchannelmessage-NOTICE", 1, self.sendChannelNotice),
                ("sendremoteusermessage-PRIVMSG", 1, self.sendRemotePrivmsg),
                ("sendremoteusermessage-NOTICE", 1, self.sendRemoteNotice) ]
    
    def userCommands(self):
        return [ ("PRIVMSG", 1, UserPrivmsg(self)),
                ("NOTICE", 1, UserNotice(self)) ]
    
    def serverCommands(self):
        return [ ("PRIVMSG", 1, ServerPrivmsg(self)),
                ("NOTICE", 1, ServerNotice(self)) ]
    
    def sendChannelMsg(self, toUsers, toServers, command, channel, *params, **kw):
        for user in toUsers:
            user.sendMessage(command, *params, **kw)
        if "to" in kw:
            params = (kw["to"],) + params # Prepend the destination to the parameters
        if "sourceuser" in kw:
            kw["prefix"] = kw["sourceuser"].uuid
        elif "sourceserver" in kw:
            kw["prefix"] = kw["sourceserver"].serverID
        for server in toServers:
            server.sendMessage(command, *params, **kw)
        del toUsers[:]
        del toServers[:]
    
    def sendChannelPrivmsg(self, toUsers, toServers, user, *params, **kw):
        self.sendChannelMsg(toUsers, toServers, "PRIVMSG", user, *params, **kw)
    
    def sendChannelNotice(self, toUsers, toServers, user, *params, **kw):
        self.sendChannelMsg(toUsers, toServers, "NOTICE", user, *params, **kw)
    
    def sendRemoteMsg(self, command, targetUser, dest, message, **kw):
        targetUser.sendMessage(command, targetUser.uuid, message, **kw)
    
    def sendRemotePrivmsg(self, targetUser, *params, **kw):
        if len(params) != 2:
            return None
        self.sendRemoteMsg("PRIVMSG", targetUser, *params, **kw)
        return True
    
    def sendRemoteNotice(self, targetUser, *params, **kw):
        if len(params) != 2:
            return None
        self.sendRemoteMsg("NOTICE", targetUser, *params, **kw)
        return True
    
    def cmdParseParams(self, user, params, prefix, tags):
        channels = []
        users = []
        services = []
        user.startErrorBatch("MsgCmd")
        for target in params[0].split(","):
            if target in self.ircd.channels:
                channels.append(self.ircd.channels[target])
            elif target in self.ircd.services:
                services.append(self.ircd.services[target])
            elif target in self.ircd.userNicks:
                users.append(self.ircd.users[self.ircd.userNicks[target]])
            else:
                user.sendBatchedError("MsgCmd", irc.ERR_NOSUCHNICK, target, ":No such nick/channel")
        message = params[1]
        chanMessages = {target: message for target in channels}
        userMessages = {target: message for target in users}
        serviceMessages = {target: message for target in services}
        data = {}
        if channels:
            data["targetchans"] = chanMessages
        if users:
            data["targetusers"] = userMessages
        if services:
            data["targetservices"] = serviceMessages
        if data:
            return data
        return None
    
    def cmdExecute(self, command, user, data):
        sentAMessage = False
        if "targetusers" in data:
            for target, message in data["targetusers"].iteritems():
                if message:
                    target.sendMessage(command, ":{}".format(message), sourceuser=user)
                    sentAMessage = True
        if "targetchans" in data:
            for target, message in data["targetchans"].iteritems():
                if message:
                    target.sendMessage(command, ":{}".format(message), to=target.name, sourceuser=user, skipusers=[user])
                    sentAMessage = True
        if "targetservices" in data:
            for target, message in data["targetservices"].iteritems():
                if message:
                    target.handleMessage(user, message)
                    sentAMessage = True
        if not sentAMessage:
            user.sendMessage(irc.ERR_NOTEXTTOSEND, ":No text to send")
            return None
        return True
    
    def serverParseParams(self, server, params, prefix, tags):
        if len(params) != 2:
            return None
        if prefix not in self.ircd.users:
            return None
        if params[0] in self.ircd.users:
            return {
                "from": self.ircd.users[prefix],
                "touser": self.ircd.users[params[0]],
                "message": params[1]
            }
        if params[0] in self.ircd.channels:
            return {
                "from": self.ircd.users[prefix],
                "tochan": self.ircd.channels[params[0]],
                "message": params[1]
            }
        return None
    
    def serverExecute(self, command, server, data):
        if "touser" in data:
            user = data["touser"]
            if user.uuid[:3] == self.ircd.serverID:
                user.sendMessage(command, ":{}".format(data["message"]), sourceuser=data["from"])
            else:
                self.ircd.servers[user.uuid[:3]].sendMessage(command, user.uuid, ":{}".format(data["message"]), prefix=data["from"].uuid)
            return True
        if "tochan" in data:
            chan = data["tochan"]
            fromUser = data["from"]
            nearServer = self.ircd.servers[fromUser.uuid[:3]]
            while nearServer.nextClosest != self.ircd.serverID:
                nearServer = self.ircd.servers[nearServer.nextClosest]
            chan.sendMessage(command, ":{}".format(data["message"]), sourceuser=data["from"], skipservers=[nearServer])
            return True
        return None

class UserPrivmsg(Command):
    implements(ICommand)
    
    def __init__(self, module):
        self.module = module
    
    def parseParams(self, user, params, prefix, tags):
        if len(params) < 2:
            user.sendSingleError("PrivMsgCmd", irc.ERR_NEEDMOREPARAMS, "PRIVMSG", ":Not enough parameters")
            return None
        return self.module.cmdParseParams(user, params, prefix, tags)
    
    def affectedUsers(self, user, data):
        if "targetusers" in data:
            return data["targetusers"].keys()
        return []
    
    def affectedChannels(self, user, data):
        if "targetchans" in data:
            return data["targetchans"].keys()
        return []
    
    def execute(self, user, data):
        return self.module.cmdExecute("PRIVMSG", user, data)

class UserNotice(Command):
    implements(ICommand)
    
    def __init__(self, module):
        self.module = module
    
    def parseParams(self, user, params, prefix, tags):
        if len(params) < 2:
            user.sendSingleError("NoticeCmd", irc.ERR_NEEDMOREPARAMS, "NOTICE", ":Not enough parameters")
            return None
        return self.module.cmdParseParams(user, params, prefix, tags)
    
    def affectedUsers(self, user, data):
        if "targetusers" in data:
            return data["targetusers"].keys()
        return []
    
    def affectedChannels(self, user, data):
        if "targetchans" in data:
            return data["targetchans"].keys()
        return []
    
    def execute(self, user, data):
        return self.module.cmdExecute("NOTICE", user, data)

class ServerPrivmsg(Command):
    implements(ICommand)
    
    def __init__(self, module):
        self.module = module
    
    def parseParams(self, server, params, prefix, tags):
        return self.module.serverParseParams(server, params, prefix, tags)
    
    def execute(self, server, data):
        return self.module.serverExecute("PRIVMSG", server, data)

class ServerNotice(Command):
    implements(ICommand)
    
    def __init__(self, module):
        self.module = module
    
    def parseParams(self, server, params, prefix, tags):
        return self.module.serverParseParams(server, params, prefix, tags)
    
    def execute(self, server, data):
        return self.module.serverExecute("NOTICE", server, data)

msgCommands = MessageCommands()