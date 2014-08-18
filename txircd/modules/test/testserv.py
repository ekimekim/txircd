from twisted.plugin import IPlugin
from txircd.module_interface import IModuleData, ModuleData, IService, Service
from zope.interface import implements


class TestServ(ModuleData, Service):
    implements(IPlugin, IModuleData, IService)

    name = "TestServ"
    help = "A test service."
    user_cmd_aliases = {
        'TEST': (20, 'TEST'),
        'TSERV': (20, None),
    }

    def userCommands(self):
        return self.generateUserCommands()

    def commands(self):
        return {
            "TEST": (self.handleTest, False, "a test command",
                "This command does nothing but send a notice echoing the input params, "
                "and is intended for testing the functionality of a very basic service."),
        }

    def services(self):
        return [self]

    def handleTest(self, user, params):
        user.sendMessage('NOTICE', self.name, ':' + ' '.join(params))

testServ = TestServ()
