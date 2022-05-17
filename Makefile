
# this make file is used to compile the c-rakeparser
# eventually a (this) make file will need to be used to compile  c-client.c

CC              = cc
CFLAGS          = -std=c99 -O -Wall -Werror -pedantic

OBJ		= strsplit.o

tester:	c-rakeparser.c $(OBJ)
	$(CC) $(CFLAGS) -o c-rakeparser c-rakeparser.c $(OBJ)

%.o:	%.c
	$(CC) $(CFLAGS) -c $<


clean:
	@rm -f tester $(OBJ)
