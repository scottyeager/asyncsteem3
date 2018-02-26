import dateutil.parser

class DateFinder(object):
    """Class for finding the first block measured from a given time in the past."""
    def __init__(self,client,log):
        """Constructor

        Args:
            client : The asyncsteem JSON-RPC RpcClient to use.
            log    : The Twisted asynchonous logger to use.

        """
        self.rpc = client
        self.log = log
        self.active_queries = 0
    def __call__(self,on_found,trigger_time=None):
        """Find a block that matches the given time and call callback

        Args:
            on_found : callback for result
            trigger_time : The time to look for, this MUST be a time in the past, but a time newer than the genesis block.
        """
        #If no trigger time is set, we fetch the "last_irreversible_block_num" value with the get_dynamic_global_properties call.
        def process_global_config(config_event,cclient):
            on_found(config_event["last_irreversible_block_num"])
        if trigger_time == None:
            cmd = self.rpc.get_dynamic_global_properties()
            cmd.on_result(process_global_config)
            return
        self.lower_limit = 0   #Initial window starts at zero
        self.upper_limit = -1  # and ends at infinity.
        self.found = False
        def get_block(blk,ndx):
            def process_block(event, client):
                if not self.found: #Don't continue if already found
                    self.active_queries = self.active_queries - 1
                    if event != None and "timestamp" in event:
                        ddt = dateutil.parser.parse(event["timestamp"])
                        if ddt < trigger_time:
                            #Our guess was to early
                            if blk > self.lower_limit:
                                if self.upper_limit > 0 and self.upper_limit - blk < 2:
                                    #We found our target block
                                    self.found = True
                                    on_found(blk)
                                else:
                                    #Adjust the lower limit for searching to the block we just fetched/
                                    self.lower_limit = blk
                                    if self.upper_limit == -1:
                                        self.log.info("Looking for block in range {rng!r}",rng=[self.lower_limit,"?"])
                                    else:
                                        self.log.info("Looking for block in range {rng!r}",rng=[self.lower_limit,self.upper_limit])
                        else:
                            #Our best guess was either to late or spot on.
                            if self.upper_limit == -1 or blk <= self.upper_limit:
                                if blk - self.lower_limit < 2:
                                    #We found our target block.
                                    self.found = True
                                    on_found(blk)
                                else:
                                    #Adjust the upper limit for searching.
                                    self.upper_limit = blk
                                    self.log.info("Looking for block in range {rng!r}",rng=[self.lower_limit,self.upper_limit])
                    else:
                        #The block we asked for does not yet exist.
                        if self.upper_limit > blk or self.upper_limit == -1:
                            #Adjust our upper limit for searching
                            self.upper_limit = blk
                            self.log.info("Looking for block in range {rng!r}",rng=[self.lower_limit,self.upper_limit])
                    if not self.found:
                        if self.upper_limit != -1:
                            #Divide our remaining seach space into four chunks and use our own search index to figure out what block to
                            #look at next.
                            nexttry = self.lower_limit + (self.upper_limit - self.lower_limit)*(ndx+1)/4
                            get_block(nexttry,ndx)
                        else:
                            nexttry = blk + 30000000
                            nexttry = int(self.lower_limit * (0.75*ndx + 1.75))
                            get_block(nexttry,ndx)
            #Get the designated block so we can check its age.
            opp = self.rpc.get_block(blk)
            #Keep track of the number of active queries
            self.active_queries = self.active_queries + 1
            #Set callback closure for results.
            opp.on_result(process_block)
        #Assume our initial search area ranges from zero to 40000000 and chop up that search area into four equaly sized chunks.
        get_block(10000000,0)
        get_block(20000000,1)
        get_block(30000000,2)
