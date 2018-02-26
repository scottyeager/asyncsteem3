#!/usr/bin/python3

# The __main__ function included with jsonrpc.py. Has not been ported to Python 3.

import sys
import dateutil.parser
from datetime import datetime as dt
from twisted.internet import reactor
from twisted.logger import Logger, textFileLogObserver
from asyncsteem import RpcClient

#When processing a block we call this function for each downvote/flag
def process_vote(vote_event,clnt):
    #Create a new JSON-RPC entry on the queue to fetch post info, including detailed vote info
    opp = clnt.get_content(vote_event["author"],vote_event["permlink"])
    #This one is for processing the results from get_content
    def process_content(event, client):
        #We geep track of votes given and the total rshares this resulted in.
        start_rshares = 0.0
        #Itterate over all votes to count rshares and to find the downvote we are interested in.
        found = False
        for vote in  event["active_votes"]:
            #Look if it is our downvote.
            if vote["voter"] == vote_event["voter"] and vote["rshares"] < 0:
                found = True
                #Diferentiate between attenuating downvotes and reputation eating flags.
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
            #Update the total rshares recorded before our downvote
            start_rshares = start_rshares + float(vote["rshares"])
        if found == False:
            print("vote not found, possibly to old.",vote_event["voter"],"=>",vote_event["author"],vote_event["permlink"])
    #Set the above closure as callback.
    opp.on_result(process_content)
#This is a bit fiddly at this low level,  start nextblock a bit higer than where we start out
nextblock = 19933100
obs = textFileLogObserver(sys.stdout)
log = Logger(observer=obs,namespace="jsonrpc_test")
#Create our JSON-RPC RpcClient
rpcclient = RpcClient(reactor,log)
#Count the number of active block queries
active_block_queries = 0
sync_block = None
#Function for fetching a block and its operations.
def get_block(blk):
    """Request a single block asynchonously."""
    global active_block_queries
    #This one is for processing the results from get_block
    def process_block(event, client):
        """Process the result from block getting request."""
        global active_block_queries
        global nextblock
        global sync_block
        active_block_queries = active_block_queries - 1
        if event != None:
            if sync_block != None and blk >= sync_block:
                sync_block = None
            #Itterate over all operations in the block.
            for t in event["transactions"]:
                for o in t["operations"]:
                    #We are only interested in downvotes
                    if o[0] == "vote" and o[1]["weight"] < 0:
                        #Call process_vote for each downvote
                        process_vote(o[1],client)
            #fetching network clients alive.
            get_block(nextblock)
            nextblock = nextblock + 1
            if active_block_queries < 8:
                treshold = active_block_queries * 20
                behind = (dt.utcnow() - dateutil.parser.parse(event["timestamp"])).seconds
                if behind >= treshold:
                    print("Behind",behind,"seconds while",active_block_queries,"queries active. Treshold =",treshold)
                    print("Spinning up an extra parallel query loop.")
                    get_block(nextblock)
                    nextblock = nextblock + 1
        else:
            if sync_block == None or blk <= sync_block:
                sync_block = blk
                get_block(blk)
            else:
                print("Overshot sync_block")
                if active_block_queries == 0:
                    print("Keeping one loop alive")
                    get_block(blk)
                else:
                    print("Scaling down paralel HTTPS queries",active_block_queries)
    #Create a new JSON-RPC entry on the queue to fetch a block.
    opp = rpcclient.get_block(blk)
    active_block_queries = active_block_queries + 1
    #Bind the above closure to the result of get_block
    opp.on_result(process_block)
#Kickstart the process by kicking off eigth block fetching operations.
for block in range(19933000, 19933100):
    get_block(block)
#By invoking the rpcclient, we will process queue entries upto the max number of paralel HTTPS requests.
rpcclient()
#Start the main twisted event loop.
reactor.run()
