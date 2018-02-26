#!/usr/bin/python3

import sys
sys.path.append('../')

from twisted.internet import reactor
from twisted.logger import Logger
from asyncsteem import ActiveBlockChain

log = Logger()

class DemoBot(object):
    def comment(self,tm,comment_event,client):
        if comment_event['author'] == 'scottyeager':
            print('Comment by {} on post {} by {}:'.format(comment_event['author'],
                 comment_event['parent_permlink'],
                 comment_event['parent_author']))
            print(comment_event['body'])
            print()


bot = DemoBot()

blockchain = ActiveBlockChain(reactor, log, rewind_days=1)
blockchain.register_bot(bot,"demobot")
reactor.run()
