VPATH = $(PWD)
OBJDIR= .

include Makefile.include

F90_SRC = $(shell ls *.f90)

OBJS = $(F90_SRC:%.f90=$(OBJDIR)/%.o) $(F95_SRC:%.f95=$(OBJDIR)/%.o)
F90_MOD_INCLUDE =  $(F90_MOD_INCLUDE_PREFIX). $(F90_MOD_INCLUDE_PREFIX)$(IPS_ROOT)/include $(F90_MOD_INCLUDE_PREFIX)$(NETCDFHOME)/include

#	*txcorp change*
#	old code:
#	EXECUTABLES = do_toric_init prepare_toric_input process_toric_output Ptoric.e Storic.e epa_driver_toric.py
#	REASON: fails with error "no target defined for epa_driver_toric.py"
EXECUTABLES = do_toric_init prepare_toric_input process_toric_output process_toric_output_mcmd # Ptoric.e Storic.e

SCRIPTS = rf_ic_toric.py rf_ic_toric_mcmd.py

TARGETS = $(EXECUTABLES) 

all: .depend 
	- $(MAKE) $(TARGETS)
	@ for i in `echo $(EXECUTABLES)`; do \
	   if [ -f $$i ]; then \
                echo "SUCCESS building $$i" >> $(IPS_ROOT)/.make-result;\
        else \
                echo "***FAILURE building $$i" >> $(IPS_ROOT)/.make-result;\
        fi;\
	done;

do_toric_init.o: toric_utils_mod.o

Ptoric.e: Ptoric.e_$(HOST)
	cp $@_$(HOST) $@

Storic.e: Storic.e_$(HOST)
	cp $@_$(HOST) $@

do_toric_init: do_toric_init.o toric_utils_mod.o toric_namelists.h
	$(F90) -o $@ $@.o toric_utils_mod.o $(LIBS)

prepare_toric_input: prepare_toric_input.o
	$(F90) -o $@ $@.o $(LIBS)

process_toric_output: process_toric_output.o
	$(F90) -g -o $@ $@.o $(LIBS)

process_toric_output_mcmd: process_toric_output_mcmd.o
	$(F90) -g -o $@ $@.o $(LIBS)

install:
	$(INSTALL) $(EXECUTABLES) $(SCRIPTS) $(IPS_ROOT)/bin

clean:
	$(RM) $(OBJS) *.a *.mod $(TARGETS)

distclean: 
	$(MAKE) clean
	$(RM) .depend

.depend: $(F90MOD_SRC) $(F90_SRC)
	touch .depend
#	$(F90) -b . $(F90MOD_SRC) $(F90_SRC) > $@

-include .depend
