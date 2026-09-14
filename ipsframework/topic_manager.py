# -------------------------------------------------------------------------------
# Copyright 2006-2022 UT-Battelle, LLC. See LICENSE for more information.
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
time, we could define a 'limit_pending_events' parameter to denote a bound on the
count of pending events exceeding which triggers an event cleanup to remove
events that outlive a 'timeToLive' parameter.
"""

from .cca_es_spec import Event, EventServiceError
from .debug import output as debug_output


class TopicManager:
    def __init__(self, limit_pending_events=10):
        """eventList is the common listing of events posted to a topic."""
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
        self.limit_pending_events = limit_pending_events

        debug_output('TopicManager.__init__')
        self.print_events_and_listeners()

    """
    Append the event to the event list.
    """

    def send_event(self, the_event):
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
            self.eventList.append(the_event)
            event_list_len = len(self.eventList)
            self.maxPendingEvents = max(event_list_len, self.maxPendingEvents)
        debug_output('TopicManager.send_event')
        self.print_events_and_listeners()

    def register_listener(self, listenerid):
        """
        For a new listener, the event list marker is initialized to the end of the
        event list in accordance with the policy that listeners receive only those
        events that are published _after_ they have registered.
        """
        if listenerid not in self.listenerDirectory:
            self.listenerDirectory[listenerid] = len(self.eventList)
            debug_output('TopicManager.register_listener')
            self.print_events_and_listeners()
        else:
            raise EventServiceError('Event listener registered earlier.')

    """
    A listener activity like unregistering or processing triggers cleanup of
    events having no pending listeners, followed by resetting of list markers
    of all registered listeners.
    """

    def cleanup_events(self, listenerid):
        self.listenerDirectory[listenerid] = len(self.eventList)

        """ First determine the oldest pending event. """
        oldest_pending_event = min(self.listenerDirectory.values())

        """
        Reset current listeners' list markers and remove events having no
        pending listeners.
        """
        if oldest_pending_event > 0:
            del self.eventList[:oldest_pending_event]
            for listener_id in self.listenerDirectory:
                self.listenerDirectory[listener_id] -= oldest_pending_event

    """
    A listener is unregistered by first performing an event cleanup, followed by
    deletion of the listener from listenerDirectory.
    """

    def unregister_listener(self, listenerid):
        self.cleanup_events(listenerid)
        del self.listenerDirectory[listenerid]
        debug_output('TopicManager.unregister_listener')
        self.print_events_and_listeners()

    """
    Returns events posted since the last fetch for a listener.
    """

    def get_event_list_for_listener(self, listenerid):
        event_list_for_listener = []
        for the_event in self.eventList[self.listenerDirectory[listenerid] :]:
            event_list_for_listener.append(Event(the_event.header, the_event.body))
        self.cleanup_events(listenerid)
        debug_output('TopicManager.get_event_list_for_listener')
        self.print_events_and_listeners()
        return event_list_for_listener

    """
    Print out the contents for debugging.
    """

    def print_events_and_listeners(self):
        string = ':::::::::\n' + 'List of events:'
        i = 0
        for i, e in enumerate(self.eventList):
            string += '\n' + str(i) + '---' + str(e)
        string += '\n\n' + 'List of listeners:'
        debug_output(string)
        sorted_keys = sorted(self.listenerDirectory.keys())
        for listenerid in sorted_keys:
            string = 'event = ' + str(self.listenerDirectory[listenerid])
            debug_output(string, listenerid)
        debug_output(':::::::::')

    """
    Gives a profile of events posted to this topic, currently just
    maxPendingEvents.
    """

    def get_event_stats(self):
        return self.maxPendingEvents
