import os
from configobj import ConfigObj
import ipsutil
import zipfile


def get_status(checklist_file):
  ips_status={}
  ips_status['create_runspace'] = False
  ips_status['run_setup'] = False
  ips_status['run'] = False

  try:
      conf = ConfigObj(checklist_file, interpolation = 'template', file_error = True)
  except IOError, ioe:
      #SEK: Remove because for the create_runspace it is not there?
      #print 'Checklist config file "%s" could not be found, continuing without.' % checklist_file
      return '', ips_status
  except SyntaxError, (ex):
      errmsg='Error parsing config file: '+checklist_file
      return errmsg, ips_status
  except Exception, e:
      print e
      return 'encountered exception during fwk.run() checklist status', ips_status

  try:
    create_runspace_str = conf['CREATE_RUNSPACE']
    if create_runspace_str == 'DONE':
      ips_status['create_runspace'] = True
    elif create_runspace_str == 'NOT_DONE':
      ips_status['create_runspace'] = False
    else:
      errmsg='Invalid value found for CREATE_RUNSPACE in '+checklist_file
      return errmsg, ips_status

    run_setup_str = conf['RUN_SETUP']
    if run_setup_str == 'DONE':
      ips_status['run_setup'] = True
    elif run_setup_str == 'NOT_DONE':
      ips_status['run_setup'] = False
    else:
      errmsg='Invalid value found for RUN_SETUP in '+checklist_file
      return errmsg, ips_status

    run_str = conf['RUN']
    if run_str == 'DONE':
      ips_status['run'] = True
    elif run_str == 'NOT_DONE':
      ips_status['run'] = False
    else:
      errmsg='Invalid value found for RUN in '+checklist_file
      return errmsg, ips_status

  except KeyError, (ex):
      print 'Missing required parameters CREATE_RUNSPACE, RUN_SETUP, or RUN in checklist file '+checklist_file
      print 'Continuing without checklist file due to missing or incorrect parameters'
      ips_status['create_runspace'] = False
      ips_status['run_setup'] = False
      ips_status['run'] = False

  return '', ips_status



def update(checklist_file,containerFilename,ips_status):
  # Make it general to be able to take fullpath or relative path
  checklist_dir=os.path.dirname(os.path.abspath(checklist_file))
  checklist = open(checklist_file, 'w')
  for step in ['create_runspace','run_setup','run']:
    if ips_status[step]:
      step_line=step.upper() + " = DONE\n"
    else:
      step_line=step.upper() + " = NOT_DONE\n"
    checklist.write(step_line)
  checklist.flush()
  checklist.close()

  container = zipfile.ZipFile(containerFilename,'a')
  # SEK: Need to delete the checklist file if it exists.
  ipsutil.writeToContainer(container, "", os.path.abspath(checklist_file))
  container.close()
  return

