
import datetime
import imp
import os
import random
import time
import yaml

from socket import timeout
from kombu.connection import BrokerConnection
from kombu.messaging import Exchange, Queue, Producer, Consumer
from twisted.internet import task
from twisted.internet import reactor
from pprint import pprint

from configurator import configure
from logsetup import DefaultLogger
from meta import PluginHelper


class MainController(object):


    """ Main loop and messaging controller """

    mq = None
    initialised = None


    def __init__(self, options, args, server=False):

        """ Constructor """

        self.options = options
        self.args = args
        self.cfg = configure()
        self.plugins = dict()
        self.logger = DefaultLogger(name="mhub", verbosity=options.verbosity).get_logger()
        self.initialised = False

        self.logger.info("Welcome to MHub")

        self.setup_messaging()
        if server: self.setup_plugins()

            
    def setup_messaging(self):

        """ Setup AMQP connection and message consumer """

        self.logger.info("Configuring AMQP messaging")

        general_cfg = self.cfg.get("general")
        amqp_cfg = self.cfg.get("amqp")

        amqp_host = self.options.host if self.options.host is not None else amqp_cfg.get("host")
        amqp_port = self.options.port if self.options.port is not None else amqp_cfg.get("port")

        self.mq_exchange = Exchange(name="mhub",
                                    type="fanout",
                                    durable=False)

        node_name = general_cfg.get("name")        
        queue_name = "queue-%s" % (node_name)

        self.logger.debug("Queue: %s" % (queue_name))

        self.mq_queue = Queue(queue_name,
                              exchange=self.mq_exchange)

        self.mq_connection = BrokerConnection(hostname=amqp_host,
                                              port=amqp_port,
                                              userid=amqp_cfg.get("username"),
                                              password=amqp_cfg.get("password"),
                                              virtual_host=amqp_cfg.get("vhost"))

        self.mq_channel = self.mq_connection.channel()

        self.mq_consumer = Consumer(self.mq_channel,
                                    self.mq_queue)

        self.mq_consumer.register_callback(self.on_message)

        self.mq_consumer.consume()
        
        self.mq_producer = Producer(channel=self.mq_channel,
                                    exchange=self.mq_exchange,
                                    serializer="json")
        

    def setup_plugins(self):

        """ Setup configured plugins """

        self.logger.info("Configuring plugins")

        base_plugins_dir = os.path.join(os.path.dirname(__file__), "plugins")
        user_plugins_dir = os.path.expanduser(self.cfg.get("general").get("plugin_dir"))
        config_dir = self.cfg.get("general").get("config_dir")
        cache_dir = self.cfg.get("general").get("cache_dir")
        plugin_config_dir = os.path.join(config_dir, "plugins")
        plugin_cache_dir = os.path.join(cache_dir, "plugins")

        plugin_list = []
        plugin_list.extend([os.path.join(base_plugins_dir, p) \
                            for p in os.listdir(base_plugins_dir) \
                            if p.endswith(".py")])
        plugin_list.extend([os.path.join(user_plugins_dir, p) \
                            for p in os.listdir(user_plugins_dir) \
                            if p.endswith(".py")])

        for plugin_path in plugin_list:

            basename = os.path.basename(plugin_path)
            name = basename[:-3]

            if name == "__init__": continue

            try:
                plugin_src = imp.load_source("mhub_%s" % (name), plugin_path)
                orig_cls = plugin_src.Plugin
                plugin_cls = type("Plugin", (orig_cls, PluginHelper), {})
                plugin_inst = plugin_cls()
            except ImportError, e:
                self.logger.error("Plugin '%s' cannot be imported" % (name))
                continue

            p_config_dir = os.path.join(plugin_config_dir, name)
            p_cache_dir = os.path.join(plugin_cache_dir, name)
            p_config_file = os.path.join(p_config_dir, "plugin.yml")

            if not os.path.exists(p_config_dir):
                os.makedirs(p_config_dir)

            if not os.path.exists(p_cache_dir):
                os.makedirs(p_cache_dir)
                            
            if os.path.exists(p_config_file):
                self.logger.debug("Loading configuration for plugin '%s'" % (name))
                stream = file(p_config_file, "r")
                p_cfg = yaml.load(stream)
                if "enabled" not in p_cfg: 
                    p_cfg["enabled"] = False
            else:
                self.logger.debug("Creating default configuration for plugin '%s'" % (name))
                if hasattr(plugin_cls, "default_config"):
                    p_cfg = plugin_cls.default_config
                else:
                    p_cfg = dict()
                p_cfg["enabled"] = False
                stream = file(p_config_file, "w")
                yaml.dump(p_cfg, stream)
                
            plugin_inst.producer = self.mq_producer
            plugin_inst.logger = self.logger
            plugin_inst.cfg = p_cfg

            if p_cfg.get("enabled"):
                self.logger.info("Registering plugin '%s'" % (name))
                self.plugins[name] = plugin_inst


    def poll_message(self):

        """ Poll AMQP messages """

        try:
            self.mq_connection.drain_events(timeout=0.1)
        except:
            pass


    def send_message(self, message):

        """ Send an AMQP message via configured AMQP connection """

        self.mq_producer.publish(message)


    def on_message(self, data, message):

        """ On MQ message received forwarding callback function """

        for name, plugin in self.plugins.iteritems():
            if hasattr(plugin, "on_message"):
                plugin.on_message(data, message)

        message.ack()


    def on_init(self):

        """ On startup forwarding function """

        if not self.initialised:
            for name, plugin in self.plugins.iteritems():
                self.logger.debug("Initialising plugin '%s'" % (name))
                if hasattr(plugin, "on_init"):
                    plugin.on_init()
            self.initialised = True
            

    def start(self):

        """ Start the main controller loop """

        self.logger.info("Controller started")

        self.on_init()

        cfg_general = self.cfg.get("general", dict())
        mq_poll_interval = float(cfg_general.get("poll_interval", 0.1))

        mq_task = task.LoopingCall(self.poll_message)
        mq_task.start(mq_poll_interval)

        for plugin_name, plugin_inst in self.plugins.iteritems():
            if not hasattr(plugin_inst, "tasks"): continue
            plugin_tasks = plugin_inst.tasks
            for plugin_task in plugin_tasks:
                interval = plugin_task[0]
                func = plugin_task[1]
                self.logger.debug("Registered '%s' from '%s' every %.2f seconds" % (func.__name__,
                                                                                  plugin_name,
                                                                                  interval))
                task_obj = task.LoopingCall(func)
                task_obj.start(interval)

        reactor.run()
