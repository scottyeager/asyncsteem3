#/usr/bin/python3

from io import BytesIO

from twisted.web.client import Agent, readBody
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.web.http_headers import Headers

from twisted.web.client import FileBodyProducer

a = Agent(reactor)

#call = FileBodyProducer(BytesIO(str.encode(str({"jsonrpc": "2.0", "method": "get_block", "id": 15, "params": [19933014]}))))

#call = FileBodyProducer(BytesIO(b'{"jsonrpc": "2.0", "method": "get_accounts", "id": 20, "params": ["scottyeager"]}'))

call = FileBodyProducer(BytesIO(b'{"jsonrpc": "2.0", "method": "get_account_count", "id": 1}'))

deferred = a.request(b'POST', 'https://api.steemit.com:443', Headers({'User-Agent': ['Twisted Test']}), call)

def cbRequest(response):
    print('Response version:', response.version)
    print('Response code:', response.code)
    print('Response phrase:', response.phrase)
    print('Response headers:')
    d = readBody(response)
    d.addCallback(cbBody)
    return d

def cbBody(body):
    print('Response body:')
    print(body)


deferred.addCallback(cbRequest)

reactor.run()
