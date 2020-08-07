#-------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
#-------------------------------------------------------------------------------
from .component import Component
from ctypes import *


"""
Use exported max constants?
"""
class FTB_client_t(Structure):
    _fields_ = [('client_schema_ver', c_char * 8),
                ('event_space', c_char * 64),
                ('client_name', c_char * 16),
                ('client_jobid', c_char * 16),
                ('client_subscription_style', c_char * 32),
                ('client_polling_queue_len', c_uint)]

class FTB_client_id_t(Structure):
    _fields_ = [('region', c_char * 64),
                ('comp_cat', c_char * 64),
                ('comp', c_char * 64),
                ('client_name', c_char * 16),
                ('ext', c_uint8)]

class FTB_client_handle_t(Structure):
    _fields_ = [('valid', c_uint8),
                ('client_id', FTB_client_id_t)]

class FTB_event_t(Structure):
    _fields_ = [('region', c_char * 64),
                ('comp_cat', c_char * 64),
                ('comp', c_char * 64),
                ('event_name', c_char * 32),
                ('severity', c_char * 16),
                ('client_jobid', c_char * 16),
                ('client_name', c_char * 16),
                ('hostname', c_char * 64),
                ('seqnum', c_uint16),
                ('event_type', c_uint8),
                ('event_payload', c_char * 368)]

class FTB_subscribe_handle_t(Structure):
    _fields_ = [('client_handle', FTB_client_handle_t),
                ('subscription_event', FTB_event_t),
                ('subscription_type', c_uint8),
                ('valid', c_uint8)]

class FTB_location_id_t(Structure):
    _fields_ = [('hostname', c_char * 64),
                ('pid_starttime', c_char * 32),
                ('pid', c_int)]

class FTB_receive_event_t(Structure):
    _fields_ = [('event_space', c_char * 64),
                ('event_name', c_char * 32),
                ('severity', c_char * 16),
                ('client_jobid', c_char * 16),
                ('client_name', c_char * 16),
                ('client_extension', c_uint8),
                ('seqnum', c_uint16),
                ('incoming_src', FTB_location_id_t),
                ('event_type', c_uint8),
                ('event_payload', c_char * 368)]


class FTBBridge(Component):

    def __init__(self, services, config):
        Component.__init__(self, services, config)
        self.services = services
        self.libftb = None
        self.client_handle = None
        self.subscribe_handle = None
        self.done = False
        self.live_count = 0


    def init(self, timestamp=0.0):
        try:
            self.libftb = cdll.LoadLibrary("libftb.so")
        except:
            self.services.error("Unable to locate the FTB.")
            return

        #TODO: job_id should be passed in here
        client_info = FTB_client_t("0.5", "ftb.applications.swim", "IPS",
                                   "", "FTB_SUBSCRIPTION_POLLING")
        self.client_handle = FTB_client_handle_t()
        ret = self.libftb.FTB_Connect(byref(client_info), byref(self.client_handle))
        self.services.debug("FTB_Connect returned %d", ret)

        #TODO: Use FTB_SUCCESS instead of hard-coded value
        if ret == 0:
            self.subscribe_handle = FTB_subscribe_handle_t()
            #TODO: FTB does not seem to accept a subscription string like
            #      'event_name=NODE_UP,event_name=NODE_DOWN'
            ret = self.libftb.FTB_Subscribe(byref(self.subscribe_handle), self.client_handle,
                                    "event_name=all", None, None)
            self.services.debug("FTB_Subscribe returned %d", ret)

            #TODO: Use FTB_SUCCESS instead of hard-coded value
            if ret != 0:
                #TODO: Report specific error denoted by ret value instead of the general msg below
                self.services.error("Unable to subscribe to FTB events.")
                self.subscribe_handle = None
            else:
                self.services.subscribe('_IPS_FTB', self.handle_ips_events)
        else:
            #TODO: Report specific error denoted by ret value instead of the general msg below
            self.services.error("Unable to connect to the FTB.")
            self.client_handle = None


    def step(self, timestamp=0.0):
        if self.subscribe_handle:
            count = 1
            while not self.done:
                receive_event = FTB_receive_event_t()
                ret = self.libftb.FTB_Poll_event(self.subscribe_handle, byref(receive_event))

                #TODO: Use FTB_SUCCESS instead of hard-coded value
                if ret == 0:
                    eventBody = {}
                    #TODO: This will have to eventually translate from FTB NODE_UP/DOWN
                    #      fault payload to a list of nodes for use by IPS subscribers
                    eventBody["NODE_STATUS"] = receive_event.event_name
                    eventBody["NODE_LIST"] = [receive_event.event_payload]
                    self.services.publish("_IPS_NODE_STATUS",receive_event.event_name,eventBody)
                    self.services.debug("FTB_Poll_event returned %s %s", receive_event.event_name,eventBody)

                if count == 10:
                    count = 1
                    self.services.process_events()
                else:
                    count += 1


    def finalize(self, timestamp=0.0):
        if self.subscribe_handle:
            ret = self.libftb.FTB_Unsubscribe(byref(self.subscribe_handle))
            self.services.debug("FTB_Unsubscribe returned %d", ret)

            #TODO: Use FTB_SUCCESS instead of hard-coded value
            if ret != 0:
                #TODO: Report specific error denoted by ret value instead of the general msg below
                self.services.error("Failed to unsubscribe from FTB events.")

        if self.client_handle:
            ret = self.libftb.FTB_Disconnect(self.client_handle)
            self.services.debug("FTB_Disconnect returned %d", ret)

            #TODO: Use FTB_SUCCESS instead of hard-coded value
            if ret != 0:
                #TODO: Report specific error denoted by ret value instead of the general msg below
                self.services.error("Failed to disconnect from the FTB.")


    def handle_ips_events(self, topic, event):
        event_body = event.getBody()
        event_type = event_body['eventtype']
        if (event_type == 'IPS_START'):
            self.live_count += 1
        elif  (event_type == 'IPS_END'):
            self.live_count -= 1

        if (self.live_count == 0):
            self.done = True
