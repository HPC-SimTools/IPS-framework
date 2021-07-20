#! /usr/bin/env python
# -------------------------------------------------------------------------------
# Copyright 2006-2021 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------

import os
import sys
import shutil
import time
from multiprocessing.connection import Client
from ipsframework.configobj import ConfigObj


class IPSDakotaClient:
    def __init__(self, config_file, log_file, platform_filename, debug, in_file, out_file):
        self.config_file = config_file
        self.platform_fname = platform_filename
        self.debug = debug
        self.platform_conf = None
        self.old_master_conf = None
        self.sim_root = None
        self.sim_name = None
        self.sim_logfile = None
        self.in_file = in_file
        self.out_file = out_file

    def run(self):
        """
        Platform Configuration
        """
        # parse file
        try:
            self.platform_conf = ConfigObj(self.platform_fname, interpolation='template',
                                           file_error=True)
        except (IOError, SyntaxError):
            raise
        """
        Master Config file
        """
        # parse file
        try:
            self.old_master_conf = ConfigObj(self.config_file, interpolation='template', file_error=True)
        except (IOError, SyntaxError):
            raise
        # Import environment variables into config file
        # giving precedence to config file definitions in case of duplicates
        for (k, v) in os.environ.items():
            if k not in list(self.old_master_conf.keys()):
                self.old_master_conf[k] = v

        self.sim_root = self.old_master_conf['SIM_ROOT']
        self.sim_name = self.old_master_conf['SIM_NAME']
        self.sim_logfile = self.old_master_conf['LOG_FILE']

        dakota_in_cfg = open(self.in_file).readlines()
        num_variables = int(dakota_in_cfg[0].split()[0])
        parameter_list = []
        for i in range(1, 1 + num_variables):
            val, var_spec = dakota_in_cfg[i].split()
            try:
                comp, var_name = var_spec.split('__')
            except ValueError:
                print('Invalid variable specification %s' % (var_spec))
                raise
            if comp == '':  # This is a global configuration variable
                parameter_list.append(("*", var_name, val))
            else:
                try:
                    comp_conf = self.old_master_conf[comp]
                except KeyError:
                    print('No component %s in IPS configuration file')
                    raise
                comp_conf[var_name] = val
                parameter_list.append((comp, var_name, val))

        for k in list(self.platform_conf.keys()):
            if k not in list(self.old_master_conf.keys()):
                self.old_master_conf[k] = self.platform_conf[k]

        server_address = os.environ['IPS_DAKOTA_SOCKET_ADDRESS']

        num_trials = 10
        for trials in range(num_trials):
            try:
                conn = Client(str(server_address), 'AF_UNIX')
            except Exception:
                print('%s: %d Failed to connect to %s: %s' %
                      (time.strftime("%b %d %Y %H:%M:%S", time.localtime()),
                       trials, server_address, str(sys.argv)))
                sys.stdout.flush()
                if trials == num_trials - 1:
                    raise
                else:
                    time.sleep(trials)
            else:
                break
        sys.stdout.flush()
        conn.send(parameter_list)
        result_file = conn.recv()
        shutil.copy(result_file, self.out_file)


def main(argv=None):
    in_file = argv[1]
    out_file = argv[2]
    debug = False
    log_file_name = None
    try:
        debug = bool(os.environ['IPS_DAKOTA_debug'])
    except KeyError:
        pass
    try:
        log_file_name = os.environ['IPS_DAKOTA_log']
    except KeyError:
        pass
    platform_filename = os.environ['IPS_DAKOTA_platform']
    config_file = os.environ['IPS_DAKOTA_config']

    try:
        ips_executer = IPSDakotaClient(config_file, log_file_name, platform_filename, debug, in_file, out_file)
        ips_executer.run()
    except Exception:
        raise
    return 0


if __name__ == "__main__":
    sys.stdout.flush()
    sys.exit(main(sys.argv))
