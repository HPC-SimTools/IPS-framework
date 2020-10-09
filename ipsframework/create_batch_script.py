#! /usr/bin/env python
# -------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import sys
from .configobj import ConfigObj
import getopt
import os

script_template =\
    """
#! /bin/bash

#PBS -A @ACCOUNT@
#PBS -q @QUEUE@
#PBS -l walltime=@WALLTIME@
#PBS -l mppwidth=@NPROC@
##PBS -l mppnppn=2
#PBS -m e
##PBS -j oe
#PBS -N @SIM_NAME@
#PBS -S /bin/bash

. @IPS_ROOT@/swim.bashrc.@host@

host=@HOST@
now=`date +%Y%m%d_%k%M%S`

fwk_logfile=@SIM_NAME@_${host}_${now}.log

@IPS_PATH@  @CONFIG_FILES@ --platform=@PLATFORM_PATH@ --log=@SIM_ROOT@/${fwk_logfile} @DEBUG@
"""


def printUsageMessage():
    print('Usage: create_batch_script.py --ips=PATH_TO_IPS [--config=CONFIG_FILE_NAME]+ \
--platform=PLATFORM_FILE_NAME [--account=CHRGE_ACCOUNT] [--queue=BATCH_QUEUE] \
[--walltime=ALLOCATION_TIME] [--nproc=NPROCESSES] [--debug] \
[--output=BATCH_SCRIPT]')


def create_script(ips_path, cfgFile_list, platform_file,
                  debug, account='AAAA', queue='QQQQ',
                  nproc='NNNN', walltime='HH:MM:SS', out_file=sys.stdout):
    conf = []
    config_cmd_string = ''
    for cfg_file in cfgFile_list:
        try:
            cfg = ConfigObj(cfg_file, interpolation='template',
                            file_error=True)
        except IOError:
            print('Error opening config file: ', cfg_file)
            raise
        except Exception:
            print('Error parsing config file: ', cfg_file)
            raise
        conf.append(cfg)
        config_cmd_string += '--config=' + cfg_file + ' '
    platform_path = os.path.abspath(platform_file)
    sim_name = conf[0]['SIM_NAME']
    sim_root = conf[0]['SIM_ROOT']

    plat = ConfigObj(platform_path, interpolation='template',
                     file_error=True)
    HOST = plat['HOST']
    try:
        os.makedirs(sim_root)
    except OSError as oserr:
        (errno, strerror) = oserr.args
        if (errno != 17):
            print('Error creating directory ', sim_root)
            raise
    except Exception:
        print('Error creating directory ', sim_root)
        raise

    if (HOST.upper() == 'FRANKLIN'):
        host = 'franklin'
    elif (HOST.upper() == 'JAGUAR'):
        host = 'jaguar'
    elif(HOST.upper() == 'MHD'):
        host = 'viz'
    else:
        host = 'unknown'

    bin_path = os.path.dirname(ips_path)
    ips_root = os.path.split(bin_path)[0]

    script = script_template.replace('@SIM_ROOT@', sim_root).\
        replace('@HOST@', HOST).\
        replace('@SIM_NAME@', sim_name).\
        replace('@IPS_PATH@', ips_path).\
        replace('@CONFIG_FILES@', config_cmd_string).\
        replace('@PLATFORM_PATH@', platform_path).\
        replace('@ACCOUNT@', account).\
        replace('@QUEUE@', queue).\
        replace('@WALLTIME@', walltime).\
        replace('@NPROC@', nproc).\
        replace('@IPS_ROOT@', ips_root).\
        replace('@host@', host)
    debug_string = ''
    if (debug):
        debug_string = '--debug'
    script = script.replace('@DEBUG@', debug_string)

    out_file.write(script)


def main(argv=None):

    cfgFile_list = []
    platform_filename = ''
    # parse command line arguments
    if argv is None:
        argv = sys.argv
        first_arg = 1
    else:
        first_arg = 0

    try:
        opts, args = getopt.gnu_getopt(argv[first_arg:], '',
                                       ["ips=",
                                        "config=",
                                        "platform=",
                                        "debug",
                                        "account=",
                                        "queue=",
                                        "nproc=",
                                        "walltime=",
                                        "output="])
    except getopt.error as msg:
        print('Invalid command line arguments', msg)
        printUsageMessage()
        return 1
    debug = False
    ips_path = ''
    account = 'AAAA'
    queue = 'QQQQ'
    nproc = 'NNNN'
    walltime = 'HH:MM:SS'
    out_file = sys.stdout
    for arg, value in opts:
        if (arg == '--ips'):
            ips_path = value
        if (arg == '--config'):
            cfgFile_list.append(value)
        elif (arg == '--platform'):
            platform_filename = value
        elif (arg == '--debug'):
            debug = True
        elif (arg == '--account'):
            account = value
        elif (arg == '--queue'):
            queue = value
        elif (arg == '--nproc'):
            nproc = value
        elif (arg == '--walltime'):
            walltime = value
        elif (arg == '--output'):
            out_file_name = value
            out_file = open(out_file_name, 'w')

    if (len(cfgFile_list) == 0 or platform_filename == '' or ips_path == ''):
        printUsageMessage()
        return 1

    absCfgFile_list = [os.path.abspath(cfgFile) for cfgFile in cfgFile_list]
    platform_file = os.path.abspath(platform_filename)
    create_script(ips_path,
                  absCfgFile_list,
                  platform_file,
                  debug,
                  account,
                  queue,
                  nproc,
                  walltime,
                  out_file)
    out_file.close()
#    if (out_file != sys.stdout):
#        os.chmod(out_file_name,'+x')

    return 0


if __name__ == "__main__":
    sys.exit(main())
