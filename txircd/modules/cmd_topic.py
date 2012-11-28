from twisted.words.protocol import irc
from txircd.modbase import Command
from txircd.utils import epoch, now

class TopicCommand(Command):
	def onUse(self, user, data):
		cdata = self.ircd.channels[data["targetchan"]]
		if "topic" not in data:
			if cdata.topic:
				user.sendMessage(irc.RPL_TOPIC, cdata.name, ":{}".format(cdata.topic))
				user.sendMessage(irc.RPL_TOPICWHOTIME, cdata.name, cdata.topicSetter, str(epoch(cdata.topicTime)))
			else:
				user.sendMessage(irc.RPL_NOTOPIC, cdata.name, "No topic is set")
		else:
			cdata.topic = data["topic"]
			cdata.topicSetter = user.nickname
			cdata.topicTime = now()
			for u in cdata.users.itervalues():
				u.sendMessage("TOPIC", ":{}".format(cdata.topic), to=cdata.name, prefix=user.prefix())
	
	def processParams(self, user, params):
		if not params:
			user.sendMessage(irc.ERR_NEEDMOREPARAMS, "TOPIC", ":Not enough parameters")
			return {}
		if params[0] not in self.ircd.channels:
			user.sendMessage(irc.ERR_NOSUCHCHANNEL, params[0], ":No such channel")
			return {}
		if params[0] not in user.channels:
			user.sendMessage(irc.ERR_NOTONCHANNEL, cdata.name, ":You're not in that channel")
			return {}
		if len(params) == 1:
			return {
				"user": user,
				"targetchan": params[0]
			}
		return {
			"user": user,
			"targetchan": params[0],
			"topic": params[1]
		}

class Spawner(object):
	def __init__(self, ircd):
		self.ircd = ircd
	
	def spawn():
		return {
			"commands": {
				"TOPIC": TopicCommand()
			}
		}
	
	def cleanup():
		del self.ircd.commands["TOPIC"]