import os
import shutil
import time
import glob

def copyFiles(src_dir, src_file_list, target_dir, prefix='', keep_old = False):
    """
       Copy files in *src_file_list* from *src_dir* to *target_dir* with an 
       optional prefix.  If *keep_old* is ``True``, existing files in 
       *target_dir* will not be overridden, otherwise files can be clobbered 
       (default).
       Wild-cards in file name specification are allowed. 
    """
    # copyFiles no longer attempts to make the directory, if this is not done by
    # the runspaceInitComponent, then we can't continue

    #try:
    #    os.makedirs(target_dir)
    #except OSError, (errno, strerror):
    #    if (errno != 17):
    #        print 'Error creating directory %s : %d-%s' % (target_dir, errno, strerror)
    #        raise
    try:
        file_list = src_file_list.split()
    except AttributeError : # srcFileList is not a string
        file_list = src_file_list
    
    globbed_file_list=[]
    for src_file in file_list:
        src_file_full = os.path.join(src_dir, src_file)
        if os.path.isfile(src_file_full):
            globbed_file_list += [src_file_full]
        else:
            globbed_files = glob.glob(src_file_full)
            if (len(globbed_files) > 0):
                globbed_file_list += globbed_files
            else:
                raise Exception('No such file : %s' %(src_file_full))
        
    #------------------------------------------------------------------#
    #  for each file in globbed_file_list, copy it from src_dir to target_dir #
    #------------------------------------------------------------------#
    for src_file in globbed_file_list:
        target = prefix + os.path.basename(src_file)
        target_file = os.path.join(target_dir, target)
        if (os.path.isfile(target_file) and os.path.samefile(src_file, target_file)):
            continue
    # Do not overwrite existing target files.    
        if (keep_old and os.path.isfile(target_file)):
            for i in range(1000):
                new_name = target_file + '.' + str(i)
                if  os.path.isfile(new_name):
                    continue
                target_file = new_name
                break

        try:
            shutil.copy(src_file, target_file)
        except:
            raise

def writeToContainer(ziphandle, src_dir, src_file_list):
  """
  Write files to the ziphandle.  Because when one wants to unzip the
  file, one typically doesn't want the full path, this handles getting
  just the shorter path name.  
  src_file_list can be a single string
  If src_dir is specified:
     relative 
  If it is not specified:
     relative 
  filename in the zip file.
  """
  try:
      file_list = src_file_list.split()
  except AttributeError : # srcFileList is not a string
      file_list = src_file_list

  # The logic for directories in the current directory follows that of
  # not specifying a src directory at all
  if src_dir==".": src_dir=""

  curdir=os.path.curdir
  if src_dir:
    for file in file_list:
      sfile=os.path.join(src_dir,file)
      if os.path.exists(sfile):
        shutil.copy(sfile, file)
        ziphandle.write(file)
        os.remove(file)
      else:
        raise Exception('No such file : %s in directory %s', file, src_dir)
  else:
    for file in file_list:
      if os.path.exists(file):
        # If it is a full path, copy it locally, write to zip, remove
        if os.path.dirname(file):
          absfile=os.path.abspath(file)
          (sdir, sfile) = os.path.split(absfile)
          shutil.copy(absfile, sfile)
          ziphandle.write(sfile)
          os.remove(sfile)
        else:
          ziphandle.write(file)
      else:
        raise Exception('No such file : %s', file)

def getTimeString(timeArg=None):
    """
    Return a string representation of *timeArg*. *timeArg* is expected
    to be an appropriate object to be processed by :py:meth:`time.strftime`.
    If *timeArg* is ``None``, current time is used.
    """
    if timeArg == None:
        arg = time.localtime()
    else:
        arg = timeArg
    return time.strftime('%Y-%m-%d|%H:%M:%S%Z', arg)