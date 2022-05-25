#include "c-client.h"

//20920822 Shao-Ming Tan
//22503639 Hamish Gillespie
//22870036 Aswin Thaikkattu Vinod

//C-client is not complete
/*
C-client cna succesuflly parse a rakefile
All actions are stored in *ACTIONS[], which is an array of pointers to action arrays

We are unable to get our C-client to communicate with our server.py
The main issue was having the server recognise messages sent by the c client.

run make on command line to compile and link code,

*/

int main(int argc, char const *argv[])
{//first thing to do is parse rakefile and store info in data structures

    if( argc < 2){
        fprintf(stderr, "Usage : c-client [filename]\n"); 
        exit(EXIT_FAILURE);
    }

    char *file = (char*) argv[1];
    printf("%s\n", file);
    //this willl assighn the global varaible *HOSTS[] the different names of hosts
    getGlobals(file);
    //checking Globals
    for(int i =0; i < NUM_HOSTS; i++){
        // printf("\n%s", HOSTS[i]);
    }
    // printf("the default port is: %i\n", PORT);
    // printf("number of actionsets is: %i\n", action_set_count);
   
    // store the number of actions in each action set, set all to 0
    int action_counts[action_set_count];
    for (int i = 0; i < action_set_count; i++){
        action_counts[i] = 0;
    }  
    fillActionCounts(action_counts,file);
    for (int i = 0; i < action_set_count; i++){
        // printf("action set %i has: %i commands\n", i+1, action_counts[i]);
    } 

    //this holds this is where actionsets are stored
    ActionSet *ACTIONS[action_set_count];
    //allocating memory to all the actionsets
    for(int i = 0; i < action_set_count; i++){
            ACTIONS[i] = malloc(sizeof(ActionSet)*3);
    }
    fillACTIONS(ACTIONS, file);
    actionsSummary(ACTIONS, action_counts);

    //a working client would look somehting like this (pseudo code)
    /*
        for(int i = 0; i<acton_set_count; i++)





    */


    return 0;

}
