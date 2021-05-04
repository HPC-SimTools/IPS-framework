/*
 * This program does hello world, sleeps for the specified number of seconds, then a random process commits a fatal error.
 *
 *  Error types:
 *    1: divide by zero
 *    2: segmentation fault
 */

#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <time.h>
#include "mpi.h"

void my_fail(int ftype){
    int x = 7364;
    int y = 937493;
    switch(ftype){
    case 1:                  // divide by zero
        printf("fail type is divide by zero\n");
        x = y / 0;
        break;
    case 2:                  // SIGFPE - floating point error
        printf("fail type is SIGFPE\n");
        kill(getpid(), SIGFPE);
        break;
    case 3:                  // SIGILL - illegal instruction
        printf("fail type is SIGILL\n");
        kill(getpid(), SIGILL);
        break;
    case 4:                  // SIGSEGV - segmentation fault
        printf("fail type is SIGSEGV\n");
        kill(getpid(), SIGSEGV);
        break;
    case 5:                  // SIGBUS - bus error
        printf("fail type is SIGBUS\n");
        kill(getpid(), SIGBUS);
        break;
    case 6:                  // SIGABRT - self-inflicted abort
        printf("fail type is SIGABRT\n");
        kill(getpid(), SIGABRT);
        break;
    case 7:                  // SIGHUP - hang up -> like loss of network connection
        printf("fail type is SIGHUP\n");
        kill(getpid(), SIGHUP);
        break;
    case 8:                  // SIGINT - ctrl+c
        printf("fail type is SIGINT\n");
        kill(getpid(), SIGINT);
        break;
    case 9:                  // SIGQUIT - ctrl+\
        printf("fail type is SIGQUIT\n");
        kill(getpid(), SIGQUIT);
        break;
    case 10:                  // SIGTERM - ignoreable kill
        printf("fail type is SIGTERM\n");
        kill(getpid(), SIGTERM);
        break;
    case 11:                  // SIGKILL - absolute kill
        printf("fail type is SIGKILL\n");
        kill(getpid(), SIGKILL);
        break;
    default:                  // do nothing
        printf("fail type is do nothing\n");
        break;
    }
}

int main(int argc, char* argv[])
{
    int my_rank;
    int my_pid;
    int cmdlnargs[3];
    int sleep_val = 0;
    int fail_type = 1;
    int who_fails;
    int x;
    int p;
    int source;
    int dest;
    int tag = 0;
    char message[100], my_hostname[23];
    MPI_Status status;
    int seed = time(0);

    srand(seed);
    gethostname(my_hostname, 23);
    my_pid = getpid();

    //Start up MPI
    MPI_Init(&argc, &argv);

    //find process rank
    MPI_Comm_rank(MPI_COMM_WORLD, &my_rank);

    //find number of procs
    MPI_Comm_size(MPI_COMM_WORLD, &p);

    MPI_Barrier(MPI_COMM_WORLD);
    if(my_rank != 0)
        {
            //create message
            sprintf(message, "host: %s -- rank %d -- pid %d", my_hostname, my_rank, my_pid);
            dest = 0;
            MPI_Send(message, strlen(message) + 1, MPI_CHAR, dest, tag, MPI_COMM_WORLD);
            MPI_Barrier(MPI_COMM_WORLD);
            MPI_Bcast(cmdlnargs, 3, MPI_INT, 0, MPI_COMM_WORLD);
            sleep_val = cmdlnargs[0];
            fail_type = cmdlnargs[1];
            who_fails = cmdlnargs[2];
            //printf("%d is sleeping for %d seconds\n", my_rank, sleep_val);
            sleep(sleep_val);
            if(my_rank == who_fails){    
                my_fail(fail_type);
                //MPI_Abort(MPI_COMM_WORLD, SIGTERM);
            }
            sleep(sleep_val);
            sprintf(message, "goodbye from rank %d", my_rank);
            MPI_Barrier(MPI_COMM_WORLD);
            MPI_Send(message, strlen(message) + 1, MPI_CHAR, dest, tag, MPI_COMM_WORLD);
        }
    else  //my rank is 0
        {
            printf("host: %s -- rank %d -- pid %d\n", my_hostname, my_rank, my_pid);
            for(source = 1; source < p; source++)
                {
                    MPI_Recv(message, 100, MPI_CHAR, source, tag, MPI_COMM_WORLD, &status);
                    printf("%s\n", message);
                }
            //printf("post-hello world barrier\n");
            MPI_Barrier(MPI_COMM_WORLD);
            //printf("get sleep_val\n");
            //get sleep_val
            if(argc == 3){
                sleep_val = atoi(argv[1]);
                fail_type = atoi(argv[2]);
            }
            who_fails = rand() % p;  // pick a random process to fail
            //who_fails = 0;  // pick a random process to fail
            cmdlnargs[0] = sleep_val;
            cmdlnargs[1] = fail_type;
            cmdlnargs[2] = who_fails;
            printf("bcast %d %d %d\n", cmdlnargs[0], cmdlnargs[1], cmdlnargs[2]);
            MPI_Bcast(cmdlnargs, 2, MPI_INT, my_rank, MPI_COMM_WORLD);
            //printf("sleeping for %d seconds\n", sleep_val);
            sleep(sleep_val);
            if(my_rank == who_fails){ 
                my_fail(fail_type);   
            }
            sleep(sleep_val);
            MPI_Barrier(MPI_COMM_WORLD);
            printf("goodbye from rank %d\n", my_rank);
            //MPI_Barrier(MPI_COMM_WORLD);
            for(source = 1; source < p; source++)
                {
                    MPI_Recv(message, 100, MPI_CHAR, source, tag, MPI_COMM_WORLD, &status);
                    printf("%s\n", message);
                }

        }

    //shutdown MPI
    MPI_Finalize();
    return 0;
    //return 0;
}
