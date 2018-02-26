#!/usr/bin/python
from __future__ import print_function
import sys
sys.path.append('../')
from datetime import timedelta
import time
import io
from termcolor import colored
from twisted.internet import reactor
from twisted.logger import Logger, textFileLogObserver
from asyncsteem import ActiveBlockChain

class TestBot:
    def __init__(self):
        self.blocks = 0
        self.hourcount = 0
        self.start = time.time()
        self.last = time.time()
    def block(self,tm,event,client):
        chunk = 100
        self.blocks = self.blocks + 1
        if self.blocks % chunk == 0:
            now = time.time()
            duration = now - self.last
            total_duration = now - self.start
            speed = int(chunk*1000.0/duration)*1.0/1000
            avspeed = int(self.blocks*1000/total_duration)*1.0/1000
            self.last = now
    def hour(self,tm,event,client):
        self.hourcount = self.hourcount + 1
        now = time.time()
        total_duration = str(timedelta(seconds=now-self.start))
        print(colored("* HOUR mark: Processed "+str(self.hourcount)+ " blockchain hours in "+ total_duration,"green"))
        if self.hourcount == 1*24:
            print("Ending eventloop")
            reactor.stop()

obs = textFileLogObserver(io.open("benchmark_asyncsteem.log", "a"))
print("NOTE: asyncsteem logging to benchmark_asyncsteem.log")
log = Logger(observer=obs,namespace="asyncsteem")
nl = "stage" #"bench_stage","bench1","bench2","bench3","bench4","bench5","bench6","bench7","bench8"]:
print("Benchmarking a full day of blocks for",nl)
bc = ActiveBlockChain(reactor,log=log,rewind_days=1,nodelist=nl)
tb = TestBot()
bc.register_bot(tb,"benchmark")
reactor.run()
print("Done.")
