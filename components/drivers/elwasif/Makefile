include Makefile.include

VPATH = $(PWD)
OBJDIR= .

- F90_SRC = $(shell ls *.f)

OBJS = $(F90_SRC:%.f=$(OBJDIR)/%.o) $(F95_SRC:%.f95=$(OBJDIR)/%.o) $(F77_SRC:%.f=$(OBJDIR)/%.o)
F90_MOD_INCLUDE =  $(F90_MOD_INCLUDE_PREFIX). $(F90_MOD_INCLUDE_PREFIX)$(IPS_ROOT)/include

MDSPLUSLIB = -L$(MDSPLUS_ROOT)/lib -L$(GLOBUS_LOCATION)/lib -lMdsLib -lglobus_xio_gcc64
LAPACKLIB= -L$(MKLHOME)/lib/64 -lmkl_lapack -lmkl_ipf -lguide -lpthread
NETCDFLIB= -L$(NETCDFHOME)/lib -lnetcdf
NTCCLIB = -L$(NTCCHOME)/lib -lxplasma2 -lgeqdsk_mds -lmdstransp -lvaxonly -lnscrunch -lfluxav -lr8bloat -lpspline -lezcdf -llsode -llsode_linpack -lcomput -lportlib
PLASMA_STATE_LIB = -L$(IPS_ROOT)/lib -lplasma_state -lps_xplasma2 -lplasma_state_kernel

LIBS = $(PLASMA_STATE_LIB) $(NTCCLIB) $(MDSPLUSLIB) $(NETCDFLIB) $(LAPACKLIB) -L$(IPS_ROOT)/lib -lswim-utils

PREPARE_INPUT_SRCS=
PREPARE_INPUT_OBJS = $(PREPARE_INPUT_SRCS:.f=.o)

ifneq ($(F90_FREEFORM_SUFFIX1),)
$(OBJDIR)/%.o : %.$(F90_FREEFORM_SUFFIX1)
	$(F90) $(F90FLAGS) $(F90_FREEFORM_FLAG) $(F90_MOD_INCLUDE) -c $< -o $@
endif

ifneq ($(F90_FREEFORM_SUFFIX2),)
$(OBJDIR)/%.o : %.$(F90_FREEFORM_SUFFIX2)
	$(F90) $(F90FLAGS) $(F90_FREEFORM_FLAG) $(F90_MOD_INCLUDE) -c $< -o $@
endif

ifneq ($(F90_FIXEDFORM_SUFFIX1),)
$(OBJDIR)/%.o : %.$(F90_FIXEDFORM_SUFFIX1)
	$(F90) $(F90FLAGS) $(F90_FIXEDFORM_FLAG) $(F90_MOD_INCLUDE) -c $< -o $@
endif

ifneq ($(F90_FIXEDFORM_SUFFIX2),)
$(OBJDIR)/%.o : %.$(F90_FIXEDFORM_SUFFIX2)
	$(F90) $(F90FLAGS) $(F90_FIXEDFORM_FLAG)  $(F90_MOD_INCLUDE) -c $< -o $@
endif

ifneq ($(F77_FREEFORM_SUFFIX1),)
$(OBJDIR)/%.o : %.$(F77_FREEFORM_SUFFIX1)
	$(F77) $(F77FLAGS) $(F77_FREEFORM_FLAG) -c $< -o $@
endif

ifneq ($(F77_FREEFORM_SUFFIX2),)
$(OBJDIR)/%.o : %.$(F77_FREEFORM_SUFFIX2)
	$(F77) $(F77FLAGS) $(F77_FREEFORM_FLAG) -c $< -o $@
endif

ifneq ($(F77_FIXEDFORM_SUFFIX1),)
$(OBJDIR)/%.o : %.$(F77_FIXEDFORM_SUFFIX1)
	$(F77) $(F77FLAGS) $(F77_FIXEDFORM_FLAG) -c $< -o $@
endif

ifneq ($(F77_FIXEDFORM_SUFFIX2),)
$(OBJDIR)/%.o : %.$(F77_FIXEDFORM_SUFFIX2)
	$(F77) $(F77FLAGS) $(F77_FIXEDFORM_FLAG) -c $< -o $@
endif

%.py:
	@echo "Checked $@"

EXECUTABLES = 
SCRIPTS = elwasif_driver.py 

TARGETS = $(SCRIPTS)

all: 
	- $(MAKE) $(TARGETS)
	@ for i in `echo $(EXECUTABLES)`; do \
	   if [ -f $$i ]; then \
                echo "SUCCESS building $$i" >> $(IPS_ROOT)/.make-result;\
        else \
                echo "***FAILURE building $$i" >> $(IPS_ROOT)/.make-result;\
        fi;\
	done;

install:
	$(INSTALL) $(EXECUTABLES) $(SCRIPTS) $(IPS_ROOT)/bin

clean:
	$(RM) $(OBJS) *.a *.mod $(EXECUTABLES)

distclean: clean 
	$(RM) .depend
	
# .depend: $(F90MOD_SRC) $(F90_SRC)
#	$(MAKEDEPF90) -b . $(F90MOD_SRC) $(F90_SRC) > $@

# -include .depend
