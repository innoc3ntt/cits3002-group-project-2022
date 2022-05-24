//-- A streaming client

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <errno.h>
#include <string.h>
#include <fcntl.h>
#include <netdb.h>
#include <sys/types.h>
#include <netinet/in.h>
#include <sys/socket.h>
// #include "pack.h"

#include <time.h>

#include <arpa/inet.h>
// #include <curl/curl.h>

#define PORT "8000" // the port client will be connecting to

#define MAXDATASIZE 100 // max number of bytes we can get at once

int write_file_to_server(int sd, const char filenm[])
{
    //  ENSURE THAT WE CAN OPEN PROVIDED FILE
    int fd = open(filenm, O_RDONLY);

    if (fd >= 0)
    {
        char buffer[1024];
        int nbytes;

        //  COPY BYTES FROM FILE-DESCRIPTOR TO SOCKET-DESCRIPTOR
        while ((nbytes = read(fd, buffer, sizeof(buffer))))
        {
            if (write(sd, buffer, nbytes) != nbytes)
            {
                close(fd);
                return 1;
            }
        }
        close(fd);
        return 0;
    }
    return 1;
}

typedef struct
{
    int first;
    int second;
} TEST;

// get sockaddr, IPv4 or IPv6:
void *get_in_addr(struct sockaddr *sa)
{
    if (sa->sa_family == AF_INET)
    {
        return &(((struct sockaddr_in *)sa)->sin_addr);
    }

    return &(((struct sockaddr_in6 *)sa)->sin6_addr);
}

int main(int argc, char *argv[])
{
    int sockfd, numbytes;
    char buf[MAXDATASIZE];
    struct addrinfo hints, *servinfo, *p;
    int rv;
    char s[INET6_ADDRSTRLEN];

    // TEST hello = {12,
    //               23};

    if (argc != 2)
    {
        fprintf(stderr, "usage: client hostname\n");
        exit(1);
    }

    memset(&hints, 0, sizeof hints);
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;

    if ((rv = getaddrinfo(argv[1], PORT, &hints, &servinfo)) != 0)
    {
        fprintf(stderr, "getaddrinfo: %s\n", gai_strerror(rv));
        return 1;
    }

    // loop through all the results and connect to the first we can
    for (p = servinfo; p != NULL; p = p->ai_next)
    {
        if ((sockfd = socket(p->ai_family, p->ai_socktype,
                             p->ai_protocol)) == -1)
        {
            perror("client: socket");
            continue;
        }

        if (connect(sockfd, p->ai_addr, p->ai_addrlen) == -1)
        {
            perror("client: connect");
            close(sockfd);
            continue;
        }

        break;
    }

    if (p == NULL)
    {
        fprintf(stderr, "client: failed to connect\n");
        return 2;
    }

    inet_ntop(p->ai_family, get_in_addr((struct sockaddr *)p->ai_addr),
              s, sizeof s);
    printf("client: connecting to %s\n", s);

    freeaddrinfo(servinfo); // all done with this structure

    //-----geting info about socket
    // int success = getpeername(int sockfd, struct sockaddr *addr, int *addrlen);

    uint16_t my_int = 2;
    uint32_t network_byte_order;
    network_byte_order = htons(my_int);
    // int myarray[] = {1, 2, 3, 4};
    // int *message = myarray;
    char message[] = "{\"hello\": \"10\"}";
    char buffer[strlen(message)];
    memcpy(buffer, message, strlen(message));

    printf("%lu bytes to be sent\n", sizeof(message));

    printf("%lu network bytes", sizeof(network_byte_order));
    printf("sending message %s\n", message);

        send(sockfd, &network_byte_order, 2, 0);

    int bytes_sent = send(sockfd, &buffer, sizeof(buffer), 0);
    // int bytes_sent = send(sockfd, message, sizeof(message), 0);

    if (bytes_sent <= 0)
    {
        puts("Send failed");
        return 1;
    }
    printf("Data Sent\n");
    printf("%i bytes have been sent\n", bytes_sent);

    if ((numbytes = recv(sockfd, buf, MAXDATASIZE - 1, 0)) == -1)
    {
        perror("recv");
        exit(1);
    }

    printf("client: received '%s'\n", buf);

    close(sockfd);

    return 0;
}
