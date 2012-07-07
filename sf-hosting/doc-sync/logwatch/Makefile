# NOTE: installing files in /etc generally requires root/sudo
LOGWATCH = /etc/logwatch

SPECIALFILES = 	$(LOGWATCH)/conf/services/update-docs-ipsframework.conf \
		$(LOGWATCH)/scripts/services/update-docs-ipsframework

all: warning $(SPECIALFILES)

$(LOGWATCH)/conf/services/update-docs-ipsframework.conf: update-docs-ipsframework.conf
	cp $< $@

$(LOGWATCH)/scripts/services/update-docs-ipsframework: update-docs-ipsframework
	cp $< $@

.phony: warning

warning:
	@if [ `id -u` != 0 ]; then \
	  echo ">>>>> IMPORTANT NOTE: installation probably requires root access <<<<<" ;\
	fi

