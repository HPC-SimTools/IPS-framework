# -------------------------------------------------------------------------------
# Copyright 2006-2022 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
"""
The CCA event service, but without CCA-specific extensions:
https://www.cca-forum.org/wiki/tiki-index.php?page=Event+Specification+Proposal

It pretty much forwards calls to an event proxy which in turn talks to the
central event service.
"""

from copy import deepcopy

_proxy = None


class EventServiceError(Exception):
    """
    Exception class for the event service.
    """

    def __init__(self, value):
        super().__init__()
        self.value = value

    def __str__(self):
        return self.value


class PublisherEventService:
    """
    Interface to topics for publishers.
    """

    def get_topic(self, topic_name):
        """ """
        return _proxy.get_topic(topic_name)

    def exists_topic(self, topic_name):
        return _proxy.exists_topic(topic_name)


class SubscriberEventService:
    def __init__(self):
        self.subscriberid = _proxy.register_subscriber()

    def get_subscription(self, subscription_name):
        """
        A Subscription object can be safely returned from here without screwing
        up automatic object tracking for cleaning up out-of-scope subscriptions.
        A framework/component subscriber uses this Subscription object to
        talk to the event service.
        """
        _proxy.get_subscription(self.subscriberid, subscription_name)
        return Subscription(self.subscriberid, subscription_name)

    def process_events(self):
        _proxy.process_events(self.subscriberid)

    def __del__(self):
        _proxy.unregister_subscriber(self.subscriberid)


class Event:
    def __init__(self, header, body):
        self.header = deepcopy(header)
        self.body = deepcopy(body)

    def get_header(self):
        return self.header

    def get_body(self):
        return self.body

    def __str__(self) -> str:
        return str(self.body)


class EventListener:
    def __init__(self):
        self.listenerid = _proxy.create_listener()

    def process_event(self, topic_name, the_event):
        """
        A listener implements the process_event method to respond to an event,
        thereby overriding the below invocation. Ideally, it should be an abstract
        method, but currently serves to check the correct operation of the
        event service.
        """


class Topic:
    def __init__(self, topic_name):
        self.topic_name = topic_name

    def get_topic_name(self):
        return self.topic_name

    def send_event(self, event_name, event_body):
        _proxy.send_event(self.topic_name, event_name, event_body)


class Subscription:
    def __init__(self, subscriberid, subscription_name):
        self.subscriberid = subscriberid
        self.subscription_name = subscription_name

    def register_event_listener(self, listener_key, the_listener):
        _proxy.register_event_listener(
            self.subscriberid,
            self.subscription_name,
            listener_key,
            the_listener.listenerid,
            the_listener,
        )

    def unregister_event_listener(self, listener_key):
        _proxy.unregister_event_listener(self.subscriberid, self.subscription_name, listener_key)

    def get_subscription_name(self):
        return self.subscription_name

    def __del__(self):
        _proxy.remove_subscription(self.subscriberid, self.subscription_name)


""" Initialize the proxy """


def initialize_event_service(service):
    global _proxy  # noqa: PLW0603

    if isinstance(service, EventService):
        _proxy = EventServiceFwkProxy(service)
    else:
        _proxy = EventServiceCmpProxy(service)


from .event_service import EventService
from .event_service_proxy import EventServiceCmpProxy, EventServiceFwkProxy
