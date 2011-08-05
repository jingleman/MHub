import feedparser


class Plugin(object):

    """ RSS Feed Plugin """

    name = "rss"
    description = "RSS feed integration"
    author = "MHub"
    
    def on_init(self):

        """ Main plugin initialisation """

        self.tasks = [(self.cfg.get("poll_interval", 60), self.get_feeds)]
        self.last_poll = dict()
        self.first_run = True

        
    def get_feeds(self):

        """ RSS feed parser helper """

        feeds = self.cfg.get("feeds")

        for url in feeds:

            self.last_poll[url] = datetime.datetime.now()
            feed = feedparser.parse(url)

            for entry in feed.entries:

                ets = entry.date_parsed
                ts = datetime.datetime(*ets[:7])

                if self.first_run or ts >= self.last_poll[url]:

                    self.producer.publish({
                        "action": "%s.input" % (self.name),
                        "params": {
                            "feed": url,
                            "title": entry.title,
                            "description": entry.description,
                            "link": entry.link
                        }
                    })

                    self.last_poll[url] = ts

        self.first_run = False
