#!/bin/bash
#while true
#do
for i in `seq 1 10`;
do
    echo "./l25_tcp_client conf/${i}servers.conf srd${i}_1000_32kB.csv > srd${i}_1000_32kB.txt"
    ./l25_tcp_client conf/${i}servers.conf srd${i}_1000_32kB.csv > srd${i}_1000_32kB.txt
done
#done
