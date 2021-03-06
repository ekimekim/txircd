from twisted.plugin import IPlugin
from txircd.module_interface import Command, ICommand, IModuleData, ModuleData
from zope.interface import implements

class CapabCommand(ModuleData, Command):
    implements(IPlugin, IModuleData, ICommand)
    
    name = "CapabCommand"
    core = True
    
    def hookIRCd(self, ircd):
        self.ircd = ircd
    
    def serverCommands(self):
        return [ ("CAPAB", 1, self) ]
    
    def parseParams(self, server, params, prefix, tags):
        if not params:
            return None
        subcmd = params[0].upper()
        if subcmd == "START":
            if len(params) != 2:
                return None
            return {
                "subcmd": subcmd,
                "version": params[1]
            }
        if subcmd == "MODULES":
            if len(params) != 2:
                return None
            return {
                "subcmd": subcmd,
                "modules": params[1].split(" ")
            }
        if subcmd == "END":
            if len(params) != 1:
                return None
            return {
                "subcmd": subcmd
            }
        return None
    
    def execute(self, server, data):
        subcmd = data["subcmd"]
        if subcmd == "START":
            version = data["version"]
            if version != "300":
                server.disconnect("Incompatible protocol version {}".format(version))
                return True
            return True
        if subcmd == "MODULES":
            moduleList = data["modules"]
            if self.ircd.commonModules.difference(moduleList):
                server.disconnect("Link Error: Not all required modules are loaded")
                return True
            return True
        if subcmd == "END":
            if server.receivedConnection:
                server.sendMessage("CAPAB", "START", "300", prefix=self.ircd.serverID)
                server.sendMessage("CAPAB", "MODULES", ":{}".format(" ".join(self.ircd.loadedModules.keys())), prefix=self.ircd.serverID)
                server.sendMessage("CAPAB", "END", prefix=self.ircd.serverID)
            self.ircd.runActionStandard("startburst", server)
            return True
        return None

capabCmd = CapabCommand()