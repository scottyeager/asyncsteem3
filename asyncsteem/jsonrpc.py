"""Version of the JSON-RPC library that should work as soon as full-API nodes start implementing the actual JSON-RPC specification"""
import time
import json
from . import nodesets
from io import BytesIO
from twisted.web.client import Agent, readBody, FileBodyProducer
from twisted.web.http_headers import Headers
from twisted.internet import defer

#This class holds a queued JSON-RPC command and also holds references to it's callbacks
class _QueueEntry(object):
    """Helper class for managing in-queue JSON-RPC command invocations"""
    def __init__(self, arpcclient, command, arguments, cmd_id, log):
        self.rpcclient = arpcclient    #We keep a reference to the RpcClient that we pass to content and error handlers.
        self.command = command         #The name of the API call
        self.arguments = arguments     #The API call arguments
        self.cmd_id = cmd_id           #Sequence number for this command
        self.result_callback = None    #Callback for the result, defaults to None
        self.error_callback = None     #Callback for error results, defaults to None
        self.log = log                 #The asynchonous logger
    def on_result(self, callback):
        """Set the on_result callback"""
        self.result_callback = callback
    def on_error(self, callback):
        """Set the on_error callback"""
        self.error_callback = callback
    def _get_rpc_call_object(self):
        """Return a partial JSON-RPC structure for this object."""
        callobj = dict()
        callobj["jsonrpc"] = "2.0"
        callobj["method"] = self.command
        callobj["id"] = self.cmd_id
        callobj["params"] = self.arguments
        return callobj
    def _handle_result(self, result):
        """Call the supplied user result handler or act as default result handler."""
        if self.result_callback != None:
            #Call the result callback but expect failure.
            try:
                self.result_callback(result, self.rpcclient)
            except Exception as ex:
                self.log.failure("Error in result handler for '{cmd!r}'.",cmd=self.command)
        else:
            #If no handler is set, all we do is log.
            self.logg.error("Error: no on_result defined for '{cmd!r}' command result: {res!r}.",cmd=self.command,res=result)
    def _handle_error(self, errno, msg):
        """Call the supplied user error handler or act as default error handler."""
        if self.error_callback != None:
            #Call the error callback but expect failure.
            try:
                self.error_callback(errno, msg, rpcclient)
            except Exception as ex:
                self.log.failure("Error in error handler for '{cmd!r}'.",cmd=self.command)
        else:
            #If no handler is set, all we do is log.
            self.log.err("Notice: no on_error defined for '{cmd!r}, command result: {msg!r}",cmd=self.command,msg=msg)


class RpcClient(object):
    """Core JSON-RPC client class."""
    def __init__(self,
                 areactor,                 #The Twisted reactor
                 log,                      #The asynchonous logger
                 nodes=None,               #If set, nodes overrules the nodelist list of nodelist. NOTE, this will set max_batch_size to one!
                 max_batch_size=None,      #If set, max_batch_size overrules the max_batchsize of nodelist.
                 nodelist = "default",     #Other than "default", "stage" can be used and will use api.steemitstage.com
                                           # with a max_batch_size of 16
                 parallel=16,              #Maximum number of paralel outstanding HTTPS JSON-RPC at any point in time.
                 rpc_timeout=15,           #Timeout for a single HTTPS JSON-RPC query.
                 stop_when_empty= False):  #Stop the reactor then the command queue is empty.
        """Constructor for asynchonour JSON-RPC client.

        Args:
                areactor : The Twisted reactor
                log      : The Twisted asynchonous logger
                nodes    : List of API nodes, you normally should NOT use this, if you use this variable, also use max_batch_size!
                max_batch_size : The max batch size to use for JSON-RPC batched calls. Only use with nodes that support batched RPC calls!
                nodelist : Name of the nodelist to use. "default" and "stage" are currently valid values for this field.
                parallel : Maximum number of paralel outstanding HTTPS JSON-RPC at any point in time.
                rpc_timeout : Timeout (in seconds) for a single HTTPS JSON-RPC query.
                stop_when_empty : Boolean indicating if reactor should be stopped when the command queue is empty and no active HTTPS
                                  sessions remain.
        """
        self.reactor = areactor
        self.log = log
        if nodes:
            #If nodes is defined, overrule nodelist with custom list of nodes.
            self.nodes = nodes
            self.max_batch_size = 1
        else:
            #See nodesets.py for content. We use the nodes and max_batch_size as specified by the nodelist argument.
            self.nodes = nodesets.nodeset[nodelist]["nodes"]
            self.max_batch_size = nodesets.nodeset[nodelist]["max_batch_size"]
        if max_batch_size != None:
            self.max_batch_size = max_batch_size
        self.parallel = parallel
        self.rpc_timeout = rpc_timeout
        self.node_index = 0            #Start of with the first JSON-RPC node in the node list.
        self.agent = Agent(areactor)   #HTTP(s) Agent
        self.cmd_seq = 0               #Unique sequence number used for commands in the command queue.
        self.last_rotate = 0           #Errors may come in batches, we keep track of the last rotate to an other node to avoid responding to
                                       #errors from previois nodes.
        self.errorcount = 0            #The number of errors seen since the previous node rotation.
        self.entries = dict()          #Here the actual commands from the command queue are stored, keyed by sequence number.
        self.queue = list()            #The actual command queue is just a list of sequence numbers.
        self.active_call_count = 0     #The current number of active HTTPS POST calls.
        self.stop_when_empty = stop_when_empty
        self.log.info("Starting off with node {node!r}.",node = self.nodes[self.node_index])
    def _next_node(self, reason):
        #We may have reason to move on to the next node, check how long ago we did so before and how many errors we have seen since.
        now = time.time()
        ago = now - self.last_rotate
        self.errorcount = self.errorcount + 1
        #Only if whe have been waiting a bit longer than the RPC timeout time, OR we have seen a bit more than the max amount of
        # paralel HTTPS requests in errors, then it will be OK to rotate once more.
        if ago > (self.rpc_timeout + 2) or self.errorcount > (self.parallel + 1) :
            self.log.error("Switching from {oldnode!r} to an other node due to error : {reason!r}",oldnode=self.nodes[self.node_index], reason=reason)
            self.last_rotate = now
            self.node_index = (self.node_index + 1) % len(self.nodes)
            self.errorcount = 0
            self.log.info("Switching to node {node!r}", node=self.nodes[self.node_index])
    def __call__(self):
        """Invoke the object to send out some of the queued commands to a server"""
        dv = None
        #Push as many queued calls as the self.max_batch_size and the max number of paralel HTTPS sessions allow for.
        while self.active_call_count < self.parallel and self.queue:
            #Get a chunk of entries from the command queue so we can make a batch.
            subqueue = self.queue[:self.max_batch_size]
            self.queue = self.queue[self.max_batch_size:]
            #Send a single batch to the currently selected RPC node.
            dv = self._process_batch(subqueue)
        #If there is nothing left to do, there is nothing left to do
        if not self.queue and self.active_call_count == 0:
            self.log.error("Queue is empty and no active HTTPS-POSTs remaining.")
            if self.stop_when_empty:
                #On request, stop reactor when queue empty while no active queries remain.
                self.reactor.stop()
        return dv
    def _process_batch(self, subqueue):
        """Send a single batch of JSON-RPC commands to the server and process the result."""
        try:
            timeoutCall = None
            jo = None
            if self.max_batch_size == 1:
                #At time of writing, the regular nodes have broken JSON-RPC batch handling.
                #So when max_batch_size is set to one, we assume we need to work around this fact.
                jo = json.dumps(self.entries[subqueue[0]]._get_rpc_call_object())
            else:
                #The api.steemitstage.com node properly supports JSON-RPC batches, and so, hopefully soon, will the other nodes.
                qarr = list()
                for num in subqueue:
                    qarr.append(self.entries[num]._get_rpc_call_object())
                jo = json.dumps(qarr)

            call = FileBodyProducer(BytesIO(str.encode(str(jo))))
            url = "https://" + self.nodes[self.node_index] + "/"
            url = str.encode(str(url))
            deferred = self.agent.request(b'POST',
                                          url,
                                          Headers({"User-Agent"  : ['Async Steem for Python v0.6.1'],
                                                   "Content-Type": ["application/json"]}),
                                          call)

            def process_one_result(reply):
                """Process a single response from an JSON-RPC command."""
                try:
                    if "id" in reply:
                        reply_id = reply["id"]
                        if reply_id in self.entries:
                            match = self.entries[reply_id]
                            if "result" in reply:
                                #Call the proper result handler for the request that this response belongs to.
                                match._handle_result(reply["result"])
                            else:
                                if "error" in reply and "code" in reply["error"]:
                                    msg = "No message included with error"
                                    if "message" in reply["error"]:
                                        msg = reply["error"]["message"]
                                    #Call the proper error handler for the request that this response belongs to.
                                    match._handle_error(reply["error"]["code"], msg)
                                else:
                                    self.log.error("Error: Invalid JSON-RPC response entry.")
                            #del self.entries[reply_id]
                        else:
                            self.log.error("Error: Invalid JSON-RPC id in entry {rid!r}",rid=reply_id)
                    else:
                        self.log.error("Error: Invalid JSON-RPC response without id in entry: {ris!r}.")
                except Exception as ex:
                    self.log.failure("Error in _process_one_result {err!r}",err=str(ex))
            def handle_response(response):
                """Handle response for JSON-RPC batch query invocation."""
                try:
                    #Cancel any active timeout for this HTTPS call.
                    if timeoutCall.active():
                        timeoutCall.cancel()
                    def cbBody(bodystring):
                        """Process response body for JSON-RPC batch query invocation."""
                        try:
                            results = None
                            #The body SHOULD be JSON, it not always is.
                            try:
                                results = json.loads(bodystring)
                            except Exception as ex:
                                #If the result is NON-JSON, may want to move to the next node in the node list
                                self._next_node("Non-JSON response from server")
                                #Add the failed sub-queue back to the command queue, we shall try again soon.
                                self.queue = subqueue + self.queue
                            if results != None:
                                ok = False
                                if isinstance(results, dict):
                                    #Running in legacy single JSON-RPC call mode (no batches), process the result of the single call.
                                    process_one_result(results)
                                    ok = True
                                else:
                                    if isinstance(results, list):
                                        #Running in batch mode, process the batch result, one response at a time
                                        for reply in results:
                                            process_one_result(reply)
                                        ok = True
                                    else:
                                        #Completely unexpected result type, may want to move to the next node in the node list.
                                        self._next_node("JSON response neither list nor object")
                                        self.log.error("Error: Invalid JSON-RPC response, expecting list as response on batch.")
                                        #Add the failed sub-queue back to the command queue, we shall try again soon.
                                        self.queue = subqueue + self.queue
                                if ok == True:
                                    #Clean up the entries dict by removing all fully processed commands that now are no longer in the queu.
                                    for request_id in subqueue:
                                        if request_id in self.entries:
                                            del self.entries[request_id]
                                        else:
                                            self.log.error("Error: No response entry for request entry in result: {rid!r}.",rid=request_id)
                        except Exception as ex:
                            self.log.failure("Error in cbBody {err!r}",err=str(ex))
                        #This HTTPS POST is now fully processed.
                        self.active_call_count = self.active_call_count - 1
                        #Invoke self, possibly sending new queues RPC calls to the current node
                        self()
                    deferred2 = readBody(response)
                    deferred2.addCallback(cbBody)
                    return deferred2
                except Exception as ex:
                    self.log.failure("Error in handle_response {err!r}",err=str(ex))
                    #If something went wrong, the HTTPS POST isn't active anymore.
                    self.active_call_count = self.active_call_count - 1
                    #Invoke self, possibly sending new queues RPC calls to the current node
                    self()
            deferred.addCallback(handle_response)
            def _handle_error(error):
                """Handle network level error for JSON-RPC request."""
                try:
                    #Abandon any active timeout triggers
                    if timeoutCall.active():
                        timeoutCall.cancel()
                    #Unexpected error on HTTPS POST, we may want to move to the next node.
                    self._next_node(error.getErrorMessage())
                    self.log.error("Error on HTTPS POST : {err!r}",err=error.getErrorMessage())
                except Exception as ex:
                    self.log.failure("Error in _handle_error {err!r}",err=str(ex))
                #Add the failed sub-queue back to the command queue, we shall try again soon.
                self.queue = subqueue + self.queue
                ##If something went wrong, the HTTPS POST isn't active anymore.
                self.active_call_count = self.active_call_count - 1
                #Invoke self, possibly sending new queues RPC calls to the current node
                self()
            deferred.addErrback(_handle_error)
            timeoutCall = self.reactor.callLater(self.rpc_timeout, deferred.cancel)
            #Keep track of the number of active parallel HTTPS posts.
            self.active_call_count = self.active_call_count + 1
            return deferred
        except Exception as ex:
            self.log.failure("Error in _process_batch {err!r}",err=str(ex))
    def __getattr__(self, name):
        def addQueueEntry(*args):
            """Return a new in-queue JSON-RPC command invocation object with auto generated command name from __getattr__."""
            try:
                #A unique id for each command.
                self.cmd_seq = self.cmd_seq + 1
                #Create a new queu entry
                self.entries[self.cmd_seq] = _QueueEntry(self, name, args, self.cmd_seq, self.log)
                #append it to the command queue
                self.queue.append(self.cmd_seq)
                #Return handle to the new entry for setting callbacks on.
                return self.entries[self.cmd_seq]
            except Exception as ex:
                self.log.failure("Error in addQueueEntry {err!r}",err=str(ex))
        return addQueueEntry
    #Need to be able to check if RpcClient equatesNone
    def __eq__(self, val):
        if val is None:
            return False
        return True
