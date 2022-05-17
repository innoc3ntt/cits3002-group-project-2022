#include  <stdio.h>
#include  <fcntl.h>
#include  <stdlib.h>
#include  <unistd.h>

#define     BUFSIZE      10000
#define     DICTIONARY  "/Users/hamishgillespie/Desktop/netWORKS/project/cits3002-group-project-2022/rakefile1"



int main(int argc, char const *argv[])
{
    //Initiating buffer and FILE
    char   line[BUFSIZ];
    FILE   *dict = fopen(DICTIONARY, "r");

    //Attempting to open the file
    if(dict == NULL) {
        printf( "cannot open dictionary '%s'\n", DICTIONARY);
        exit(EXIT_FAILURE);
    }

    //procesing each line of the file
    while( fgets(line, sizeof line, dict) != NULL ) {  
        printf("%s", line);
    }



    printf("hello file parser\n");
    fclose(dict);
    return 0;
}
