#! /usr/bin/env python

import os
import sys
import getopt
import platform
import inspect
from configobj import ConfigObj
import subprocess
import tempfile
import re
import time
from multiprocessing.connection import Client


def which(program, alt_paths=None):
    def is_exe(fpath):
        return os.path.exists(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

        # Trust locations in platform file over those in environment path
        if alt_paths:
            for path in alt_paths:
                exe_file = os.path.join(path, program)
                if is_exe(exe_file):
                    return exe_file

    return None

#DakotaDynamic(dakota_cfg, meta_config, log_file_name, platform_filename, debug, ips_config_file)

class DakotaDynamic(object):
    def __init__(self, dakota_cfg, log_file, platform_filename, debug, ips_config_template):
        self.dakota_cfg = dakota_cfg
        self.log_file = log_file
        self.platform_fname = platform_filename
        self.debug = debug
        self.config_template = ips_config_template
        self.template_conf = None
        self.platform_conf = None
        self.dakota_conf = None
        self.master_conf = ConfigObj()
        
    def run(self):
        alt_paths = []

        """
        Dakota Configuration
        Control variables expected in the format COMPONENT__VARIABLE (two _)
        """
        try:
            self.dakota_conf=[t.strip() for t in open(self.dakota_cfg).readlines()]
        except:
            raise
        
        """
        Platform Configuration
        """
        # parse file
        try:
            current_dir = inspect.getfile(inspect.currentframe())
            (self.platform_fname, self.ipsShareDir) = \
                                  platform.get_share_and_platform(self.platform_fname,
                                                                  current_dir)

            if self.ipsShareDir:
                if os.path.exists(os.path.join(self.ipsShareDir,'component-generic.conf')):
                    comp_conf_file = os.path.join(self.ipsShareDir,'component-generic.conf')
                    conf_list=[self.platform_fname,comp_conf_file]
                else:
                    conf_list=[self.platform_fname]

                conf_tuple=tuple(conf_list)
                self.platform_conf=ConfigObj(conf_tuple, interpolation='template',
                                     file_error=True)
            else:
                self.platform_conf=ConfigObj(self.platform_fname, interpolation='template',
                                     file_error=True)

            alt_paths.append(self.platform_conf['IPS_ROOT'])
            alt_paths.append(os.path.join(self.platform_conf['IPS_ROOT'],'framework/src'))
        except IOError, (ex):
            raise
        except SyntaxError, (ex):
            raise

        new_dakota_config = self.dakota_cfg+'.resolved'
        comp_vars = {}
#        print self.dakota_conf
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
                        (comp, var ) = raw_token.split('__')
                    except ValueError:
                        print 'Error: variable %s not of the form COMP__VARNAME'
                        raise
                    comp_vars[comp] = var
            elif tokens[0] == 'analysis_driver':
                raw_prog = line.split('=')[1]
                prog = raw_prog.strip(' "\'')
#                print raw_prog, prog
                exec_prog = which(prog, alt_paths)
                if not exec_prog:
                    raise Exception('Error: analysis driver %s not found in path' % prog)
                line.replace(prog, exec_prog)
            elif tokens[0] == 'system':
                if 'asynchronous' not in line:
                    raise Exception('Asynchronous specification missing from DAKOTA system line in interface section')
                match = re.search('evaluation_concurrency\s*=\s*\d*', line)
                if match:
                    conc_tokens = match.group(0).split(' =')
                    self.batch_size = int(conc_tokens[1])
                    print 'Using evaluation_concurrency = ', self.batch_size
                else:
                    print 'Missing evaluation_concurrency spec, using default value of %d' % (self.batch_size)
        

        
        """
        Master Config file
        """
        # parse file
        try:
            self.template_conf=ConfigObj(self.config_template, interpolation='template', file_error=True)
        except IOError, (ex):
            raise
        except SyntaxError, (ex):
            raise
#        for k in self.platform_conf.keys():
#            if k not in self.template_conf.keys():
#                self.template_conf[k] = self.platform_conf[k]
                
        self.master_conf['PORTS'] = {'NAMES' : 'DRIVER'}
        self.master_conf['PORTS']['DRIVER'] = {'IMPLEMENTATION': 'DAKOTA_BRIDGE'}
        self.master_conf['PORTS']['INIT'] = {'IMPLEMENTATION': ''}
        driver_conf = {}
        driver_conf['CLASS'] = 'DAKOTA'
        driver_conf['SUB_CLASS'] = 'BRIDGE'
        driver_conf['NAME'] = 'Driver'
        driver_conf['NPROC'] = 1
        driver_conf['BIN_PATH'] = os.path.join(self.platform_conf['IPS_ROOT'], 'framework', 'src')
        driver_conf['INPUT_DIR'] = '/dev/null'
        driver_conf['INPUT_FILES'] = ''
        driver_conf['OUTPUT_FILES'] = ''
        driver_conf['SCRIPT'] = os.path.join(self.platform_conf['IPS_ROOT'], 'framework', 'src', 'dakota_bridge.py')
        self.master_conf['DAKOTA_BRIDGE'] = driver_conf
        
        for (comp, val) in comp_vars.iteritems():
            try:
                comp_conf = self.template_conf[comp]
            except KeyError:
                print 'Error: missing component %s in IPS configuration file'
                raise

        sim_root = self.template_conf['SIM_ROOT']
        try:
            os.makedirs(sim_root)
        except OSError, (errno, strerror):
            if (errno != 17):
                print 'Error creating Simulation directory %s : %d %s' % \
                        (sim_root, errno, strerror)
                raise
            
        for (k,v) in self.template_conf.iteritems():
            if k not in self.master_conf.keys():
                try:
                    dummy = v.keys()
                except:
                    self.master_conf[k] = v

        self.master_conf.filename = os.path.join(sim_root, 'dakota_bridge_%d.conf' % (os.getpid()))
        self.master_conf.write()
                
        
        sock_address = os.path.join(tempfile.gettempdir(), 'ips_dynamic_%d.tmp' %(os.getpid()))
        os.environ['IPS_DAKOTA_platform'] = os.path.abspath(self.platform_fname)
        os.environ['IPS_DAKOTA_config'] = os.path.abspath(self.config_template)
        os.environ['IPS_DAKOTA_runid'] = str(os.getpid())
        os.environ['IPS_DAKOTA_SOCKET_ADDRESS'] = sock_address
        print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%', sock_address
        
        fd = open(new_dakota_config, 'w')
        [fd.write('%s\n'%(l)) for l in self.dakota_conf]
        fd.close()
        
        ips = which('ips.py', alt_paths)
        if (not ips):
            raise Exception('Error: ips not found in path.')
        
        cmd = '%s --all --simulation=%s --platform=%s --verbose' % (ips, self.master_conf.filename, 
                                                 os.environ['IPS_DAKOTA_platform'])
        if (self.log_file):
            cmd += ' --log=' + self.log_file
        
        if self.debug:
            cmd += '  --debug'
        
        ips_server_proc = subprocess.Popen(cmd, shell = True)
        print '%s  Launched IPS' % (time.strftime("%b %d %Y %H:%M:%S", time.localtime()))
        sys.stdout.flush()
        msg = {'SIMSTATUS':'START'}
        num_trials = 30
        for trials in range(num_trials):
            try:
                conn = Client(sock_address, 'AF_UNIX')
                conn.send(msg)
                response = conn.recv()
            except Exception as inst:
                print '%s  %d ips_dakota_dynamic connecting to IPS dakota bridge' % \
                    (time.strftime("%b %d %Y %H:%M:%S", time.localtime()), 
                     trials), type(inst), str(inst)
                sys.stdout.flush()
                if (trials == num_trials - 1):
                    ips_server_proc.kill()
                    raise
                else:
                    time.sleep(5)
            else:
                print '%s  ips_dakota_dynamic received response from IPS ' % \
                       (time.strftime("%b %d %Y %H:%M:%S", time.localtime())), str(response)
                conn.close()  
                break
 
        command = 'dakota %s ' % new_dakota_config
        dakota_logfile = open('dakota_%s.log' % (str(os.getpid())),'w')
        proc = subprocess.Popen(command, shell=True, stdout=dakota_logfile, stderr=subprocess.STDOUT)
        print '%s  Launched DAKOTA' % (time.strftime("%b %d %Y %H:%M:%S", time.localtime()))
        sys.stdout.flush()
        proc.wait()
        
        msg = {'SIMSTATUS':'END'}
        num_trials = 1
        for trials in range(num_trials):
            try:
                conn = Client(sock_address, 'AF_UNIX')
                conn.send(msg)
                response = conn.recv()
            except Exception as inst:
                print '%s  %d ips_dakota_dynamic connecting to IPS dakota bridge' % \
                    (time.strftime("%b %d %Y %H:%M:%S", time.localtime()), trials), type(inst), str(inst)
                sys.stdout.flush()
                if (trials == num_trials - 1):
                    ips_server_proc.kill()
                    raise
                else:
                    time.sleep(5)
            else:
                print '%s  ips_dakota_dynamic received response from IPS ' % \
                       (time.strftime("%b %d %Y %H:%M:%S", time.localtime())), str(response)
                conn.close()  
                break
 
        ips_server_proc.wait()
        return 
        
def printUsageMessage():
    print 'Usage: ips_dakota_dynamic --dakotaconfig=DAKOTA_CONFIG_FILE --simulation=CONFIG_FILE_NAME --platform=PLATFORM_FILE_NAME --log=LOG_FILE_NAME [--debug]'

def main(argv=None):
#    print "hello from main"

    ips_config_file = None
    platform_filename = ''
    log_file = sys.stdout
    # parse command line arguments
    if argv is None:
        argv = sys.argv
        first_arg = 1
    else:
        first_arg = 0

    try:
        opts, args = getopt.gnu_getopt(argv[first_arg:], '',
                                       ["dakotaconfig=", "simulation=", "platform=", "log=", "debug"])
    except getopt.error, msg:
        print 'Invalid command line arguments', msg
        printUsageMessage()
        return 1
    debug = False
    log_file_name = None
    dakota_cfg = None
    platform_filename = None
    for arg, value in opts:
        if (arg == '--simulation'):
            ips_config_file =value
        elif (arg == '--log'):
            log_file_name = value
        elif (arg == '--platform'):
            platform_filename = value
        elif (arg == '--dakotaconfig'):
            dakota_cfg = value
        elif (arg == '--debug'):
            debug = True


    if (not ips_config_file or not dakota_cfg):
        printUsageMessage()
        return 1
    try:
        sweep = DakotaDynamic(dakota_cfg, log_file_name, platform_filename, debug, ips_config_file)
        sweep.run()
    except :
        raise 
    return 0

# ----- end main -----

if __name__ == "__main__":
    sys.stdout.flush()
    sys.exit(main())
