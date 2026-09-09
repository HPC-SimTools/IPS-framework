# -------------------------------------------------------------------------------
# Copyright 2006-2022 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
from .cca_es_spec import EventListener, PublisherEventService, SubscriberEventService


class MyEventListener(EventListener):
    def __init__(self, callback_method):
        super().__init__()
        self.callback_method = callback_method

    def process_event(self, topic_name, the_event):
        self.callback_method(topic_name, the_event)


class EventManager:
    def __init__(self, obj_ref):
        self.obj_ref = obj_ref
        self.objcache = {}
        self._publisher_svc = None
        self._subscriber_svc = None

    def publish(self, topic_name, event_name, event_body):
        if self._publisher_svc is None:
            self._publisher_svc = PublisherEventService()

        topic = self._publisher_svc.get_topic(topic_name)
        topic.send_event(event_name, event_body)

    def subscribe(self, topic_name, callback):
        if not callable(callback):
            callback_method = getattr(self.obj_ref, callback, None)
        else:
            callback_method = callback

        if not callback_method:
            # TODO: do we notify the client that the callback is invalid?
            #      throw an exception?
            return

        if self._subscriber_svc is None:
            self._subscriber_svc = SubscriberEventService()

        if topic_name in self.objcache:
            # TODO: do we notify the client to do an unsubscribe before
            #      re-subscribing to the same topic? the event service
            #      currently throws an exception in this scenario...
            scp = self.objcache[topic_name]
        else:
            scp = self._subscriber_svc.get_subscription(topic_name)
            self.objcache[topic_name] = scp

        evl = MyEventListener(callback_method)
        scp.register_event_listener(topic_name, evl)

    def unsubscribe(self, topic_name):
        if topic_name in self.objcache:
            self.objcache[topic_name].unregister_event_listener(topic_name)
            del self.objcache[topic_name]
        # else:
        # TODO: do we notify the client to do a subscribe first?
        #      throw an exception?

    def process_events(self):
        if self._subscriber_svc is not None:
            self._subscriber_svc.process_events()
        # else:
        # TODO: do we notify the client to do a subscribe before processing?
        #      throw an exception?
