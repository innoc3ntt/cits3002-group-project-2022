#include  <stdio.h>
#include  <fcntl.h>
#include  <stdlib.h>
#include  <unistd.h>
#include <string.h>
#include <stdbool.h>


extern  char    **strsplit(const char *line, int *nwords);
extern  void    free_words(char **words);

#define     BUFSIZE      10000
#define     DICTIONARY  "/Users/hamishgillespie/Desktop/netWORKS/project/cits3002-group-project-2022/rakefile1"
#define     MAX_HOSTNAME_LEN    20

typedef struct {
  char **command;
  char **requirements; // string of the requirements
  bool requires;    //does this string have requirements? 
  int nwords_command; //number of words in command
  int nwords_requirement; //number of words in requirements
} *action;

typedef action ActionSet;

action creatAction(char* mystring){
    int nwords;
    action a = malloc(sizeof(action)+sizeof(mystring)*3); 
    a->command = strsplit(mystring, &nwords);
    a->nwords_command = nwords;
    a->requires = false; //no requirements for this command so far
    return a;
}

void addRequirement(action theAction, char *mystring){
    int nwords;
    char *addRequirement = mystring;
    theAction->requirements = strsplit(addRequirement, &nwords);
    theAction->nwords_requirement = nwords;
    theAction->requires = true;
}

int PORT;
int NUM_HOSTS;


int main(int argc, char const *argv[])
{
    //Initiating some variables 
    int act_set_count = 0; // the the number of actions sets
    char* HOSTS[MAX_HOSTNAME_LEN];

    //Initiating buffer and FILE
    char   line[BUFSIZE];
    FILE   *dict = fopen(DICTIONARY, "r");

    //Attempting to open the file
    if(dict == NULL) {
        printf( "cannot open dictionary '%s'\n", DICTIONARY);
        exit(EXIT_FAILURE);
    }
    //intiating words which will hold words


    //procesing each line of the file
    printf("Inital File read----------------------------\n");
    while( fgets(line, sizeof line, dict) != NULL ) {  
        // printing each line in rakefile for debugging purposes
        printf("%s", line);

        // counting the number of actionsets in the rakefile
        if( strstr(line,"actionset") ){
            act_set_count++;
            //if line contains actionset but also contains a tab, we dont want to count it twice
            if( strstr(line,"    ") ){
                act_set_count--;
            }
        }

        //if the line contains a port
        if( strstr(line,"PORT") ){
            // printf("we got a config port line: %s", line);
            int nwords;
            char **words = strsplit(line, &nwords);
            for(int w=0 ; w<nwords ; ++w) {
                // printf("\t[%i]  \"%s\"\n", w, words[w]);
            }
            PORT = atoi(words[2]);
        }

        //if the line contains hostnames, add host name to HOST array
        if( strstr(line,"HOSTS") ){
            int nwords;
            char **words = strsplit(line, &nwords);
            for(int w=0 ; w<nwords ; ++w) {
                // printf("\t[%i]  \"%s\"\n", w, words[w]);
            }
            for(int i =0; i < nwords -2 ; ++i){
                HOSTS[i] = words[i+2];
            }
            NUM_HOSTS = nwords - 2;
        }

    }
    fclose(dict);
    printf("\nEnd of first opening of rakeFile------------\n");


    //procesing each actionset of file to get number of actions--------------------------
    printf("starting second read of file\n");
    dict = fopen(DICTIONARY, "r");

    if(dict == NULL) {
        printf( "cannot open dictionary '%s'\n", DICTIONARY);
        exit(EXIT_FAILURE);
    }

    //Creating array to hold the amount of actions in each actionset
    int action_counts[act_set_count];
    //setting all actionset counts to 0;
    for (size_t i = 0; i < act_set_count; i++)
    {
        action_counts[i] = 0;
    }
    //a variable to track what action set we are in (i.e. actionset1, actionset2 ...)
    int cur_act_set = -1;
    
    while( fgets(line, sizeof line, dict) != NULL ) {

        if(strstr(line,"#")) continue;

        //entering a new actions set
        if( strstr(line,"actionset") && !strstr(line,"    ") ){
            cur_act_set++;
            // printf("swag\n");
        }

        //action line, and not a required line
        if(strstr(line,"    ") && !strstr(line,"        ")){
            action_counts[cur_act_set]++;
        }
    } 
    fclose(dict);
    //Fillinf in the ACTIONS Array------------------------
    //ACTIONS is an Array of action_set's, an action set contains different actions
    printf("starting third read of file\n");

    //this holds this is where actionsets are stored
    ActionSet *ACTIONS[act_set_count];
    //allocating memory to all the actionsets
    for(int i = 0; i < act_set_count; i++){
            ACTIONS[i] = malloc(sizeof(ActionSet)*3);
    }


    dict = fopen(DICTIONARY, "r");

    //using cur_act_set again
    cur_act_set = -1;
    //tracking the current action in an action set
    int current_action_in_set = 0;

    //Attempting to open the file
    if(dict == NULL) {
        printf( "cannot open dictionary '%s'\n", DICTIONARY);
        exit(EXIT_FAILURE);
    }

    while( fgets(line, sizeof line, dict) != NULL ) {
        // if line is a comment skip it
        if(strstr(line,"#")) continue;

        //entering a new actions set 
        if( strstr(line,"actionset") && !strstr(line,"    ") ){
            //increment the current action set
            printf("swag %s", line);
            cur_act_set++;
            //creat the actionSet
            //set current action count for this action set back to -1
            current_action_in_set = -1;
        }

        //the line is an action, belonging to an action set
        if( strstr(line,"    ") && !strstr(line,"        ") ){
            current_action_in_set++;
            ACTIONS[cur_act_set][current_action_in_set] = creatAction(line);
        }

        //if the line is requirements
        if(strstr(line, "requires") && strstr(line,"        ")){
            addRequirement(ACTIONS[cur_act_set][current_action_in_set], line);
        }

        
    }




    //SUMMARY OF PARSED FILE---------------------------
    printf("\n\nFILE SUMMARY------------\n");
    printf("the port is %i\n", PORT);
    printf("these are the hosts:");
    for(int i =0; i < NUM_HOSTS; i++){
        printf("\n\t%s", HOSTS[i]);
    }
    printf("\nThere are %i action sets\n", act_set_count);
    //iterating through action_counts;
    for(int i = 0; i < act_set_count; i++){
        printf("actionset: %i has %i actions\n", i ,action_counts[i]);
    }
    printf("\n");
    //TRYING TO LOOP THROUGH ACTIONS, final stage
    for(int i = 0; i < act_set_count; i++){
        ActionSet *c = ACTIONS[i];

        for(int z = 0; z<action_counts[i];z++){
            action b =  c[z];
            printf("\t");
            for(int w = 0; w<b->nwords_command; w++){
                printf("%s ", b->command[w]);
            }
            if(b->requires == true){
                for(int w = 0; w < b->nwords_requirement; w++){
                    printf("%s ", b->requirements[w]);
                }
            }

        }
        printf("\n");
    }
    return 0;
}
