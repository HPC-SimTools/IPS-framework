from component import Component
import sys, urllib, os
from subprocess import Popen, PIPE
import uuid, urllib2
import time
import ipsutil
#from event_service_spec import SubscriberEventService, EventListener

class PortalBridge(Component):
    """
    Framework component to communicate with the `SWIM web portal <http://swim.gat.com:8080/monitor/>`_.
    """

    class SimulationData(object):
        """
        Container for simulation data.
        """
        def __init__(self):
            self.counter = 0
            self.monitor_file = None
            self.portal_runid = None
            self.sim_name = ''
            self.sim_root = ''
            self.monitor_file= None
            self.phys_time_stamp = -1
            self.monitor_url = None

    def __init__(self, services, config):
        """
        Declaration of private variables and initialization of 
        :py:class:`component.Component` object.
        """
        Component.__init__(self, services, config)
        self.host = ''
        self.curTime = time.localtime()
        self.startTime = self.curTime
        self.services = services
        self.sim_map = {}
        self.runid_url = None
        self.portal_url = None
        self.done = False
        self.first_event = True
        self.childProcess = None

    def init(self, timestamp=0.0):
        """
        Try to connect to the portal, subscribe to *_IPS_MONITOR* events and 
        register callback :py:meth:`.process_event`.
        """
        try:
            self.portal_url = self.PORTAL_URL
        except AttributeError:
            pass
        try:
            self.runid_url = self.RUNID_URL
        except AttributeError:
            pass
        self.host = self.services.get_config_param('HOST')
        self.services.subscribe('_IPS_MONITOR', "process_event")
        return

    def step(self, timestamp=0.0):
        """
        Poll for events.
        """
        while not self.done:
            self.services.process_events()
            time.sleep(0.5)

    def get_elapsed_time(self):
        """
        Return total elapsed time since simulation started in seconds
        (including a possible fraction)
        """
        self.curTime = time.localtime()
        delta_t = time.mktime(self.curTime) - time.mktime(self.startTime)
        return delta_t

    def process_event(self, topicName, theEvent):
        """
        Process a single event *theEvent* on topic *topicName*.
        """
        event_body = theEvent.getBody()
#        self.services.debug('Processing : %s -- %s ', topicName, str(event_body))
        sim_name = event_body['sim_name']
        portal_data = event_body['portal_data']
        if (portal_data['eventtype'] == 'IPS_START'):
            sim_root = event_body['sim_root']
            self.init_simulation(sim_name, sim_root)

        sim_data = self.sim_map[sim_name]
        if (portal_data['eventtype'] == 'PORTALBRIDGE_UPDATE_TIMESTAMP'):
            sim_data.phys_time_stamp = portal_data['phystimestamp']
            return
        else:
            portal_data['phystimestamp'] = sim_data.phys_time_stamp

        if (portal_data['eventtype'] == 'IPS_SET_MONITOR_URL'):
            sim_data.monitor_url = portal_data['vizurl']
        elif sim_data.monitor_url:
            portal_data['vizurl'] = sim_data.monitor_url

#        portal_data['walltime'] = int(self.get_elapsed_time())
        portal_data['portal_runid'] = sim_data.portal_runid
        portal_data['seqnum'] = sim_data.counter

        self.send_event(sim_data, portal_data)
        sim_data.counter +=  1

        if (portal_data['eventtype'] == 'IPS_END'):
            del self.sim_map[sim_name]

        if (len(self.sim_map) == 0):
            if self.childProcess:
                self.childProcess.stdin.close()
                self.childProcess.wait()
            self.done = True
            self.services.debug('No more simulation to monitor - exiting')
            time.sleep(1)
        return

    def send_event(self, sim_data, event_data):
        """
        Send contents of *event_data* and *sim_data* to portal.
        """
        timestamp = ipsutil.getTimeString()
        buf = '%8d %s ' % (sim_data.counter, timestamp)
        for (k, v) in event_data.iteritems():
            if (len(str(v).strip()) == 0):
                continue
            if (' ' in str(v)):
                buf += '%s=\'%s\' ' %(k, str(v))
            else:
                buf += '%s=%s ' % (k, str(v))
        buf += '\n'
        sim_data.monitor_file.write(buf)
#        self.services.debug('Wrote to monitor file : %s', buf)
        if (self.portal_url):
            webmsg = urllib.urlencode(event_data)
            try:
                if (self.first_event):  #First time, launch sendPost.py daemon
                    cmd = os.path.join(sys.path[0],'sendPost.py')
                    self.childProcess = Popen(cmd, shell=True, bufsize=128,
                                              stdin=PIPE, stdout=PIPE, 
                                              stderr=PIPE, close_fds=True)
                    #self.childProcess = popen2.Popen3(cmd, bufsize=128)
                    self.first_event = False
                self.childProcess.stdin.write('%s %s\n' % \
                                                (self.portal_url, webmsg))
#                self.services.debug('Wrote event to sendPost.py buffer : %s', 
#                                    str(event_data))
                self.childProcess.stdin.flush()
            except Exception , e:
                self.services.exception('Error transmitting event number %6d to %s : %s' , \
                     sim_data.counter, self.portal_url, str(e))
        return

    def init_simulation(self, sim_name, sim_root):
        """
        Create and send information about simulation *sim_name* living in 
        *sim_root* so the portal can set up corresponding structures to manage 
        data from the sim.
        """
        self.services.debug('Initializing simulation : %s -- %s ', sim_name, sim_root)
        sim_data = self.SimulationData()
        sim_data.sim_name = sim_name
        sim_data.sim_root = sim_root

        sim_data.portal_runid = str(uuid.uuid4())
        self.services.debug('PORTAL_RUNID_URL = %s', str(self.runid_url))
        if (self.runid_url != None):
            try:
#               raise urllib2.URLError('TEXT')
                f = urllib2.urlopen(self.runid_url, None, 10)
                sim_data.portal_runid = f.read().strip()
            except (urllib2.URLError), e :
                self.services.error('Error obtaining runID from service at %s : %s' % \
                                    (self.runid_url, str(e)))
                self.services.error('Using a UUID instead')
        try:
            self.services.set_config_param('PORTAL_RUNID', sim_data.portal_runid,
                                       target_sim_name = sim_name)
        except Exception:
            self.services.error('Simulation %s is not accessible', sim_name)
            return

        sim_log_dir = os.path.join(sim_data.sim_root, 'simulation_log')
        try:
            os.makedirs(sim_log_dir)
        except OSError, (errno, strerror):
            if (errno != 17):
                self.services.exception('Error creating Simulation Log directory %s : %d %s' % \
                                    (sim_log_dir, errno, strerror))
                raise

        monitor_filename = os.path.join(sim_log_dir,
                                       sim_data.sim_name + '-' + sim_data.portal_runid + '.eventlog')
        try:
            sim_data.monitor_file = open(monitor_filename, 'w', 0)
        except IOError, (errno, strerror):
            self.services.error("Error opening file %s: error(%s): %s" % \
                    (monitor_filename, errno, strerror))
            self.services.error('Using /dev/null instead')
            sim_data.monitor_file = open('/dev/null', 'w')

        self.sim_map[sim_data.sim_name] = sim_data
        return
