# -------------------------------------------------------------------------------
# Copyright 2006-2021 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import os
import sys
import select
import time
from multiprocessing.connection import Listener
from .component import Component
from .configobj import ConfigObj


class Driver(Component):

    def __init__(self, services, config):
        Component.__init__(self, services, config)
        self.done = False
        self.events_received = []
        self.socket_address = ''
        self.log_file = None
        self.config_file = None
        self.debug = None
        self.old_master_conf = None
        self.sim_root = None
        self.sim_name = None
        self.sim_logfile = None
        self.in_file = None
        self.out_file = None
        self.idle_timeout = 300

    def init(self, timestamp=0, **keywords):
        self.services.subscribe('_IPS_DYNAMIC_SIMULATION', "process_event")

    def step(self, timestamp=0, **keywords):

        services = self.services
        sim_root = services.get_config_param('SIM_ROOT')
        sim_name = services.get_config_param('SIM_NAME')
        self.socket_address = os.environ['IPS_DAKOTA_SOCKET_ADDRESS']
        self.config_file = os.environ['IPS_DAKOTA_config']

        override = {}
        """
        Master Config file
        """
        # parse file
        try:
            self.old_master_conf = ConfigObj(self.config_file, interpolation='template', file_error=True)
        except (IOError, SyntaxError):
            raise
        self.sim_root = services.get_config_param('SIM_ROOT')
        self.sim_name = services.get_config_param('SIM_NAME')
        self.sim_logfile = services.get_config_param('LOG_FILE')
        dakota_runid = os.environ['IPS_DAKOTA_runid']

        sim_config_files = []
        idx = 0
        print('%s  About to Create Listener %s' % (
            time.strftime("%b %d %Y %H:%M:%S", time.localtime()), str(self.socket_address)))
        sys.stdout.flush()
        listener = Listener(str(self.socket_address), 'AF_UNIX')
        self.services.warning('Created listener %s', str(self.socket_address))
        print('%s  Created Listener %s' % (
            time.strftime("%b %d %Y %H:%M:%S", time.localtime()), str(self.socket_address)))
        sys.stdout.flush()
        sim_cache = {}
        sock_fileno = listener._listener._socket.fileno()
        time_out = 0.5
        # last_conn_time = -1
        last_simend_time = time.time()
        first_sim = True

        summary_file = None
        failed_connections = 0
        while True:
            (ready_r, _, _) = select.select([sock_fileno], [], [], time_out)
            self.events_received = []
            self.services.process_events()
            for event in self.events_received:
                event_type = event['eventtype']
                sim_name = event['SIM_NAME']
                ok = event['ok']
                if event_type == 'IPS_END':
                    try:
                        (sim_root, conn) = sim_cache[sim_name]
                    except KeyError:
                        pass
                    else:
                        last_simend_time = time.time()
                        if not ok:
                            open(os.path.join(sim_root, 'RESULT'), 'w').write('FAIL')
                        conn.send(os.path.join(sim_root, 'RESULT'))
                        conn.close()
                        del sim_cache[sim_name]
            if not ready_r:
                if sim_cache:
                    continue
                if time.time() - last_simend_time > self.idle_timeout:
                    break
                else:
                    continue

            conn = listener.accept()

            try:
                msg = conn.recv()
            except Exception as inst:
                print('%s EXCEPTION in conn.recv(): failed connections = ' % (
                    time.strftime("%b %d %Y %H:%M:%S", time.localtime())), type(inst), str(inst))
                if failed_connections > 5:
                    raise
                else:
                    failed_connections += 1
                    continue
            try:
                status = msg['SIMSTATUS']
            except KeyError:
                pass
            except TypeError:
                pass
            else:
                response = {'SIMSTATUS': 'ACK'}
                conn.send(response)
                conn.close()
                if status == 'START':
                    continue
                else:
                    print('%s ' % (time.strftime("%b %d %Y %H:%M:%S", time.localtime())), end=' ')
                    print('Received status = ' + status + ', returning from dakota_bridge.')
                    break
            instance_id = '%s_%04d' % (dakota_runid, idx)
            file_name = os.path.join(self.sim_root, 'simulation_%s.conf' % (instance_id))

            self.old_master_conf.filename = file_name
            self.old_master_conf['SIM_ROOT'] = os.path.join(self.sim_root, 'simulation_%s' % (instance_id))
            self.old_master_conf['SIM_NAME'] = self.sim_name + '_%s' % (instance_id)
            self.old_master_conf['LOG_FILE'] = self.sim_logfile + '_%s' % (instance_id)
            self.old_master_conf['OUT_REDIRECT'] = 'TRUE'
            fname = "%s.out" % (self.old_master_conf['SIM_NAME'])
            fname = os.path.join(self.sim_root, fname)
            self.old_master_conf['OUT_REDIRECT_FNAME'] = fname
            print('Redirecting stdout for %s to %s ' % (self.old_master_conf['SIM_NAME'], fname))
            try:
                os.makedirs(self.old_master_conf['SIM_ROOT'], exist_ok=True)
            except OSError as oserr:
                print('Error creating Simulation directory %s : %d %s' %
                      (self.old_master_conf['SIM_ROOT'], oserr.errno, oserr.strerror))
                raise
            if first_sim:
                summary_file = open(os.path.join(self.sim_root, 'SIMULATION_LIST.%s' % (dakota_runid)), 'a', 1)

            param_file = os.path.join(self.old_master_conf['SIM_ROOT'], 'parameters.conf')
            param_string = ''
            summary_string = 'simulation_%s    ' % (instance_id)
            title_string = 'SIMULATION    '
            for (comp, param, val) in msg:
                if comp == '*':
                    self.old_master_conf[param] = val
                else:
                    comp_conf = self.old_master_conf[comp]
                    comp_conf[param] = val
                param_string += '%s  %s  %s\n' % (comp, param, val)
                title_string += '%s:%s    ' % (comp, param)
                summary_string += '%s    ' % (val)
            if first_sim:
                summary_file.write("%s\n" % (title_string))
                first_sim = False
            summary_file.write('%s\n' % (summary_string))
            summary_file.flush()
            self.old_master_conf.write()
            open(param_file, 'w').write(param_string)
            sim_config_files.append(file_name)
            sim_cache[self.old_master_conf['SIM_NAME']] = (self.old_master_conf['SIM_ROOT'], conn)
            self.services.create_simulation(file_name, override)
            idx += 1

        listener.close()
        if summary_file is not None:
            summary_file.close()

    def finalize(self, timestamp=0, **keywords):
        # Driver finalize - nothing to be done
        pass

    def process_event(self, topicName, theEvent):
        event_body = theEvent.getBody()
        self.events_received.append(event_body)
        self.services.debug('In Component: Just received %s', str(event_body))
        self.services.debug('In Component: There are %d events in self.events_received', len(self.events_received))
