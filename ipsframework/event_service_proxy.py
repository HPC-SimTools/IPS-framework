# -------------------------------------------------------------------------------
# Copyright 2006-2022 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------


class EventServiceProxy:
    def get_topic(self, topic_name):
        pass

    def exists_topic(self, topic_name):
        pass

    def register_subscriber(self):
        pass

    def unregister_subscriber(self, subscriberid):
        pass

    def get_subscription(self, subscriberid, subscription_name):
        pass

    def process_events(self, subscriberid):
        pass

    def send_event(self, topic_name, event_name, event_body):
        pass

    def create_listener(self):
        pass

    def register_event_listener(
        self, subscriberid, subscription_name, listener_key, listenerid, ref_listener
    ):
        pass

    def unregister_event_listener(self, subscriberid, subscription_name, listener_key):
        pass

    def remove_subscription(self, subscriberid, subscription_name):
        pass


# TODO: Is eventService.py the right placeholder for this class?#
class EventServiceFwkProxy(EventServiceProxy):
    def __init__(self, event_service):
        self.event_service = event_service
        self.listenerDirectory = {}

    def get_topic(self, topic_name):
        return self.event_service.get_topic(topic_name)

    def exists_topic(self, topic_name):
        return self.event_service.exists_topic(topic_name)

    def register_subscriber(self):
        return self.event_service.register_subscriber()

    def unregister_subscriber(self, subscriberid):
        listener_list = self.event_service.unregister_subscriber(subscriberid)
        for listenerid in listener_list:
            self._remove_event_listener(listenerid)

    def get_subscription(self, subscriberid, subscription_name):
        self.event_service.get_subscription(subscriberid, subscription_name)

    def process_events(self, subscriberid):
        event_list = self.event_service.process_events(subscriberid)
        for listenerid in event_list:
            for topic_name in event_list[listenerid]:
                for the_event in event_list[listenerid][topic_name]:
                    self.listenerDirectory[listenerid].process_event(topic_name, the_event)

    def send_event(self, topic_name, event_name, event_body):
        self.event_service.send_event(topic_name, event_name, event_body)

    def create_listener(self):
        return self.event_service.create_listener()

    def register_event_listener(
        self, subscriberid, subscription_name, listener_key, listenerid, ref_listener
    ):
        self.event_service.register_event_listener(
            subscriberid, subscription_name, listener_key, listenerid
        )
        self._add_event_listener(listenerid, ref_listener)

    def unregister_event_listener(self, subscriberid, subscription_name, listener_key):
        listenerid = self.event_service.unregister_event_listener(
            subscriberid, subscription_name, listener_key
        )
        self._remove_event_listener(listenerid)

    def remove_subscription(self, subscriberid, subscription_name):
        listener_list = self.event_service.remove_subscription(subscriberid, subscription_name)
        for listenerid in listener_list:
            self._remove_event_listener(listenerid)

    def _add_event_listener(self, listenerid, ref_listener):
        if listenerid not in self.listenerDirectory:
            self.listenerDirectory[listenerid] = ref_listener

    def _remove_event_listener(self, listenerid):
        if listenerid in self.listenerDirectory:
            del self.listenerDirectory[listenerid]


# TODO: Is services.py the right placeholder for this class?#
class EventServiceCmpProxy(EventServiceProxy):
    def __init__(self, service_proxy):
        self.service_proxy = service_proxy
        self.listenerDirectory = {}

    def get_topic(self, topic_name):
        msg_id = self.service_proxy._invoke_service(
            self.service_proxy.fwk.component_id, 'get_topic', topic_name
        )
        return self.service_proxy._get_service_response(msg_id, True)

    def exists_topic(self, topic_name):
        msg_id = self.service_proxy._invoke_service(
            self.service_proxy.fwk.component_id, 'exists_topic', topic_name
        )
        return self.service_proxy._get_service_response(msg_id, True)

    def register_subscriber(self):
        msg_id = self.service_proxy._invoke_service(
            self.service_proxy.fwk.component_id, 'register_subscriber'
        )
        return self.service_proxy._get_service_response(msg_id, True)

    def unregister_subscriber(self, subscriberid):
        msg_id = self.service_proxy._invoke_service(
            self.service_proxy.fwk.component_id, 'unregister_subscriber', subscriberid
        )
        listener_list = self.service_proxy._get_service_response(msg_id, True)
        for listenerid in listener_list:
            self._remove_event_listener(listenerid)

    def get_subscription(self, subscriberid, subscription_name):
        msg_id = self.service_proxy._invoke_service(
            self.service_proxy.fwk.component_id, 'get_subscription', subscriberid, subscription_name
        )
        self.service_proxy._get_service_response(msg_id, True)

    def process_events(self, subscriberid):
        msg_id = self.service_proxy._invoke_service(
            self.service_proxy.fwk.component_id, 'process_events', subscriberid
        )
        event_list = self.service_proxy._get_service_response(msg_id, True)
        for listenerid in event_list:
            for topic_name in event_list[listenerid]:
                for the_event in event_list[listenerid][topic_name]:
                    self.listenerDirectory[listenerid].process_event(topic_name, the_event)

    def send_event(self, topic_name, event_name, event_body):
        msg_id = self.service_proxy._invoke_service(
            self.service_proxy.fwk.component_id, 'send_event', topic_name, event_name, event_body
        )
        self.service_proxy._get_service_response(msg_id, True)

    def create_listener(self):
        msg_id = self.service_proxy._invoke_service(
            self.service_proxy.fwk.component_id, 'create_listener'
        )
        return self.service_proxy._get_service_response(msg_id, True)

    def register_event_listener(
        self, subscriberid, subscription_name, listener_key, listenerid, ref_listener
    ):
        msg_id = self.service_proxy._invoke_service(
            self.service_proxy.fwk.component_id,
            'register_event_listener',
            subscriberid,
            subscription_name,
            listener_key,
            listenerid,
        )
        self.service_proxy._get_service_response(msg_id, True)
        self._add_event_listener(listenerid, ref_listener)

    def unregister_event_listener(self, subscriberid, subscription_name, listener_key):
        msg_id = self.service_proxy._invoke_service(
            self.service_proxy.fwk.component_id,
            'unregister_event_listener',
            subscriberid,
            subscription_name,
            listener_key,
        )
        listenerid = self.service_proxy._get_service_response(msg_id, True)
        self._remove_event_listener(listenerid)

    def remove_subscription(self, subscriberid, subscription_name):
        msg_id = self.service_proxy._invoke_service(
            self.service_proxy.fwk.component_id,
            'remove_subscription',
            subscriberid,
            subscription_name,
        )
        listener_list = self.service_proxy._get_service_response(msg_id, True)
        for listenerid in listener_list:
            self._remove_event_listener(listenerid)

    def _add_event_listener(self, listenerid, ref_listener):
        if listenerid not in self.listenerDirectory:
            self.listenerDirectory[listenerid] = ref_listener

    def _remove_event_listener(self, listenerid):
        if listenerid in self.listenerDirectory:
            del self.listenerDirectory[listenerid]
