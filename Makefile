
# this make file is used to compile the c-rakeparser
# eventually a (this) make file will need to be used to compile  c-client.c

CC              = cc
CFLAGS          = -std=c99 -O -Wall -Werror -pedantic

OBJ		= strsplit.o

# c-rakeparser:	c-rakeparser.c strsplit.o
# 	$(CC) $(CFLAGS) -o c-rakeparser c-rakeparser.c $(OBJ)

c-clientV2 : c-clientV2.o c-parsing.o globals.o strsplit.o
	$(CC) $(CFLAGS) -o c-clientV2 \c-clientV2.o c-parsing.o globals.o strsplit.o

c-clientV2.o : c-clientV2.c c-client.h
	$(CC) $(CFLAGS) -c c-clientV2.c

strsplit.o :	strsplit.c
	$(CC) $(CFLAGS) -c strsplit.c

c-parsing.o : c-parsing.c c-client.h strsplit.o
	$(CC) $(CFLAGS) -c c-parsing.c

globals.o : globals.c c-client.h
	$(CC) $(CFLAGS) -c globals.c

clean:
	@rm globals.o c-parsing.o strsplit.o c-clientV2.o c-clientV2