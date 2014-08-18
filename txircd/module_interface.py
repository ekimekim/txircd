from zope.interface import Attribute, Interface, implements
from txircd.utils import splitMessage

class IModuleData(Interface):
    name = Attribute("The module name.")
    requiredOnAllServers = Attribute("""
        Whether the module must be loaded on all servers in order to function properly.
        This is determined automatically in many cases, such as if the module provides modes
        or server commands.  If the IRCd determines that the module doesn't need to be loaded
        on all servers but it actually does, it will check this value.
        """)
    core = Attribute("Always false for custom modules.")
    
    def hookIRCd(ircd):
        """
        Provides the IRCd instance to save and use later.
        """
    
    def channelModes():
        """
        Returns the channel modes provided by the module.  The modes are returned as
        a list of tuples:
        [ (letter, type, object, rank, symbol) ]
        The letter is the letter of the mode.
        The type is a mode type, one of ModeType.List, ModeType.ParamOnUnset, ModeType.Param,
            ModeType.NoParam, and ModeType.Status.  (ModeType is in txircd.utils.)
        The object is an instance of the class that implements the mode.
        The rank is a numeric value only relevant for ModeType.Status modes.  Higher numbers
            indicate a higher channel rank.  The default chanop mode +o has a rank of 100, and
            the default voice mode +v has a rank of 10.
        The symbol is a single character, also only relevant for ModeType.Status modes.
        """
    
    def userModes():
        """
        Returns the user modes provided by the module.  The modes are returned as a list
        of tuples:
        [ (letter, type, object) ]
        The letter is the letter of the mode.
        The type is a mode type, one of ModeType.List, ModeType.ParamOnUnset, ModeType.Param,
            and ModeType.NoParam.  (ModeType is in txircd.utils.)
        The object is an instance of the class that implements the mode.
        """
    
    def actions():
        """
        Returns the actions this module handles.  The actions are returned as a list
        of tuples:
        [ (type, priority, function) ]
        The name is the name of the action as a string.
        The priority is a number.  Higher priorities will be executed first.  This may
        not be important for all actions; if you think priority doesn't matter for the
        action you're implementing, a typical "normal priority" is 10.
        The function is a reference to the function which handles the action in your module.
        """

    def services():
        """
        Returns the services this module provides.
        """

    def userCommands():
        """
        Returns commands supported by this module.  Commands are returned as a list of tuples:
        [ (name, priority, object) ]
        The name is the command.
        The priority is a number indicating where in priority order a module should handle
            the command.  It is recommended that the default implementation of a commmand have
            a priority of 1; other modules may then extend the default implementation by
            providing higher numbers.
        The object is an instance of the class that implements the command.
        """
    
    def serverCommands():
        """
        Returns server commands supported by this module.  Server commands are returned as
        a list of tuples:
        [ (name, priority, object) ]
        The name is the command.
        The priority is a number indicating where in priority order a module should handle
            the command.  It is recommended that the default implementation of a command have
            a priority of 1; other modules may then extend the default implementation by
            providing higher numbers.
        The object is an instance of the class that implements the command.
        """
    
    def load():
        """
        Called when the module is successfully loaded.
        """
    
    def rehash():
        """
        Called when the server is rehashed.  Indicates that new configuration values are loaded
        and that any changes should be acted upon.
        """
    
    def unload():
        """
        Called when the module is being unloaded for any reason, including to be reloaded.
        Should do basic cleanup.
        """
    
    def fullUnload():
        """
        Called when the module is being fully unloaded with no intention to reload.
        Should do full cleanup of any data this module uses, including unsetting of modes
        handled by this module.
        """

class ModuleData(object):
    requiredOnAllServers = False
    core = False
    
    def hookIRCd(self, ircd):
        pass
    
    def channelModes(self):
        return []
    
    def userModes(self):
        return []
    
    def actions(self):
        return []

    def services(self):
        return []

    def userCommands(self):
        return []
    
    def serverCommands(self):
        return []
    
    def load(self):
        pass
    
    def rehash(self):
        pass
    
    def unload(self):
        pass
    
    def fullUnload(self):
        pass


class ICommand(Interface):
    resetsIdleTime = Attribute("Whether this command resets the user's idle time.")
    forRegisteredUsers = Attribute("""
        Whether this command should be triggered for users only after they've registered.
        True to only activate for registered users.
        False to only activate for unregistered users.
        None to be agnostic about the whole thing.
        This flag is ignored for servers.
        """)
    
    def parseParams(source, params, prefix, tags):
        """
        Parses the parameters to the command.  Returns a dictionary of data, or None if
        the parameters cannot be properly parsed.
        """
    
    def affectedUsers(source, data):
        """
        Determines which users are affected given parsed command data to determine which
        action functions to call.
        Returns a list of users (or an empty list for no users).
        The user who issued the command is automatically added to this list if that user
        is not already in it.
        """
    
    def affectedChannels(source, data):
        """
        Determines which channels are affected given parsed command data to determine
        which action functions to call.
        Returns a list of channels (or an empty list for no channels).
        """
    
    def execute(source, data):
        """
        Performs the command action.
        Returns True if successfully handled; otherwise defers to the next handler in the chain
        """

class Command(object):
    resetsIdleTime = True
    forRegisteredUsers = True
    
    def parseParams(self, source, params, prefix, tags):
        return None
    
    def affectedUsers(self, source, data):
        return []
    
    def affectedChannels(self, source, data):
        return []
    
    def execute(self, source, data):
        pass


class IMode(Interface):
    affectedActions = Attribute("A list of action types for which to trigger the mode handler.")
    
    def checkSet(target, param):
        """
        Checks whether the mode can be set.  Returns a list of parameters, or None if the mode cannot be set.
        For non-list modes, return a list of one item.
        For non-parameter modes, return an empty list.
        """
    
    def checkUnset(target, param):
        """
        Checks whether the mode can be unset.  Returns a list of parameters, or None if the mode cannot be unset.
        For non-list modes, return a list of one item.
        For non-parameter modes, return an empty list.
        """
    
    def apply(actionType, target, param, *params, **kw):
        """
        Affect the mode should have.
        This is similar binding the appropriate actions directly, except that the IRCd will automatically determine
        whether the mode function should fire instead of making you figure that out.  This allows features like
        extbans to just work consistently across the board without every module having to try to implement them.
        A parameter is provided for the particular target to which the mode action is being applied.
        """
    
    def showParam(user, target):
        """
        Affects parameter modes only (ModeType.ParamOnUnset or ModeType.Param).  Returns how to display the mode
        parameter to users.
        """
    
    def showListParams(user, target):
        """
        Affects list modes only (ModeType.List).  Sends the parameter list to the user.  Returns None.
        """

class Mode(object):
    affectedActions = []
    
    def checkSet(self, target, param):
        return [param]
    
    def checkUnset(self, target, param):
        return [param]
    
    def apply(self, actionType, target, param, *params, **kw):
        pass
    
    def showParam(self, user, target):
        return None
    
    def showListParams(self, user, target):
        pass


class IService(Interface):
    servname = Attribute("A string that is the nick of the service. Defaults to the class name.")
    help = Attribute("A string describing the purpose of the service and how to use it.")
    user_cmd_aliases = Attribute("""An optional dict mapping user commands to (priority, service_command).
        For example, {"PASS": (20, "LOGIN")} will alias the irc command PASS to the service command
        "LOGIN" with the same params.
        If you give None instead of a service command, it will instead expect the command as an arg,
        eg. {"MYSERV": (20, None)} wil alias the command MYSERV to send a message to your service.
        """)
    def commands():
        """Should return a dict mapping commands to tuple (handler, admin_only, summary, help).
        Commands MUST be upper case.
        handler: The function to be called in response to this command.
        admin_only: Flag. When true, only admins for this service can use this command.
        summary: A one-line summary for what the command does.
        help: Full-length usage help for the command.
        """


class Service(object):

    @property
    def servname(self):
        return type(self).__name__

    help = ""
    user_cmd_aliases = {}

    def commands(self):
        return {}

    def handleMessage(self, user, message):
        params = message.split()
        if not params:
            return
        command = params.pop(0)
        self.handleCommand(user, command, params)

    def generateUserCommands(self):
        """To make this work, call it from your module's userCommands."""
        class AliasCommand(Command):
            implements(ICommand)
            def __init__(self, service, service_cmd):
                self.service = service
                self.service_cmd = service_cmd
            def parseParams(self, source, params, prefix, tags):
                if self.service_cmd:
                    command = self.service_cmd
                else:
                    if not params:
                        return None
                    command, params = params[0], params[1:]
                return {'command': command, 'params': params}
            def execute(self, source, data):
                self.service.handleCommand(source, data['command'], data['params'])
        return [(user_cmd, priority, AliasCommand(self, service_cmd))
                for user_cmd, (priority, service_cmd) in self.user_cmd_aliases.items()]

    def handleCommand(self, user, command, params):
        command = command.upper()
        if command == 'HELP':
            self.handleHelp(user, params)
            return
        if command in self.commands():
            handler, admin_only, summary, long_help = self.commands()[command]
            if not admin_only or self.isAdmin(user):
                handler(user, params)
                return
        user.sendMessage('NOTICE', self.name,
                         ":Unknown command \x02{}\x02. Use \x1f/msg {} HELP\x1f for help.".format(command, self.name))

    def handleHelp(self, user, params):
        if not params:
            for chunk in splitMessage(self.help, 80):
                user.sendMessage('NOTICE', self.name, ":{}".format(chunk))
            for command, (handler, admin_only, summary, long_help) in sorted(self.commands().items()):
                if admin_only and not self.isAdmin(user):
                    continue
                user.sendMessage('NOTICE', self.name, ":\x02{}\x02: {}".format(command, summary))
            user.sendMessage('NOTICE', self.name, ":*** End of help")
            return
        for command in params:
            command = command.upper()
            if command in self.commands():
                handler, admin_only, summary, long_help = self.commands()[command]
                if not admin_only or self.isAdmin(user):
                    user.sendMessage('NOTICE', self.name, ":*** Help for \x02{}\x02:".format(command))
                    for chunk in splitMessage(long_help, 80):
                        user.sendMessage('NOTICE', self.name, ":{}".format(chunk))
                    user.sendMessage('NOTICE', self.name, ":*** End of help for \x02{}\x02".format(command))
                    continue
            user.sendMessage('NOTICE', self.name, ":No help available for \x02{}\x02".format(command))

    def isAdmin(self, user):
        return False # TODO how?