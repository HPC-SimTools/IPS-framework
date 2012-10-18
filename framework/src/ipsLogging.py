#-------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
#-------------------------------------------------------------------------------
"""
This file implements several objects that customize logging in the IPS.
"""

import logging
import atexit
import sys
import cPickle
import logging.handlers
import SocketServer
import struct
import functools
import logging.handlers
import socket
import os, os.path
import Queue

class IPSLogSocketHandler(logging.handlers.SocketHandler):
    def __init__(self, port):
        logging.handlers.SocketHandler.__init__(self, None, None)
        self.host = None
        self.port = port
        self.my_socket = None

    def makeSocket(self):
        if True:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(self.port)
            self.my_socket = s
        return self.my_socket

class myLogRecordStreamHandler(SocketServer.StreamRequestHandler):

    def __init__(self, request, client_address, server, handler):
        self.handler=handler
        SocketServer.StreamRequestHandler.__init__(self,
                                                   request,
                                                   client_address,
                                                   server)
        return

    def handle(self):
        """
        Handle multiple requests - each expected to be a 4-byte length,
        followed by the LogRecord in pickle format. Logs the record
        according to whatever policy is configured locally.
        """
        while 1:
            chunk = self.connection.recv(4)
            if len(chunk) < 4:
                break
            slen = struct.unpack(">L", chunk)[0]
            chunk = self.connection.recv(slen)
            while len(chunk) < slen:
                chunk = chunk + self.connection.recv(slen - len(chunk))
            obj = self.unPickle(chunk)
            record = logging.makeLogRecord(obj)
            self.handleLogRecord(record)

    def unPickle(self, data):
        return cPickle.loads(data)

    def handleLogRecord(self, record):
        name = record.name
        logger = logging.getLogger(name)
        # Need to make sure we only have one handler, since the handler on the
        # sender side is packaged during pickling.
        logger.handlers=[]
        logger.addHandler(self.handler)
        # N.B. EVERY record gets logged. This is because Logger.handle
        # is normally called AFTER logger-level filtering. If you want
        # to do filtering, do it at the client end to save wasting
        # cycles and network bandwidth!
        logger.handle(record)
        logger.removeHandler(self.handler)
        return

class LogRecordSocketReceiver(SocketServer.ThreadingUnixStreamServer):
    """simple TCP socket-based logging receiver suitable for testing.
    """

    allow_reuse_address = 1

    def __init__(self, log_pipe,
                 handler=myLogRecordStreamHandler):
        SocketServer.UnixStreamServer.__init__(self, log_pipe, handler)

    def get_file_no(self):
        return self.socket.fileno()

class ipsLogger(object):
    def __init__(self, dynamic_sim_queue = None):
        self.log_map={}
        self.stdout_handler = logging.StreamHandler(sys.stdout)
        self.formatter = logging.Formatter("%(asctime)s %(name)-15s %(levelname)-8s %(message)s")
        self.handle_map = {}
        fileno_map = {}
        self.log_dynamic_sim_queue = dynamic_sim_queue

    def add_sim_log(self, log_pipe_name, log_file=sys.stdout):
        if (log_file == sys.stdout or log_file == None):
            log_handler = self.stdout_handler
        else:
            try:
                log_handler = self.handle_map[log_file]
            except KeyError:
                if(log_file.__class__.__name__ == 'file'):
                    log_handler = logging.StreamHandler(log_file)
                else:
                    dir = os.path.dirname(os.path.abspath(log_file))
                    try:
                        os.makedirs(dir)
                    except OSError, (errno, strerror):
                        if (errno != 17):
                            print 'Error creating directory %s : %s-%s' % \
                                (dir, errno, strerror)
                            sys.exit(1)
                    log_handler = logging.FileHandler(log_file, mode = 'w')
                self.handle_map[log_file] = log_handler

#        log_handler.setLevel(logging.DEBUG)
        log_handler.setFormatter(self.formatter)
        partial_handler = functools.partial(myLogRecordStreamHandler,
                                            handler=log_handler)
        recvr = LogRecordSocketReceiver(log_pipe_name, handler=partial_handler)
        fileno = recvr.get_file_no()
        self.log_map[fileno] = (recvr, log_handler, log_pipe_name)
        return

    def __run__(self):
#        logging.basicConfig(
#            format="%(relativeCreated)5d %(name)-15s %(levelname)-8s %(message)s",
#           filename = self.log_file,
#           filemode = 'w')
        import select
        time_out = 1.0
        read_set = self.log_map.keys()
        while 1:
            #print 'read_set = ', read_set
            rd, wr, ex = select.select(read_set,
                                       [], [],
                                       time_out)
            if rd:
                for fileno in rd:
                    (recvr, log_handler, log_pipe_name) = self.log_map[fileno]
                    recvr.handle_request()
            try:
                msg = self.log_dynamic_sim_queue.get(block=False)
            except Queue.Empty:
                pass
            else:
                tokens = msg.split()
                if (tokens[0] == 'CREATE_SIM'): # Expecting Message: 'CREATE_SIM  log_pipe_name  log_file
                    self.add_sim_log(tokens[1], tokens[2])
                    read_set = self.log_map.keys()
                elif (tokens[0] == 'END_SIM'):  # Expecting Message 'END_SIM log_pipe_name'
                    log_pipe_name = tokens[1]
                    for fileno , (recvr, log_handler, f_name) in self.log_map.items():
                        if f_name == log_pipe_name:
                            del self.log_map[fileno]
                            read_set.remove(fileno)
