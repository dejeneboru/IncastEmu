CC = gcc
CFLAGS = -Wall -g -std=gnu99 -pthread

SOURCES = tcp_client.c
HEADERS = tcp_client.h
TARGET = tcp_client

.PHONY: all clean tags submit

objects = $(SOURCES:.c=.o)

proxy: $(objects) 
	$(CC) $(CFLAGS) -o $(TARGET) $(objects) -lm

all: $(TARGET)

clean: 
	@rm -f *.o $(TARGET) 

tags:
	@ctags $(SOURCES)


