# -------------------------------------------------------------------------------
# Copyright 2006-2022 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import os
from ipsframework import Component
from ipsframework import ipsutil


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
        super().__init__(services, config)
        # get the simRootDir
        self.simRootDir = services.get_config_param('SIM_ROOT')
        self.cwd = self.config['OS_CWD']

    def init(self, timestamp=0.0, **keywords):
        """
        Creates base directory, copies IPS and FacetsComposer input files.
        """

        if not self.simRootDir.startswith("/"):
            self.simRootDir = os.path.join(self.cwd, self.simRootDir)

        config_files = self.services.fwk.config_file_list
        platform_file = self.services.fwk.platform_file_name

        # Determine where the file is...if there's not an absolute path specified,
        # assume that it was in the directory that the IPS was launched from.
        # NOTE: This is not necessarily where the IPS is installed.
        if not config_files[0].startswith("/"):
            conf_file_loc = self.cwd
        else:
            (head, _) = os.path.split(os.path.abspath(config_files[0]))
            conf_file_loc = head
        if not platform_file.startswith("/"):
            plat_file_loc = self.cwd
        else:
            (head, _) = os.path.split(os.path.abspath(platform_file))
            plat_file_loc = head

        ipsutil.copyFiles(conf_file_loc, config_files, self.simRootDir)
        ipsutil.copyFiles(plat_file_loc, platform_file, self.simRootDir)

    def step(self, timestamp=0.0, **keywords):
        """
        Copies individual subcomponent input files into working subdirectories.
        """

        sim_comps = self.services.fwk.config_manager.get_all_simulation_components_map()
        sim_roots = self.services.fwk.config_manager.get_all_simulation_sim_root()
        registry = self.services.fwk.comp_registry

        simulation_setup = os.path.join(self.simRootDir, 'simulation_setup')

        # for each simulation component
        for name, comp_list in sim_comps.items():
            # for each component_id in the list of components
            for comp_id in comp_list:
                # build the work directory name
                comp_conf = registry.getEntry(comp_id).component_ref.config
                full_comp_id = '_'.join([comp_conf['CLASS'], comp_conf['SUB_CLASS'],
                                         comp_conf['NAME'],
                                         str(comp_id.get_seq_num())])

                # compose the workdir name
                workdir = os.path.join(sim_roots[name], 'work', full_comp_id)

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
