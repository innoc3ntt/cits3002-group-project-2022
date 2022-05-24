//-- A streaming client

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <stdbool.h>
#include <errno.h>
#include <string.h>
#include <netdb.h>
#include <sys/types.h>
#include <netinet/in.h>
#include <sys/socket.h>

#include <time.h>

#include <fcntl.h>

#include <arpa/inet.h>

//some constant variables
#define MAX_HOSTNAME_LEN    20
#define FILE_BUFSIZE        10000

// type definititons for holding Actions in c-rakeparser
typedef struct {
  char **command;
  char **requirements; // string of the requirements
  bool requires;    //does this string have requirements? 
  int nwords_command; //number of words in command
  int nwords_requirement; //number of words in requirements
} *action;

typedef action ActionSet;

//function defined in strsplit.c----------------------------
extern  char    **strsplit(const char *line, int *nwords);
extern  void    free_words(char **words);

//functions defined in c-parsing.c--------------------------
//creating an action
extern action creatAction(char* mystring);

//Add requirements to an action
extern void addRequirement(action theAction, char *mystring);

//functions that assighn global variables
extern void getGlobals(char filepath[]);// get PORT number, hostnames and action set count



//Global Variables------------------------------------------
extern int NUM_HOSTS; //number of hosts
extern int PORT; // gets the port number
extern int action_set_count; // action set count
extern char* HOSTS[MAX_HOSTNAME_LEN];// hosts

//ACTION parsing
extern void fillActionCounts(int action_counts[], char filepath[]);//assighn actions counts array
extern void fillACTIONS(ActionSet *ACTIONS[], char filePath[]);
extern void actionsSummary(ActionSet *ACTIONS[], int action_coutns[]);
