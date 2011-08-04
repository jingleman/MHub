import urllib


class Plugin(object):

    """ HTTP Plugin """

    def __init__(self, cfg, producer, logger):

        """ Constructor """

        self.name = "http"
        self.description = "HTTP integration"
        self.author = "MHub"
        self.cfg = cfg
        self.producer = producer
        self.logger = logger
        

    def on_init(self):

        """ Main plugin initialisation """

        self.tasks = [(self.cfg.get("poll_interval", 60), self.get_pages)]
        self.last_poll = dict()
        self.first_run = True

        
    def get_pages(self):

        """ HTTP page processor helper """

        pages = self.cfg.get("pages")

        for url in pages:

            self.last_poll[url] = datetime.datetime.now()
            body = get_page(url)

            self.producer.publish({
                "action": "%s.input" % (self.name),
                "params": {
                    "url": url,
                    "body": body
            })


    def get_page(self, url):

        """ HTTP page fetcher helper """

        sock = urllib.urlopen("www.python.org")
        body = sock.read()
        sock.close()
        return body
