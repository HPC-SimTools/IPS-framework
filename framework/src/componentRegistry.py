#-------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
#-------------------------------------------------------------------------------
import sys
class Singleton(object):
    def __new__(cls, *param, **keywords):
        if not '_the_instance' in cls.__dict__:
            cls._the_instance = object.__new__(cls)
        return cls._the_instance

class ComponentID(object):
    """
    Object to facilitate the creation, serialization and deserialization of
    component ids.
    """
    delimiter = '@'
    seq_num = 0
    all_ids ={}

    @staticmethod
    def deserialize(comp_id_string):
        """
        Return the deserialized version of the component id.
        """
        tokens = comp_id_string.split(ComponentID.delimiter)
        if (len(tokens) != 3) :
            print 'Invalid serialized component ID : ', comp_id_string
            sys.exit(1)
        return ComponentID.all_ids[comp_id_string]

    def __init__(self, class_name, sim_name):
        """
        Create a component id from *class_name* and *sim_name*.
        """
        self.class_name = class_name
        self.sim_name = sim_name
        self.seq_num = ComponentID.seq_num
        ComponentID.seq_num += 1
        self.serialization = ''
        self.instance_name = ''
        self.serialization = self.get_serialization()
        self.instance_name = self.get_instance_name()
        ComponentID.all_ids[self.serialization] = self
#        print self.serialization, self.class_name, self.sim_name
        return

    def __str__(self):
        """
        Return serialization.
        """
        return self.get_serialization()

    def __repr__(self):
        """
        Return string version (serialization).
        """
        return self.__str__()

    def __eq__(self, other):
        return str(self) == str(other)

    def get_instance_name(self):
        """
        Return instance name of component id.
        """
        if self.instance_name == '':
            self.instance_name = '@'.join([self.sim_name, self.class_name, str(self.seq_num)])
        return self.instance_name

    def get_serialization(self):
        """
        Return serialization.
        """
        if self.serialization == '':
            self.serialization = self.get_instance_name()
        return self.serialization

    def get_sim_name(self):
        """
        Return simulation name for the component.
        """
        return self.sim_name

    def get_class_name(self):
        """
        Return class name of component.
        """
        return self.class_name

    def get_seq_num(self):
        """
        Return sequence number of component.
        """
        return self.seq_num

class ComponentRegistry(Singleton):

    class RegistryEntry(object):
        """
        Container for queues and references associated with a component.
        """
        def __init__(self, svc_response_q, invocation_q, component_ref,
                     services, config):
            self.svc_response_q = svc_response_q
            self.invocation_q = invocation_q
            self.component_ref = component_ref
            self.services = services
            self.config = config

    def __init__(self):
        self.registry = {}
        return

    def get_component_ids(self, sim_name):
        """
        Return all of the component ids associated with sim *sim_name*
        """
#        ids = []
#        for i in self.registry.keys():
#           comp_id = ComponentID.deserialize(i)
#            if (comp_id.get_sim_name() == sim_name):
#                ids.append(comp_id)
        ids = [ ComponentID.deserialize(i) for i in self.registry.keys() \
               if ComponentID.deserialize(i).get_sim_name() == sim_name ]
        return ids

    def addEntry(self, component_id, svc_response_q, invocation_q,
                 component_ref, services, config):
        """
        Create a component registry entry for *component_id* and its
        associated queues, component ref, services and configuration
        information.
        """
        key = component_id.get_serialization()
        value = self.RegistryEntry(svc_response_q, invocation_q,
                                   component_ref,
                                   services, config )
        try:
            self.registry[key] = value
        except KeyError, e:
            print 'Error creating component registery entry for ', key, \
                  ' : ', str(e)
            raise e
        return

    def removeEntry(self, component_id):
        key = component_id.get_serialization()
        try:
            del self.registry[key]
        except KeyError, e:
            print 'Error removing component registry entry for ', key, \
                  ' : ', str(e)
            raise
        return

    # SIMYAN: this was added to provide an easy way to use the component
    # registry to get a registry entry
    def getEntry(self, component_id):
        """
        Return a registry entry.
        """
        key = component_id.get_serialization()
        try:
            entry = self.registry[key]
        except KeyError:
            print 'No registry entry found for ', key
            raise
        return entry

    def getComponentArtifact(self, component_id, artifact):
        """
        Return value of *artifact* in *component_id*'s registry entry.
        """
        key = component_id.get_serialization()
        try:
            entry = self.registry[key]
        except KeyError:
            print 'No registry entry found for ', key
            raise
        try:
            value = entry.__getattribute__(artifact)
        except KeyError:
            print 'Invalid registry attribute : ', artifact
            print 'Possible values are : ', entry.__dict__.keys()
            raise
        return value

    def setComponentArtifact(self, component_id, artifact, value):
        """
        Set the value of *artifact* in *component_id*'s registry entry to
        *value*.
        """
        key = component_id.get_serialization()
        try:
            entry = self.registry[key]
        except KeyError:
            print 'No registry entry found for ', key
            raise
        setattr(entry, artifact, value)
        return
