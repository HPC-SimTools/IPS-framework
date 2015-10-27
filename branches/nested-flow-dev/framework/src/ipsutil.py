#-------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
#-------------------------------------------------------------------------------
import os
import shutil
import time
import glob
import zipfile

def copyFiles(src_dir, src_file_list, target_dir, prefix='', keep_old = False):
    """
       Copy files in *src_file_list* from *src_dir* to *target_dir* with an
       optional prefix.  If *keep_old* is ``True``, existing files in
       *target_dir* will not be overridden, otherwise files can be clobbered
       (default).
       Wild-cards in file name specification are allowed.
    """
    try:
        file_list = src_file_list.split()
    except AttributeError : # srcFileList is not a string
        file_list = src_file_list

    globbed_file_list=[]
    for src_file in file_list:

        if not target_dir == src_dir:
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

        (head, tail) = os.path.split(os.path.abspath(target_file))
        try:
            os.makedirs(head)
        except OSError, (errno, strerror):
            if (errno != 17):
                self.services.exception('Error creating directory %s : %s' ,
                                        head, strerror)
        try:
            #print 'trying to copy...'
            #print 'src_file =', src_file
            #print 'target_file =', target_file
            shutil.copy(src_file, target_file)
        except:
            raise

# SIMYAN: added a utility method to write to the container file
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

    #print 'src_file_list = ', src_file_list
    #print 'ziphandle = ', ziphandle
    #print 'os.path.exists(ziphandle) = ', os.path.exists(ziphandle)
    try:
        if os.path.exists(ziphandle):
            zin = zipfile.ZipFile(ziphandle,'r')
            zout = zipfile.ZipFile('temp.ctz','a')
        else:
            #print 'so it is None'
            zin = None
            zout = zipfile.ZipFile(ziphandle,'a')
    except zipfile.BadZipfile, (ex):
        print 'Found a bad container file, removing...'
        os.remove(ziphandle)
        zin = None
        zout = zipfile.ZipFile(ziphandle,'a')

    curdir=os.path.curdir
    if src_dir:
        for file in file_list:
            sfile=os.path.join(src_dir,file)
            if os.path.exists(sfile):
                #print 'srcdir has'
                #print 'sfile =', sfile
                #print 'file =', file
                (head, tail) = os.path.split(os.path.abspath(file))
                file = tail
                if not os.path.exists(file):
                    shutil.copy(sfile, file)
                    zout.write(file)
                    os.remove(file)
                else:
                    zout.write(file)
            else:
                raise Exception('No such file : %s in directory %s', file, src_dir)
    else:
        for file in file_list:
            if os.path.exists(file):
                # If it is a full path, copy it locally, write to zip, remove
                if os.path.dirname(file):
                    absfile=os.path.abspath(file)
                    (sdir, sfile) = os.path.split(absfile)
                    #print 'srcdir has not'
                    #print 'absfile =', absfile
                    #print 'sfile =', sfile
                    (head, tail) = os.path.split(os.path.abspath(sfile))
                    sfile = tail
                    if not os.path.exists(sfile):
                        shutil.copy(absfile, sfile)
                        zout.write(sfile)
                        os.remove(sfile)
                    else:
                        zout.write(sfile)
                else:
                    zout.write(file)
            else:
                raise Exception('No such file : %s', file)


    #print 'zin is ', zin
    if zin:
        for item in zin.infolist():
            buffer = zin.read(item.filename)
            #print 'item.filename = ', item.filename
            #print 'zout.namelist() = ', zout.namelist()
            #print 'item.filename in zout.namelist() = ', item.filename in zout.namelist()
            if not item.filename in zout.namelist():
                zout.writestr(item, buffer)

        zin.close()
        shutil.move('temp.ctz',ziphandle)

    zout.close()

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