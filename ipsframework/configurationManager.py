# -------------------------------------------------------------------------------
# Copyright 2006-2021 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import os
import sys
import importlib
import importlib.util
import tempfile
import uuid
import logging
import socket
from multiprocessing import Queue, Process, set_start_method
from .configobj import ConfigObj
from . import ipsLogging
from .services import ServicesProxy
from .componentRegistry import ComponentID, ComponentRegistry

# Try using fork for starting subprocesses, this is the default on
# Linux but not macOS with python >= 3.8
if sys.platform == 'darwin':
    try:
        set_start_method('fork')
    except RuntimeError:
        # context can only be set once
        pass


class ConfigurationManager:
    """
    The configuration manager is responsible for paring the simulation and
    platform configuration files, creating the framework and simulation
    components, as well as providing an interface to accessing items from the
    configuration files (e.g., the time loop).
    """

    # CM init
    class SimulationData:
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
            self.conf_file_dir = None
            self.driver_comp = None
            self.init_comp = None
            self.all_comps = []
            self.port_map = {}
            self.component_process = None
            self.process_list = []

    def __init__(self, fwk, config_file_list, platform_file_name):
        """
        Initialize the values to be used by the configuration manager.  Also
        specified are the required fields of the simulation configuration
        file, and the configuration files are read in.
        """
        # ref to framework
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

        class Unbuffered:
            def __init__(self, stream):
                self.stream = stream

            def write(self, data):
                self.stream.write(data)
                self.stream.flush()

            def writelines(self, data):
                self.stream.writelines(data)
                self.stream.flush()

            def __getattr__(self, attr):
                return getattr(self.stream, attr)

        for conf_file in config_file_list:
            abs_path = os.path.abspath(conf_file)
            if abs_path not in self.config_file_list:
                self.config_file_list.append(abs_path)
            else:
                print('Ignoring duplicate configuration file ', abs_path)

        # sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
        sys.stdout = Unbuffered(sys.stdout)
        self.platform_file = os.path.abspath(platform_file_name)
        self.platform_conf = {}
        loc_keys = []
        mach_keys = ['MPIRUN', 'NODE_DETECTION', 'CORES_PER_NODE', 'SOCKETS_PER_NODE', 'NODE_ALLOCATION_MODE']
        prov_keys = ['HOST']
        self.platform_keywords = loc_keys + mach_keys + prov_keys

        self.service_methods = ['get_port',
                                'get_config_parameter',
                                'set_config_parameter',
                                'get_time_loop',
                                'create_simulation']
        self.fwk.register_service_handler(self.service_methods,
                                          getattr(self, 'process_service_request'))
        self.sim_map = {}
        self.finished_sim_map = {}
        self.fwk_sim_name = None  # "Fake" simconf for framework components
        self.fwk_components = []  # List of framework specific components
        self.myTopic = None
        self.log_daemon = ipsLogging.ipsLogger(self.log_dynamic_sim_queue)
        self.log_process = None

    # CM initialize
    def initialize(self, data_mgr, resource_mgr, task_mgr):
        """
        Parse the platform and simulation configuration files using the
        :py:obj:`ConfigObj` module.  Create and initialize simulation(s) and
        their components, framework components and loggers.
        """
        self.event_mgr = None  # eventManager(self)
        self.data_mgr = data_mgr
        self.resource_mgr = resource_mgr
        self.task_mgr = task_mgr
        # Parse configuration files into configuration map
        sim_root_list = self.sim_root_list = []
        sim_name_list = self.sim_name_list = []
        log_file_list = self.log_file_list = []

        # Idiot checks
        if len(self.config_file_list) == 0:
            self.fwk.exception('Missing config file? Something is very wrong')
            raise ValueError('Missing config file? Something is very wrong')

        """
        Platform Configuration
        """
        # parse file
        try:
            self.platform_conf = ConfigObj(self.platform_file,
                                           interpolation='template',
                                           file_error=True)
        except (IOError, SyntaxError):
            self.fwk.exception('Error opening config file: %s',
                               self.platform_file)
            raise
        # get mandatory values
        for kw in self.platform_keywords:
            try:
                self.platform_conf[kw]
            except KeyError:
                self.fwk.exception('Missing required parameter %s in platform config file',
                                   kw)
                raise
        # Make sure the HOST variable is defined
        try:
            host = self.platform_conf['HOST']
        except KeyError:
            self.platform_conf['HOST'] = socket.gethostname()
        else:
            if not host:
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

        # Grab environment variables
        plat_keys = list(self.platform_conf.keys())
        for (k, v) in os.environ.items():
            if k not in plat_keys \
                    and not any(x in v for x in '{}()$'):
                self.platform_conf[k] = v

        mpirun_version = self.platform_conf.get('MPIRUN_VERSION', 'OpenMPI-generic')

        # node allocation mode describes how node allocation should be handled
        # in the IPS.
        #  EXCLUSIVE - only one application can run on a single node.
        #  SHARE - applications may share nodes.

        try:
            node_alloc_mode = self.platform_conf['NODE_ALLOCATION_MODE'].upper()
            if node_alloc_mode not in ['EXCLUSIVE', 'SHARED']:
                self.fwk.exception("bad value for NODE_ALLOCATION_MODE. expected 'EXCLUSIVE' or 'SHARED'.")
                raise ValueError("bad value for NODE_ALLOCATION_MODE. expected 'EXCLUSIVE' or 'SHARED'.")
        except Exception:
            self.fwk.exception("missing value or bad type for NODE_ALLOCATION_MODE.  expected 'EXCLUSIVE' or 'SHARED'.")
            raise

        uan_val = self.platform_conf.get('USE_ACCURATE_NODES', 'ON').upper()
        if uan_val in ['OFF', 'FALSE']:
            use_accurate_nodes = False
        else:
            use_accurate_nodes = True

        self.platform_conf['TOTAL_PROCS'] = int(self.platform_conf.get('TOTAL_PROCS', 0))
        self.platform_conf['NODES'] = int(self.platform_conf.get('NODES', 0))
        self.platform_conf['PROCS_PER_NODE'] = int(self.platform_conf.get('PROCS_PER_NODE', 0))
        self.platform_conf['CORES_PER_NODE'] = int(self.platform_conf.get('CORES_PER_NODE', 0))
        self.platform_conf['SOCKETS_PER_NODE'] = int(self.platform_conf.get('SOCKETS_PER_NODE', 0))
        self.platform_conf['USE_ACCURATE_NODES'] = use_accurate_nodes
        self.platform_conf['MPIRUN_VERSION'] = mpirun_version

        """
        Simulation Configuration
        """
        for conf_file in self.config_file_list:
            try:
                conf = ConfigObj(conf_file, interpolation='template', file_error=True)

                # Import environment variables into config file
                # giving precedence to config file definitions in case of duplicates
                conf_keys = list(conf.keys())
                for (k, v) in os.environ.items():
                    if k not in conf_keys and not any(x in v for x in '{}()$'):
                        conf[k] = v

                # Allow simulation file to override platform values
                # and then put all platform values into simulation map
                for key in self.platform_conf:
                    if key in conf_keys and key not in os.environ.keys():
                        self.platform_conf[key] = conf[key]
                    if key not in conf_keys:
                        conf[key] = self.platform_conf[key]

                # Override platform value for PORTAL_URL if in simulation
                if 'PORTAL_URL' in conf_keys:
                    self.platform_conf['PORTAL_URL'] = conf['PORTAL_URL']

            except (IOError, SyntaxError):
                self.fwk.exception('Error opening config file %s: ', conf_file)
                raise
            except Exception:
                self.fwk.exception('Error(s) during parsing of supplied config file %s: ', conf_file)
                raise

            try:
                sim_name = conf['SIM_NAME']
                sim_root = conf['SIM_ROOT']
                log_file = os.path.abspath(conf['LOG_FILE'])
            except KeyError:
                self.fwk.exception('Missing required parameters SIM_NAME, SIM_ROOT or LOG_FILE\
 in configuration file %s', conf_file)
                raise

            if sim_name in sim_name_list:
                self.fwk.exception('Error: Duplicate SIM_NAME in configuration files')
                sys.exit(1)
            if sim_root in sim_root_list:
                self.fwk.exception('Error: Duplicate SIM_ROOT in configuration files')
                sys.exit(1)
            if log_file in log_file_list:
                self.fwk.exception('Error: Duplicate LOG_FILE in configuration files')
                sys.exit(1)
            if 'SIMULATION_CONFIG_FILE' not in conf:
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
            new_sim.conf_file_dir = os.path.dirname(os.path.abspath(conf_file))
            new_sim.sim_root = sim_root
            new_sim.log_file = log_file
            new_sim.log_pipe_name = f'{tempfile.gettempdir()}/ips_{uuid.uuid4()}.logpipe'

            self.log_daemon.add_sim_log(new_sim.log_pipe_name,
                                        new_sim.log_file)
            self.sim_map[sim_name] = new_sim

            # Use first simulation for framework components
            if not self.fwk_sim_name:
                fwk_sim_conf = conf.dict()
                fwk_sim_conf['SIM_NAME'] = '_'.join([conf['SIM_NAME'], 'FWK'])
                fwk_sim = self.SimulationData(fwk_sim_conf['SIM_NAME'])
                fwk_sim.sim_conf = fwk_sim_conf
                fwk_sim.sim_root = new_sim.sim_root
                fwk_sim.log_file = self.fwk.log_file  # sys.stdout
                fwk_sim.log_pipe_name = f'{tempfile.gettempdir()}/ips_{uuid.uuid4()}.logpipe'
                fwk_sim_conf['LOG_LEVEL'] = 'DEBUG'
                self.log_daemon.add_sim_log(fwk_sim.log_pipe_name, fwk_sim.log_file)
                self.fwk_sim_name = fwk_sim_conf['SIM_NAME']
                self.sim_map[fwk_sim.sim_name] = fwk_sim

        self.log_process = Process(target=self.log_daemon.__run__)
        self.log_process.start()

        for sim_name, sim_data in self.sim_map.items():
            if sim_name != self.fwk_sim_name:
                self._initialize_sim(sim_data)

        # ***** commenting out portal stuff for now
        self._initialize_fwk_components()

        # do later - subscribe to events, set up event publishing structure
        # publish "CM initialized" event

    def _initialize_fwk_components(self):
        """
        Initialize 'components' that are part of the framework infrastructure.
        Those components (for now) communicate using the event bus and are not
        part of the normal framework-mediated RPC inter-compponent interactions
        """

        # SIMYAN: set up the runspaceInit component
        runspace_conf = {}
        runspace_conf['CLASS'] = 'FWK'
        runspace_conf['SUB_CLASS'] = 'COMP'
        runspace_conf['NAME'] = 'runspaceInitComponent'
        runspace_conf['SCRIPT'] = ''
        runspace_conf['MODULE'] = 'ipsframework.runspaceInitComponent'
        runspace_conf['INPUT_DIR'] = '/dev/null'
        runspace_conf['INPUT_FILES'] = ''
        runspace_conf['IPS_CONFFILE_DIR'] = ''
        runspace_conf['DATA_FILES'] = ''
        runspace_conf['OUTPUT_FILES'] = ''
        runspace_conf['NPROC'] = 1
        runspace_conf['LOG_LEVEL'] = 'WARNING'
        runspace_conf['OS_CWD'] = os.getcwd()
        if self.fwk.log_level == logging.DEBUG:
            runspace_conf['LOG_LEVEL'] = 'DEBUG'

        runspace_component_id = self._create_component(runspace_conf,
                                                       self.sim_map[self.fwk_sim_name])
        self.fwk_components.append(runspace_component_id)

        # SIMYAN: set up The Portal bridge, allowing for an absence of a portal
        use_portal = True
        if 'USE_PORTAL' in self.sim_map[self.fwk_sim_name].sim_conf:
            use_portal = self.sim_map[self.fwk_sim_name].sim_conf['USE_PORTAL']
            if use_portal.lower() == "false":
                use_portal = False
        if use_portal:
            portal_conf = {}
            portal_conf['CLASS'] = 'FWK'
            portal_conf['SUB_CLASS'] = 'COMP'
            portal_conf['NAME'] = 'PortalBridge'
            if 'FWK_COMPS_PATH' in self.sim_map[self.fwk_sim_name].sim_conf:
                portal_conf['BIN_PATH'] = self.sim_map[self.fwk_sim_name].sim_conf['FWK_COMPS_PATH']
                portal_conf['SCRIPT'] = os.path.join(portal_conf['BIN_PATH'], 'portalBridge.py')
            else:
                portal_conf['SCRIPT'] = ''
                portal_conf['MODULE'] = 'ipsframework.portalBridge'
            portal_conf['INPUT_DIR'] = '/dev/null'
            portal_conf['INPUT_FILES'] = ''
            portal_conf['DATA_FILES'] = ''
            portal_conf['OUTPUT_FILES'] = ''
            portal_conf['NPROC'] = 1
            portal_conf['LOG_LEVEL'] = 'WARNING'
            try:
                portal_conf['USER'] = self.sim_map[self.fwk_sim_name].sim_conf['USER']
            except KeyError:
                portal_conf['USER'] = self.platform_conf['USER']
            if self.fwk.log_level == logging.DEBUG:
                portal_conf['LOG_LEVEL'] = 'DEBUG'

            portal_conf['PORTAL_URL'] = self.get_platform_parameter('PORTAL_URL', silent=True)

            component_id = self._create_component(portal_conf,
                                                  self.sim_map[self.fwk_sim_name])
            self.fwk_components.append(component_id)

    def _initialize_sim(self, sim_data):
        """
        Parses the configuration data (*sim_conf*) associated with a simulation
        (*sim_name*). Instantiate the components associated with each simulation.
        Populate the *component_registry* with appropriate component and port
        mapping info.
        """
        sim_conf = sim_data.sim_conf
        sim_name = sim_data.sim_name
        ports_config = sim_conf['PORTS']
        ports_list = ports_config['NAMES'].split()

        # simRootDir = self.get_sim_parameter(sim_name, 'SIM_ROOT')
        # SIMYAN: removed code that would make the simrootDir from here and
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
                raise Exception("Bad 'NODE_ALLOCATION_MODE' value %s" % pn_simconf)
        except Exception:
            sim_data.sim_conf['NODE_ALLOCATION_MODE'] = self.platform_conf['NODE_ALLOCATION_MODE']

        for port in ports_list:
            try:
                comp_ref = ports_config[port]['IMPLEMENTATION']
                if comp_ref.strip() == '':
                    continue
                comp_conf = sim_conf[comp_ref]
            except Exception:
                self.fwk.exception('Error accessing configuration section for ' +
                                   'component %s in simulation %s', comp_ref, sim_name)
                sys.exit(1)
            conf_fields = set(comp_conf.keys())

            # Move the paths to the component levels so that they can use it
            # If they already have it, then they are effectively overriding the global values
            if 'INPUT_DIR' not in comp_conf:
                if 'INPUT_DIR' in sim_conf:
                    comp_conf['INPUT_DIR'] = sim_conf['INPUT_DIR']
                else:
                    comp_conf['INPUT_DIR'] = sim_data.conf_file_dir
            if 'IPS_ROOT' not in comp_conf:
                if 'IPS_ROOT' in sim_conf:
                    comp_conf['IPS_ROOT'] = sim_conf['IPS_ROOT']
            if 'DATA_TREE_ROOT' not in comp_conf:
                if 'DATA_TREE_ROOT' in sim_conf:
                    comp_conf['DATA_TREE_ROOT'] = sim_conf['DATA_TREE_ROOT']
                else:
                    comp_conf['DATA_TREE_ROOT'] = sim_data.conf_file_dir
            if 'BIN_DIR' not in comp_conf:
                if 'BIN_DIR' in sim_conf:
                    comp_conf['BIN_DIR'] = sim_conf['BIN_DIR']
            if 'BIN_PATH' not in comp_conf:
                if 'BIN_PATH' in sim_conf:
                    comp_conf['BIN_PATH'] = sim_conf['BIN_PATH']
                else:
                    comp_conf['BIN_PATH'] = comp_conf['BIN_DIR']
            if not self.required_fields.issubset(conf_fields):
                msg = 'Error: missing required entries {} in simulation {} component {} configuration section'.format(
                    list(self.required_fields - conf_fields), sim_name, comp_ref)
                self.fwk.critical(msg)
                raise RuntimeError(msg)
            component_id = self._create_component(comp_conf, sim_data)
            sim_data.port_map[port] = component_id
            if port == 'DRIVER':
                sim_data.driver_comp = component_id
            elif port == 'INIT':
                sim_data.init_comp = component_id

        if sim_data.driver_comp is None:
            msg = 'Missing DRIVER specification in config file for simulation {}'.format(sim_data.sim_name)
            self.fwk.critical(msg)
            raise RuntimeError(msg)
        if sim_data.init_comp is None:
            self.fwk.warning('Missing INIT specification in ' +
                             'config file for simulation %s', sim_data.sim_name)

    def _create_component(self, comp_conf, sim_data):
        """
        Create component and populate it with the information from the
        component's configuration section.
        """
        sim_name = sim_data.sim_name
        class_name = comp_conf['NAME']

        if comp_conf['SCRIPT']:
            try:
                fullpath = os.path.abspath(comp_conf['SCRIPT'])
                script = comp_conf['SCRIPT'].rsplit('.', 1)[0].split('/')[-1]
                spec = importlib.util.spec_from_file_location(script, fullpath)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                component_class = getattr(module, class_name)
            except (FileNotFoundError, AttributeError):
                self.fwk.error('Error in configuration file : NAME = %s   SCRIPT = %s',
                               comp_conf['NAME'], comp_conf['SCRIPT'])
                self.fwk.exception('Error instantiating IPS component %s From %s', class_name, script)
                raise
        else:
            try:
                module = importlib.import_module(comp_conf['MODULE'])
                component_class = getattr(module, class_name)
            except (ModuleNotFoundError, AttributeError):
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
        return component_id

    def get_component_map(self):
        """
        Return a dictionary of simulation names and lists of component
        references.  (May only be the driver, and init (if present)???)
        """
        sim_comps = {}
        for sim_name in self.sim_map:
            if sim_name == self.fwk_sim_name:
                continue
            sim_comps[sim_name] = self.get_simulation_components(sim_name)
        return sim_comps

    def get_simulation_components(self, sim_name):
        comp_list = []
        sim_data = self.sim_map[sim_name]
        if sim_data.init_comp:
            comp_list.append(sim_data.init_comp)
        comp_list.append(sim_data.driver_comp)
        return comp_list

    def get_all_simulation_components_map(self):
        sim_comps = {name: sim_map.all_comps[:] for name, sim_map in self.sim_map.items()}
        del sim_comps[self.fwk_sim_name]
        return sim_comps

    def get_framework_components(self):
        """
        Return list of framework components.
        """
        fwk_components = self.fwk_components[:]
        return fwk_components

    def get_sim_parameter(self, sim_name, param):
        """
        Return value of *param* from simulation configuration file for
        *sim_name*.
        """
        try:
            sim_data = self.sim_map[sim_name]
        except KeyError:
            sim_data = self.finished_sim_map[sim_name]
        try:
            val = sim_data.sim_conf[param]
        except KeyError:
            val = self.platform_conf[param]
        self.fwk.debug('Returning value = %s for config parameter %s in simulation %s', val, param, sim_name)
        return val

    def get_sim_names(self):
        """
        Return list of names of simulations.
        """
        return list(self.sim_map.keys())

    def process_service_request(self, msg):
        """
        Invokes public configuration manager method for a component.  Return
        method's return value.
        """
        self.fwk.debug('Configuration Manager received message: %s', str(msg.__dict__))
        sim_name = msg.sender_id.get_sim_name()
        method = getattr(self, msg.target_method)
        self.fwk.debug('Configuration manager dispatching method %s on simulation %s',
                       method, sim_name)
        retval = method(sim_name, *msg.args)
        return retval

    def create_simulation(self, sim_name, config_file, override, sub_workflow=False):
        try:
            conf = ConfigObj(config_file, interpolation='template',
                             file_error=True)
        except IOError:
            self.fwk.exception('Error opening config file %s: ', config_file)
            raise
        except SyntaxError:
            self.fwk.exception(' Error parsing config file %s: ', config_file)
            raise
        parent_sim_name = sim_name
        parent_sim = self.sim_map[parent_sim_name]
        # Incorporate environment variables into config file
        # Use config file entries when duplicates are detected
        conf_keys = list(conf.keys())
        for (k, v) in os.environ.items():
            # Do not include functions from environment
            if k not in conf_keys and \
                    not any(x in v for x in '{}()$'):
                conf[k] = v

        # Allow propagation of entries from platform config file to simulation
        # config file
        for keyword in list(self.platform_conf.keys()):
            if keyword not in list(conf.keys()):
                conf[keyword] = self.platform_conf[keyword]
        if override:
            for kw in list(override.keys()):
                conf[kw] = override[kw]
        try:
            sim_name = conf['SIM_NAME']
            sim_root = conf['SIM_ROOT']
            log_file = os.path.abspath(conf['LOG_FILE'])
        except KeyError:
            self.fwk.exception('Missing required parameters SIM_NAME, SIM_ROOT or LOG_FILE\
in configuration file %s', config_file)
            raise
        if sim_name in self.sim_name_list:
            self.fwk.error('Error: Duplicate SIM_NAME %s in configuration files' % (sim_name))
            raise Exception('Duplicate SIM_NAME %s in configuration files' % (sim_name))
        if sim_root in self.sim_root_list:
            self.fwk.exception('Error: Duplicate SIM_ROOT in configuration files')
            raise Exception('Duplicate SIM_ROOT in configuration files')
        if log_file in self.log_file_list:
            self.fwk.exception('Error: Duplicate LOG_FILE in configuration files')
            raise Exception('Duplicate LOG_FILE in configuration files')

        # Add path to configuration file to simulation configuration in memory
        if 'SIMULATION_CONFIG_FILE' not in conf:
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
            new_sim.log_pipe_name = f'{tempfile.gettempdir()}/ips_{uuid.uuid4()}.logpipe'
            self.log_dynamic_sim_queue.put('CREATE_SIM  %s  %s' % (new_sim.log_pipe_name, new_sim.log_file))
        else:
            new_sim.portal_sim_name = parent_sim.portal_sim_name
            new_sim.log_pipe_name = parent_sim.log_pipe_name

        conf['__PORTAL_SIM_NAME'] = new_sim.portal_sim_name
        self.sim_map[sim_name] = new_sim
        self._initialize_sim(new_sim)

        if not sub_workflow:
            self.fwk.initiate_new_simulation(sim_name)

        return (sim_name, new_sim.init_comp, new_sim.driver_comp)

    def get_port(self, sim_name, port_name):
        """
        Return a reference to the component from simulation *sim_name*
        implementing port *port_name*.
        """
        sim_data = self.sim_map[sim_name]
        comp_id = sim_data.port_map[port_name]
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
        if target_sim_name == self.fwk_sim_name:  # apply to all simulations
            target_sims = list(self.sim_map.keys())
        else:
            target_sims = [target_sim_name]
        for other_sim_name in target_sims:
            self.fwk.debug('Setting %s to %s in simulation %s', param, value, other_sim_name)
            try:
                sim_data = self.sim_map[other_sim_name]
            except KeyError:
                sim_data = self.finished_sim_map[other_sim_name]
            self.fwk.debug('Setting %s to %s in simulation %s', param, value, other_sim_name)
            sim_conf = sim_data.sim_conf
            sim_conf[param] = value

        return value

    def get_platform_parameter(self, param, silent=False):
        """
        Return value of platform parameter *param*.  If *silent* is ``False``
        (default) ``None`` is returned when *param* not found, otherwise an
        exception is raised.
        """
        val = None
        try:
            val = self.platform_conf[param]
        except KeyError:
            if not silent:
                self.fwk.warning('CM: No platform data for %s ', param)
                raise
        return val

    def terminate_sim(self, sim_name):
        sim_data = self.sim_map[sim_name]
        all_sim_components = sim_data.all_comps
        msg = 'END_SIM %s' % (sim_data.log_pipe_name)
        self.log_dynamic_sim_queue.put(msg)
        proc_list = sim_data.process_list
        for p in proc_list:
            p.terminate()
            p.join()
        try:
            os.remove(sim_data.log_pipe_name)
        except Exception:
            pass
        for comp_id in all_sim_components:
            self.comp_registry.removeEntry(comp_id)
        sim_data.logger = None
        sim_data.process_list = []
        self.finished_sim_map[sim_name] = sim_data
        del self.sim_map[sim_name]

    def terminate(self, status):
        """
        Terminates all processes attached to the framework.  *status* not used.
        """
        try:
            for sim_name in list(self.sim_map.keys()):
                self.terminate_sim(sim_name)
        except Exception:
            print('Encountered exception when terminating simulation')
            raise
        for k in list(self.sim_map.keys()):
            del self.sim_map[k]
        self.log_process.terminate()
