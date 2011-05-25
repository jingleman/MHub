import feedparser


class Plugin(object):

    """ RSS Feed Plugin """

    def __init__(self, cfg, publisher, logger):

        """ Constructor """

        self.cfg = cfg
        self.publisher = publisher
        self.logger = logger
        

    def on_init(self):

        """ Main plugin initialisation """

        self.tasks = [(self.cfg.get("poll_interval", 60), self.get_feeds)]
        self.last_poll = dict()
        self.first_run = True

        
    def get_feeds(self):

        feeds = self.cfg.get("feeds")

        for url in feeds:
            self.last_poll[url] = datetime.datetime.now()
            feed = feedparser.parse(url)
            for entry in feed.entries:
                ets = entry.date_parsed
                ts = datetime.datetime(*ets[:7])
                if self.first_run or ts >= self.last_poll[url]:
                    self.publisher.send({
                        "action": "rss",
                        "params": {
                            "feed": url,
                            "title": entry.title,
                            "description": entry.description,
                            "link": entry.link
                        }
                    })
                    self.last_poll[url] = ts
        self.first_run = False
