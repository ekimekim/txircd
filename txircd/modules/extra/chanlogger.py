from twisted.plugin import IPlugin
from txircd.module_interface import IModuleData, ModuleData
from zope.interface import implements


class ChanLogger(ModuleData):
    implements(IPlugin, IModuleData)

    name = "ChanLogger"

    def hookIRCd(self, ircd):
        self.ircd = ircd

    def actions(self):
        return [
            # high priority as we need to catch the message before targets get removed (and it stops processing)
            ("sendchannelmessage-PRIVMSG", 100, self.handlePrivmsg),
            ("sendchannelmessage-NOTICE", 100, self.handleNotice),
            ("joinmessage", 100, self.handleJoin),
            ("partmessage", 100, self.handlePart),
            ("modechanges-channel", 10, self.handleModeChange),
            ("channeldestroy", 10, self.cleanupChannel),
        ]

    def handlePrivmsg(self, users, servers, channel, *params, **kw):
        handleMessage(channel, "PRIVMSG", *params, **kw)

    def handleNotice(self, users, servers, channel, *params, **kw):
        handleMessage(channel, "NOTICE", *params, **kw)

    def handleMessage(self, channel, command, *params, **kw):
        # TODO

    def handleJoin(self, users, channel, user):
        # TODO

    def handlePart(self, users, channel, user):
        # TODO

    def handleModeChange(self, channel, source, sourceName, modes):
        # source is user or server - use sourceName
        # changing is list of (bool adding/removing, mode letter, mode param (may be None))
        # use utils.formatModes
        # TODO

    def cleanupChannel(self, channel):
        if "logfile" in channel.cache:
            channel.cache.pop("logfile").close()

chanLogger = ChanLogger()
