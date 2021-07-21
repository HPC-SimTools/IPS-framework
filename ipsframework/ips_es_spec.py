# -------------------------------------------------------------------------------
# Copyright 2006-2021 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
from .cca_es_spec import EventListener, PublisherEventService, SubscriberEventService


class myEventListener(EventListener):
    def __init__(self, callback_method):
        super().__init__()
        self.callback_method = callback_method

    def processEvent(self, topicName, theEvent):
        self.callback_method(topicName, theEvent)


class eventManager:
    def __init__(self, obj_ref):
        self.obj_ref = obj_ref
        self.objcache = {}
        self.publisher = "self.publisher"
        self.subscriber = "self.subscriber"

    def publish(self, topicName, eventName, eventBody):
        if self.publisher in self.objcache:
            pub = self.objcache[self.publisher]
        else:
            pub = PublisherEventService()
            self.objcache[self.publisher] = pub

        topic = pub.getTopic(topicName)
        topic.sendEvent(eventName, eventBody)

    def subscribe(self, topicName, callback):
        if not callable(callback):
            callback_method = getattr(self.obj_ref, callback, None)
        else:
            callback_method = callback

        if not callback_method:
            # TODO: do we notify the client that the callback is invalid?
            #      throw an exception?
            return

        if self.subscriber in self.objcache:
            sub = self.objcache[self.subscriber]
        else:
            sub = SubscriberEventService()
            self.objcache[self.subscriber] = sub

        if topicName in self.objcache:
            # TODO: do we notify the client to do an unsubscribe before
            #      re-subscribing to the same topic? the event service
            #      currently throws an exception in this scenario...
            scp = self.objcache[topicName]
        else:
            scp = sub.getSubscription(topicName)
            self.objcache[topicName] = scp

        evl = myEventListener(callback_method)
        scp.registerEventListener(topicName, evl)

    def unsubscribe(self, topicName):
        if topicName in self.objcache:
            self.objcache[topicName].unregisterEventListener(topicName)
            del self.objcache[topicName]
        # else:
            # TODO: do we notify the client to do a subscribe first?
            #      throw an exception?

    def process_events(self):
        if self.subscriber in self.objcache:
            self.objcache[self.subscriber].processEvents()
        # else:
            # TODO: do we notify the client to do a subscribe before processing?
            #      throw an exception?
