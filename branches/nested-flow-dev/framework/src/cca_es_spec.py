#-------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
#-------------------------------------------------------------------------------
"""
The CCA event service, but without CCA-specific extensions:
https://www.cca-forum.org/wiki/tiki-index.php?page=Event+Specification+Proposal

It pretty much forwards calls to an event proxy which in turn talks to the
central event service.
"""

class EventServiceException(Exception):
    """
    Exception class for the event service.
    """
    def __init__(self,value):
        self.value = value

    def __str__(self):
        return self.value


class PublisherEventService(object):
    """
    Interface to topics for publishers.
    """
    def getTopic(self,topicName):
        """

        """
        return _proxy.getTopic(topicName)

    def existsTopic(self,topicName):
        return _proxy.existsTopic(topicName)


class SubscriberEventService(object):
    def __init__(self):
        self.subscriberid = _proxy.registerSubscriber()

    def getSubscription(self,subscriptionName):
        """
        A Subscription object can be safely returned from here without screwing
        up automatic object tracking for cleaning up out-of-scope subscriptions.
        A framework/component subscriber uses this Subscription object to
        talk to the event service.
        """
        _proxy.getSubscription(self.subscriberid,subscriptionName)
        return Subscription(self.subscriberid,subscriptionName)

    def processEvents(self):
        _proxy.processEvents(self.subscriberid)

    def __del__(self):
        _proxy.unregisterSubscriber(self.subscriberid)


class Event(object):
    def __init__(self,header={},body={}):
        self.header = deepcopy(header)
        self.body = deepcopy(body)

    def getHeader(self):
        return self.header

    def getBody(self):
        return self.body

    def __str__(self):
        return str(self.body)


class EventListener(object):
    def __init__(self):
        self.listenerid = _proxy.createListener()

    def processEvent(self,topicName,theEvent):
        """
        A listener implements the processEvent method to respond to an event,
        thereby overriding the below invocation. Ideally, it should be an abstract
        method, but currently serves to check the correct operation of the
        event service.
        """
        #TODO: To be deleted#
        _proxy._processEvent(self.listenerid,topicName,theEvent)


class Topic(object):
    def __init__(self,topicName):
        self.topicName = topicName

    def getTopicName(self):
        return self.topicName

    def sendEvent(self,eventName,eventBody):
        _proxy.sendEvent(self.topicName,eventName,eventBody)


class Subscription(object):
    def __init__(self,subscriberid,subscriptionName):
        self.subscriberid = subscriberid
        self.subscriptionName = subscriptionName

    def registerEventListener(self,listenerKey,theListener):
        _proxy.registerEventListener(self.subscriberid,self.subscriptionName,
            listenerKey,theListener.listenerid,theListener)

    def unregisterEventListener(self,listenerKey):
        _proxy.unregisterEventListener(self.subscriberid,self.subscriptionName,listenerKey)

    def getSubscriptionName(self):
        return self.subscriptionName

    def __del__(self):
        _proxy.removeSubscription(self.subscriberid,self.subscriptionName)


""" Initialize the proxy """
def initialize_event_service(service):
    global _proxy

    if isinstance(service, EventService):
        _proxy = EventServiceFwkProxy(service)
    else:
        _proxy = EventServiceCmpProxy(service)


from eventService import EventService
from eventServiceProxy import EventServiceFwkProxy, EventServiceCmpProxy
from copy import deepcopy
