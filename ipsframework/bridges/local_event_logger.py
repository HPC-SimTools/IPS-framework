import datetime
import glob
import hashlib
import itertools
import json
import os
import re
import time
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from ipsframework import ipsutil
from ipsframework.convert_log_function import convert_logdata_to_html
from ipsframework.services import ServicesProxy

if TYPE_CHECKING:
    from io import FileIO


def hash_file(file_name):  # pragma: no cover
    """
    Return the MD5 hash of a file
    :rtype: str
    :param file_name: Full path to file
    :return: MD5 of file_name
    """
    BLOCKSIZE = 65536
    hasher = hashlib.md5()
    with open(file_name, 'rb') as afile:
        buf = afile.read(BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(BLOCKSIZE)
    return hasher.hexdigest()


class SimulationData:
    """
    Container for simulation data.
    """

    def __init__(self):
        self.counter = 0
        self.monitor_file_name = ''
        self.portal_runid = ''
        self.parent_portal_runid = ''
        self.sim_name = ''
        self.sim_root = ''
        self.monitor_file: FileIO = None  # type: ignore
        self.json_monitor_file: FileIO = None  # type: ignore
        self.phys_time_stamp = -1
        self.monitor_url = ''
        self.mpo_steps = [None]
        self.mpo_wid = None
        self.bigbuf = ''


class LocalEventLogger:
    """The LocalEventLogger class manages event logging for the supplemental bridge components."""

    def __init__(self) -> None:
        # self.curTime = time.localtime()
        # self.startTime = self.curTime
        self.mpo = None
        self.mpo_name_counter: defaultdict[str, int] = defaultdict(lambda: 0)
        self.counter = 0
        self.dump_freq = 10
        self.min_dump_interval = 300  # Minimum time interval in Sec for HTML dump operation
        self.last_dump_time = time.time()
        self.write_to_htmldir = True
        self.html_dir = ''
        self.first_portal_runid = None

    def init(self, services: ServicesProxy) -> None:
        """Called from the bridge component's `init` function."""
        try:
            freq = int(services.get_config_param('HTML_DUMP_FREQ', silent=True))
        except Exception:
            pass
        else:
            self.dump_freq = freq

        try:
            self.html_dir = services.get_config_param('USER_W3_DIR', silent=True) or ''
        except Exception:
            services.warning('Missing USER_W3_DIR configuration - disabling web-visible logging')
            self.write_to_htmldir = False
        else:
            if self.html_dir.strip() == '':
                services.warning('Empty USER_W3_DIR configuration - disabling web-visible logging')
                self.write_to_htmldir = False
            else:
                try:
                    os.mkdir(self.html_dir)
                except FileExistsError:
                    pass
                except Exception:
                    services.warning('Unable to create HTML directory - disabling web-visible logging')
                    self.write_to_htmldir = False

    def finalize(self, sim_map: dict[str, SimulationData]) -> None:
        for sim_data in sim_map.values():
            try:
                sim_data.monitor_file.close()
                sim_data.json_monitor_file.close()
            except Exception:
                pass

    def init_simulation(self, services: ServicesProxy, sim_name: str, sim_root: str, hostname: str, username: str) -> SimulationData:
        """
        Create and send information about simulation *sim_name* living in
        *sim_root* so the portal can set up corresponding structures to manage
        data from the sim.

        :returns:
        """
        sim_data = SimulationData()
        sim_data.sim_name = sim_name
        sim_data.sim_root = sim_root

        d = datetime.datetime.now()
        date_str = '%s.%03d' % (d.strftime('%Y-%m-%dT%H:%M:%S'), int(d.microsecond / 1000))
        sim_data.portal_runid = f'{sim_name}_{hostname}_{username}_{date_str}'
        try:
            services.set_config_param('PORTAL_RUNID', sim_data.portal_runid, target_sim_name=sim_name)
        except Exception:
            services.error('Simulation %s is not accessible', sim_name)
            return

        if self.first_portal_runid:
            sim_data.parent_portal_runid = self.first_portal_runid
        else:
            self.first_portal_runid = sim_data.portal_runid

        if sim_data.sim_root.strip() == '.':
            sim_data.sim_root = os.environ['IPS_INITIAL_CWD']
        sim_log_dir = os.path.join(sim_data.sim_root, 'simulation_log')
        try:
            os.makedirs(sim_log_dir, exist_ok=True)
        except OSError as oserr:
            services.exception('Error creating Simulation Log directory %s : %d %s' % (sim_log_dir, oserr.errno, oserr.strerror))
            raise

        sim_data.monitor_file_name = os.path.join(sim_log_dir, sim_data.portal_runid + '.eventlog')
        try:
            sim_data.monitor_file = open(sim_data.monitor_file_name, 'wb', 0)
        except IOError as oserr:
            services.error('Error opening file %s: error(%s): %s' % (sim_data.monitor_file_name, oserr.errno, oserr.strerror))
            services.error('Using /dev/null instead')
            sim_data.monitor_file = open('/dev/null', 'w')
        json_fname = sim_data.monitor_file_name.replace('eventlog', 'jsonl')
        sim_data.json_monitor_file = open(json_fname, 'w')

        if self.mpo:  # pragma: no cover
            try:
                sim_data.mpo_wid = self.mpo.init(name='SWIM Workflow ' + os.environ['USER'], desc=sim_data.sim_name, wtype='SWIM')
                print('sim_data.mpo_wid = ', sim_data.mpo_wid)
            except Exception as e:
                print(e)
                print('sim_data.mpo_wid = ', sim_data.mpo_wid)
                sim_data.mpo_wid = None
            else:
                sim_data.mpo_steps = [sim_data.mpo_wid['uid']]

        return sim_data

    def send_event(self, services: ServicesProxy, sim_data: SimulationData, event_data: dict[str, Any]):
        """
        Send contents of *event_data* and *sim_data* to portal.
        """
        timestamp = ipsutil.getTimeString()
        buf = '%8d %s ' % (sim_data.counter, timestamp)
        for k, v in event_data.items():
            if len(str(v).strip()) == 0:
                continue
            if ' ' in str(v):
                buf += "%s='%s' " % (k, str(v))
            else:
                buf += '%s=%s ' % (k, str(v))
        buf += '\n'
        sim_data.monitor_file.write(bytes(buf, encoding='UTF-8'))
        sim_data.bigbuf += buf

        buf = json.dumps(event_data)
        sim_data.json_monitor_file.write('%s\n' % buf)

        freq = self.dump_freq
        if ((self.counter % freq == 0) and (time.time() - self.last_dump_time > self.min_dump_interval)) or (event_data['eventtype'] == 'IPS_END'):
            self.last_dump_time = time.time()
            html_filename = sim_data.monitor_file_name.replace('eventlog', 'html')
            html_page = convert_logdata_to_html(sim_data.bigbuf)
            open(html_filename, 'w').writelines(html_page)
            if self.write_to_htmldir:
                html_file = os.path.join(self.html_dir, os.path.basename(html_filename))
                try:
                    open(html_file, 'w').writelines(html_page)
                except Exception:
                    services.exception('Error writing html file into USER_W3_DIR directory')
                    self.write_to_htmldir = False

        if sim_data.mpo_wid:
            self.send_mpo_data(event_data, sim_data)

    def send_mpo_data(self, event_data, sim_data: SimulationData):  # pragma: no cover
        def md5(fname):
            "Courtesy of stackoverflow 3431825"
            hash_md5 = hashlib.md5()
            with open(fname, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()

        def mpo_add_file(workflow, parent, file, shortname='Need a name', longdesc='did not add a description.'):
            """Add a local file to the workflow attaching to parent. Calculate
            checksum and if the file is already in the mpo database, use the
            already the UID of the already existing file when adding the data
            object - this creates a linkage to the original. The checksum and
            local file path and name are added as metadata.

            This function relies on the user space metadata, ips_checksum
            and ips_filename. The checksum is the md5 sum and the filename
            is expected should have at least a relative qualifying path.

            workflow : workflow_id
            parent : parent_id
            """
            # if file exist, look for its checksum in the database
            try:
                checksum = md5(file)
            except Exception:
                print(('checksum could not find file:', file))
                raise

            is_checksum = self.mpo.search('metadata', params={'key': 'ips_checksum', 'value': checksum})
            # search always returns a list of dictionaries
            # if checksum exists, use first dataobject that has it
            # api search results are sorted by time
            # Note, check this with eqdsk dataobject in test-api
            print('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
            print(len(is_checksum), file)
            print('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')

            if len(is_checksum) > 0:
                # uid is chosen to be first occurrence
                # parent_uid is uid of object metadata is attached to.
                file_uid = is_checksum[0]['parent_uid']

                # Create dataobject reference by uid in the workflow
                dataobject = self.mpo.add(workflow, parent, uid=file_uid, name=shortname, desc=longdesc)
                self.mpo.meta(dataobject['uid'], 'ips_checksum', checksum)
                # add filename metadata the dataobject reference
                self.mpo.meta(dataobject['uid'], 'ips_filename', file)
            else:
                print(('file', file))
                file_uri = file
                # Create new dataobject by uri and insert reference in to workflow
                dataobject = self.mpo.add(workflow, parent, uri=file_uri, name=shortname, desc=longdesc)
                # add checksum metadata to original data object
                # add function currently only returns uri field, so fetch full record
                full_dataobject = self.mpo.search('dataobject/' + dataobject['uid'])[0]
                # add checksum so dataobject and also
                self.mpo.meta(full_dataobject['do_uid'], 'ips_checksum', checksum)
                self.mpo.meta(dataobject['uid'], 'ips_filename', file)
                self.mpo.meta(dataobject['uid'], 'ips_checksum', checksum)
                dataobject = full_dataobject
            return dataobject

        recordable_events = ['IPS_CALL_BEGIN', 'IPS_STAGE_INPUTS', 'IPS_STAGE_OUTPUTS', 'IPS_CALL_END']
        recordable_mpo_activities = ['IPS_CALL_BEGIN']
        comment = event_data['comment']
        event_type = event_data['eventtype']

        if event_type not in recordable_events:
            return
        inp_objs = []
        if event_type == 'IPS_CALL_END':
            del sim_data.mpo_steps[-1]
            return
        try:
            if event_type == 'IPS_STAGE_INPUTS':
                r = re.compile(r'^Elapsed time = ([0-9]*\.[0-9]*) Path = ([^ ]*) Files = (.*)')
                o = r.match(comment)
                (_, path, files) = o.groups()
                glist = [glob.glob(os.path.join(path, f)) for f in files.split()]
                for file_name in [os.path.basename(f) for f in itertools.chain(*glist)]:
                    mpo_data_obj = mpo_add_file(
                        sim_data.mpo_wid, sim_data.mpo_wid['uid'], os.path.join(path, file_name), shortname=file_name, longdesc='An input file'
                    )
                    inp_objs.append(mpo_data_obj['uid'])

            if event_type == 'IPS_STAGE_INPUTS' and not inp_objs:
                return

            count = self.mpo_name_counter[sim_data.sim_name + event_data['code']]
            if event_type == 'IPS_CALL_BEGIN':
                target = event_data['comment'].split()[-1]
                step_name = '%s %d' % (target, count)
            else:
                step_name = '{0:s} {1:s} {2:d}'.format(event_data['code'].split('_')[-1], event_type, count)

            if event_type == 'IPS_STAGE_OUTPUTS':
                r = re.compile(r'^Elapsed time = ([0-9]*\.[0-9]*) Path = ([^ ]*) Files = (.*)')
                o = r.match(comment)
                (_, path, files) = o.groups()
                if not files:
                    return
            activity = self.mpo.step(
                workflow_ID=sim_data.mpo_wid, parentobj_ID=sim_data.mpo_steps[-1], input_objs=inp_objs, name=step_name, desc='%s' % event_data['comment']
            )
            self.mpo_name_counter[sim_data.sim_name + event_data['code']] += 1
            if event_type == 'IPS_STAGE_OUTPUTS':
                glist = [glob.glob(os.path.join(path, f)) for f in files.split()]
                for file_name in [os.path.basename(f) for f in itertools.chain(*glist)]:
                    """
                    (f_uid, f_hash) = get_file_uid(path, file_name)
                    if f_uid:
                        mpo_data_obj = self.mpo.add(workflow_ID=sim_data.mpo_wid,
                                                parentobj_ID=activity['uid'],
                                                name=file_name,
                                                desc="An output file",
                                                uri='file:' + os.path.join(path, file_name),
                                                uid=f_uid,
                                                source = f_uid)
                    else:
                        mpo_data_obj = self.mpo.add(workflow_ID=sim_data.mpo_wid,
                                                parentobj_ID=activity['uid'],
                                                name=file_name,
                                                desc="An output file",
                                                uri='file:' + os.path.join(path, file_name))
                    """
                    mpo_data_obj = mpo_add_file(
                        sim_data.mpo_wid,
                        activity['uid'],
                        # sim_data.mpo_wid['uid'],
                        os.path.join(path, file_name),
                        shortname=file_name,
                        longdesc='An output file',
                    )

        except Exception as e:
            print('*************', e)
        else:
            if event_type in recordable_mpo_activities:
                sim_data.mpo_steps.append(activity['uid'])
