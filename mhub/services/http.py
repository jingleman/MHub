from twisted.web import resource, static


class HTTPService(resource.Resource):
 
    cs = None
    isLeaf = True


    def getChild(self, name, request):
        
        if name == "":
            return self
        return resource.Resource.getChild(self, name, request)


    def render_GET(self, request):

        args = request.args
 
        action = args.get("action", "")

        success = False

        if len(action) > 0:

            del args["action"]
            action_str = action[0]

            for k, v in args.iteritems():
                val = v[0]
                if val.lower() == "true":
                    val = True
                elif val.lower() == "false": 
                    val = False
                args[k] = val

            msg = dict(action=action, params=args)
    
            self.cs.amqp_send_message(msg)
            success = True
        
        return "OK" if success else "ERROR"
