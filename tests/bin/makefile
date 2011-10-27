#
# General Makefile for creating MPI programs
# Requires that mpirun/mpicc/... are in your path.
#

#CC          = gcc 
mpiCC 	    = cc
#mpiCC		= mpicc
#flags 		= -lmpi

#
# Compile all programs
#
all: parallel_sleep faulty_parallel_sleep

parallel_sleep: 
	$(mpiCC) $(flags) -o parallel_sleep parallel_sleep.c

faulty_parallel_sleep: faulty_parallel_sleep.o
	$(mpiCC) -o faulty_parallel_sleep faulty_parallel_sleep.o

clean: 
	rm -f *.o parallel_sleep faulty_parallel_sleep
