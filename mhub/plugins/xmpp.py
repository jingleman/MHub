import logging

from twisted.words.protocols.jabber import jid
from wokkel.client import XMPPClient
from wokkel.xmppim import MessageProtocol, AvailablePresence

from base import BasePlugin


class XmppPlugin(BasePlugin):

    """
    XMPP/Jabber (Google Talk) plugin.
    """

    default_config = {
        "enabled": False,
        "username": "user@gmail.com",
        "password": "changeme",
        "server": "talk.google.com",
        "port": 5222
    }

    def setup(self, cfg):

        BasePlugin.setup(self, cfg)
        
        self.client = XmppClient(self.cfg.get("username"),
                                 self.cfg.get("password"),
                                 self.cfg.get("server"),
                                 self.cfg.get("port"))

        self.factory = XmppFactory(plugin=self)
        self.factory.setHandlerParent(self.client)


class XmppFactory(MessageProtocol):


    def __init__(self, plugin):

        self.logger = logging.getLogger("plugin.factory")
        self.plugin = plugin
        self.service = plugin.service


    def connectionMade(self):
        self.logger.debug("XMPP connected")
        self.send(AvailablePresence())

    def connectionLost(self, reason):
        self.logger.debug("XMPP disconnected")
        pass

    def onMessage(self, msg):

        for e in msg.elements():
            if e.name == "body":
                body = unicode(e.__str__())

        self.plugin.publish_event("receive", {
            "to": msg["to"],
            "from": msg["from"],
            "type": msg["type"],
            "body": body
        })



class XmppClient(XMPPClient):

    def __init__(self, user, password, host=None, port=5222):

        jid_obj = jid.internJID(user)
        XMPPClient.__init__(self, jid_obj, password, host, port)
