#-------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
#-------------------------------------------------------------------------------
from configobj import ConfigObj
import shutil
import os
import sys
import imp
import inspect
from services import ServicesProxy
from componentRegistry import ComponentID, ComponentRegistry
import messages
import tempfile
import ipsLogging
import logging
import socket
import string
import copy
my_version = float(sys.version[:3])
from multiprocessing import Queue, Process
from ipsTiming import create_timer, start, stop, TauWrap
import ipsutil


class ConfigurationManager(object):
    """
    The configuration manager is responsible for paring the simulation and
    platform configuration files, creating the framework and simulation
    components, as well as providing an interface to accessing items from the
    configuration files (e.g., the time loop).
    """
    # CM init
    class SimulationData(object):
        """
        Structure to hold simulation data stored into the sim_map
        entry in the configurationManager class
        """
        def __init__(self, sim_name):
            self.sim_name = sim_name
            self.portal_sim_name = None
            self.sim_root = None
            self.sim_conf = None
            self.config_file = None
            # SIMYAN: used for the directory of the platform conf file
            self.conf_file_dir = None
            self.driver_comp = None
            self.init_comp = None
            self.all_comps = []
            self.port_map = {}
            self.component_process = None
            self.log_file = None
            self.log_pipe_name = None
            self.logger = None
            self.process_list = []
            self.fwk_logger = None

   #@TauWrap(TIMERS['__init__'])
    # SIMYAN: accept a compset_list to find specific configuration files for
    # the components
    def __init__(self, fwk, config_file_list, platform_file_name, compset_list):
        """
        Initialize the values to be used by the configuration manager.  Also
        specified are the required fields of the simulation configuration
        file, and the configuration files are read in.
        """
        # ref to framework
        #self.timers = make_timers()
        #start(self.timers['__init__'])
        #pytau.start(self.timers['__init__'])
        self.fwk = fwk
        self.event_mgr = None
        self.data_mgr = None
        self.resource_mgr = None
        self.task_mgr = None
        self.comp_registry = ComponentRegistry()
        # SIMYAN: here is where we removed the requirement for BIN_PATH, etc.
        # from the required fields. This was done so that we could specify it
        # in the component-generic.conf file, which allows you to point to a
        # directory that contains physics and other binaries on a global level
        # i.e. removing the requirement that it be specified for each component
        self.required_fields = set(['CLASS', 'SUB_CLASS', 'NAME', 'SCRIPT',
                                    'INPUT_FILES', 'OUTPUT_FILES', 'NPROC'])
        self.config_file_list = []
        self.sim_name_list = None
        self.sim_root_list = None
        self.log_file_list = None
        self.log_dynamic_sim_queue = Queue(0)

        for conf_file in config_file_list:
            abs_path = os.path.abspath(conf_file)
            if (abs_path not in self.config_file_list):
                self.config_file_list.append(abs_path)
            else:
                print 'Ignoring duplicate configuration file ', abs_path

        sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
        self.platform_file = os.path.abspath(platform_file_name)
        self.platform_conf = {}
        # SIMYAN: breaking up the keywords a little bit
        self.compset_list = compset_list
        loc_keys=['IPS_ROOT']#,'PORTAL_URL','RUNID_URL']
        loc_keys=[]
        mach_keys=['MPIRUN','NODE_DETECTION','CORES_PER_NODE','SOCKETS_PER_NODE','NODE_ALLOCATION_MODE']
        prov_keys=['HOST']
        self.platform_keywords=loc_keys+mach_keys+prov_keys
        # SIMYAN: keywords specific to individual components
        self.compset_keywords=['BIN_PATH','PHYS_BIN_ROOT','DATA_TREE_ROOT']

        self.service_methods = ['get_port',
                                'getPort',
                                'get_config_parameter',
                                'set_config_parameter',
                                'getTimeLoop',
                                'create_simulation']
        self.fwk.register_service_handler(self.service_methods,
                                  getattr(self,'process_service_request'))
        self.sim_map = {}
        self.finished_sim_map = {}
        self.fwk_sim_name = None  #"Fake" simconf for framework components
        self.fwk_components = [] #List of framework specific components
        # create publisher event service object
        # self.publisherES = PublisherEventService()
        # get a topic to publish on
        #self.myTopic = self.publisherES.getTopic("test")
        self.myTopic = None
        self.log_daemon = ipsLogging.ipsLogger(self.log_dynamic_sim_queue)
        self.log_process = None
        #pytau.stop(self.timers['__init__'])
        #stop(self.timers['__init__'])

    # CM initialize
   #@TauWrap(TIMERS['initialize'])
    def initialize(self, data_mgr, resource_mgr, task_mgr, ftb):
        """
        Parse the platform and simulation configuration files using the
        :py:obj:`ConfigObj` module.  Create and initialize simulation(s) and
        their components, framework components and loggers.
        """
        #pytau.start(self.timers['initialize'])
        #start(self.timers['initialize'])
        local_debug = False
        self.event_mgr = None # eventManager(self)
        self.data_mgr = data_mgr
        self.resource_mgr = resource_mgr
        self.task_mgr = task_mgr
        self.FTB = ftb
        #Parse configuration files into configuration map
        sim_root_list = self.sim_root_list = []
        sim_name_list = self.sim_name_list = []
        log_file_list = self.log_file_list = []

        # Idiot checks
        if len(self.config_file_list)==0:
            self.fwk.exception('Missing config file? Something is very wrong')
            raise

        """
        Platform Configuration
        """
        # parse file
        try:
            self.platform_conf = ConfigObj(self.platform_file,
                                           interpolation='template',
                                           file_error=True)
        except IOError, (ex):
            self.fwk.exception('Error opening config file: %s',
                               self.platform_file)
            #pytau.stop(self.timers['initialize'])
            #stop(self.timers['initialize'])
            raise
        except SyntaxError, (ex):
            self.fwk.exception('Error parsing config file: %s',
                               self.platform_file)
            #pytau.stop(self.timers['initialize'])
            #stop(self.timers['initialize'])
            raise
        # get mandatory values
        for kw in self.platform_keywords:
            try:
                val = self.platform_conf[kw]
            except KeyError, ex:
                self.fwk.exception('Missing required parameter %s in platform config file',
                                   kw)
                #pytau.stop(self.timers['initialize'])
                #stop(self.timers['initialize'])
                raise
        # Make sure the HOST variable is defined
        try:
            host = self.platform_conf['HOST']
        except KeyError:
            self.platform_conf['HOST'] = socket.gethostname()

        """
        optional platform values are obtained and read here
        """
        user = ''
        try:
            user = self.platform_conf['USER']
        except KeyError:
            try:
                user = os.environ['USER']
            except Exception:
                pass
        self.platform_conf['USER'] = user

        try:
            mpirun_version = self.platform_conf['MPIRUN_VERSION']
        except KeyError:
            mpirun_version = 'OpenMPI-generic'

        # node allocation mode describes how node allocation should be handled
        # in the IPS.
        #  EXCLUSIVE - only one application can run on a single node.
        #  SHARE - applications may share nodes.

        try:
            node_alloc_mode = self.platform_conf['NODE_ALLOCATION_MODE'].upper()
            if node_alloc_mode not in ['EXCLUSIVE', 'SHARED']:
                self.fwk.exception("bad value for NODE_ALLOCATION_MODE. expected 'EXCLUSIVE' or 'SHARED'.")
                raise
        except:
            self.fwk.exception("missing value or bad type for NODE_ALLOCATION_MODE.  expected 'EXCLUSIVE' or 'SHARED'.")
            raise

        try:
            uan_val = self.platform_conf['USE_ACCURATE_NODES'].upper()
            if uan_val in ['OFF', 'FALSE']:
                use_accurate_nodes = False
            else:
                use_accurate_nodes = True
        except:
            use_accurate_nodes = True

        try:
            user_def_tprocs = int(self.platform_conf['TOTAL_PROCS'])
        except KeyError:
            user_def_tprocs = 0

        try:
            user_def_nodes = int(self.platform_conf['NODES'])
        except KeyError:
            user_def_nodes = 0

        try:
            user_def_ppn = int(self.platform_conf['PROCS_PER_NODE'])
        except KeyError:
            user_def_ppn = 0

        try:
            user_def_cpn = int(self.platform_conf['CORES_PER_NODE'])
        except KeyError:
            user_def_cpn = 0

        try:
            user_def_spn = int(self.platform_conf['SOCKETS_PER_NODE'])
        except KeyError:
            user_def_spn = 0

        self.platform_conf['TOTAL_PROCS'] = user_def_tprocs
        self.platform_conf['NODES'] = user_def_nodes
        self.platform_conf['PROCS_PER_NODE'] = user_def_ppn
        self.platform_conf['CORES_PER_NODE'] = user_def_cpn
        self.platform_conf['SOCKETS_PER_NODE'] = user_def_spn
        self.platform_conf['USE_ACCURATE_NODES'] = use_accurate_nodes
        self.platform_conf['MPIRUN_VERSION'] = mpirun_version

        # section to parse component conf files
        """
        Physics (compset) configuration files (PHYS_BIN_ROOT, BIN_PATH, ...)
        """
        self.compset_conf=[]
        if self.compset_list:
            for csfile in self.compset_list:
                if local_debug: print csfile
                try:
                    csconf = ConfigObj(csfile, interpolation='template', file_error=True)
                except IOError, (ex):
                    self.fwk.exception('Error opening config file: %s', csfile)
                    raise
                except SyntaxError, (ex):
                    self.fwk.exception('Error parsing config file: %s', csfile)
                    raise
                # get mandatory values
                for kw in self.compset_keywords:
                    try:
                        val = csconf[kw]
                    except KeyError, ex:
                        self.fwk.exception('Missing required parameter %s in %s config file',
                                           kw, csfile)
                        raise

                # allow any csconf parameters override the platform file
                for key in self.platform_conf.keys():
                    if key in csconf.keys():
                        self.platform_conf[key] = csconf[key]

                self.compset_conf.append(csconf)

        """
        Simulation Configuration
        """
        for conf_file in self.config_file_list:
            try:
                conf = ConfigObj(conf_file, interpolation='template', file_error=True)

                # Allow simulation file to override compset values
                # and then put all compset values into simulation map
                # The fact that csconf is a list is confusing
                for csconf in self.compset_conf:
                    for key in csconf.keys():
                        if key in conf.keys():
                            csconf[key] = conf[key]
                    conf.merge(csconf)
                # Import environment variables into config file
                # giving precedence to config file definitions in case of duplicates
                for (k,v) in os.environ.iteritems():
                    if k not in conf.keys() and '(' not in k:
                        conf[k] = v

                # Allow simulation file to override platform values
                # and then put all platform values into simulation map
                for key in self.platform_conf.keys():
                    if key in conf.keys():
                        self.platform_conf[key] = conf[key]
                conf.merge(self.platform_conf)

            except IOError, (ex):
                self.fwk.exception('Error opening config file %s: ', conf_file)
                #pytau.stop(self.timers['initialize'])
                #stop(self.timers['initialize'])
                raise
            except SyntaxError, (ex):
                self.fwk.exception('Error parsing config file %s: ', conf_file)
                #pytau.stop(self.timers['initialize'])
                #stop(self.timers['initialize'])
                raise
            except Exception, (ex):
                self.fwk.exception('Error(s) during parsing of supplied config file %s: ', conf_file)
                raise

            try:
                sim_name = conf['SIM_NAME']
                sim_root = conf['SIM_ROOT']
                log_file = os.path.abspath(conf['LOG_FILE'])
            except KeyError, (ex):
                self.fwk.exception('Missing required parameters SIM_NAME, SIM_ROOT or LOG_FILE\
 in configuration file %s', conf_file)
                #pytau.stop(self.timers['initialize'])
                #stop(self.timers['initialize'])
                raise


            # SIMYAN allow for a container file with default .zip extension
            self.container_ext = 'zip'
            if conf.has_key('CONTAINER_FILE_EXT'):
                self.container_ext = conf['CONTAINER_FILE_EXT']
            else:
                conf['CONTAINER_FILE_EXT'] = self.container_ext

            if (sim_name in sim_name_list):
                self.fwk.exception('Error: Duplicate SIM_NAME in configuration files')
                #pytau.stop(self.timers['initialize'])
                #stop(self.timers['initialize'])
                sys.exit(1)
            if (sim_root in sim_root_list):
                self.fwk.exception('Error: Duplicate SIM_ROOT in configuration files')
                #pytau.stop(self.timers['initialize'])
                #stop(self.timers['initialize'])
                sys.exit(1)
            if (log_file in log_file_list):
                self.fwk.exception('Error: Duplicate LOG_FILE in configuration files')
                #pytau.stop(self.timers['initialize'])
                #stop(self.timers['initialize'])
                sys.exit(1)
            if not conf.has_key('SIMULATION_CONFIG_FILE'):
                                conf['SIMULATION_CONFIG_FILE'] = conf_file
            sim_name_list.append(sim_name)
            sim_root_list.append(sim_root)
            log_file_list.append(log_file)
            new_sim = self.SimulationData(sim_name)
            conf['__PORTAL_SIM_NAME'] = sim_name
            new_sim.sim_conf = conf
            new_sim.config_file = conf_file
            new_sim.portal_sim_name = sim_name

            # SIMYAN: store the directory of the configuration file
            new_sim.conf_file_dir=os.path.dirname(os.path.abspath(conf_file))
            new_sim.sim_root = sim_root
            new_sim.log_file = log_file
            new_sim.log_pipe_name = tempfile.mktemp('.logpipe', 'ips_')

            self.log_daemon.add_sim_log(new_sim.log_pipe_name,
                                        new_sim.log_file)
            self.sim_map[sim_name] = new_sim
            log_level = 'DEBUG'
            try:
                log_level = conf['LOG_LEVEL']
            except KeyError:
                pass
            try:
                real_log_level = getattr(logging, log_level)
            except AttributeError:
                self.fwk.exception('Invalid LOG_LEVEL value %s in config file %s ',
                       log_level, conf_file)
                #pytau.stop(self.timers['initialize'])
                #stop(self.timers['initialize'])
                raise
            socketHandler = ipsLogging.IPSLogSocketHandler(new_sim.log_pipe_name)
            new_sim.fwk_logger = logging.getLogger(sim_name + '_FRAMEWORK')
            new_sim.fwk_logger.setLevel(real_log_level)
            new_sim.fwk_logger.addHandler(socketHandler)
            #SEK: It'd be nice to log to the zip file but I don't understand the handles

            # Use first simulation for framework components
            if (not self.fwk_sim_name):
                fwk_sim_conf = conf.dict()
                fwk_sim_conf['SIM_NAME'] = '_'.join([conf['SIM_NAME'], 'FWK'])
                fwk_sim = self.SimulationData(fwk_sim_conf['SIM_NAME'])
                fwk_sim.sim_conf = fwk_sim_conf
                fwk_sim.sim_root = new_sim.sim_root
                fwk_sim.log_file = self.fwk.log_file #sys.stdout
                fwk_sim.log_pipe_name = tempfile.mktemp('.logpipe', 'ips_')
                fwk_sim_conf['LOG_LEVEL'] = 'DEBUG'
                self.log_daemon.add_sim_log(fwk_sim.log_pipe_name, fwk_sim.log_file)
                self.fwk_sim_name = fwk_sim_conf['SIM_NAME']
                self.sim_map[fwk_sim.sim_name] = fwk_sim

        self.log_process = Process(target=self.log_daemon.__run__)
        self.log_process.start()

        for sim_name, sim_data in self.sim_map.items():
            if (sim_name != self.fwk_sim_name):
                self._initialize_sim(sim_data)

        # ***** commenting out portal stuff for now
        self._initialize_fwk_components()

        #pytau.stop(self.timers['initialize'])
        #stop(self.timers['initialize'])
        # do later - subscribe to events, set up event publishing structure
        # publish "CM initialized" event


   #@TauWrap(TIMERS['_initialize_fwk_components'])
    def _initialize_fwk_components(self):
        """
        Initialize 'components' that are part of the framework infrastructure.
        Those components (for now) communicate using the event bus and are not
        part of the normal framework-mediated RPC inter-compponent interactions
        """
        #pytau.start(self.timers['_initialize_fwk_components'])
        #start(self.timers['_initialize_fwk_components'])

        # SIMYAN: set up the runspaceInit component
        runspace_conf = {}
        runspace_conf['CLASS'] = 'FWK'
        runspace_conf['SUB_CLASS'] = 'COMP'
        runspace_conf['NAME'] = 'runspaceInitComponent'
        # SIMYAN: using inspect to grab the ipsPathName from the current frame
        ipsPathName=inspect.getfile(inspect.currentframe())
        ipsDir=os.path.dirname(ipsPathName)
        runspace_conf['BIN_PATH'] = ipsDir
        runspace_conf['SCRIPT'] = os.path.join(runspace_conf['BIN_PATH'],
                'runspaceInitComponent.py')
        runspace_conf['INPUT_DIR'] = '/dev/null'
        runspace_conf['INPUT_FILES'] = ''
        runspace_conf['IPS_CONFFILE_DIR'] = ''
        runspace_conf['DATA_FILES'] = ''
        runspace_conf['OUTPUT_FILES'] = ''
        runspace_conf['NPROC'] = 1
        runspace_conf['LOG_LEVEL'] = 'WARNING'
        runspace_conf['OS_CWD'] = os.getcwd()
        if (self.fwk.log_level == logging.DEBUG):
            runspace_conf['LOG_LEVEL'] = 'DEBUG'

        runspace_component_id = self._create_component(runspace_conf,
                                               self.sim_map[self.fwk_sim_name])
        self.fwk_components.append(runspace_component_id)

        # SIMYAN: set up The Portal bridge, allowing for an absense of a portal
        use_portal=True
        if self.sim_map[self.fwk_sim_name].sim_conf.has_key('USE_PORTAL'):
            use_portal=self.sim_map[self.fwk_sim_name].sim_conf['USE_PORTAL']
            if use_portal.lower()=="false": use_portal=False
        if use_portal:
            portal_conf={}
            portal_conf['CLASS'] = 'FWK'
            portal_conf['SUB_CLASS'] = 'COMP'
            portal_conf['NAME'] = 'PortalBridge'
            if self.sim_map[self.fwk_sim_name].sim_conf.has_key('FWK_COMPS_PATH'):
                portal_conf['BIN_PATH'] = self.sim_map[self.fwk_sim_name].sim_conf['FWK_COMPS_PATH']
            else:
                portal_conf['BIN_PATH'] = ipsDir
            portal_conf['SCRIPT'] = os.path.join(portal_conf['BIN_PATH'], 'portalBridge.py')
            portal_conf['INPUT_DIR'] = '/dev/null'
            portal_conf['INPUT_FILES']  = ''
            portal_conf['DATA_FILES']  = ''
            portal_conf['OUTPUT_FILES'] = ''
            portal_conf['NPROC'] = 1
            portal_conf['LOG_LEVEL'] = 'WARNING'
            havePortal=True
            if (self.fwk.log_level == logging.DEBUG):
                portal_conf['LOG_LEVEL'] = 'DEBUG'

            # does not work, this returns True, not a url
#           try:
#               portal_conf['PORTAL_URL']=self.sim_map[self.fwk_sim_name].sim_conf.has_key('PORTAL_URL')
#               portal_conf['RUNID_URL']=self.sim_map[self.fwk_sim_name].sim_conf.has_key('RUNID_URL')
#           except KeyError:
            try:
                portal_conf['PORTAL_URL'] = self.get_platform_parameter('PORTAL_URL', silent = True)
                portal_conf['RUNID_URL'] = self.get_platform_parameter('RUNID_URL', silent = True)
            except KeyError:
                havePortal=False

            if havePortal:
                component_id = self._create_component(portal_conf,
                                                self.sim_map[self.fwk_sim_name])
                self.fwk_components.append(component_id)


        # set up the FTB
        if self.FTB:
            ftb_conf={}
            ftb_conf['CLASS'] = 'FWK'
            ftb_conf['SUB_CLASS'] = 'COMP'
            ftb_conf['NAME'] = 'FTBBridge'
            # SIMYAN: set the BIN_PATH from the FWK_COMPS_PATH
            ftb_conf['BIN_PATH'] = self.sim_map[self.fwk_sim_name].sim_conf['FWK_COMPS_PATH']
            ftb_conf['SCRIPT'] = os.path.join(ftb_conf['BIN_PATH'], 'ftbBridge.py')
            ftb_conf['INPUT_DIR'] = ''
            ftb_conf['INPUT_FILES']  = ''
            # SIMYAN: initialize the DATA_FILES value to ''
            ftb_conf['DATA_FILES']  = ''
            ftb_conf['OUTPUT_FILES'] = ''
            ftb_conf['NPROC'] = 1
            ftb_conf['LOG_LEVEL'] = 'WARNING'
            if (self.fwk.log_level == logging.DEBUG):
                ftb_conf['LOG_LEVEL'] = 'DEBUG'

            ftb_component_id = self._create_component(ftb_conf,
                                                      self.sim_map[self.fwk_sim_name])
            self.fwk_components.append(ftb_component_id)


        #pytau.stop(self.timers['_initialize_fwk_components'])
        #stop(self.timers['_initialize_fwk_components'])

   #@TauWrap(TIMERS['_initialize_sim'])
    def _initialize_sim(self, sim_data):
        """
        Parses the configuration data (*sim_conf*) associated with a simulation
        (*sim_name*). Instantiate the components associated with each simulation.
        Populate the *component_registry* with appropriate component and port
        mapping info.
        """
        #pytau.start(self.timers['_initialize_sim'])
        #start(self.timers['_initialize_sim'])
        sim_conf = sim_data.sim_conf
        sim_name = sim_data.sim_name
        ports_config = sim_conf['PORTS']
        ports_list  = ports_config['NAMES'].split()

        simRootDir = self.get_sim_parameter(sim_name, 'SIM_ROOT')

        #SIMYAN: removed code that would make the simrootDir from here and
        # moved it to the runspaceInit component
        # set simulation level partial_nodes
        try:
            pn_simconf = sim_conf['NODE_ALLOCATION_MODE']
            if pn_simconf.upper() == 'SHARED':
                sim_data.sim_conf['NODE_ALLOCATION_MODE'] = 'SHARED'
            elif pn_simconf.upper() == 'EXCLUSIVE':
                sim_data.sim_conf['NODE_ALLOCATION_MODE'] = 'EXCLUSIVE'
            else:
                self.fwk.exception("Bad 'NODE_ALLOCATION_MODE' value %s" % pn_simconf)
                raise("Bad 'NODE_ALLOCATION_MODE' value %s" % pn_simconf)
        except:
            sim_data.sim_conf['NODE_ALLOCATION_MODE'] = self.platform_conf['NODE_ALLOCATION_MODE']


        for port in ports_list:
            try:
                comp_ref = ports_config[port]['IMPLEMENTATION']
                if(comp_ref.strip() == ''):
                    continue
                comp_conf = sim_conf[comp_ref]
            except Exception, e:
                self.fwk.exception('Error accessing configuration section for ' +
                            'component %s in simulation %s' , comp_ref, sim_name)
                #pytau.stop(self.timers['_initialize_sim'])
                #stop(self.timers['_initialize_sim'])
                sys.exit(1)
            conf_fields = set(comp_conf.keys())

            # Move the paths to the component levels so that they can use it
            # If they already have it, then they are effectively overriding the global values
            if not comp_conf.has_key('INPUT_DIR'):
                if sim_conf.has_key('INPUT_DIR'):
                    comp_conf['INPUT_DIR']=sim_conf['INPUT_DIR']
                else:
                    comp_conf['INPUT_DIR']=sim_data.conf_file_dir
            if not comp_conf.has_key('IPS_ROOT'):
                if sim_conf.has_key('IPS_ROOT'):
                    comp_conf['IPS_ROOT']=sim_conf['IPS_ROOT']
            if not comp_conf.has_key('DATA_TREE_ROOT'):
                if sim_conf.has_key('DATA_TREE_ROOT'):
                    comp_conf['DATA_TREE_ROOT']=sim_conf['DATA_TREE_ROOT']
                else:
                    comp_conf['DATA_TREE_ROOT']=sim_data.conf_file_dir
            if not comp_conf.has_key('BIN_DIR'):
                if sim_conf.has_key('BIN_DIR'):
                    comp_conf['BIN_DIR'] = sim_conf['BIN_DIR']
                else:
                    comp_conf['BIN_DIR'] = os.path.join(sim_conf['IPS_ROOT'], 'bin')
#                    comp_conf['BIN_DIR']=sim_data.conf_file_dir
            if not comp_conf.has_key('BIN_PATH'):
                if sim_conf.has_key('BIN_PATH'):
                    comp_conf['BIN_PATH']=sim_conf['BIN_PATH']
                else:
                    comp_conf['BIN_PATH']=comp_conf['BIN_DIR']
            if (not self.required_fields.issubset(conf_fields)):
                self.fwk.exception('Error: missing required entries %s \
                    in simulation %s component %s configuration section' ,
                    list(self.required_fields - conf_fields), sim_name, comp_ref)
                #pytau.stop(self.timers['_initialize_sim'])
                #stop(self.timers['_initialize_sim'])
                sys.exit(1)
            component_id = self._create_component(comp_conf, sim_data)
            sim_data.port_map[port] = component_id
            if (port == 'DRIVER'):
                sim_data.driver_comp = component_id
            elif (port == 'INIT'):
                sim_data.init_comp = component_id

        if (sim_data.driver_comp == None):
            self.fwk.error('Missing DRIVER specification in ' +
                           'config file for simulation %s' , sim_data.sim_name)
            #pytau.stop(self.timers['_initialize_sim'])
            #stop(self.timers['_initialize_sim'])
            sys.exit(1)
        if (sim_data.init_comp == None):
            self.fwk.warning('Missing INIT specification in ' +
                             'config file for simulation %s' , sim_data.sim_name)

        conf_file = sim_data.config_file

        # SIMYAN: No longer doing this in configurationManager.py
        # Copy the configuration and platform files to the simRootDir
        #ipsutil.copyFiles(os.path.dirname(conf_file),
        #                  os.path.basename(conf_file), simRootDir)
        #ipsutil.copyFiles(os.path.dirname(self.platform_file),
        #                  os.path.basename(self.platform_file), simRootDir)

        # try to find the statedir
        try:
            statedir = self.get_sim_parameter(sim_name,
                                        'PLASMA_STATE_WORK_DIR')
            haveStateDir=True
        except:
            haveStateDir=False

        # SIMYAN: removed from configurationManager
        # if haveStateDir:
        #   try:
        #       os.makedirs(statedir)
        #   except OSError, (errno, strerror):
        #       if (errno != 17):
        #           self.fwk.exception('Error creating State directory %s : %d %s' ,
        #                              statedir, errno, strerror)
        #           #pytau.stop(self.timers['_initialize_sim'])
        #           #stop(self.timers['_initialize_sim'])
        #           #raise
        #   #pytau.stop(self.timers['_initialize_sim'])
        return

   #@TauWrap(TIMERS['_create_component'])
    def _create_component(self, comp_conf, sim_data):
        """
        Create component and populate it with the information from the
        component's configuration section.
        """
        #pytau.start(self.timers['_create_component'])
        sim_name = sim_data.sim_name
        path = comp_conf['BIN_PATH']
        script = comp_conf['SCRIPT'].rsplit('.', 1)[0].split('/')[-1]
        endpath = comp_conf['SCRIPT'].rfind('/')
        #print 'path[0]', comp_conf['SCRIPT'][0:endpath]
        #print 'script', script
        #print 'endpath', endpath
        if (endpath != -1):
            path = [comp_conf['SCRIPT'][0:endpath],
                    comp_conf['SCRIPT'][0:endpath] + '/' + script,
                    comp_conf['SCRIPT'][0:endpath] + '/' + script + '.py']
        class_name = comp_conf['NAME']
        try:
            (modFile, pathname, description) = imp.find_module(script, path)
            module = imp.load_module(script, modFile, pathname, description)
            component_class = getattr(module, class_name)
        except Exception, e:
            self.fwk.error('Error in configuration file : NAME = %s   SCRIPT = %s',
                           comp_conf['NAME'], comp_conf['SCRIPT'] )
            self.fwk.exception('Error instantiating IPS component %s From %s', class_name, script)
            #pytau.stop(self.timers['_create_component'])
            raise

        # SIMYAN: removed else conditional, copying files in runspaceInit
        # component now

        svc_response_q = Queue(0)
        invocation_q = Queue(0)
        component_id = ComponentID(class_name, sim_name)
        fwk_inq = self.fwk.get_inq()

        log_pipe_name = sim_data.log_pipe_name
        services_proxy = ServicesProxy(self.fwk, fwk_inq, svc_response_q,
                                   sim_data.sim_conf, log_pipe_name)
        new_component = component_class(services_proxy, comp_conf)
        new_component.__initialize__(component_id, invocation_q, self.fwk.start_time)
        services_proxy.__initialize__(new_component)
        self.comp_registry.addEntry(component_id, svc_response_q,
                                    invocation_q, new_component,
                                    services_proxy,
                                    comp_conf)
        p = Process(target=new_component.__run__)
        p.start()
        sim_data.process_list.append(p)
        sim_data.all_comps.append(component_id)
        #pytau.stop(self.timers['_create_component'])
        return component_id

    #@TauWrap(TIMERS['get_component_map'])
    def get_component_map(self):
        """
        Return a dictionary of simulation names and lists of component
        references.  (May only be the driver, and init (if present)???)
        """
        #pytau.start(self.timers['get_component_map'])
        sim_comps ={}
        for sim_name in self.sim_map.keys():
            if (sim_name == self.fwk_sim_name):
                continue
            sim_comps[sim_name]= self.get_simulation_components(sim_name)
        return sim_comps

    def get_simulation_components(self, sim_name):
        comp_list = []
        sim_data = self.sim_map[sim_name]
        if (sim_data.init_comp):
            comp_list.append(sim_data.init_comp)
        comp_list.append(sim_data.driver_comp)
        return comp_list

    def get_all_simulation_components_map(self):
        sim_comps = {name : self.sim_map[name].all_comps[:] 
                      for name in self.sim_map.keys()} 
        del sim_comps[self.fwk_sim_name]
        return sim_comps

    def get_driver_components(self):
        """
        Return a list of driver components, one for each sim.
        """
        #pytau.start(self.timers['get_driver_components'])
        driver_list = []
        for sim in self.sim_map.values():
            driver_list.append(sim.driver_comp)
        #pytau.stop(self.timers['get_driver_components'])
        return driver_list

    def get_framework_components(self):
        """
        Return list of framework components.
        """
        #pytau.start(self.timers['get_framework_components'])
        fwk_components = self.fwk_components[:]
        #pytau.stop(self.timers['get_framework_components'])
        return fwk_components

    def get_init_components(self):
        """
        Return list of init components.
        """
        #pytau.start(self.timers['get_init_components'])
        init_list = []
        for sim_data in self.sim_map.values():
            if (sim_data.init_comp):
                init_list.append(sim_data.init_comp)
        #pytau.stop(self.timers['get_init_components'])
        return init_list

    def get_sim_parameter(self, sim_name, param):
        """
        Return value of *param* from simulation configuration file for
        *sim_name*.
        """
        #pytau.start(self.timers['get_sim_parameter'])
        try:
            sim_data = self.sim_map[sim_name]
        except KeyError:
            sim_data = self.finished_sim_map[sim_name]
        #self.fwk.debug('CONFIG VALUES =  %s', str(sim_data.sim_conf))
        try:
            val = sim_data.sim_conf[param]
        except KeyError:
            val = self.platform_conf[param]
        self.fwk.debug('Returning value = %s for config parameter %s in simulation %s', val, param, sim_name)
        #pytau.start(self.timers['get_sim_parameter'])
        return val

    def get_sim_names(self):
        """
        Return list of names of simulations.
        """
        return self.sim_map.keys()

    def process_service_request(self, msg):
        """
        Invokes public configuration manager method for a component.  Return
        method's return value.
        """
        #pytau.start(self.timers['process_service_request'])
        self.fwk.debug( 'Configuration Manager received message: %s', str(msg.__dict__))
        sim_name = msg.sender_id.get_sim_name()
        method = getattr(self, msg.target_method)
        self.fwk.debug('Configuration manager dispatching method %s on simulation %s',
                       method, sim_name)
        retval = method(sim_name, *msg.args)
        #pytau.start(self.timers['process_service_request'])
        return retval

    def create_simulation(self, sim_name, config_file, override, sub_workflow=False):
        try:
            conf = ConfigObj(config_file, interpolation='template',
                            file_error=True)
        except IOError, (ex):
            self.fwk.exception('Error opening config file %s: ', config_file)
            raise
        except SyntaxError, (ex):
            self.fwk.exception(' Error parsing config file %s: ', config_file)
            raise
        parent_sim_name = sim_name
        parent_sim = self.sim_map[parent_sim_name]
        # Incorporate environment variables into config file
        # Use config file entries when duplicates are detected
        for (k,v) in os.environ.iteritems():
            # Do not include functions from environment
            if k not in conf.keys() and '(' not in k:
                conf[k] = v

        # Allow propagation of entries from platform config file to simulation
        # config file
        for keyword in self.platform_conf.keys():
            if keyword not in conf.keys():
                conf[keyword] = self.platform_conf[keyword]
        if (override):
            for kw in override.keys():
                conf[kw] = override[kw]
        try:
            sim_name = conf['SIM_NAME']
            sim_root = conf['SIM_ROOT']
            log_file = os.path.abspath(conf['LOG_FILE'])
        except KeyError, (ex):
            self.fwk.exception('Missing required parameters SIM_NAME, SIM_ROOT or LOG_FILE\
in configuration file %s', config_file)
            raise
        if (sim_name in self.sim_name_list):
            self.fwk.error('Error: Duplicate SIM_NAME %s in configuration files' % (sim_name))
            raise Exception('Duplicate SIM_NAME %s in configuration files' % (sim_name))
        if (sim_root in self.sim_root_list):
            self.fwk.exception('Error: Duplicate SIM_ROOT in configuration files')
            raise Exception('Duplicate SIM_ROOT in configuration files')
        if (log_file in self.log_file_list):
            self.fwk.exception('Error: Duplicate LOG_FILE in configuration files')
            raise Exception('Duplicate LOG_FILE in configuration files')

        # Add path to configuration file to simulation configuration in memory
        if not conf.has_key('SIMULATION_CONFIG_FILE'):
                            conf['SIMULATION_CONFIG_FILE'] = config_file

        self.sim_name_list.append(sim_name)
        self.sim_root_list.append(sim_root)
        self.log_file_list.append(log_file)
        new_sim = self.SimulationData(sim_name)
        new_sim.sim_conf = conf
        new_sim.config_file = config_file
        new_sim.sim_root = sim_root
        new_sim.log_file = log_file
        if not sub_workflow:
            new_sim.portal_sim_name = sim_name
            new_sim.log_pipe_name = tempfile.mktemp('.logpipe', 'ips_')
            self.log_dynamic_sim_queue.put('CREATE_SIM  %s  %s' % (new_sim.log_pipe_name, new_sim.log_file))
        else:
            new_sim.portal_sim_name = parent_sim.portal_sim_name
            new_sim.log_pipe_name = parent_sim.log_pipe_name

        conf['__PORTAL_SIM_NAME'] = new_sim.portal_sim_name
        log_level = 'DEBUG'
        try:
            log_level = conf['LOG_LEVEL']
        except KeyError:
            pass
        try:
            real_log_level = getattr(logging, log_level)
        except AttributeError:
            self.fwk.exception('Invalid LOG_LEVEL value %s in config file %s ',
                  log_level, config_file)
            raise
        #self.log_dynamic_sim_queue.put('CREATE_SIM  %s  %s' % (new_sim.log_pipe_name, new_sim.log_file))
        self.sim_map[sim_name] = new_sim
        self._initialize_sim(new_sim)

        if not sub_workflow:
            self.fwk.initiate_new_simulation(sim_name)

        return (sim_name, new_sim.init_comp, new_sim.driver_comp)

    def getPort(self, sim_name, port_name):
        """
        .. deprecated:: 1.0 Use :py:meth:`.get_port`
        """
        return self.get_port(sim_name, port_name)

    def get_port(self, sim_name, port_name):
        """
        Return a reference to the component from simulation *sim_name*
        implementing port *port_name*.
        """
        #print sim_name, port_name
        #pytau.start(self.timers['get_port'])
        sim_data = self.sim_map[sim_name]
        comp_id = sim_data.port_map[port_name]
        #pytau.stop(self.timers['get_port'])
        return comp_id

    def get_config_parameter(self, sim_name, param):
        """
        Return value of *param* from simulation configuration file for
        *sim_name*.
        """
        return self.get_sim_parameter(sim_name, param)

    def set_config_parameter(self, sim_name, param, value, target_sim_name):
        """
        Set the configuration parameter *param* to value *value* in
        *target_sim_name*.  If *target_sim_name* is the framework, all
        simulations will get the change.  Return *value*.
        """
        if (target_sim_name == self.fwk_sim_name): # apply to all simulations
            target_sims = self.sim_map.keys()
        else:
            target_sims = [target_sim_name]
        for sim_name in target_sims:
            self.fwk.debug('Setting %s to %s in simulation %s', param, value, sim_name)
            try:
                sim_data = self.sim_map[sim_name]
            except KeyError:
                sim_data = self.finished_sim_map[sim_name]
            self.fwk.debug('Setting %s to %s in simulation %s', param, value, sim_name)
            sim_conf = sim_data.sim_conf
            sim_conf[param] = value

        #self.fwk.debug('CONFIG VALUES =  %s', str(sim_data.sim_conf))

        return value

    def get_platform_parameter(self, param, silent=False):
        """
        Return value of platform parameter *param*.  If *silent* is ``False``
        (default) ``None`` is returned when *param* not found, otherwise an
        exception is raised.
        """
        #pytau.start(self.timers['get_platform_parameter'])
        val = None
        try:
            val = self.platform_conf[param]
        except KeyError, ex:
            if not silent:
                self.fwk.warning('CM: No platform data for %s ', param)
            #pytau.stop(self.timers['get_platform_parameter'])
                raise
        #pytau.stop(self.timers['get_platform_parameter'])
        return val

    def terminate_sim(self, sim_name):
        sim_data = self.sim_map[sim_name]
        all_sim_components = sim_data.all_comps
        msg = 'END_SIM %s' % (sim_data.log_pipe_name)
        self.log_dynamic_sim_queue.put(msg)
        proc_list = sim_data.process_list
        for p in proc_list:
            #p.terminate()
            p.join()
        try:
            os.remove(sim_data.log_pipe_name)
        except :
            pass
        for comp_id in all_sim_components:
            self.comp_registry.removeEntry(comp_id)
        sim_data.logger = None
        sim_data.process_list=[]
        self.finished_sim_map[sim_name] = sim_data
        del self.sim_map[sim_name]
        return

    def terminate(self, status):
        """
        Terminates all processes attached to the framework.  *status* not used.
        """
        try:
            for sim_name in self.sim_map.keys():
                self.terminate_sim(sim_name)
        except:
            print 'Encountered exception when terminating simulation'
            raise
        for k in self.sim_map.keys():
            del self.sim_map[k]
        self.log_process.terminate()
