# -------------------------------------------------------------------------------
# Copyright 2006-2021 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
"""
This file hosts the central event service and is not directly accessible to IPS.
The cca_es_spec.py file provides a CCA-style event service interface to IPS,
with calls on the interface being routed here via the proxy. The CCA event
interface is straightforwardly mapped onto matching methods in this file.
"""
from .debug import debug
from .cca_es_spec import EventServiceException, Event, Topic
from .topicManager import TopicManager


class EventService:
    def __init__(self, fwk=None):
        """
        The following two data structures are at the heart of the event service.
        The design and implementation of the event service becomes clear from
        the composition of these two structures.


        topicDirectory is a <topic,events> map, where topic is identified by
        topicName and events are stored in an TopicManager object. The TopicManager
        class appears in topicManager.py and holds events posted to a topic.
        It also maintains the list of listeners subscribed to that topic.
        The topicDirectory is a flat listing of topics. A topic hierarchy can be
        built as an adjunct structure, without sacrificing topicDirectory. The
        topicDirectory facilitates very easy posting and propagation of events to
        topics and listeners respectively. The actual mechanics of it is hidden
        inside the TopicManager class.


        subscriberDirectory is a three-level nested map:
            subscriberid - subscriptionName - listenerKey - listenerid.

        This structure reflects the fact that a subscriber can create multiple
        subscriptions, a subscription in turn can comprise of multiple listenerKeys
        , and a listenerKey is linked with one listenerid or listener object.
        """

        """ Singleton pattern """

        self.topicDirectory = {}
        self.subscriberDirectory = {}
        self.numSubscribers = 0
        self.numListeners = 0
        self.fwk = fwk
        if fwk:
            service_methods = ['getTopic', 'existsTopic', 'registerSubscriber',
                               'unregisterSubscriber', 'getSubscription',
                               'processEvents', 'sendEvent', 'createListener',
                               'registerEventListener', 'unregisterEventListener',
                               'removeSubscription']
            fwk.register_service_handler(service_methods,
                                         getattr(self, 'process_service_request'))

    def _print_stats(self):
        if self.fwk:
            self.fwk.debug(":::::::::TOPIC-WISE EVENT STATS:::::::::")
            for topicName in list(self.topicDirectory.keys()):
                self.fwk.debug("%s = %s", topicName, self.topicDirectory[topicName].getEventStats())
            self.fwk.debug("::::::::::::::::::::::::::::::::::::::::")

    def process_service_request(self, msg):
        method = getattr(self, msg.target_method)
        return method(*msg.args)

    """""""""PublisherEventService methods start here"""""""""

    def getTopic(self, topicName):
        """ Add an entry to the topicDirectory for a new topic. """
        if topicName not in self.topicDirectory:
            debug.output("getTopic %s" % topicName)
            self.topicDirectory[topicName] = TopicManager()
        return Topic(topicName)

    def existsTopic(self, topicName):
        return topicName in self.topicDirectory

    """""""""PublisherEventService methods end here"""""""""

    """""""""SubscriberEventService methods start here"""""""""

    def registerSubscriber(self):
        self.numSubscribers += 1
        subscriberid = self.numSubscribers
        self.subscriberDirectory[subscriberid] = {}
        debug.output("Subscriber registered", subscriberid)
        return subscriberid

    """
    unregisterSubscriber is called when a subscriber object is being deleted.
    This involves removal of the subscriber's listener entries from
    listenerDirectory as well as all the TopicManagers corresponding to the
    topics on which the subscriber is registered. Finally the subscriber record
    in subscriberDirectory is purged.
    """

    def unregisterSubscriber(self, subscriberid):
        listenerList = []
        if subscriberid in self.subscriberDirectory:
            debug.output("\n\n------Subscriber is unregistering", subscriberid)

            """
            Step through all the listeners for the subscriber in turn,
            first unregistering a listener from all subscribed topics and then
            deleting it from the listenerDirectory.
            """
            for subscriptionName in list(self.subscriberDirectory[subscriberid].keys()):
                for listenerKey in list(self.subscriberDirectory[subscriberid][subscriptionName].keys()):
                    listenerid = self.subscriberDirectory[subscriberid][subscriptionName][listenerKey]
                    debug.output("Unregistering listener on listenerKey %s, subscription %s"
                                 % (listenerKey, subscriptionName), listenerid, subscriberid)
                    topicList = self._mapListenerKeytoTopicList(subscriptionName, listenerKey)
                    for topicName in topicList:
                        self.topicDirectory[topicName].unregisterListener(listenerid)
                    debug.output("Listener on listenerKey %s, subscription %s unregistered"
                                 % (listenerKey, subscriptionName), listenerid, subscriberid)
                    listenerList.append(listenerid)
            """ Remove the subscriber entry in subscriberDirectory. """
            del self.subscriberDirectory[subscriberid]
            debug.output("Subscriber unregistered", subscriberid)
        else:
            raise EventServiceException("Subscriber not recognized.")
        return listenerList

    def getSubscription(self, subscriberid, subscriptionName):
        if subscriberid in self.subscriberDirectory:
            """
            We do not allow for the possibility that a subscriptionName may mean more
            than one topic name. May need to be changed in future for greater
            flexibility. Note that we do a getTopic here as a subscribe could happen
            before any publisher creates the particular topic.
            """
            self.getTopic(subscriptionName)

            if subscriptionName not in self.subscriberDirectory[subscriberid]:
                self.subscriberDirectory[subscriberid][subscriptionName] = {}
                debug.output("Subscriber subscribed to %s" % subscriptionName, subscriberid)

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
                # return Subscription(subscriberid,subscriptionName)
            else:
                """ Should we permit duplicate subscription requests? """
                raise EventServiceException("Duplicate subscription request.")
        else:
            raise EventServiceException("Subscriber not recognized.")

    """
    A subscriber performs a processEvents to learn about events posted to its
    topics of interest. This requires traversing the complete subscriber record
    in subscriberDirectory, and doing a processEvent for every event sent since
    the last such call to topics on which the subscriber is registered.
    """

    def processEvents(self, subscriberid):
        eventList = {}
        if subscriberid in self.subscriberDirectory:
            for subscriptionName in list(self.subscriberDirectory[subscriberid].keys()):
                for listenerKey in list(self.subscriberDirectory[subscriberid][subscriptionName].keys()):
                    listenerid = self.subscriberDirectory[subscriberid][subscriptionName][listenerKey]
                    """ This check is required to allow the _same_ listener to handle different topics. """
                    if listenerid not in eventList:
                        eventList[listenerid] = {}
                    topicList = self._mapListenerKeytoTopicList(subscriptionName, listenerKey)
                    for topicName in topicList:
                        eventList[listenerid][topicName] = self.topicDirectory[topicName].getEventListForListener(listenerid)
        else:
            raise EventServiceException("Subscriber not recognized.")
        return eventList

    """""""""SubscriberEventService methods end here"""""""""

    """""""""Topic methods start here"""""""""

    """
    sendEvent adds an event to the topic's TopicManager object.
    """

    def sendEvent(self, topicName, eventName, eventBody):
        if topicName in self.topicDirectory:
            eventHeader = {}
            eventHeader[eventName] = eventName
            theEvent = Event(eventHeader, eventBody)
            debug.output("Event %s sent to topic %s" % (theEvent, topicName))
            self.topicDirectory[topicName].sendEvent(theEvent)
        else:
            raise EventServiceException("Topic not recognized.")

    """""""""Topic methods end here"""""""""

    """""""""EventListener methods start here"""""""""

    def createListener(self):
        self.numListeners += 1
        listenerid = self.numListeners
        debug.output("Listener created", listenerid)
        return listenerid

    """""""""EventListener methods end here"""""""""

    """""""""Subscription methods start here"""""""""

    """
    registerEventListener adds a listener to its subscriber's subscriberDirectory
    record, the TopicManager for the associated topic, and the listenerDirectory.
    """

    def registerEventListener(self, subscriberid, subscriptionName, listenerKey, listenerid):
        if subscriberid in self.subscriberDirectory:
            if subscriptionName in self.subscriberDirectory[subscriberid]:
                """
                We do not allow for the possibility that a subscriptionName may mean
                more than one topic name. May need to be changed in future for greater
                flexibility.
                """
                if subscriptionName == listenerKey:
                    if listenerKey not in self.subscriberDirectory[subscriberid][subscriptionName]:
                        debug.output("Registering listener on listenerKey %s, subscription %s"
                                     % (listenerKey, subscriptionName), listenerid, subscriberid)
                        topicList = self._mapListenerKeytoTopicList(subscriptionName, listenerKey)
                        for topicName in topicList:
                            self.topicDirectory[topicName].registerListener(listenerid)
                        self.subscriberDirectory[subscriberid][subscriptionName][listenerKey] = listenerid
                    else:
                        """
                        Should we allow a listenerKey to be re-registered before first
                        unregistering?
                        """
                        raise EventServiceException("Duplicate event listener.")
                else:
                    raise EventServiceException("Listener key not recognized.")
            else:
                raise EventServiceException("Subscription not recognized.")
        else:
            raise EventServiceException("Subscriber not recognized.")

    """
    unregisterEventListener removes a listener from its subscriber's
    subscriberDirectory record, the TopicManager for the associated topic, and
    the listenerDirectory.
    """

    def unregisterEventListener(self, subscriberid, subscriptionName, listenerKey):
        listenerid = -1
        if subscriberid in self.subscriberDirectory:
            if subscriptionName in self.subscriberDirectory[subscriberid]:
                if listenerKey in self.subscriberDirectory[subscriberid][subscriptionName]:
                    listenerid = self.subscriberDirectory[subscriberid][subscriptionName][listenerKey]
                    debug.output("Unregistering listener on listenerKey %s, subscription %s"
                                 % (listenerKey, subscriptionName), listenerid, subscriberid)
                    topicList = self._mapListenerKeytoTopicList(subscriptionName, listenerKey)
                    for topicName in topicList:
                        self.topicDirectory[topicName].unregisterListener(listenerid)
                    del self.subscriberDirectory[subscriberid][subscriptionName][listenerKey]
                    debug.output("Listener on listenerKey %s, subscription %s unregistered"
                                 % (listenerKey, subscriptionName), listenerid, subscriberid)
                else:
                    raise EventServiceException("Listener key not recognized.")
        """
        Do not raise exception if subscriberid/subscriptionName turn out to be
        invalid as this can very well happen if subscriber/subscription object
        is garbage collected before its listener object. In such a scenario,
        unregisterSubscriber/removeSubscription will clean up this listener also.
        """
        return listenerid

    """
    removeSubscription is called when a subscription object is being deleted.
    It unregisters associated listeners from their respective TopicManagers and the
    listenerDirectory, and then removes its subscription information from the
    subscriber entry in subscriberDirectory.
    """

    def removeSubscription(self, subscriberid, subscriptionName):
        listenerList = []
        if subscriberid in self.subscriberDirectory:
            if subscriptionName in self.subscriberDirectory[subscriberid]:
                debug.output("\n\n------Subscriber's subscription to %s is being removed"
                             % subscriptionName, subscriberid)
                for listenerKey in list(self.subscriberDirectory[subscriberid][subscriptionName].keys()):
                    listenerid = self.subscriberDirectory[subscriberid][subscriptionName][listenerKey]
                    debug.output("Unregistering listener on listenerKey %s, subscription %s"
                                 % (listenerKey, subscriptionName), listenerid, subscriberid)
                    topicList = self._mapListenerKeytoTopicList(subscriptionName, listenerKey)
                    for topicName in topicList:
                        self.topicDirectory[topicName].unregisterListener(listenerid)
                    debug.output("Listener on listenerKey %s, subscription %s unregistered"
                                 % (listenerKey, subscriptionName), listenerid, subscriberid)
                    listenerList.append(listenerid)
                del self.subscriberDirectory[subscriberid][subscriptionName]
                debug.output("Subscriber's subscription to %s removed"
                             % subscriptionName, subscriberid)
        """
        Do not raise exception if subscriberid/subscriptionName turn out to be
        invalid as this can very well happen if subscriber object is garbage
        collected before its subscription object. In such a scenario,
        unregisterSubscriber will clean up this subscription as well.
        """
        return listenerList

    """""""""Subscription methods end here"""""""""

    """""""""Methods internal to the event service start here"""""""""

    """
    A listenerKey may specify a bunch of topics using wildcarding.
    Currently this is not supported. Need a more rigorous design to allow
    wildcarding.
    """

    def _mapListenerKeytoTopicList(self, subscriptionName, listenerKey):
        topicList = []
        topicList.append(listenerKey)
        return topicList

    """""""""Methods internal to the event service end here"""""""""
