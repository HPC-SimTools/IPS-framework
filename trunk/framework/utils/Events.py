
""" An event channel dummy that allows testing even when the event channel
cannot be accessed.  Writes to a local file called logfile

This code assumes that the jar files listed below are in the directory above
Events.py.  If you get the error "Package wsmg.WseClientAPI is not Callable,"
that means that the jar files are missing or not in the necessary location.
"""

from time import time, ctime, sleep
import os

# JAR locations for using the WSMG client
wsmgjar=os.path.abspath("../wsmg.jar")
xppjar=os.path.abspath("../xpp3-1.1.3.4.M.jar")
xsuljar=os.path.abspath("../xsul-2.1.15_SE4.jar")
xmlbjar=os.path.abspath("../xmlbeans-1.0.jar")

#TODO: figure out how to use the set_default_broker thing better
broker="shortly.cs.indiana.edu:12345"

def set_default_broker(b="shortly.cs.indiana.edu:12345"):
    global broker
    broker = b

def get_default_broker():
    return broker

def wrap_message(message, action):
    import os
    import string
    import time

    now = map(str, time.gmtime())
    ts = string.join(now[0:3],'-')+' '+string.join(now[3:6],':')
    publisher = os.environ['USER']
    component = string.split(os.getcwd(),"/")[-3]
    host = os.environ['HOSTNAME']
    wrapstr = 'publishing_time=\"' + ts + '\" ' + 'publisher=\"' + publisher + '\" ' + 'publishing_component=\"' + component + '\" ' + 'publishing_host=\"' + host + '\" ' + 'action=\"' + action + '\" ' + 'message=\"' + message + '\" '
    return wrapstr

def publish_event(message, topic = 'FSP_log', action = 'Announce'):
    try:
	import jpype
	if (jpype.isJVMStarted()==0):
           jpype.startJVM(jpype.getDefaultJVMPath(), "-Djava.class.path=%s:%s:%s:%s"%(wsmgjar, xppjar, xsuljar, xmlbjar))

	api = jpype.JPackage('wsmg').WseClientAPI()
	message = wrap_message(message, action)
        api.publish(broker, topic, message)

    except Exception, inst:
       logfile = open('logfile', 'a')
       logfile.write('---------Message Start: ' + ctime(time()) + ' -----------\n')
       logfile.write('broker    = ' + broker + '\n')
       logfile.write('topic     = ' + topic + '\n')
       logfile.write('message   = ' + message + '\n')
       logfile.write('error     = ' + str(inst) + '\n')
       logfile.write('action     = ' + action + '\n')
       logfile.write('---------Message End-----------------\n\n')
       logfile.close()
    
    return
