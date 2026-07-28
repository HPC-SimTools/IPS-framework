# -------------------------------------------------------------------------------
# Copyright 2006-2022 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
"""
This file hosts the central event service and is not directly accessible to IPS.
The cca_es_spec.py file provides a CCA-style event service interface to IPS,
with calls on the interface being routed here via the proxy. The CCA event
interface is straightforwardly mapped onto matching methods in this file.
"""

from .cca_es_spec import Event, EventServiceError, Topic
from .debug import debug
from .topic_manager import TopicManager


class EventService:
    def __init__(self, fwk=None):
        """
        The following two data structures are at the heart of the event service.
        The design and implementation of the event service becomes clear from
        the composition of these two structures.


        topicDirectory is a <topic,events> map, where topic is identified by
        topic_name and events are stored in an TopicManager object. The TopicManager
        class appears in topicManager.py and holds events posted to a topic.
        It also maintains the list of listeners subscribed to that topic.
        The topicDirectory is a flat listing of topics. A topic hierarchy can be
        built as an adjunct structure, without sacrificing topicDirectory. The
        topicDirectory facilitates very easy posting and propagation of events to
        topics and listeners respectively. The actual mechanics of it is hidden
        inside the TopicManager class.


        subscriberDirectory is a three-level nested map:
            subscriberid - subscription_name - listener_key - listenerid.

        This structure reflects the fact that a subscriber can create multiple
        subscriptions, a subscription in turn can comprise of multiple listenerKeys
        , and a listener_key is linked with one listenerid or listener object.
        """

        """ Singleton pattern """

        self.topicDirectory = {}
        self.subscriberDirectory = {}
        self.numSubscribers = 0
        self.numListeners = 0
        self.fwk = fwk
        if fwk:
            service_methods = [
                'get_topic',
                'exists_topic',
                'register_subscriber',
                'unregister_subscriber',
                'get_subscription',
                'process_events',
                'send_event',
                'create_listener',
                'register_event_listener',
                'unregister_event_listener',
                'remove_subscription',
            ]
            fwk.register_service_handler(service_methods, self.process_service_request)

    def _print_stats(self):
        if self.fwk:
            self.fwk.debug(':::::::::TOPIC-WISE EVENT STATS:::::::::')
            for topic_name, topic in self.topicDirectory.items():
                self.fwk.debug('%s = %s', topic_name, topic.get_event_stats())
            self.fwk.debug('::::::::::::::::::::::::::::::::::::::::')

    def process_service_request(self, msg):
        method = getattr(self, msg.target_method)
        return method(*msg.args)

    """""" """PublisherEventService methods start here""" """"""

    def get_topic(self, topic_name):
        """Add an entry to the topicDirectory for a new topic."""
        if topic_name not in self.topicDirectory:
            debug.output('get_topic %s' % topic_name)
            self.topicDirectory[topic_name] = TopicManager()
        return Topic(topic_name)

    def exists_topic(self, topic_name):
        return topic_name in self.topicDirectory

    """""" """PublisherEventService methods end here""" """"""

    """""" """SubscriberEventService methods start here""" """"""

    def register_subscriber(self):
        self.numSubscribers += 1
        subscriberid = self.numSubscribers
        self.subscriberDirectory[subscriberid] = {}
        debug.output('Subscriber registered', subscriberid)
        return subscriberid

    """
    unregister_subscriber is called when a subscriber object is being deleted.
    This involves removal of the subscriber's listener entries from
    listenerDirectory as well as all the TopicManagers corresponding to the
    topics on which the subscriber is registered. Finally the subscriber record
    in subscriberDirectory is purged.
    """

    def unregister_subscriber(self, subscriberid):
        listener_list = []
        if subscriberid in self.subscriberDirectory:
            debug.output('\n\n------Subscriber is unregistering', subscriberid)

            """
            Step through all the listeners for the subscriber in turn,
            first unregistering a listener from all subscribed topics and then
            deleting it from the listenerDirectory.
            """
            for subscription_name in self.subscriberDirectory[subscriberid]:
                for listener_key in self.subscriberDirectory[subscriberid][subscription_name]:
                    listenerid = self.subscriberDirectory[subscriberid][subscription_name][
                        listener_key
                    ]
                    debug.output(
                        'Unregistering listener on listener_key %s, subscription %s'
                        % (listener_key, subscription_name),
                        listenerid,
                        subscriberid,
                    )
                    topic_list = self._map_listener_key_to_topic_list(
                        subscription_name, listener_key
                    )
                    for topic_name in topic_list:
                        self.topicDirectory[topic_name].unregister_listener(listenerid)
                    debug.output(
                        'Listener on listener_key %s, subscription %s unregistered'
                        % (listener_key, subscription_name),
                        listenerid,
                        subscriberid,
                    )
                    listener_list.append(listenerid)
            """ Remove the subscriber entry in subscriberDirectory. """
            del self.subscriberDirectory[subscriberid]
            debug.output('Subscriber unregistered', subscriberid)
        else:
            raise EventServiceError('Subscriber not recognized.')
        return listener_list

    def get_subscription(self, subscriberid, subscription_name):
        if subscriberid in self.subscriberDirectory:
            """
            We do not allow for the possibility that a subscription_name may mean more
            than one topic name. May need to be changed in future for greater
            flexibility. Note that we do a get_topic here as a subscribe could happen
            before any publisher creates the particular topic.
            """
            self.get_topic(subscription_name)

            if subscription_name not in self.subscriberDirectory[subscriberid]:
                self.subscriberDirectory[subscriberid][subscription_name] = {}
                debug.output('Subscriber subscribed to %s' % subscription_name, subscriberid)

                """
                  A Subscription object cannot be safely returned without screwing
                  up automatic object tracking for cleaning up out-of-scope
                  subscriptions on the component side. The reason being a component
                  is handed a copy of the object returned from here, while the
                  object itself goes out-of-scope immediately, thereby triggering
                  a cleanup of the associated subscription, with the undesirable
                  result of a subscription becoming invalid even while the
                  component-side Subscription object is still in use.
                """
                # return Subscription(subscriberid,subscription_name)
            else:
                """ Should we permit duplicate subscription requests? """
                raise EventServiceError('Duplicate subscription request.')
        else:
            raise EventServiceError('Subscriber not recognized.')

    """
    A subscriber performs a process_events to learn about events posted to its
    topics of interest. This requires traversing the complete subscriber record
    in subscriberDirectory, and doing a process_event for every event sent since
    the last such call to topics on which the subscriber is registered.
    """

    def process_events(self, subscriberid):
        event_list = {}
        if subscriberid in self.subscriberDirectory:
            for subscription_name in self.subscriberDirectory[subscriberid]:
                for listener_key in self.subscriberDirectory[subscriberid][subscription_name]:
                    listenerid = self.subscriberDirectory[subscriberid][subscription_name][
                        listener_key
                    ]
                    """ This check is required to allow the _same_ listener to handle different topics. """
                    if listenerid not in event_list:
                        event_list[listenerid] = {}
                    topic_list = self._map_listener_key_to_topic_list(
                        subscription_name, listener_key
                    )
                    for topic_name in topic_list:
                        event_list[listenerid][topic_name] = self.topicDirectory[
                            topic_name
                        ].get_event_list_for_listener(listenerid)
        else:
            raise EventServiceError('Subscriber not recognized.')
        return event_list

    """""" """SubscriberEventService methods end here""" """"""

    """""" """Topic methods start here""" """"""

    """
    send_event adds an event to the topic's TopicManager object.
    """

    def send_event(self, topic_name, event_name, event_body):
        if topic_name in self.topicDirectory:
            event_header = {}
            event_header[event_name] = event_name
            the_event = Event(event_header, event_body)
            debug.output('Event %s sent to topic %s' % (the_event, topic_name))
            self.topicDirectory[topic_name].send_event(the_event)
        else:
            raise EventServiceError('Topic not recognized.')

    """""" """Topic methods end here""" """"""

    """""" """EventListener methods start here""" """"""

    def create_listener(self):
        self.numListeners += 1
        listenerid = self.numListeners
        debug.output('Listener created', listenerid)
        return listenerid

    """""" """EventListener methods end here""" """"""

    """""" """Subscription methods start here""" """"""

    """
    register_event_listener adds a listener to its subscriber's subscriberDirectory
    record, the TopicManager for the associated topic, and the listenerDirectory.
    """

    def register_event_listener(self, subscriberid, subscription_name, listener_key, listenerid):
        if subscriberid in self.subscriberDirectory:
            if subscription_name in self.subscriberDirectory[subscriberid]:
                """
                We do not allow for the possibility that a subscription_name may mean
                more than one topic name. May need to be changed in future for greater
                flexibility.
                """
                if subscription_name == listener_key:
                    if (
                        listener_key
                        not in self.subscriberDirectory[subscriberid][subscription_name]
                    ):
                        debug.output(
                            'Registering listener on listener_key %s, subscription %s'
                            % (listener_key, subscription_name),
                            listenerid,
                            subscriberid,
                        )
                        topic_list = self._map_listener_key_to_topic_list(
                            subscription_name, listener_key
                        )
                        for topic_name in topic_list:
                            self.topicDirectory[topic_name].register_listener(listenerid)
                        self.subscriberDirectory[subscriberid][subscription_name][listener_key] = (
                            listenerid
                        )
                    else:
                        """
                        Should we allow a listener_key to be re-registered before first
                        unregistering?
                        """
                        raise EventServiceError('Duplicate event listener.')
                else:
                    raise EventServiceError('Listener key not recognized.')
            else:
                raise EventServiceError('Subscription not recognized.')
        else:
            raise EventServiceError('Subscriber not recognized.')

    """
    unregister_event_listener removes a listener from its subscriber's
    subscriberDirectory record, the TopicManager for the associated topic, and
    the listenerDirectory.
    """

    def unregister_event_listener(self, subscriberid, subscription_name, listener_key):
        listenerid = -1
        if subscriberid in self.subscriberDirectory:
            if subscription_name in self.subscriberDirectory[subscriberid]:
                if listener_key in self.subscriberDirectory[subscriberid][subscription_name]:
                    listenerid = self.subscriberDirectory[subscriberid][subscription_name][
                        listener_key
                    ]
                    debug.output(
                        'Unregistering listener on listener_key %s, subscription %s'
                        % (listener_key, subscription_name),
                        listenerid,
                        subscriberid,
                    )
                    topic_list = self._map_listener_key_to_topic_list(
                        subscription_name, listener_key
                    )
                    for topic_name in topic_list:
                        self.topicDirectory[topic_name].unregister_listener(listenerid)
                    del self.subscriberDirectory[subscriberid][subscription_name][listener_key]
                    debug.output(
                        'Listener on listener_key %s, subscription %s unregistered'
                        % (listener_key, subscription_name),
                        listenerid,
                        subscriberid,
                    )
                else:
                    raise EventServiceError('Listener key not recognized.')
        """
        Do not raise exception if subscriberid/subscription_name turn out to be
        invalid as this can very well happen if subscriber/subscription object
        is garbage collected before its listener object. In such a scenario,
        unregister_subscriber/remove_subscription will clean up this listener also.
        """
        return listenerid

    """
    remove_subscription is called when a subscription object is being deleted.
    It unregisters associated listeners from their respective TopicManagers and the
    listenerDirectory, and then removes its subscription information from the
    subscriber entry in subscriberDirectory.
    """

    def remove_subscription(self, subscriberid, subscription_name):
        listener_list = []
        if subscriberid in self.subscriberDirectory:
            if subscription_name in self.subscriberDirectory[subscriberid]:
                debug.output(
                    "\n\n------Subscriber's subscription to %s is being removed"
                    % subscription_name,
                    subscriberid,
                )
                for listener_key in self.subscriberDirectory[subscriberid][subscription_name]:
                    listenerid = self.subscriberDirectory[subscriberid][subscription_name][
                        listener_key
                    ]
                    debug.output(
                        'Unregistering listener on listener_key %s, subscription %s'
                        % (listener_key, subscription_name),
                        listenerid,
                        subscriberid,
                    )
                    topic_list = self._map_listener_key_to_topic_list(
                        subscription_name, listener_key
                    )
                    for topic_name in topic_list:
                        self.topicDirectory[topic_name].unregister_listener(listenerid)
                    debug.output(
                        'Listener on listener_key %s, subscription %s unregistered'
                        % (listener_key, subscription_name),
                        listenerid,
                        subscriberid,
                    )
                    listener_list.append(listenerid)
                del self.subscriberDirectory[subscriberid][subscription_name]
                debug.output(
                    "Subscriber's subscription to %s removed" % subscription_name, subscriberid
                )
        """
        Do not raise exception if subscriberid/subscription_name turn out to be
        invalid as this can very well happen if subscriber object is garbage
        collected before its subscription object. In such a scenario,
        unregister_subscriber will clean up this subscription as well.
        """
        return listener_list

    """""" """Subscription methods end here""" """"""

    """""" """Methods internal to the event service start here""" """"""

    """
    A listener_key may specify a bunch of topics using wildcarding.
    Currently this is not supported. Need a more rigorous design to allow
    wildcarding.
    """

    def _map_listener_key_to_topic_list(self, subscription_name, listener_key):
        topic_list = []
        topic_list.append(listener_key)
        return topic_list

    """""" """Methods internal to the event service end here""" """"""
