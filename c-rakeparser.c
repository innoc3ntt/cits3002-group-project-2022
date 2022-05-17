#include  <stdio.h>
#include  <fcntl.h>
#include  <stdlib.h>
#include  <unistd.h>
#include <string.h>
// #include <"strsplit.c">

extern  char    **strsplit(const char *line, int *nwords);
extern  void    free_words(char **words);

#define     BUFSIZE      10000
#define     DICTIONARY  "/Users/hamishgillespie/Desktop/netWORKS/project/cits3002-group-project-2022/rakefile1"
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
    while( fgets(line, sizeof line, dict) != NULL ) {  
        // printing each line in rakefile for debugging purposes
        printf("%s", line);

        // counting the number of actionsets in the rakefile
        if( strstr(line,"actionset") ){
            act_set_count++;
            if( strstr(line,"   ") ){
                act_set_count--;
            }
        }

        //if the line contains a port
        if( strstr(line,"PORT") ){
            printf("we got a config port line: %s", line);
            int nwords;
            char **words = strsplit(line, &nwords);
            for(int w=0 ; w<nwords ; ++w) {
                printf("\t[%i]  \"%s\"\n", w, words[w]);
            }
            PORT = atoi(words[2]);
        }

        //if the line contains hostnames, add host name to HOST array
        if( strstr(line,"HOSTS") ){
            int nwords;
            char **words = strsplit(line, &nwords);
            for(int w=0 ; w<nwords ; ++w) {
                printf("\t[%i]  \"%s\"\n", w, words[w]);
            }
            for(int i =0; i < nwords -2 ; ++i){
                HOSTS[i] = words[i+2];
            }
            NUM_HOSTS = nwords - 2;
        }

    }
    printf("\n");
    printf("the port is %i\n", PORT);
    printf("these are the hosts:\n");
    for(int i =0; i < NUM_HOSTS; i++){
        printf("\t%s\n", HOSTS[i]);
    }


    // printf("%i\n\n", act_set_count);
    fclose(dict);
    return 0;
}
