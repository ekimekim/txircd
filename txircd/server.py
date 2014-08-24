from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.task import LoopingCall
from twisted.python import log
from twisted.words.protocols.irc import IRC
import logging

class IRCServer(IRC):
    def __init__(self, ircd, ip, received):
        self.ircd = ircd
        self.serverID = None
        self.name = None
        self.description = None
        self.ip = ip
        self.remoteServers = {}
        self.nextClosest = self.ircd.serverID
        self.cache = {}
        self.bursted = None
        self.disconnectedDeferred = Deferred()
        self.receivedConnection = received
        self._pinger = LoopingCall(self._ping)
        self._registrationTimeoutTimer = reactor.callLater(self.ircd.config.getWithDefault("server_registration_timeout", 10), self._timeoutRegistration)
    
    def handleCommand(self, command, prefix, params):
        if command not in self.ircd.serverCommands:
            self.disconnect("Unknown command {}".format(command)) # If we receive a command we don't recognize, abort immediately to avoid a desync
            return
        handlers = self.ircd.serverCommands[command]
        if self.bursted is False and handlers[0].forRegistered:
            if "burst_queue" not in self.cache:
                self.cache["burst_queue"] = []
            self.cache["burst_queue"].append((command, prefix, params))
            return
        data = None
        for handler in handlers:
            data = handler[0].parseParams(self, params, prefix, {})
            if data is not None:
                break
        if data is None:
            self.disconnect("Failed to parse command {} from {} with parameters '{}'".format(command, prefix, " ".join(params))) # If we receive a command we can't parse, also abort immediately
            return
        for handler in handlers:
            if handler[0].execute(self, data):
                break
        else:
            self.disconnect("Couldn't process command {} from {} with parameters '{}'".format(command, prefix, " ".join(params))) # Also abort connection if we can't process a command
            return
    
    def endBurst(self):
        self.bursted = True
        for command, prefix, params in self.cache["burst_queue"]:
            self.handleCommand(command, prefix, params)
        del self.cache["burst_queue"]
    
    def connectionLost(self, reason):
        if self.serverID in self.ircd.servers:
            self.disconnect("Connection reset")
        self.disconnectedDeferred.callback(None)
    
    def disconnect(self, reason):
        if self.bursted:
            self.ircd.runActionStandard("serverquit", self, reason)
            del self.ircd.servers[self.serverID]
            del self.ircd.serverNames[self.name]
            netsplitQuitMsg = "{} {}".format(self.ircd.servers[self.nextClosest].name if self.nextClosest in self.ircd.servers else self.ircd.name, self.name)
            allUsers = self.ircd.users.values()
            for user in allUsers:
                if user.uuid[:3] == self.serverID or user.uuid[:3] in self.remoteServers:
                    user.disconnect(netsplitQuitMsg)
        self._endConnection()
    
    def _endConnection(self):
        self.transport.loseConnection()
    
    def _timeoutRegistration(self):
        if self.serverID and self.name:
            self._pinger.start(self.ircd.config.getWithDefault("server_ping_frequency", 60))
            return
        log.msg("Disconnecting unregistered server", logLevel=logging.INFO)
        self.disconnect("Registration timeout")
    
    def _ping(self):
        self.ircd.runActionStandard("pingserver", self)
    
    def register(self):
        if not self.serverID:
            return
        if not self.name:
            return
        self.ircd.servers[self.serverID] = self
        self.ircd.serverNames[self.name] = self.serverID
        self.ircd.runActionStandard("serverconnect", self)

class RemoteServer(IRCServer):
    def __init__(self, ircd, ip):
        IRCServer.__init__(self, ircd, ip, True)
        self._registrationTimeoutTimer.cancel()
    
    def sendMessage(self, command, *params, **kw):
        target = self
        while target.nextClosest != self.ircd.serverID:
            target = self.ircd.servers[target.nextClosest]
        target.sendMessage(command, *params, **kw)
    
    def _endConnection(self):
        pass