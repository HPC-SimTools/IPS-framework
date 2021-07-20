#! /usr/bin/env python
# -------------------------------------------------------------------------------
# Copyright 2006-2021 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------

import os
import sys
import getopt
import inspect
import subprocess
import tempfile
import re
import time
from multiprocessing.connection import Client
from ipsframework.configobj import ConfigObj
from ipsframework import platformspec
from ipsframework.ipsutil import which


class DakotaDynamic:
    def __init__(self, dakota_cfg, log_file, platform_filename, debug, ips_config_template, restart_file):
        self.dakota_cfg = dakota_cfg
        self.log_file = log_file
        self.platform_fname = platform_filename
        self.debug = debug
        self.config_template = ips_config_template
        self.template_conf = None
        self.platform_conf = None
        self.dakota_conf = None
        self.master_conf = ConfigObj()
        self.restart_file = restart_file

    def run(self):  # noqa: C901
        alt_paths = []

        """
        Dakota Configuration
        Control variables expected in the format COMPONENT__VARIABLE (two _)
        """
        try:
            self.dakota_conf = [t.strip() for t in open(self.dakota_cfg).readlines()]
        except Exception:
            raise

        """
        Platform Configuration
        """
        # parse file
        try:
            current_dir = inspect.getfile(inspect.currentframe())
            (self.platform_fname, self.ipsShareDir) = \
                platformspec.get_share_and_platform(self.platform_fname,
                                                    current_dir)

            if self.ipsShareDir:
                haveComp = False
                if os.path.exists(os.path.join(self.ipsShareDir, 'component-generic.conf')):
                    comp_conf_file = os.path.join(self.ipsShareDir, 'component-generic.conf')
                    comp_confgobj = ConfigObj(comp_conf_file, interpolation='template',
                                              file_error=True)
                    haveComp = True

                self.platform_conf = ConfigObj(self.platform_fname, interpolation='template',
                                               file_error=True)
                if haveComp:
                    self.platform_conf.merge(comp_confgobj)
            else:
                self.platform_conf = ConfigObj(self.platform_fname, interpolation='template',
                                               file_error=True)

        except (IOError, SyntaxError):
            raise

        """
        Master Config file
        """
        # parse file
        try:
            self.template_conf = ConfigObj(self.config_template, interpolation='template', file_error=True)
        except (IOError, SyntaxError):
            raise
        for k in list(self.platform_conf.keys()):
            if k not in list(self.template_conf.keys()):
                self.template_conf[k] = self.platform_conf[k]

        # Import environment variables into config file
        # giving precedence to config file definitions in case of duplicates
        for (k, v) in os.environ.items():
            if k not in list(self.template_conf.keys()) and not any(x in v for x in '{}()$'):
                self.template_conf[k] = v

        alt_paths.append(self.template_conf['IPS_ROOT'])
        alt_paths.append(os.path.join(self.template_conf['IPS_ROOT'], 'bin'))
        alt_paths.append(os.path.join(self.template_conf['IPS_ROOT'], 'framework/src'))

        new_dakota_config = self.dakota_cfg + '.resolved'
        comp_vars = {}
        for line in self.dakota_conf:
            if not line:
                continue
            if line[0] == '#':
                continue
            tokens = line.split()
            if tokens[0] == 'descriptors':
                for token in tokens[1:]:
                    raw_token = token.replace("'", '').replace('"', '')
                    try:
                        (comp, var) = raw_token.split('__')
                    except ValueError:
                        print('Error: variable %s not of the form COMP__VARNAME')
                        raise
                    comp_vars[comp] = var
            elif tokens[0] == 'analysis_driver':
                raw_prog = line.split('=')[1]
                prog = raw_prog.strip(' "\'')
                exec_prog = which(prog, alt_paths)
                if not exec_prog:
                    raise Exception('Error: analysis driver %s not found in path' % prog)
                line.replace(prog, exec_prog)
            elif tokens[0] == 'system':
                if 'asynchronous' not in line:
                    raise Exception('Asynchronous specification missing from DAKOTA system line in interface section')
                match = re.search(r'evaluation_concurrency\s*=\s*\d*', line)
                if match:
                    conc_tokens = match.group(0).split(' =')
                    self.batch_size = int(conc_tokens[1])
                    print('Using evaluation_concurrency = ', self.batch_size)
                else:
                    print('Missing evaluation_concurrency spec, using default value of %d' % (self.batch_size))

        self.master_conf['PORTS'] = {'NAMES': 'DRIVER'}
        self.master_conf['PORTS']['DRIVER'] = {'IMPLEMENTATION': 'DAKOTA_BRIDGE'}
        self.master_conf['PORTS']['INIT'] = {'IMPLEMENTATION': ''}
        driver_conf = {}
        driver_conf['CLASS'] = 'DAKOTA'
        driver_conf['SUB_CLASS'] = 'BRIDGE'
        driver_conf['NAME'] = 'Driver'
        driver_conf['NPROC'] = 1
        driver_conf['BIN_PATH'] = os.path.join(self.template_conf['IPS_ROOT'], 'bin')
        driver_conf['BIN_DIR'] = driver_conf['BIN_PATH']
        driver_conf['INPUT_DIR'] = '/dev/null'
        driver_conf['INPUT_FILES'] = ''
        driver_conf['OUTPUT_FILES'] = ''
        script = os.path.join(self.template_conf['IPS_ROOT'],
                              'bin', 'dakota_bridge.py')
        if os.path.isfile(script):
            driver_conf['SCRIPT'] = script
        else:
            script = os.path.join(self.template_conf['IPS_ROOT'], 'framework',
                                  'src', 'dakota_bridge.py')
            if os.path.isfile(script):
                driver_conf['SCRIPT'] = script
            else:
                raise Exception('Error: unable to locate dakota_bridge.py in \
IPS_ROOT/bin or IPS_ROOT/framework/src')
        self.master_conf['DAKOTA_BRIDGE'] = driver_conf

        for comp in comp_vars:
            if comp == '':
                continue
            try:
                self.template_conf[comp]
            except KeyError:
                print('Error: missing component %s in IPS configuration file')
                raise

        sim_root = self.template_conf['SIM_ROOT']
        try:
            os.makedirs(sim_root, exist_ok=True)
        except OSError as oserr:
            print('Error creating Simulation directory %s : %d %s' %
                  (sim_root, oserr.errno, oserr.strerror))
            raise

        for (k, v) in self.template_conf.items():
            if k not in list(self.master_conf.keys()):
                try:
                    list(v.keys())
                except Exception:
                    self.master_conf[k] = v

        self.master_conf.filename = os.path.join(sim_root, 'dakota_bridge_%d.conf' % (os.getpid()))
        self.master_conf.write()

        sock_address = os.path.join(tempfile.gettempdir(), 'ips_dynamic_%d.tmp' % (os.getpid()))
        os.environ['IPS_DAKOTA_platform'] = os.path.abspath(self.platform_fname)
        os.environ['IPS_DAKOTA_config'] = os.path.abspath(self.config_template)
        os.environ['IPS_DAKOTA_runid'] = str(os.getpid())
        os.environ['IPS_DAKOTA_SOCKET_ADDRESS'] = sock_address

        with open(new_dakota_config, 'w') as fd:
            for line in self.dakota_conf:
                fd.write('%s\n' % (line))

        ips = which('ips.py', alt_paths)
        if not ips:
            raise Exception('Error: ips not found in path.')

        if self.restart_file:
            if not os.path.isfile(self.restart_file):
                raise Exception("Error accessing DAKOTA restart file %s" % (self.restart_file))

        cmd = '%s --all --simulation=%s --platform=%s --verbose' % (ips, self.master_conf.filename,
                                                                    os.environ['IPS_DAKOTA_platform'])
        if self.log_file:
            cmd += ' --log=' + self.log_file

        if self.debug:
            cmd += '  --debug'

        print('cmd =', cmd)
        ips_server_proc = subprocess.Popen(cmd)
        print('%s  Launched IPS' % (time.strftime("%b %d %Y %H:%M:%S", time.localtime())))
        sys.stdout.flush()
        msg = {'SIMSTATUS': 'START'}
        num_trials = 30
        for trials in range(num_trials):
            try:
                conn = Client(sock_address, 'AF_UNIX')
                conn.send(msg)
                response = conn.recv()
            except Exception as inst:
                print('%s  %d ips_dakota_dynamic connecting to IPS dakota bridge' %
                      (time.strftime("%b %d %Y %H:%M:%S", time.localtime()),
                       trials), type(inst), str(inst))
                sys.stdout.flush()
                if trials == num_trials - 1:
                    ips_server_proc.kill()
                    raise
                else:
                    time.sleep(5)
            else:
                print('%s  ips_dakota_dynamic received response from IPS ' %
                      (time.strftime("%b %d %Y %H:%M:%S", time.localtime())), str(response))
                conn.close()
                break

        if self.restart_file:
            command = "dakota -read_restart %s -input %s" % (self.restart_file, new_dakota_config)
        else:
            command = 'dakota %s ' % new_dakota_config
        dakota_logfile = open('dakota_%s.log' % (str(os.getpid())), 'w')
        proc = subprocess.Popen(command, stdout=dakota_logfile, stderr=subprocess.STDOUT)
        print('%s  Launched DAKOTA' % (time.strftime("%b %d %Y %H:%M:%S", time.localtime())))
        sys.stdout.flush()
        proc.wait()

        msg = {'SIMSTATUS': 'END'}
        num_trials = 1
        for trials in range(num_trials):
            try:
                conn = Client(sock_address, 'AF_UNIX')
                conn.send(msg)
                response = conn.recv()
            except Exception as inst:
                print('%s  %d ips_dakota_dynamic connecting to IPS dakota bridge' %
                      (time.strftime("%b %d %Y %H:%M:%S", time.localtime()), trials), type(inst), str(inst))
                sys.stdout.flush()
                if trials == num_trials - 1:
                    ips_server_proc.kill()
                    raise
                else:
                    time.sleep(5)
            else:
                print('%s  ips_dakota_dynamic received response from IPS ' %
                      (time.strftime("%b %d %Y %H:%M:%S", time.localtime())), str(response))
                conn.close()
                break

        ips_server_proc.wait()


def printUsageMessage():
    print("Usage: ips_dakota_dynamic --dakotaconfig=DAKOTA_CONFIG_FILE --simulation=CONFIG_FILE_NAME "
          "--platform=PLATFORM_FILE_NAME --log=LOG_FILE_NAME --restart=DAKOTA_RESTART_FILE [--debug]")


def main(argv=None):

    ips_config_file = None
    platform_filename = ''
    # parse command line arguments
    if argv is None:
        argv = sys.argv
        first_arg = 1
    else:
        first_arg = 0

    try:
        opts, _ = getopt.gnu_getopt(argv[first_arg:], '',
                                    ["dakotaconfig=", "simulation=", "platform=", "log=", "restart=", "debug"])
    except getopt.error as msg:
        print('Invalid command line arguments', msg)
        printUsageMessage()
        return 1
    debug = False
    log_file_name = None
    dakota_cfg = None
    platform_filename = None
    restart_file = None
    for arg, value in opts:
        if arg == '--simulation':
            ips_config_file = value
        elif arg == '--log':
            log_file_name = value
        elif arg == '--platform':
            platform_filename = value
        elif arg == '--dakotaconfig':
            dakota_cfg = value
        elif arg == '--restart':
            restart_file = value
        elif arg == '--debug':
            debug = True

    if (not ips_config_file or not dakota_cfg):
        printUsageMessage()
        return 1
    try:
        sweep = DakotaDynamic(dakota_cfg, log_file_name, platform_filename, debug, ips_config_file, restart_file)
        sweep.run()
    except Exception:
        raise
    return 0

# ----- end main -----


if __name__ == "__main__":
    sys.stdout.flush()
    sys.exit(main())
