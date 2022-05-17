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



int main(int argc, char const *argv[])
{
    //Initiating some variables 
    int act_set_count = 0; // the the number of actions sets
    // int host_count; // the number of hostnames provided
    // int port_Number; // the port number provided

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



        //tring to get strsplit to work
        char* str = line;

        int nwords;
        char **words = strsplit(str, &nwords);


         for(int w=0 ; w<nwords ; ++w) {
            printf("\t[%i]  \"%s\"\n", w, words[w]);
        }
        // free_words(words);
        printf("\n");



    }


    printf("%i\n\n", act_set_count);

    printf("hello file parser\n"); 
    fclose(dict);
    return 0;
}
