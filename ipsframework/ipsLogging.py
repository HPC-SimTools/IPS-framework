"""
This file implements several objects that customize logging in the IPS.
"""

import logging
import sys
import pickle
import socketserver
import struct
import functools
import os
import os.path
import queue
import time
import select


class myLogRecordStreamHandler(socketserver.StreamRequestHandler):

    def __init__(self, request, client_address, server, handler):
        self.handler = handler
        socketserver.StreamRequestHandler.__init__(self,
                                                   request,
                                                   client_address,
                                                   server)

    def handle(self):
        """
        Handle multiple requests - each expected to be a 4-byte length,
        followed by the LogRecord in pickle format. Logs the record
        according to whatever policy is configured locally.
        """
        while True:
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
        return pickle.loads(data)

    def handleLogRecord(self, record):
        name = record.name
        logger = logging.getLogger(name)
        # Need to make sure we only have one handler, since the handler on the
        # sender side is packaged during pickling.
        logger.handlers = []
        logger.addHandler(self.handler)
        # N.B. EVERY record gets logged. This is because Logger.handle
        # is normally called AFTER logger-level filtering. If you want
        # to do filtering, do it at the client end to save wasting
        # cycles and network bandwidth!
        logger.handle(record)
        logger.removeHandler(self.handler)


class LogRecordSocketReceiver(socketserver.ThreadingUnixStreamServer):
    """simple TCP socket-based logging receiver suitable for testing.
    """

    allow_reuse_address = True

    def __init__(self, log_pipe,
                 handler=myLogRecordStreamHandler):
        socketserver.UnixStreamServer.__init__(self, log_pipe, handler)

    def get_file_no(self):
        return self.socket.fileno()


class ipsLogger:
    def __init__(self, dynamic_sim_queue=None):
        self.log_map = {}
        self.server_map = {}
        self.stdout_handler = logging.StreamHandler(sys.stdout)
        self.formatter = logging.Formatter("%(asctime)s %(name)-15s %(levelname)-8s %(message)s")
        self.log_dynamic_sim_queue = dynamic_sim_queue

    def add_sim_log(self, log_pipe_name, log_file=sys.stdout):
        if (log_file == sys.stdout or log_file is None):
            log_handler = self.stdout_handler
        else:
            if log_file.__class__.__name__ == 'TextIOWrapper':
                log_handler = logging.StreamHandler(log_file)
            else:
                directory = os.path.dirname(os.path.abspath(log_file))
                try:
                    os.makedirs(directory, exist_ok=True)
                except OSError as oserr:
                    print('Error creating directory %s : %s-%s' %
                          (directory, oserr.errno, oserr.strerror))
                    sys.exit(1)
                log_handler = logging.FileHandler(log_file, mode='w')

        log_handler.setFormatter(self.formatter)
        partial_handler = functools.partial(myLogRecordStreamHandler,
                                            handler=log_handler)
        recvr = LogRecordSocketReceiver(log_pipe_name, handler=partial_handler)
        fileno = recvr.get_file_no()
        self.log_map[fileno] = (recvr, log_handler, log_pipe_name)

    def __run__(self):
        time_out = 1.0
        while 1:
            read_set = list(self.log_map.keys())
            if read_set:
                rd, _, _ = select.select(read_set,
                                         [], [],
                                         time_out)
            else:
                time.sleep(time_out)
                rd = []

            if len(rd) > 0:
                for fileno in rd:
                    (recvr, _, log_pipe_name) = self.log_map[fileno]
                    recvr.handle_request()
                rd = []
            try:
                msg = self.log_dynamic_sim_queue.get(block=False)
            except queue.Empty:
                pass
            else:
                tokens = msg.split()
                if tokens[0] == 'CREATE_SIM':  # Expecting Message: 'CREATE_SIM  log_pipe_name  log_file
                    self.add_sim_log(tokens[1], tokens[2])
                elif tokens[0] == 'END_SIM':  # Expecting Message 'END_SIM log_pipe_name'
                    log_pipe_name = tokens[1]
                    for fileno, (recvr, _, f_name) in list(self.log_map.items()):
                        if f_name == log_pipe_name:
                            del recvr
                            del self.log_map[fileno]
