VPATH = $(PWD)
OBJDIR = .

include Makefile.include

F95MOD_SRC = $(wildcard *mod.f95) 
F90MOD_SRC = $(wildcard *mod.f90)
F90_SRC =

MOD_OBJS=$(F90MOD_SRC:%.f90=$(OBJDIR)/%.o) $(F95MOD_SRC:%.f95=$(OBJDIR)/%.o)
OBJS = $(MOD_OBJS) $(F90_SRC:%.f9?=$(OBJDIR)/%.o)
F90_MOD_INCLUDE =  $(F90_MOD_INCLUDE_PREFIX). $(F90_MOD_INCLUDE_PREFIX)$(IPS_ROOT)/include

UTILLIB = libswim-utils.a

LIBS += -L. -l$(UTILLIB)

#EXECUTABLES = change_power commit_state swim_state_init
EXECUTABLES = 

TARGETS =  $(UTILLIB) $(EXECUTABLES)

all: .depend 
	- $(MAKE) $(TARGETS)

$(UTILLIB): $(MOD_OBJS)
	ar rv $@ $(MOD_OBJS)
	ranlib -v $@

change_power: $(OBJDIR)/change_power.o
	$(F90) -o $@ $(OBJDIR)/$@.o $(LIBS)

commit_state: $(OBJDIR)/commit_state.o
	$(F90) -o $@ $(OBJDIR)/$@.o $(LIBS)

swim_state_init: $(OBJDIR)/swim_state_init.o
	$(F90) -o $@ $(OBJDIR)/$@.o $(LIBS)
	
install:
	-$(INSTALL) $(UTILLIB) $(IPS_ROOT)/lib
	-$(INSTALL) $(OBJDIR)/*.mod $(IPS_ROOT)/include
#	-$(INSTALL) $(EXECUTABLES) $(IPS_ROOT)/bin

clean:
	$(RM) $(OBJS) *.a $(OBJDIR)/*.mod *.mod $(EXECUTABLES)
	$(RM) $(IPS_ROOT)/lib/$(UTILLIB)

distclean: 
	$(MAKE) clean
	$(RM) .depend

.depend: $(F90MOD_SRC) $(F90_SRC)
	$(MAKEDEPF90) -b $(OBJDIR) $(F90MOD_SRC) $(F90_SRC) > $@

-include .depend
