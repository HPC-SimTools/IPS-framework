OBJDIR= .

include Makefile.include

F90_SRC = $(shell ls *.f90)

F90MOD_SRC = 

OBJS = $(F90_SRC:%.f90=$(OBJDIR)/%.o) $(F95_SRC:%.f95=$(OBJDIR)/%.o)  $(F90MOD_SRC:%.f=$(OBJDIR)/%.o)

F90_MOD_INCLUDE =  $(F90_MOD_INCLUDE_PREFIX). $(F90_MOD_INCLUDE_PREFIX)$(IPS_ROOT)/include 
#LIBS += 

EXECUTABLES =  # insert helper executables here
SCRIPTS =      # insert python component scripts here

TARGETS = $(EXECUTABLES) 

all: .depend 
	echo $(F90_MOD_INCLUDE)
	- $(MAKE) $(TARGETS)
	@ for i in `echo $(EXECUTABLES)`; do \
	   if [ -f $$i ]; then \
                echo "SUCCESS building $$i" >> $(IPS_ROOT)/.make-result;\
        else \
                echo "***FAILURE building $$i" >> $(IPS_ROOT)/.make-result;\
        fi;\
	done;

# insert targets for each executable
#hello_app: hello_app.o 
#	$(F90)  -o   $@ $^  $(LIBS)

install:
	$(INSTALL) $(EXECUTABLES) $(SCRIPTS) $(IPS_ROOT)/bin

clean:
	$(RM) *.o *.a *.mod $(TARGETS)

distclean: clean 
	$(RM) .depend
	
.depend: $(F90MOD_SRC) $(F90_SRC)
	$(MAKEDEPF90) -b . $(F90MOD_SRC) $(F90_SRC) > $@

-include .depend
