#include "c-client.h"

#define RAKEPATH "/Users/hamishgillespie/Desktop/netWORKS/project/cits3002-group-project-2022/rakefile1"

int main(int argc, char const *argv[])
{//first thing to do is parse rakefile and store info in data structures

    //this willl assighn the global varaible *HOSTS[] the different names of hosts
    getGlobals(RAKEPATH);
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
    fillActionCounts(action_counts,RAKEPATH);
    for (int i = 0; i < action_set_count; i++){
        // printf("action set %i has: %i commands\n", i+1, action_counts[i]);
    } 

    //this holds this is where actionsets are stored
    ActionSet *ACTIONS[action_set_count];
    //allocating memory to all the actionsets
    for(int i = 0; i < action_set_count; i++){
            ACTIONS[i] = malloc(sizeof(ActionSet)*3);
    }
    fillACTIONS(ACTIONS, RAKEPATH);
    actionsSummary(ACTIONS, action_counts);

    return 0;

}
