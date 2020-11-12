# -------------------------------------------------------------------------------
# Copyright 2006-2020 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import subprocess
cmd = list()
# cmd.append(['aprun', '-n', '16', './parallel_sleep', '10'])
"""
cmd.append(['aprun', '-n', '16', './faulty_parallel_sleep', '10', '0']) # segmentation fault
cmd.append(['aprun', '-n', '16', './faulty_parallel_sleep', '10', '1']) # divide by zero
cmd.append(['aprun', '-n', '16', './faulty_parallel_sleep', '10', '2']) # SIGFPE - floating point error
cmd.append(['aprun', '-n', '16', './faulty_parallel_sleep', '10', '3']) # SIGILL - illegal instruction
cmd.append(['aprun', '-n', '16', './faulty_parallel_sleep', '10', '4']) # SIGSEGV - segmentation fault
cmd.append(['aprun', '-n', '16', './faulty_parallel_sleep', '10', '5']) # SIGBUS - bus error
cmd.append(['aprun', '-n', '16', './faulty_parallel_sleep', '10', '6']) # SIGABRT - self-inflicted abort
cmd.append(['aprun', '-n', '16', './faulty_parallel_sleep', '10', '7']) # SIGHUP - hang up -> loss of network connection
cmd.append(['aprun', '-n', '16', './faulty_parallel_sleep', '10', '8']) # SIGINT - ctrl+c
cmd.append(['aprun', '-n', '16', './faulty_parallel_sleep', '10', '9']) # SIGQUIT - ctrl+\
cmd.append(['aprun', '-n', '16', './faulty_parallel_sleep', '10', '10']) # SIGTERM - ignorable kill
cmd.append(['aprun', '-n', '16', './faulty_parallel_sleep', '10', '11']) # SIGKILL - absolute kill
"""
cmd.append(['aprun', '-n', '16', './faulty_serial_sleep', '10', '0'])  # segmentation fault
cmd.append(['aprun', '-n', '16', './faulty_serial_sleep', '10', '1'])  # divide by zero
cmd.append(['aprun', '-n', '16', './faulty_serial_sleep', '10', '2'])  # SIGFPE - floating point error
cmd.append(['aprun', '-n', '16', './faulty_serial_sleep', '10', '3'])  # SIGILL - illegal instruction
cmd.append(['aprun', '-n', '16', './faulty_serial_sleep', '10', '4'])  # SIGSEGV - segmentation fault
cmd.append(['aprun', '-n', '16', './faulty_serial_sleep', '10', '5'])  # SIGBUS - bus error
cmd.append(['aprun', '-n', '16', './faulty_serial_sleep', '10', '6'])  # SIGABRT - self-inflicted abort
cmd.append(['aprun', '-n', '16', './faulty_serial_sleep', '10', '7'])  # SIGHUP - hang up -> loss of network connection
cmd.append(['aprun', '-n', '16', './faulty_serial_sleep', '10', '8'])  # SIGINT - ctrl+c
cmd.append(['aprun', '-n', '16', './faulty_serial_sleep', '10', '9'])  # SIGQUIT - ctrl+\
cmd.append(['aprun', '-n', '16', './faulty_serial_sleep', '10', '10'])  # SIGTERM - ignorable kill
cmd.append(['aprun', '-n', '16', './faulty_serial_sleep', '10', '11'])  # SIGKILL - absolute kill


for c in cmd:
    p = subprocess.Popen(c)
    p.wait()
    print('retcode from "%s" = %d' % (c, p.returncode))
