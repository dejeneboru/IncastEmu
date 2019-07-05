#!/bin/bash
while true
do
    for i in `seq 1 10`;
    do
        echo "./tcp_client conf/${i}servers.conf t.csv"
        ./tcp_client conf/${i}servers.conf t.csv
    done
done
