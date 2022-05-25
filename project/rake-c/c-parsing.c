//20920822 Shao-Ming Tan
//22503639 Hamish Gillespie
//22870036 Aswin Thaikkattu Vinod

#include "c-client.h"

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

//gets hostnames, ports, and the number of action sets
void getGlobals(char filepath[]){
    char line[FILE_BUFSIZE];
    FILE *dict = fopen(filepath, "r");
    //If file can not be opened 
    if(dict == NULL) {
        printf( "cannot open dictionary '%s'\n", filepath);
        exit(EXIT_FAILURE);
    }
    while( fgets(line, sizeof line, dict) != NULL ) {
        // if line contains a port address 
        if( strstr(line,"PORT") && strstr(line, "=") && !strstr(line,"    ") ){
            // printf("we got a config port line: %s", line);
            int nwords;
            char **words = strsplit(line, &nwords);
            for(int w=0 ; w<nwords ; ++w) {
                // printf("\t[%i]  \"%s\"\n", w, words[w]);
            }
            PORT = atoi(words[2]);
        }

        //if line contains Hosts
        if( strstr(line,"HOSTS") && strstr(line, "=") && !strstr(line,"    ")){
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

        if( strstr(line,"actionset") ){
            action_set_count++;
            //if line contains actionset but also contains a tab, we dont want to count it twice
            if( strstr(line,"    ") ){
                action_set_count--;
            }
        }
    }
    fclose(dict);
}

void fillActionCounts(int action_counts[], char filepath[]){
    char line[FILE_BUFSIZE];
    FILE *dict = fopen(filepath, "r");

    if(dict == NULL) {
        printf( "cannot open dictionary '%s'\n", filepath);
        exit(EXIT_FAILURE);
    }   

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
}

void fillACTIONS(ActionSet *ACTIONS[],char filepath[]){
    char line[FILE_BUFSIZE];
    FILE *dict = fopen(filepath, "r");

    if(dict == NULL) {
        printf( "cannot open dictionary '%s'\n", filepath);
        exit(EXIT_FAILURE);
    }  

    int cur_act_set = -1;
    int current_action_in_set = 0;
    while( fgets(line, sizeof line, dict) != NULL ) {
        // if line is a comment skip it
        if(strstr(line,"#")) continue;

        //entering a new actions set 
        if( strstr(line,"actionset") && !strstr(line,"    ") ){
            //increment the current action set
            // printf("swag %s", line);
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
    fclose(dict);    
}

//simply prints out a summary of the parsed file
void actionsSummary(ActionSet *ACTIONS[],  int action_counts[]){
    //SUMMARY OF PARSED FILE---------------------------
    printf("\n\nFILE SUMMARY------------\n");
    printf("the port is %i\n", PORT);
    printf("these are the hosts:");
    for(int i =0; i < NUM_HOSTS; i++){
        printf("\n\t%s", HOSTS[i]);
    }
    printf("\nThere are %i action sets\n", action_set_count);
    //iterating through action_counts;
    for(int i = 0; i < action_set_count; i++){
        printf("actionset: %i has %i actions\n", i ,action_counts[i]);
    }
    printf("\n");
    //Looping through ACTIONS
    for(int i = 0; i < action_set_count; i++){
        //getting an actionset
        ActionSet *c = ACTIONS[i];
        printf("Action set %i\n",i);
        //iterating through every item in that actionset
        for(int z = 0; z<action_counts[i];z++){
            action b =  c[z];
            printf("\t");
            //printing the words of the commands
            for(int w = 0; w<b->nwords_command; w++){
                printf("%s ", b->command[w]);
            }
            //printing the words of teh requirements, if the action has any
            if(b->requires == true){
                for(int w = 0; w < b->nwords_requirement; w++){
                    printf("%s ", b->requirements[w]);
                }
            }

        }
        printf("\n");
    }

}





   


