IPS_ROOT=$(shell cd ../../; pwd)
INSTALL=/usr/bin/install

VPATH = $(PWD)
OBJDIR= .

PYTHON_SRC = $(shell ls *.py)
FRAMEWORK_SRCS = cca_es_spec.py \
				 component.py \
				 componentRegistry.py \
				 configurationManager.py \
				 dataManager.py \
				 eventServiceProxy.py \
				 eventService.py \
				 ftbBridge.py \
				 ips_es_spec.py \
				 ipsExceptions.py \
				 ipsLogging.py \
				 ips.py \
				 ipsTiming.py \
				 ipsutil.py \
				 messages.py \
				 portalBridge.py \
				 resourceHelper.py \
				 resourceManager.py \
				 node_structure.py \
				 sendPost.py \
				 services.py \
				 taskManager.py \
				 topicManager.py 

SCRIPTS = 

all:
	
install:
	$(INSTALL) $(PYTHON_SRC) $(SCRIPTS) $(IPS_ROOT)/bin
	ln -sf ips.py $(IPS_ROOT)/bin/ips
	ln -sf ips-config.py $(IPS_ROOT)/bin/ips-config

doc: $(FRAMEWORK_SRCS)
	- epydoc --pdf -n 'IPS Framework' -v --exclude-introspect ips  -o doc $(FRAMEWORK_SRCS)
	- epydoc --html -n 'IPS Framework' -v --exclude-introspect ips  -o doc $(FRAMEWORK_SRCS)

clean:

distclean:
	${RM} -r doc
	
.PHONY: doc
