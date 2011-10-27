/*
 * This program takes in an integer as a command-line argument and sleeps for that many seconds.
 */

#include<unistd.h>
#include<stdio.h>

int main(int argc, char* argv[]){
    if(argc < 1){
        printf("No argument given.  Please provide an integer value for which the program will sleep.\n");
        return 1;
    }

    sleep(atoi(argv[1]));
    return 0;
}
