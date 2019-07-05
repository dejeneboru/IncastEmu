#!/bin/bash

# csync.sh - (Cluster) SYNC a [file|directory|symbolic_link] on all nodes
# Usage: ./csync.sh ~/conf/hadoop_conf

if [ -z $1 ]; then
    echo "csync.sh - (Cluster) SYNC a [file|directory|symbolic_link] on all nodes"
    echo "Usage: ./csync.sh [file|directory|symbolic_link]"
    exit 0
fi

REALPATH=`readlink -f $1`
serverlist='server1 server2 server3 server4 server5 server6 server7 server8 server9 server10 switch'

# Remove the last component of the pathname
# For example, /users/lc/foo/tar ---> /users/lc/foo
PARENTPATH=`echo $REALPATH | sed 's,/*[^/]\+/*$,,'`

if [ -L $1 ]; then
    for node in $serverlist; do
        SYMPATH=`realpath -s $1`
        echo "doing... 'rsync -avzrq $SYMPATH $node:$SYMPATH'"
	SYMPARENTPATH=`echo $SYMPATH | sed 's,/*[^/]\+/*$,,'`
        ssh $node "mkdir -p $SYMPARENTPATH"
        rsync -avzrq $SYMPATH $node:$SYMPATH
    done
fi

if [ -d $REALPATH ]; then 
    for node in $serverlist; do
        ssh $node "mkdir -p $PARENTPATH"
        echo "doing... 'rsync -avzrq $REALPATH/ $node:$REALPATH'"
        rsync -avzrq $REALPATH/ $node:$REALPATH
    done
elif [ -f $REALPATH ]; then
    for node in $serverlist; do
        echo "doing... 'rsync -avzrq $REALPATH $node:$REALPATH'"
        rsync -avzrq $REALPATH $node:$REALPATH
    done
fi
