import socket


class Plugin(object):

    """ Schedule Plugin """

    def __init__(self, cfg, producer, logger):

        """ Constructor """

        self.name = "lirc"
        self.description = "Linux infrared remote control daemon integration"
        self.author = "MHub"
        self.cfg = cfg
        self.producer = producer
        self.logger = logger
        

    def on_init(self):

        """ Main plugin initialisation """

        self.tasks = [(0.10, self.process_events)]
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.setblocking(False)
        try:
            self.socket.connect(self.cfg.get("lircd_socket", "/dev/lircd"))
        except:
            pass

        
    def process_events(self):

        try:
            data = str(self.socket.recv(1024))
        except:
            data = ""

        parts = data.split("\n")[0].split(" ")

        if len(parts) == 4:

            self.producer.publish({
                "action": "%s.input",
                "params": {
                    "raw": parts[0],
                    "count": parts[1],
                    "command": parts[2],
                    "remote": parts[3]
                }
            })