from twisted.plugin import IPlugin
from twisted.words.protocols import irc
from txircd.module_interface import Command, ICommand, IModuleData, ModuleData
from txircd.utils import durationToSeconds, ircLower, now, timestamp
from zope.interface import implements
from datetime import datetime

class WhowasCommand(ModuleData, Command):
    implements(IPlugin, IModuleData, ICommand)
    
    name = "WhowasCommand"
    core = True
    
    def hookIRCd(self, ircd):
        self.ircd = ircd
    
    def actions(self):
        return [ ("quit", 10, self.addUserToWhowas),
                ("remotequit", 10, self.addUserToWhowas),
                ("localquit", 10, self.addUserToWhowas) ]
    
    def userCommands(self):
        return [ ("WHOWAS", 1, self) ]
    
    def load(self):
        if "whowas" not in self.ircd.storage:
            self.ircd.storage["whowas"] = {}
    
    def removeOldEntries(self, whowasEntries):
        expireDuration = durationToSeconds(self.ircd.config.getWithDefault("whowas_duration", "1d"))
        maxCount = self.ircd.config.getWithDefault("whowas_max_entries", 10)
        while whowasEntries and len(whowasEntries) > maxCount:
            whowasEntries.pop(0)
        expireTime = timestamp(now()) - expireDuration
        while whowasEntries and whowasEntries[0]["when"] < expireTime:
            whowasEntries.pop(0)
        return whowasEntries
    
    def addUserToWhowas(self, user, reason):
        if user.nick is None:
            # user never registered a nick, so no whowas entry to add
            return
        lowerNick = ircLower(user.nick)
        allWhowas = self.ircd.storage["whowas"]
        if lowerNick in allWhowas:
            whowasEntries = allWhowas[lowerNick]
        else:
            whowasEntries = []
        serverName = self.ircd.name
        if user.uuid[:3] != self.ircd.serverID:
            serverName = self.ircd.servers[user.uuid[:3]].name
        whowasEntries.append({
            "nick": user.nick,
            "ident": user.ident,
            "host": user.host,
            "gecos": user.gecos,
            "server": serverName,
            "when": timestamp(now())
        })
        whowasEntries = self.removeOldEntries(whowasEntries)
        if whowasEntries:
            allWhowas[lowerNick] = whowasEntries
        elif lowerNick in allWhowas:
            del allWhowas[lowerNick]
    
    def parseParams(self, user, params, prefix, tags):
        if not params:
            user.sendSingleError("WhowasCmd", irc.ERR_NEEDMOREPARAMS, "WHOWAS", ":Not enough parameters")
            return None
        lowerParam = ircLower(params[0])
        if lowerParam not in self.ircd.storage["whowas"]:
            print("Nick not found in whowas.")
            user.sendSingleError("WhowasNick", irc.ERR_WASNOSUCHNICK, params[0], ":There was no such nickname")
            return None
        return {
            "nick": lowerParam,
            "param": params[0]
        }
    
    def execute(self, user, data):
        nick = data["nick"]
        allWhowas = self.ircd.storage["whowas"]
        whowasEntries = allWhowas[nick]
        print("1. {}".format(whowasEntries))
        whowasEntries = self.removeOldEntries(whowasEntries)
        print("2. {}".format(whowasEntries))
        if not whowasEntries:
            del allWhowas[nick]
            self.ircd.storage["whowas"] = allWhowas
            user.sendMessage(irc.ERR_WASNOSUCHNICK, data["param"], ":There was no such nickname")
            return True
        allWhowas[nick] = whowasEntries # Save back to the list excluding the removed entries
        self.ircd.storage["whowas"] = allWhowas
        for entry in whowasEntries:
            entryNick = entry["nick"]
            user.sendMessage(irc.RPL_WHOWASUSER, entryNick, entry["ident"], entry["host"], "*", ":{}".format(entry["gecos"]))
            user.sendMessage(irc.RPL_WHOISSERVER, entryNick, entry["server"], ":{}".format(datetime.utcfromtimestamp(entry["when"])))
        user.sendMessage(irc.RPL_ENDOFWHOWAS, nick, ":End of WHOWAS")
        return True

whowasCmd = WhowasCommand()