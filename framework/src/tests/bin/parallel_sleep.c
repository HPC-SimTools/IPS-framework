#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include "mpi.h"

int main(int argc, char* argv[])
{
    int my_rank;
    int my_pid;
    int sleep_val = 0;
    int p;
    int source;
    int dest;
    int tag = 0;
    char message[100], my_hostname[23];
    MPI_Status status;

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
            MPI_Bcast(&sleep_val, 1, MPI_INT, 0, MPI_COMM_WORLD);
            //printf("%d is sleeping for %d seconds\n", my_rank, sleep_val);
            sleep(sleep_val);
        }
    else  //my rank is 0
        {
            printf("host: %s -- rank %d -- pid %d\n", my_hostname, my_rank, my_pid);
            for(source = 1; source < p; source++)
                {
                    MPI_Recv(message, 100, MPI_CHAR, source, tag, MPI_COMM_WORLD, &status);
                    printf("%s\n", message);
                }
            printf("post-hello world barrier\n");
            MPI_Barrier(MPI_COMM_WORLD);
            printf("get sleep_val\n");
            //get sleep_val
            if(argc < 2){
                sleep_val = 0;
            }
            else{
                sleep_val = atoi(argv[1]);
            }
            printf("bcast\n");
            MPI_Bcast(&sleep_val, 1, MPI_INT, my_rank, MPI_COMM_WORLD);
            printf("%d is sleeping for %d seconds\n", my_rank, sleep_val);
            sleep(sleep_val);
        }

    //shutdown MPI
    MPI_Finalize();

    return 0;
}
