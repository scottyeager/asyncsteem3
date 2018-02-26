#!/usr/bin/python3

import sys
sys.path.append('../')

from twisted.internet import reactor
from twisted.logger import Logger
from asyncsteem import ActiveBlockChain

log = Logger()

class DemoBot(object):
    def vote(self,tm,vote_event,client):
        w = vote_event["weight"]
        if w > 0:
            print("Vote by",vote_event["voter"],"for",vote_event["author"])
        else:
            if w < 0:
                print("Downvote by",vote_event["voter"],"for",vote_event["author"])
            else:
                print("(Down)vote by",vote_event["voter"],"for",vote_event["author"],"CANCELED")

bot = DemoBot()

blockchain = ActiveBlockChain(reactor, log)
blockchain.register_bot(bot,"demobot")
reactor.run()
