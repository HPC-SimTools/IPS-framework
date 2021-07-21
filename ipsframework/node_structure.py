# -------------------------------------------------------------------------------
# Copyright 2006-2021 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
"""
Node structures for RM are implemented here for convenience.
"""

# local version


class Node:
    """
    Models a node in the allocation.

      * *name*: name of node, typically actual name from resource detection phase.
      * *task_ids*, *owners*: identifiers for the tasks and components that are currently using the node.
      * *allocated*, *available*: list of sockets that have cores allocated and available.  A socket may appear in both lists if it is only partially allocated.
      * *sockets*: list of sockets belonging to this node
      * *avail_cores*: number of cores that are currently available.
      * *total_cores*: total number of cores that can be allocated on this node.
      * *status*: indicates if the node is 'UP' or 'DOWN'.  Currently not used, all nodes are considered functional..
    """

    def __init__(self, name, socks, cores, p):
        self.status = 'UP'
        self.name = name
        self.task_ids = []
        self.owners = []
        self.allocated = []  # sockets allocated
        self.available = []  # sockets available
        self.sockets = []
        if isinstance(p, int):
            self.avail_cores = p
        else:
            self.avail_cores = len(p)
        cps = cores // socks

        self.total_cores = self.avail_cores
        c = 0
        s = 0
        i = 0
        while c < self.total_cores:
            if c + cps <= self.total_cores:
                if isinstance(p, int):
                    self.sockets.append(Socket(s, cps))
                else:
                    self.sockets.append(Socket(s, cps, p[i:cps]))
                    i += cps
                self.available.append(s)
                s += 1
                c += cps
            else:
                if isinstance(p, int):
                    self.sockets.append(Socket(s, p - c))
                    c = p
                else:
                    self.sockets.append(Socket(s, len(p) - c, p[i:]))
                    i = len(p)
                    c = len(p)
                self.available.append(s)

    def print_sockets(self, fname=''):
        """
        Pretty print of state of sockets.
        """
        if fname:
            for sock in self.sockets:
                print("    socket:", sock.name, file=fname)
                print("    availablilty:", sock.avail_cores, file=fname)
                print("    task ids:", sock.task_ids, file=fname)
                print("    owners:", sock.owners, file=fname)
                print("    cores:", sock.total_cores, file=fname)
                sock.print_cores(fname)

        else:
            for sock in self.sockets:
                print("    socket:", sock.name)
                print("    availablilty:", sock.avail_cores)
                print("    task ids:", sock.task_ids)
                print("    owners:", sock.owners)
                print("    cores:", sock.total_cores)
                sock.print_cores()

    def allocate(self, whole_nodes, whole_sockets, tid, o, procs):
        """
        Mark *procs* number of cores as allocated subject to the values of
        *whole_nodes* and *whole_sockets*.  Return the number of cores
        allocated and their corresponding slots, a list of strings of the form:

          <socket name>:<core name>
        """
        # add tid and o to lists
        slots = []
        self.task_ids.append(tid)
        self.owners.append(o)
        k = 0   # number of cores allocated

        if whole_nodes:
            for sock in self.sockets:
                slots.extend(sock.allocate(whole_sockets, tid, o,
                                           sock.avail_cores))
                self.available.remove(sock.name)
                self.allocated.append(sock.name)
                k += sock.total_cores
        elif whole_sockets:
            for sock in self.sockets:
                if sock.avail_cores == sock.total_cores:
                    slots.extend(sock.allocate(whole_sockets, tid, o,
                                               sock.avail_cores))
                    self.available.remove(sock.name)
                    self.allocated.append(sock.name)
                    k += sock.total_cores
                    if k >= procs:
                        break
        else:
            for sock in self.sockets:
                if sock.avail_cores > procs - k:
                    slots.extend(sock.allocate(whole_sockets, tid, o,
                                               procs - k))
                    k = procs
                    if sock.name not in self.allocated:
                        self.allocated.append(sock.name)
                    if sock.avail_cores == 0:
                        self.available.remove(sock.name)

                elif sock.avail_cores > 0:  # sock.avail_cores < procs - k
                    k += sock.avail_cores
                    slots.extend(sock.allocate(whole_sockets, tid, o,
                                               sock.avail_cores))
                    if sock.name not in self.allocated:
                        self.allocated.append(sock.name)
                    if sock.avail_cores == 0:
                        self.available.remove(sock.name)
                if k >= procs:
                    break

        self.avail_cores -= k
        return k, slots

    def release(self, tid, o):
        """
        Mark cores used by task *tid* and component *o* as available.  Return
        the number of cores released.
        """
        # remove tid and o from lists
        self.task_ids.remove(tid)
        self.owners.remove(o)
        ac = 0
        start = self.avail_cores
        for s in self.sockets:
            if tid in s.task_ids:
                s.release(tid)
                if s.name not in self.available:
                    self.available.append(s.name)
                elif s.avail_cores == s.total_cores:
                    self.allocated.remove(s.name)
            ac += s.avail_cores

        # update avail_cores
        self.avail_cores = ac
        return self.avail_cores - start


class Socket:
    """
    Models a socket in a node.

      * *name*: identifier for the socket
      * *task_ids*, *owners*: identifiers for the tasks and components that
        are currently using the socket.
      * *allocated*, *available*: lists of cores that are allocated
        and available.
      * *cores*: list of :py:class:`.Core` objects belonging to this socket
      * *avail_cores*: number of cores that are currently available.
      * *total_cores*: total number of cores that can be allocated on this
        socket.
    """

    def __init__(self, name, cps, coreids=[]):
        """
        s = number of sockets (per node)
        c = number of cores (per node)
        """
        self.name = name
        self.task_ids = []
        self.owners = []
        self.allocated = []
        self.available = []
        self.cores = []
        self.avail_cores = cps
        self.total_cores = cps
        self.my_tasks = {}  # tid: (owner, cores, num_procs)
        if coreids:
            for c in coreids:
                self.cores.append(Core(c))
                self.available.append(c)
        else:
            for c in range(cps):
                self.cores.append(Core(c))
                self.available.append(c)

    def print_cores(self, fname=''):
        """
        Pretty print of state of cores.
        """
        if fname:
            for c in self.cores:
                print("      core:", c.name, end=' ', file=fname)
                if c.is_available:
                    print(" - available", file=fname)
                else:
                    print(" - task_id:", c.task_id, end=' ', file=fname)
                    print(" - owner:", c.owner, file=fname)
        else:
            for c in self.cores:
                print("      core:", c.name, end=' ')
                if c.is_available:
                    print(" - available")
                else:
                    print(" - task_id:", c.task_id, end=' ')
                    print(" - owner:", c.owner)

    def allocate(self, whole, tid, o, num_procs):
        """
        Mark *num_procs* cores as allocated subject to the value of *whole*.
        Return a list of strings of the form:

          <socket name>:<core name>
        """
        self.task_ids.append(tid)
        self.owners.append(o)
        slots = []
        k = 0

        if whole:
            # fill the whole socket!
            for c1 in self.cores:
                self.available.remove(c1.name)
                slots.append(str(self.name) + ":" +
                             str(c1.allocate(tid, o)))
                self.allocated.append(c1.name)
                k += 1
        else:
            for c1 in self.cores:
                if c1.is_available:
                    self.available.remove(c1.name)
                    slots.append(str(self.name) + ":" +
                                 str(c1.allocate(tid, o)))
                    self.allocated.append(c1.name)
                    k += 1
                if k == num_procs:
                    break
        self.avail_cores -= k
        self.my_tasks.update({tid: (o, k, num_procs)})
        return slots

    def release(self, tid):
        """
        Mark cores that are allocated to task *tid* as available.  Return
        number of cores set to available.
        """
        o, k, _ = self.my_tasks[tid]
        self.task_ids.remove(tid)
        self.owners.remove(o)  # make sure it just removes one instance
        count = 0

        # release cores
        for c in self.cores:
            if c.task_id == tid:
                self.allocated.remove(c.name)
                c.release()
                self.available.append(c.name)
                count += 1
        if count != k:
            print("<<<error>>>")
        # set avail_cores
        self.avail_cores += k
        return count


class Core:
    """
    Models a core of a socket.

      * *name*: name of core
      * *is_available*: boolean value indicating the availability of the core.
      * *task_id*, *owner*: identifiers of the task and component using the core.
    """

    def __init__(self, name):
        self.name = name
        self.is_available = True
        self.task_id = -1
        self.owner = ''

    def allocate(self, tid, o):
        """
        Mark core as allocated.
        """
        if self.is_available:
            self.is_available = False
            self.task_id = tid
            self.owner = o
            return self.name
        else:
            print("trying to allocate core that is not available")
            raise RuntimeError("trying to allocate core that is not available")

    def release(self):
        """
        Mark core as available.
        """
        if self.is_available:
            print("warning: trying to release core when not in use")
        else:
            self.is_available = True
            self.task_id = -1
            self.owner = ''
