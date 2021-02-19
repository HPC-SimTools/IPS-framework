# -------------------------------------------------------------------------------
# Copyright 2006-2020 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------


class BlockedMessageException(Exception):
    """ Exception Raised by the any manager when a blocking service
        invocation is made, and the invocation result is not readily
        available.
    """

    def __init__(self, msg, reason):
        super().__init__(msg)
        self.msg = msg
        self.reason = reason
        self.args = (msg, reason)

    def __str__(self):
        return 'message blocked because %s' % self.reason


class IncompleteCallException(Exception):
    """ Exception Raised by the taskManager when a nonblocking wait_call()
        method is invoked  before the call has finished.
    """

    def __init__(self, callID):
        super().__init__()
        self.callID = callID
        self.args = (callID,)

    def __str__(self):
        return 'nonblocking wait_call() invoked before call %s finished' % self.callID


class AllocatedNodeDownException(Exception):
    """ Exception is raised when an allocated node is discovered to be faulty.
        The task manager should catch the exception and do something with it.
    """

    def __init__(self, identifier, tid, comp_id):
        super().__init__()
        self.node = identifier
        self.tid = tid
        self.component = comp_id
        self.args = (identifier, tid, comp_id)

    def __str__(self):
        return 'allocated node {} has been deemed unfit. task {} of component {} needs to be killed and restarted.'.format(self.node, self.tid, self.component)


class NonexistentResourceException(Exception):
    """ Exception for any time nonexistent (nodes) are tried to be used
    """

    def __init__(self, identifier):
        super().__init__()
        self.thing = identifier

    def __str__(self):
        return self.thing + ' does not exist'


class InsufficientResourcesException(Exception):
    """ Exception Raised by the resource manager when not enough resources
        are available to satisfy an allocate() call
    """

    def __init__(self, caller_id, tid, request, deficit):
        super().__init__()
        self.caller_id = caller_id
        self.task_id = tid
        self.request = request
        self.deficit = deficit
        self.args = (caller_id, tid, request, deficit)

    def __str__(self):
        return ("component " + str(self.caller_id) + " requested " + str(self.request) +
                " nodes, which is more than available by " + str(self.deficit) +
                " nodes, for task " + str(self.task_id) + ".")


class ResourceRequestMismatchException(Exception):
    """ Exception raised by the resource manager when it is possible to launch
    the requested number of processes, but not on the requested number of
    processes per node.
    """

    def __init__(self, caller_id, tid, nproc, ppn, max_procs, max_ppn):
        super().__init__()
        self.caller_id = caller_id
        self.task_id = tid
        self.nproc = nproc
        self.ppn = ppn
        self.max_procs = max_procs
        self.max_ppn = max_ppn
        self.args = (caller_id, tid, nproc, ppn, max_procs, max_ppn)

    def __str__(self):
        s = "component %s requested %d processes with %d processes per node, while the number of processes requested"\
            "is less than the max (%d), the processes per node value is too low." % (self.caller_id, self.nproc, self.ppn, self.max_procs)
        return s


class InvalidResourceSettingsException(Exception):
    """
    Exception raised by the resource helper to indicate inconsistent resource settings.
    """

    def __init__(self, t, spn, cpn):
        super().__init__()
        self.type = t
        self.spn = spn
        self.cpn = cpn

    def __str__(self):
        preamble = "Invalid resource specification in platform configuration file: "
        if self.type == "spn > cpn":
            return "%s socket per node count (%d) greater than core per node count (%d)." % (preamble, self.spn, self.cpn)
        elif self.type == "spn not divisible by cpn":
            return "%s socket per node count (%d) not divisible by core per node count (%d)." % (preamble, self.spn, self.cpn)
        elif self.type == "total procs and nodes mismatch":
            return "%s values for total procs (%d) and nodes (%d) do not make sense." % (preamble, self.spn, self.cpn)
        else:
            return "%s unknown error" % (preamble)


class BadResourceRequestException(Exception):
    """ Exception raised by the resource manager when a component requests
        a quantity of resources that can never be satisfied during a
        get_allocation() call
    """

    def __init__(self, caller_id, tid, request, deficit):
        super().__init__()
        self.caller_id = caller_id
        self.task_id = tid
        self.request = request
        self.deficit = deficit
        self.args = (caller_id, tid, request, deficit)

    def __str__(self):
        return ("component " + str(self.caller_id) + " requested " + str(self.request) +
                " nodes, which is more than possible by " + str(self.deficit) +
                " nodes, for task " + str(self.task_id) + ".")


class ReleaseMismatchException(Exception):
    """ Exception raised by the resource manager when a release allocation
        request accounting yields unexpected results.
    """

    def __init__(self, caller_id, tid, old_alc, old_avc, new_alc, new_avc):
        super().__init__()
        self.caller_id = caller_id
        self.tid = tid
        self.old_alc = old_alc
        self.old_avc = old_avc
        self.new_alc = new_alc
        self.new_avc = new_avc
        self.args = (caller_id, tid, old_alc, old_avc, new_alc, new_avc)

    def __str__(self):
        return ("component " + str(self.caller_id) + " released nodes for task " + str(self.tid) +
                ".  old_alc = " + str(self.old_alc) + " new_alc = " + str(self.new_alc) +
                "  old_avc = " + str(self.old_avc) + " new_avc = " + str(self.new_avc))
