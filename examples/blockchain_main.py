#!/usr/bin/python3

# The __main__ function included with blockchain.py. Has not been ported to Python 3.

import sys
sys.path.append('../')
from twisted.internet import reactor
from twisted.logger import Logger, textFileLogObserver
from asyncsteem import ActiveBlockChain
class Bot(object):
    def vote(self,tm,vote_event,client):
        opp = client.get_content(vote_event["author"],vote_event["permlink"])
        def process_vote_content(event, client):
            start_rshares = 0.0
            for vote in  event["active_votes"]:
                if vote["voter"] == vote_event["voter"] and vote["rshares"] < 0:
                    if start_rshares + float(vote["rshares"]) < 0:
                        print(vote["time"],\
                                "FLAG",\
                                vote["voter"],"=>",vote_event["author"],\
                                vote["rshares"]," rshares (",\
                                start_rshares , "->", start_rshares + float(vote["rshares"]) , ")")
                    else:
                        print(vote["time"],\
                                "DOWNVOTE",\
                                vote["voter"],"=>",vote_event["author"],\
                                vote["rshares"],"(",\
                                start_rshares , "->" , start_rshares + float(vote["rshares"]) , ")")
                start_rshares = start_rshares + float(vote["rshares"])
        opp.on_result(process_vote_content)
obs = textFileLogObserver(sys.stdout)
log = Logger(observer=obs,namespace="blockchain_test")
bc = ActiveBlockChain(reactor,log,rewind_days=1,nodelist="stage")
bot=Bot()
bc.register_bot(bot,"testbot")
reactor.run()
