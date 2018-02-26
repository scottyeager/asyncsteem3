#!/usr/bin/python3

import sys
sys.path.append('../')

from twisted.internet import reactor
from twisted.logger import Logger
from asyncsteem import ActiveBlockChain

log = Logger()

class DemoBot(object):
    def block(self,tm,block_event,client):
        print(block_event)
        print()


bot = DemoBot()

blockchain = ActiveBlockChain(reactor, log)
blockchain.register_bot(bot,"demobot")
reactor.run()
