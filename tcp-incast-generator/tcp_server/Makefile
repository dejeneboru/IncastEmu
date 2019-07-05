CC = gcc
CFLAGS = -Wall -g -std=gnu99 -pthread

SOURCES = tcp_server.c
HEADERS = tcp_server.h
TARGET = tcp_server

.PHONY: all clean tags submit

objects = $(SOURCES:.c=.o)

proxy: $(objects) 
	$(CC) $(CFLAGS) -o $(TARGET) $(objects)

all: $(TARGET)

clean: 
	@rm -f *.o $(TARGET) 

tags:
	@ctags $(SOURCES)
