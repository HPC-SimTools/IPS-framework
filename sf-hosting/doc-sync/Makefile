# Simple makefile to install user-side bits of auto-update infrastructure

BASENAME = update-docs-ipsframework

CRON_FRAG = $(BASENAME).crontab
LOGR_FRAG = logrotate-$(BASENAME).conf

BIN_DIR = $(HOME)/bin
CRON_DIR = $(HOME)/src/crontabs
LOGR_DIR = $(HOME)/src/logrotate

BIN_DEST = $(BIN_DIR)/$(BASENAME)
CRON_DEST = $(CRON_DIR)/crontab.d/$(CRON_FRAG)
LOGR_DEST = $(LOGR_DIR)/logrotate.d/$(LOGR_FRAG)

.phony: requires-root files install install-cron install-logr

files: 	$(BIN_DEST) \
	$(CRON_DEST) \
	$(LOGR_DEST) 

install: install-cron install-logr requires-root

install-cron: $(CRON_DEST)
	( cd $(CRON_DIR) && make install )

install-logr: $(LOGR_DEST)
	( cd $(LOGR_DIR) && make install )

$(BIN_DEST): $(BASENAME)
	cp $< $@
	chmod a+rx $@

$(CRON_DEST): $(CRON_FRAG)
	cp $< $@

$(LOGR_DEST): $(LOGR_FRAG)
	cp $< $@

requires-root:
	@echo ">>>>> Don't forget to install logwatch files too <<<<<"
