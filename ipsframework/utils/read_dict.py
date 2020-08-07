#-------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
#-------------------------------------------------------------------------------
def read_dict (conf_dict = {}, filename = "SWIM_config"):
    """

    Open and read a dictionary of key-value pairs from the file given by
    filename. Use the read-in values to augment or update the dictionary passed
    in, then return the new dictionary.

    """
    from utils import publish_event
    try:
        config_file = open(filename, "r")
        if config_file:
            line = config_file.readline().strip()
        else:
            line = ""
    except:
        message = "Unable to open config file " + filename
        publish_event(message, topic = FSP_log, action = "halt_run")
        print(message)
        raise IOError("Unable to open config file in read_dict")

    try:
        while line:
            name, val = line.split("=")
            name = name.strip()
            val = val.strip()
            conf_dict[name] = val
            if config_file:
                line = config_file.readline().strip()
            else:
                line = ""
        config_file.close()
        return conf_dict
    except Exception as ex:
        print("Unable to augment conf_dict in read_dict: %s" % ex)
        raise IOError("Unable to augment conf_dict in read_dict")
