#!/usr/bin/python3

# The __main__ function included with blockfinder.py. Has not been ported to Python 3.

import sys
sys.path.append('../')
from twisted.internet import reactor
from asyncsteem import RpcClient, DateFinder
from datetime import date
from dateutil import relativedelta
from twisted.logger import Logger, textFileLogObserver
def process_blockno(bno):
    print("BLOCK: ",bno)
obs = textFileLogObserver(sys.stdout)
log = Logger(observer=obs,namespace="blockfinder_test")
rpcclient = RpcClient(reactor,log,stop_when_empty=True)
datefinder = DateFinder(rpcclient,log)
ddt = date.today() - relativedelta.relativedelta(hour=0,days=1)
datefinder(process_blockno,ddt)
rpcclient()
reactor.run()
