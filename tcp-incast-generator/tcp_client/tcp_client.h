#ifndef __l25_client_server_h
#define __l25_client_server_h

#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <pthread.h>
#include <signal.h>
#include <ctype.h>

#include <netdb.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#define MAX_LINE 8192
#define MAC_CONNECTIONS 100
#define APP_PORT 5001

int listenfd;

#endif
