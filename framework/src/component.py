#-------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
#-------------------------------------------------------------------------------
from messages import Message, MethodResultMessage
import sys
import os
import ipsTiming
import weakref

try:
    if os.environ['IPS_TIMING'] == '1':
        try:
            import pytau
        except:
            raise
        IPS_TIMING = True
except KeyError:
    pass

class Component(object):
    """
    Base class for all IPS components.  Common set up, connection and
    invocation actions are implemented here.
    """
    def __init__(self, services, config):
        """
        Set up config values and reference to services.
        """
        #pytau.setNode(1)
        #timer = pytau.profileTimer("component.__init__", "", str(os.getpid()))
        #pytau.start(timer)
        self.component_id = None
        self.invocation_q = None
        self.services = weakref.proxy(services)
        self.config = config
        self.start_time=0.0
        self.sys_exit = None
        for i in list(config.keys()):
            try:
                setattr(self, i, config[i])
            except Exception as e:
                print('Error setting Component parameter : ', i, ' - ', e)
                #pytau.stop(timer)
                raise

        #pytau.stop(timer)

    def __initialize__(self, component_id, invocation_q, start_time=0.0):
        """
        Establish connection to *invocation_q*.
        """
        #timer = pytau.profileTimer("component.__initialize__", "", str(os.getpid()))
        #pytau.start(timer)
        self.component_id = component_id
        self.invocation_q = invocation_q
        self.start_time = start_time
#        setattr(sys, 'exit', sys.exit)

        #pytau.stop(timer)
        return

    def __my_exit__(self, arg=0):
        """
        Produce message and exception about exit.
        """
        self.services.error('Called sys.exit() from component code')
        raise Exception('Called sys.exit() from component code')

    def __run__(self):
        """
        Set (and possibly create) the working directory for the component
        and change the working directory to the (possibly newly created)
        directory.
        Wait for incoming commands delivered via the *invocation_q*, and
        dispatch the incoming methods accordingly.
        """
        #timer = pytau.profileTimer(self.component_id.__str__() + ".__run__", "", str(os.getpid()))
        #pytau.start(timer)
        tmp = sys.exit
        sys.exit = self.__my_exit__
        self.sys_exit = tmp
        try:
            redirect = self.services.sim_conf['OUT_REDIRECT']
        except KeyError:
            pass
        else:
            if str(redirect).strip() !='':
                if ('OUT_REDIRECT_FNAME') not in list(self.services.sim_conf.keys()):
                    fname = "%s.out" %(self.services.sim_conf['SIM_NAME'])
                    fname = os.path.join(self.services.sim_conf['PWD'], fname)
                    print('Redirecting stdout to ', fname)
                else:
                    fname = self.services.sim_conf['OUT_REDIRECT_FNAME']
                original_stdout_fd = sys.stdout.fileno()
                original_sterr_fd = sys.stderr.fileno()
                saved_stdout_fd = os.dup(original_stdout_fd)
                saved_stderr_fd = os.dup(original_sterr_fd)
                outf = open(fname, "a")
                outf_fno = outf.fileno()
                #sys.stdout.close()
                os.dup2(outf_fno, original_stdout_fd)
                os.dup2(outf_fno, original_sterr_fd)
                sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
                sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', 0)

        # SIMYAN: reversed changes that took directory creation in work out of
        # a component's hands. Now this class creates the directory and changes
        # into it as before.
        workdir = self.services.get_working_dir()

        try:
            os.chdir(workdir)
        except OSError :
            self.services.debug('Working directory %s does not exist - will attempt creation',
                                workdir)
            try:
                os.makedirs(workdir)
            except OSError as oserr:
                (errno, strerror) = oserr.args
                self.services.exception('Error creating directory %s : %s' ,
                                        workdir, strerror)
                #pytau.stop(timer)
                raise
            os.chdir(workdir)
        self.services.debug('Running - CompID =  %s',
                            self.component_id.get_serialization())

        if (self.services.profile):
            self.services.debug('Instrumenting - CompID =  %s',
                            self.component_id.get_serialization())
            pytau.setNode(int(self.component_id.get_seq_num()))
            pytau.dbPurge()
            self.services._make_timers()
        self.services._init_event_service()

        while True :
            msg = self.invocation_q.get()
            self.services.log('Received Message ')
            sender_id = msg.sender_id
            call_id = msg.call_id
            method_name = msg.target_method
            args = msg.args
            keywords = msg.keywords
            formatted_args = ['%.3f' % (x) if isinstance(x, float)
                              else str(x) for x in args]
            if keywords:
                formatted_args += [" %s=" % k + str(v) for (k, v) in keywords.items()]

            self.services.debug('Calling method ' + method_name +
                                "(" + ' ,'.join(formatted_args) + ")")
            try:
                method = getattr(self, method_name)
                retval = method(*args, **keywords)
            except Exception as e:
                self.services.exception('Uncaught Exception in component method.')
                response_msg = MethodResultMessage(self.component_id,
                                                 sender_id,
                                                 call_id,
                                                 Message.FAILURE, e)
            else:
                response_msg = MethodResultMessage(self.component_id,
                                                 sender_id,
                                                 call_id,
                                                 Message.SUCCESS, retval)
            self.services.fwk_in_q.put(response_msg)
        #pytau.stop(timer)

    def init(self, timestamp=0.0, **keywords):
        """
        Produce some default debugging information before the rest of the code
        is executed.
        """
        self.services.debug('init() method called')
        pass

    # SIMYAN: This is the step method that is used for run-setup
    def setup(self, timestamp=0.0, **keywords):
        """
        Produce some default debugging information before the rest of the code
        is executed.
        """
        self.services.debug('setup() method called')
        pass

    # SIMYAN: this is a placeholder for future validation methods (i.e.
    # checking data)
    def validate(self, timestamp=0.0, **keywords):
        """
        Produce some default debugging information before the rest of the code
        is executed.
        """
        self.services.debug('validate() method called')
        pass

    def restart(self, timestamp=0.0, **keywords):
        """
        Produce some default debugging information before the rest of the code
        is executed.
        """
        self.services.debug('restart() method called')
        pass

    def step(self, timestamp=0.0, **keywords):
        """
        Produce some default debugging information before the rest of the code
        is executed.
        """
        self.services.debug('step() method called')
        pass

    def finalize(self, timestamp=0.0, **keywords):
        """
        Produce some default debugging information before the rest of the code
        is executed.
        """
        self.services.debug('finalize() method called')
        pass

    def checkpoint(self, timestamp=0.0, **keywords):
        """
        Produce some default debugging information before the rest of the code
        is executed.
        """
        self.services.debug('checkpoint() method called')
        pass

    def terminate(self, status):
        """
        Clean up services and call :py:obj:`sys_exit`.
        """
        #print self.services.full_comp_id, ": terminate() method called"
        self.services._cleanup()
#        self.services.debug('###(1) %s %s', str(self), str(self.__dict__))

        if (status == Message.SUCCESS):
            self.services.debug('Calling self.sys_exit(0)')
            self.sys_exit(0)
        else:
            self.services.debug('Calling self.sys_exit(1)')
            self.sys_exit(1)
