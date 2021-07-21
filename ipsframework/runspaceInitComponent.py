# -------------------------------------------------------------------------------
# Copyright 2006-2021 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import os
from ipsframework import Component
from ipsframework import ipsutil


def catch_and_go(func_to_decorate):
    def new_func(*original_args, **original_kwargs):
        # Do whatever else you want here
        obj = original_args[0]
        try:
            func_to_decorate(*original_args, **original_kwargs)
        except Exception as e:
            obj.services.exception("Exception in call to %s:%s" % (obj.__class__.__name__, func_to_decorate.__name__))
            print(e)
    return new_func


class runspaceInitComponent(Component):
    """
    Framework component to manage runspace initialization, container file
    management, and file staging for simulation and analysis runs.
    """

    def __init__(self, services, config):
        """
        Declaration of private variables and initialization of
        :py:class:`component.Component` object.
        """
        Component.__init__(self, services, config)
        # get the simRootDir
        self.simRootDir = services.get_config_param('SIM_ROOT')
        self.cwd = self.config['OS_CWD']

    @catch_and_go
    def init(self, timestamp=0.0, **keywords):
        """
        Creates base directory, copies IPS and FacetsComposer input files.
        """

        services = self.services

        try:
            os.chdir(self.cwd)
        except OSError:
            self.services.debug('Working directory %s does not exist - this is impossibile',
                                self.cwd)
            raise

        if not self.simRootDir.startswith("/"):
            self.simRootDir = os.path.join(self.cwd, self.simRootDir)

        # try making the simulation root directory
        try:
            os.makedirs(self.simRootDir, exist_ok=True)
        except OSError as oserr:
            self.services.exception('Error creating directory %s : %s',
                                    self.simRootDir, oserr.strerror)

        self.config_files = services.fwk.config_file_list
        self.platform_file = services.fwk.platform_file_name
        self.main_log_file = services.get_config_param('LOG_FILE')

        # Determine where the file is...if there's not an absolute path specified,
        # assume that it was in the directory that the IPS was launched from.
        # NOTE: This is not necessarily where the IPS is installed.
        if not self.config_files[0].startswith("/"):
            self.conf_file_loc = self.cwd
        else:
            (head, _) = os.path.split(os.path.abspath(self.config_files[0]))
            self.conf_file_loc = head
        if not self.platform_file.startswith("/"):
            self.plat_file_loc = self.cwd
        else:
            (head, _) = os.path.split(os.path.abspath(self.platform_file))
            self.plat_file_loc = head

        ipsutil.copyFiles(self.conf_file_loc, self.config_files, self.simRootDir)
        ipsutil.copyFiles(self.plat_file_loc, self.platform_file, self.simRootDir)

    @catch_and_go
    def step(self, timestamp=0.0, **keywords):
        """
        Copies individual subcomponent input files into working subdirectories.
        """

        services = self.services

        # sim_comps = services.fwk.config_manager.get_component_map()
        sim_comps = services.fwk.config_manager.get_all_simulation_components_map()
        registry = services.fwk.comp_registry

        simulation_setup = os.path.join(self.simRootDir, 'simulation_setup')

        # make the simulation_setup directory for scripts
        try:
            os.makedirs(simulation_setup, exist_ok=True)
        except OSError as oserr:
            self.services.exception('Error creating directory %s : %s',
                                    simulation_setup, oserr.strerror)

        # for each simulation component
        for comp_list in sim_comps.values():
            # for each component_id in the list of components
            for comp_id in comp_list:
                # build the work directory name
                comp_conf = registry.getEntry(comp_id).component_ref.config
                full_comp_id = '_'.join([comp_conf['CLASS'], comp_conf['SUB_CLASS'],
                                         comp_conf['NAME'],
                                         str(comp_id.get_seq_num())])

                # compose the workdir name
                workdir = os.path.join(self.simRootDir, 'work', full_comp_id)

                # make the working directory
                try:
                    os.makedirs(workdir, exist_ok=True)
                except OSError as oserr:
                    self.services.exception('Error creating directory %s : %s',
                                            workdir, oserr.strerror)
                    raise

                # copy the input files into the working directory
                try:
                    ipsutil.copyFiles(os.path.abspath(comp_conf['INPUT_DIR']),
                                      comp_conf['INPUT_FILES'],
                                      workdir)
                except Exception:
                    print('Error copying input files for initialization')
                    raise

                # This is a bit tricky because we want to look either in the same
                # place as the input files or the data_tree root
                if 'DATA_FILES' in comp_conf:
                    filesCopied = False
                    if 'DATA_TREE_ROOT' in comp_conf:
                        dtrdir = os.path.abspath(comp_conf['DATA_TREE_ROOT'])
                        if os.path.exists(os.path.join(dtrdir, comp_conf['DATA_FILES'][0])):
                            ipsutil.copyFiles(dtrdir, os.path.basename(comp_conf['DATA_FILES']),
                                              workdir)
                            filesCopied = True
                    if not filesCopied:
                        ipsutil.copyFiles(os.path.abspath(comp_conf['INPUT_DIR']),
                                          os.path.basename(comp_conf['DATA_FILES']),
                                          workdir)

                # copy the component's script to the simulation_setup directory
                if comp_conf['SCRIPT']:
                    if os.path.isabs(comp_conf['SCRIPT']):
                        ipsutil.copyFiles(os.path.dirname(comp_conf['SCRIPT']),
                                          [os.path.basename(comp_conf['SCRIPT'])],
                                          simulation_setup)
                    else:
                        ipsutil.copyFiles(comp_conf['BIN_DIR'],
                                          [os.path.basename(comp_conf['SCRIPT'])],
                                          simulation_setup)

            # get the working directory from the runspaceInitComponent
            workdir = services.get_working_dir()

            # create the working directory for this component
            try:
                os.makedirs(workdir, exist_ok=True)
            except OSError as oserr:
                self.services.exception('Error creating directory %s : %s',
                                        workdir, oserr.strerror)
                raise
