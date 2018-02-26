# asyncsteem3
Twisted based asynchonous python STEEM JSON-RPC API.

This project is a Python 3 port of [asyncsteem](https://github.com/pibara-utopian/asyncsteem) by [@pibara](github.com/pibara), which aims to implement a complete asynchronous alternative to [steem-python](https://github.com/steemit/steem-python). It is designed to work with the defacto Python asynchonous networking framework [twisted](https://twistedmatrix.com/trac/). Twisted is the only dependency for asyncsteem3.

The current beta does not yet implement cryptographic signing operations that would be needed to, post, vote, etc. However, it is easy to create bots for collecting stats or dispatching alerts by monitoring the blockchain with minimal boilerplate code.

If you wish to stay informed on the progress of asyncsteem, please follow [@mattockfs](https://steemit.com/@mattockfs) on steemit or join [this](https://discord.gg/dUjUqmE) discord server. Donations for this project in the form of STEEM or in the form of steemit post upvotes are very much welcomed, as are pull requests with features or bug fixes.

## Install

A setup.py file is included, if you wish to install the package.

```
python setup.py install
```

## Usage

See examples/print_votes.py for a simple bot that spits out info about votes happening on the Steem blockchain.

```
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
```

A bot class can implement one or more of the following methods, which are called whenever a new event of that type arrives:

* account\_create
* account\_create\_with\_delegation
* account\_update
* account\_witness\_proxy
* account\_witness\_vote
* cancel\_transfer\_from\_savings
* change\_recovery\_account
* claim\_reward\_balance
* comment
* comment\_options
* convert
* custom
* custom\_json
* delegate\_vesting_shares
* delete\_comment
* feed\_publish
* limit\_order\_cancel
* limit\_order\_create
* recover\_account
* request\_account\_recovery
* set\_withdraw\_vesting\_route
* transfer
* transfer\_from\_savings
* transfer\_to\_savings
* transfer\_to\_vesting
* vote
* withdraw\_vesting
* witness\_update

These methods map one on one to the operation types that are found on the blockchain. For convenience, the following methods may also be implemented:

* transaction
* block
* hour
* day
* week

### Rewind

You may also instead opt to pick a day in the past where the bot should start streaming. This could come in handy if you want to test your code, or if you want to limit your bot's online time.

```python
blockchain = ActiveBlockChain(reactor,rewind_days=7)
```

### Other API Methods

While the core of the library is aimed at streaming operations from the blockchain, it is likely your bot will need to query other JSON-RPC API's as well. For this, the *client* argument of the bots methods provides the entry point. But note, the API is asynchonous and works through a command queue and a client pool. Let us zoom in a bit on how to use the *client* argument in our code.

```python
    def vote(self,tm,vote_event,client):
        def process_vote_content(event, client):
            for vote in  event["active_votes"]:
                if vote["voter"] == vote_event["voter"] and vote["rshares"] != 0:
                    print( vote["time"],vote["voter"],"=>",vote_event["author"],vote["rshares"])
        opp = client.get_content(vote_event["author"],vote_event["permlink"])
        opp.on_result(process_vote_content)
```

Basically, you define a closure for handling the additional API query, you put the command you wish to invoke on the asynchonous command queue and then you bind the result to your closure that will be invoked asynchonously when the command on the queue has been handled by the HTTPS client pool.

In some cases, a JSON-RPC call may return an error for your command. You may create an other callback for the error situation:

```python
   def err_handler(errno, msg, rpcclient):
       print("OOPS:",msg,"(",errno,")")
   opp.on_error(err_handler)
```

You've seen the example using *get\_content*, this is one of a wide range of JSON-RPC API calls available through the API. The API is fully transperant, so any silly typo you make will result in a bogus JSON-RPC call to one of the STEEM API nodes. For convenience, here is a list of currently commonly available valid API method names:

* get\_account\_bandwidth
* get\_account\_count
* get\_account\_history
* get\_account\_references
* get\_account\_votes
* get\_accounts
* get\_active\_votes
* get\_active\_witnesses
* get\_block
* get\_block\_header
* get\_chain\_properties
* get\_comment\_discussions\_by\_payout
* get\_config
* get\_content
* get\_content\_replies
* get\_conversion\_requests
* get\_current\_median\_history\_price
* get\_discussions\_by\_active
* get\_discussions\_by\_author\_before\_date
* get\_discussions\_by\_blog
* get\_discussions\_by\_cashout
* get\_discussions\_by\_children
* get\_discussions\_by\_comments
* get\_discussions\_by\_created
* get\_discussions\_by\_feed
* get\_discussions\_by\_hot
* get\_discussions\_by\_payout
* get\_discussions\_by\_promoted
* get\_discussions\_by\_trending
* get\_discussions\_by\_votes
* get\_dynamic\_global\_properties
* get\_escrow
* get\_expiring\_vesting\_delegations
* get\_feed\_history
* get\_hardfork\_version
* get\_key\_references
* get\_liquidity\_queue
* get\_miner\_queue
* get\_next\_scheduled\_hardfork
* get\_open\_orders
* get\_ops\_in\_block
* get\_order\_book
* get\_owner\_history
* get\_post\_discussions\_by\_payout
* get\_potential\_signatures
* get\_recovery\_request
* get\_replies\_by\_last\_update
* get\_required\_signatures
* get\_reward\_fund
* get\_savings\_withdraw\_from
* get\_savings\_withdraw\_to
* get\_state
* get\_tags\_used\_by\_author
* get\_transaction
* get\_transaction\_hex
* get\_trending\_tags
* get\_vesting\_delegations
* get\_withdraw\_routes
* get\_witness\_by\_account
* get\_witness\_count
* get\_witness\_schedule
* get\_witnesses
* get\_witnesses\_by\_vote
* lookup\_account\_names
* lookup\_accounts
* lookup\_witness\_accounts
* set\_block\_applied\_callback
* verify\_account\_authority
* verify\_authority

Documentation for steemd API calls can be found on [GitHub](https://steemit.github.io/steemit-docs/). Often the error messages can provide some info on correct usage—use an on\_error callback to print the error.

Both asyncsteem and asyncsteem3 are beta releases. Please report any issues with asyncsteem3 to its own GitHub repository so they can be addressed or forwarded to asyncsteem as appropriate.
