# -------------------------------------------------------------------------------
# Copyright 2006-2021 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------


class EventServiceProxy:
    def getTopic(self, topicName):
        pass

    def existsTopic(self, topicName):
        pass

    def registerSubscriber(self):
        pass

    def unregisterSubscriber(self, subscriberid):
        pass

    def getSubscription(self, subscriberid, subscriptionName):
        pass

    def processEvents(self, subscriberid):
        pass

    def sendEvent(self, topicName, eventName, eventBody):
        pass

    def createListener(self):
        pass

    def registerEventListener(self, subscriberid, subscriptionName, listenerKey, listenerid, refListener):
        pass

    def unregisterEventListener(self, subscriberid, subscriptionName, listenerKey):
        pass

    def removeSubscription(self, subscriberid, subscriptionName):
        pass


# TODO: Is eventService.py the right placeholder for this class?#
class EventServiceFwkProxy(EventServiceProxy):
    def __init__(self, event_service):
        self.event_service = event_service
        self.listenerDirectory = {}

    def getTopic(self, topicName):
        return self.event_service.getTopic(topicName)

    def existsTopic(self, topicName):
        return self.event_service.existsTopic(topicName)

    def registerSubscriber(self):
        return self.event_service.registerSubscriber()

    def unregisterSubscriber(self, subscriberid):
        listenerList = self.event_service.unregisterSubscriber(subscriberid)
        for listenerid in listenerList:
            self._removeEventListener(listenerid)

    def getSubscription(self, subscriberid, subscriptionName):
        self.event_service.getSubscription(subscriberid, subscriptionName)

    def processEvents(self, subscriberid):
        eventList = self.event_service.processEvents(subscriberid)
        for listenerid in list(eventList.keys()):
            for topicName in list(eventList[listenerid].keys()):
                for theEvent in eventList[listenerid][topicName]:
                    self.listenerDirectory[listenerid].processEvent(topicName, theEvent)

    def sendEvent(self, topicName, eventName, eventBody):
        self.event_service.sendEvent(topicName, eventName, eventBody)

    def createListener(self):
        return self.event_service.createListener()

    def registerEventListener(self, subscriberid, subscriptionName, listenerKey, listenerid, refListener):
        self.event_service.registerEventListener(subscriberid, subscriptionName, listenerKey, listenerid)
        self._addEventListener(listenerid, refListener)

    def unregisterEventListener(self, subscriberid, subscriptionName, listenerKey):
        listenerid = self.event_service.unregisterEventListener(subscriberid, subscriptionName, listenerKey)
        self._removeEventListener(listenerid)

    def removeSubscription(self, subscriberid, subscriptionName):
        listenerList = self.event_service.removeSubscription(subscriberid, subscriptionName)
        for listenerid in listenerList:
            self._removeEventListener(listenerid)

    def _addEventListener(self, listenerid, refListener):
        if listenerid not in self.listenerDirectory:
            self.listenerDirectory[listenerid] = refListener

    def _removeEventListener(self, listenerid):
        if listenerid in self.listenerDirectory:
            del self.listenerDirectory[listenerid]


# TODO: Is services.py the right placeholder for this class?#
class EventServiceCmpProxy(EventServiceProxy):
    def __init__(self, service_proxy):
        self.service_proxy = service_proxy
        self.listenerDirectory = {}

    def getTopic(self, topicName):
        msg_id = self.service_proxy._invoke_service(self.service_proxy.fwk.component_id,
                                                    'getTopic', topicName)
        return self.service_proxy._get_service_response(msg_id, True)

    def existsTopic(self, topicName):
        msg_id = self.service_proxy._invoke_service(self.service_proxy.fwk.component_id,
                                                    'existsTopic', topicName)
        return self.service_proxy._get_service_response(msg_id, True)

    def registerSubscriber(self):
        msg_id = self.service_proxy._invoke_service(self.service_proxy.fwk.component_id,
                                                    'registerSubscriber')
        return self.service_proxy._get_service_response(msg_id, True)

    def unregisterSubscriber(self, subscriberid):
        msg_id = self.service_proxy._invoke_service(self.service_proxy.fwk.component_id,
                                                    'unregisterSubscriber', subscriberid)
        listenerList = self.service_proxy._get_service_response(msg_id, True)
        for listenerid in listenerList:
            self._removeEventListener(listenerid)

    def getSubscription(self, subscriberid, subscriptionName):
        msg_id = self.service_proxy._invoke_service(self.service_proxy.fwk.component_id,
                                                    'getSubscription', subscriberid, subscriptionName)
        self.service_proxy._get_service_response(msg_id, True)

    def processEvents(self, subscriberid):
        msg_id = self.service_proxy._invoke_service(self.service_proxy.fwk.component_id,
                                                    'processEvents', subscriberid)
        eventList = self.service_proxy._get_service_response(msg_id, True)
        for listenerid in list(eventList.keys()):
            for topicName in list(eventList[listenerid].keys()):
                for theEvent in eventList[listenerid][topicName]:
                    self.listenerDirectory[listenerid].processEvent(topicName, theEvent)

    def sendEvent(self, topicName, eventName, eventBody):
        msg_id = self.service_proxy._invoke_service(self.service_proxy.fwk.component_id,
                                                    'sendEvent', topicName, eventName, eventBody)
        self.service_proxy._get_service_response(msg_id, True)

    def createListener(self):
        msg_id = self.service_proxy._invoke_service(self.service_proxy.fwk.component_id,
                                                    'createListener')
        return self.service_proxy._get_service_response(msg_id, True)

    def registerEventListener(self, subscriberid, subscriptionName, listenerKey, listenerid, refListener):
        msg_id = self.service_proxy._invoke_service(self.service_proxy.fwk.component_id,
                                                    'registerEventListener', subscriberid, subscriptionName, listenerKey, listenerid)
        self.service_proxy._get_service_response(msg_id, True)
        self._addEventListener(listenerid, refListener)

    def unregisterEventListener(self, subscriberid, subscriptionName, listenerKey):
        msg_id = self.service_proxy._invoke_service(self.service_proxy.fwk.component_id,
                                                    'unregisterEventListener', subscriberid, subscriptionName, listenerKey)
        listenerid = self.service_proxy._get_service_response(msg_id, True)
        self._removeEventListener(listenerid)

    def removeSubscription(self, subscriberid, subscriptionName):
        msg_id = self.service_proxy._invoke_service(self.service_proxy.fwk.component_id,
                                                    'removeSubscription', subscriberid, subscriptionName)
        listenerList = self.service_proxy._get_service_response(msg_id, True)
        for listenerid in listenerList:
            self._removeEventListener(listenerid)

    def _addEventListener(self, listenerid, refListener):
        if listenerid not in self.listenerDirectory:
            self.listenerDirectory[listenerid] = refListener

    def _removeEventListener(self, listenerid):
        if listenerid in self.listenerDirectory:
            del self.listenerDirectory[listenerid]
