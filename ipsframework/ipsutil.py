# -------------------------------------------------------------------------------
# Copyright 2006-2021 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import os
import shutil
import time
import glob
try:
    import Pyro4
except ImportError:
    pass

remote_copy_fun = None


def which(program, alt_paths=None):
    def is_exe(fpath):
        return os.path.exists(fpath) and os.access(fpath, os.X_OK)

    fpath, _ = os.path.split(program)
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


def copyFiles(src_dir, src_file_list, target_dir, prefix='', keep_old=False):
    """
       Copy files in *src_file_list* from *src_dir* to *target_dir* with an
       optional prefix.  If *keep_old* is ``True``, existing files in
       *target_dir* will not be overridden, otherwise files can be clobbered
       (default).
       Wild-cards in file name specification are allowed.
    """

    global remote_copy_fun
    use_data_server = os.getenv('USE_DATA_SERVER', "DATA_SERVER_NOT_USED")
    if use_data_server != "DATA_SERVER_NOT_USED":
        if not remote_copy_fun:
            data_server = Pyro4.Proxy("PYRONAME:DataServer")
        data_server.copyFiles(src_dir, src_file_list, target_dir, prefix, keep_old)
        return

    try:
        file_list = src_file_list.split()
    except AttributeError:  # srcFileList is not a string
        file_list = src_file_list

    globbed_file_list = []
    for src_file in file_list:

        if not target_dir == src_dir:
            src_file_full = os.path.join(src_dir, src_file)

            if os.path.isfile(src_file_full):
                globbed_file_list += [src_file_full]
            else:
                globbed_files = glob.glob(src_file_full)
                if len(globbed_files) > 0:
                    globbed_file_list += globbed_files
                else:
                    raise Exception('No such file : %s' % (src_file_full))

    # ------------------------------------------------------------------#
    #  for each file in globbed_file_list, copy it from src_dir to target_dir #
    # ------------------------------------------------------------------#
    for src_file in globbed_file_list:
        target = prefix + os.path.basename(src_file)
        target_file = os.path.join(target_dir, target)
        if (os.path.isfile(target_file) and os.path.samefile(src_file, target_file)):
            continue
    # Do not overwrite existing target files.
        if (keep_old and os.path.isfile(target_file)):
            for i in range(1000):
                new_name = target_file + '.' + str(i)
                if os.path.isfile(new_name):
                    continue
                target_file = new_name
                break

        (head, _) = os.path.split(os.path.abspath(target_file))
        try:
            os.makedirs(head, exist_ok=True)
        except OSError as oserr:
            print('Error creating directory %s : %s' % (head, oserr.strerror))
            raise
        try:
            shutil.copy(src_file, target_file)
        except Exception:
            raise


def getTimeString(timeArg=None):
    """
    Return a string representation of *timeArg*. *timeArg* is expected
    to be an appropriate object to be processed by :py:meth:`time.strftime`.
    If *timeArg* is ``None``, current time is used.
    """
    if timeArg is None:
        arg = time.localtime()
    else:
        arg = timeArg
    return time.strftime('%Y-%m-%d|%H:%M:%S%Z', arg)
