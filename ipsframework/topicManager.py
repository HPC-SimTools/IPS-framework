# -------------------------------------------------------------------------------
# Copyright 2006-2021 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
"""
This file hosts the TopicManager class that manages the set of events and
listeners for a given topic. For reasons of efficient storage and O(1)-time
processing, TopicManager maintains a single list of events for the topic, and
marks the start of next event delivery in this list for individual listeners.
Listeners receive only the events that are published _after_ they have
registered. This simplifies event cleanup to a great deal and also avoids the
uncertainty that arises when trying to deliver prior events. Events not pending
processing by any listener are purged periodically as a result of a listener
activity like processing or unregistering. For cases where the event list could
grow unbounded in the absence of any listener activity for prolonged periods of
time, we could define a 'limitPendingEvents' parameter to denote a bound on the
count of pending events exceeding which triggers an event cleanup to remove
events that outlive a 'timeToLive' parameter.
"""

from .cca_es_spec import EventServiceException, Event
from .debug import debug


class TopicManager:
    def __init__(self, limitPendingEvents=10):
        """ eventList is the common listing of events posted to a topic. """
        self.eventList = []

        """
        listenerDirectory holds listeners alongside their event list
        markers.
        """
        self.listenerDirectory = {}

        """
        maxPendingEvents denotes the maximum number of events pending for this
        topic over the lifetime of an actual run.
        """
        self.maxPendingEvents = 0

        """
        A parameter to bound the memory for individual event queues; specifies an
        upper limit on the number of events permitted to be pending for this topic
        at any point in time. Not pressed into service yet.
        """
        self.limitPendingEvents = limitPendingEvents

        debug.output("TopicManager.__init__")
        self.printEventsAndListeners()

    """
    Append the event to the event list.
    """

    def sendEvent(self, theEvent):
        """
        A new event is appended to the end of the event list provided there is at
        least one registered listener. This is in accordance with the policy that
        listeners receive only those events that are published _after_ they
        have registered. An event that is published before any listener has
        registered will then never be consumed and hence is not stored. This also
        prevents the event list from growing in an unbounded manner when there are
        no registered listeners.
        """
        if len(self.listenerDirectory) > 0:
            self.eventList.append(theEvent)
            eventList_len = len(self.eventList)
            if eventList_len > self.maxPendingEvents:
                self.maxPendingEvents = eventList_len
        debug.output("TopicManager.sendEvent")
        self.printEventsAndListeners()

    def registerListener(self, listenerid):
        """
        For a new listener, the event list marker is initialized to the end of the
        event list in accordance with the policy that listeners receive only those
        events that are published _after_ they have registered.
        """
        if listenerid not in self.listenerDirectory:
            self.listenerDirectory[listenerid] = len(self.eventList)
            debug.output("TopicManager.registerListener")
            self.printEventsAndListeners()
        else:
            raise EventServiceException("Event listener registered earlier.")

    """
    A listener activity like unregistering or processing triggers cleanup of
    events having no pending listeners, followed by resetting of list markers
    of all registered listeners.
    """

    def cleanupEvents(self, listenerid):
        self.listenerDirectory[listenerid] = len(self.eventList)

        """ First determine the oldest pending event. """
        oldestPendingEvent = min(self.listenerDirectory.values())

        """
        Reset current listeners' list markers and remove events having no
        pending listeners.
        """
        if oldestPendingEvent > 0:
            del self.eventList[:oldestPendingEvent]
            for listener_id in self.listenerDirectory:
                self.listenerDirectory[listener_id] -= oldestPendingEvent

    """
    A listener is unregistered by first performing an event cleanup, followed by
    deletion of the listener from listenerDirectory.
    """

    def unregisterListener(self, listenerid):
        self.cleanupEvents(listenerid)
        del self.listenerDirectory[listenerid]
        debug.output("TopicManager.unregisterListener")
        self.printEventsAndListeners()

    """
    Returns events posted since the last fetch for a listener.
    """

    def getEventListForListener(self, listenerid):
        eventListForListener = []
        for theEvent in self.eventList[self.listenerDirectory[listenerid]:]:
            eventListForListener.append(Event(theEvent.header, theEvent.body))
        self.cleanupEvents(listenerid)
        debug.output("TopicManager.getEventListForListener")
        self.printEventsAndListeners()
        return eventListForListener

    """
    Print out the contents for debugging.
    """

    def printEventsAndListeners(self):
        string = ":::::::::\n" + "List of events:"
        i = 0
        for i, e in enumerate(self.eventList):
            string += "\n" + str(i) + "---" + str(e)
        string += "\n\n" + "List of listeners:"
        debug.output(string)
        sortedKeys = sorted(self.listenerDirectory.keys())
        for listenerid in sortedKeys:
            string = "event = " + str(self.listenerDirectory[listenerid])
            debug.output(string, listenerid)
        debug.output(":::::::::")

    """
    Gives a profile of events posted to this topic, currently just
    maxPendingEvents.
    """

    def getEventStats(self):
        return self.maxPendingEvents
