#include  <stdio.h>
#include  <fcntl.h>
#include  <stdlib.h>
#include  <unistd.h>
#include <string.h>
#include <stdbool.h>


extern  char    **strsplit(const char *line, int *nwords);
extern  void    free_words(char **words);

#define     BUFSIZE      10000
#define     DICTIONARY  "/Users/hamishgillespie/Desktop/netWORKS/project/cits3002-group-project-2022/rakefile3"
#define     MAX_HOSTNAME_LEN    20


int PORT;
int NUM_HOSTS;


int main(int argc, char const *argv[])
{
    //Initiating some variables 
    int act_set_count = 0; // the the number of actions sets
    char* HOSTS[MAX_HOSTNAME_LEN];

    //Initiating buffer and FILE
    char   line[BUFSIZ];
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


    //procesing each actionset of file--------------------------
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
    // a variabl to track the action count in the current action set

    

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
    return 0;
}
