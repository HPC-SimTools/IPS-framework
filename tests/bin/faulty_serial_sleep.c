/*
 * This program takes in a sleep parameter and will trigger a failure after that many seconds.
 *
 * How to run:
 *   ./a.out <sleep_param> <failure_type>
 *
 * Possible failure types:
 *   1: divide by zero
 *   2: segmentation fault
 */

#include<unistd.h>
#include<stdio.h>
#include<math.h>
#include<signal.h>

void my_fail(int ftype){
    int x = 7364;
    int y = 937493;
    switch(ftype){
    case 0:
        printf("fail type is seg fault\n");
        int * x;
        x = NULL;
        printf("%d", *x);
        break;
    case 1:                  // divde by zero                                                                                                              
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


int main(int argc, char* argv[]){
    // declare variables
    int sleep_time = 0;
    int err_type = 1;
    int x = 0;

    // process input
    if(argc != 3){
        printf("Bad arguments.  Expecting sleep parameter and a failure type.\n  1: divide by zero\n\n");
        return 1;
    }
    sleep_time = atoi(argv[1]);
    err_type = atoi(argv[2]);

    // sleep
    sleep(sleep_time);

    // trigger failure
    my_fail(err_type);
    return 0;
}
