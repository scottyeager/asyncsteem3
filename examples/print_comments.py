#!/usr/bin/python3

import sys
sys.path.append('../')

from twisted.internet import reactor
from twisted.logger import Logger
from asyncsteem import ActiveBlockChain

log = Logger()

class DemoBot(object):
    def comment(self,tm,comment_event,client):
        print('Comment by {} on post {} by {}:'.format(comment_event['author'],
                                                       comment_event['parent_permlink'],
                                                       comment_event['parent_author']))
        print(comment_event['body'])
        print()


bot = DemoBot()

blockchain = ActiveBlockChain(reactor, log)
blockchain.register_bot(bot,"demobot")
reactor.run()
