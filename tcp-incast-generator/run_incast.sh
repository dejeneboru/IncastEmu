#!/bin/bash


ovsdb-server --remote=punix:/usr/local/var/run/openvswitch/db.sock \
    --remote=db:Open_vSwitch,Open_vSwitch,manager_options \
    --private-key=db:Open_vSwitch,SSL,private_key \
    --certificate=db:Open_vSwitch,SSL,certificate \
    --bootstrap-ca-cert=db:Open_vSwitch,SSL,ca_cert \
    --pidfile --detach --log-file

ovs-vsctl --no-wait init
ovs-vswitchd --pidfile --detach --log-file

mn -c


# bws="100 1000"
bws="100"
t=15
n=6
maxq=20
delay="0.2ms"
qmaxhost=20
ecnqlim=20
fct=0



function tcp {
	bw=$1
	odir=tcp-n$n-bw$bw
	python incast.py --bw $bw --maxq $maxq --dir $odir -t $t -n $n --delay $delay --tcpdump --qmaxhost $qmaxhost --fct $fct
	# sudo python util/plot_rate.py --maxy $bw -f $odir/txrate.txt -o $odir/rate.png
	#python util/plot_queue.py --maxy 100 -f $odir/qlen_s1-eth1.txt -o $odir/qlen.pdf
	# sudo python util/plot_tcpprobe.py -f $odir/tcp_probe.txt -o $odir/cwnd.pdf
}

function tcp_red_dctcp {
	bw=$1
	odir=tcp_red_dctcp-n$n-bw$bw
	python incast.py --bw $bw --maxq $maxq --dir $odir -t $t --tcp_reddctcp -n $n --delay $delay --tcpdump --qmaxhost $qmaxhost --fct $fct
	# sudo python util/plot_rate.py --maxy $bw -f $odir/txrate.txt -o $odir/rate.png
	#python util/plot_queue.py --maxy 100 -f $odir/qlen_s1-eth1.txt -o $odir/qlen.pdf
	# sudo python util/plot_tcpprobe.py -f $odir/tcp_probe.txt -o $odir/cwnd.pdf
}


function ecn {
	bw=$1
	odir=tcp-n$n-bw$bw-red-ecn
	python incast.py --bw $bw --maxq $maxq --dir $odir -t $t -n $n --ecn --delay $delay --tcpdump --qmaxhost $qmaxhost --fct $fct
	# sudo python util/plot_rate.py --maxy $bw -f $odir/txrate.txt -o $odir/rate.png
	#python  util/plot_queue.py --maxy 100 -f $odir/qlen_s1-eth1.txt -o $odir/qlen.pdf
	# sudo python util/plot_tcpprobe.py -f $odir/tcp_probe.txt -o $odir/cwnd.png
}

function dctcp {
        
        
	bw=$1
	odir=dctcp-n$n-bw$bw
	python incast.py --bw $bw --maxq $ecnqlim --dir $odir -t $t -n $n --dctcp --delay $delay --tcpdump --qmaxhost $ecnqlim --fct $fct
	# sudo python util/plot_rate.py --maxy $bw -f $odir/txrate.txt -o $odir/rate.png
	#python  util/plot_queue.py --maxy 40 -f $odir/qlen_s1-eth1.txt -o $odir/qlen.pdf
	# sudo python util/plot_tcpprobe.py -f $odir/tcp_probe.txt -o $odir/cwnd.png
}

function mptcp {
	bw=$1
	odir=mptcp-n$n-bw$bw
	python incast.py --bw $bw --maxq $maxq --dir $odir -t $t -n $n --delay $delay --mptcp \
         --delay $delay --tcpdump --qmaxhost $qmaxhost --fct $fct
	# sudo python util/plot_rate.py --maxy $bw -f $odir/txrate.txt -o $odir/rate.png
	#python  util/plot_queue.py --maxy 100 -f $odir/qlen_s1-eth1.txt -o $odir/qlen.pdf
	# sudo python  util/plot_tcpprobe.py -f $odir/tcp_probe.txt -o $odir/cwnd.png
}

function mdtcp {
       
	bw=$1
	odir=mdtcp-n$n-bw$bw
	python incast.py --bw $bw --maxq $ecnqlim --dir $odir -t $t -n $n --delay $delay \
         --mdtcp --delay $delay --tcpdump --qmaxhost $ecnqlim --fct $fct
	# sudo python  util/plot_rate.py --maxy $bw -f $odir/txrate.txt -o $odir/rate.png
	#python  util/plot_queue.py --maxy 100 -f $odir/qlen_s1-eth1.txt -o $odir/qlen.pdf
	# sudo python  util/plot_tcpprobe.py -f $odir/tcp_probe.txt -o $odir/cwnd.png
}

m=1


while [ $m -le 1 ] ; 
do

	for bw in $bws; do
		# sysctl -w net.ipv4.tcp_congestion_control=reno
		# mn -c
	    # tcp $bw
	    # mn -c
	    # sleep 2
            
            #sudo truncate -s 0 /var/log/syslog
	    ecn $bw
	    sleep 2
            #cat /var/log/syslog | grep qavg > tcpecn_idletime
	    #sudo truncate -s 0 /var/log/syslog

	    dctcp $bw
	    sleep 2
            #cat /var/log/syslog | grep qavg > dctcp_idletime

            #sudo truncate -s 0 /var/log/syslog

	    mptcp $bw
	    sleep 2
             #cat /var/log/syslog | grep qavg > mptcp_idletime

            #sudo truncate -s 0 /var/log/syslog
	    mdtcp $bw
            #cat /var/log/syslog | grep qavg > mdtcp_idletime

	    #sleep 2 
	    #tcp_red_dctcp $bw

	

      m=$(( m + 1 ))

    done  #end for   

done #while



