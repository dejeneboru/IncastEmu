#!/usr/bin/python
import sys
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.log import lg
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.link import TCIntf
from mininet.util import irange, custom, quietRun, dumpNetConnections
from mininet.cli import CLI
from mininet.log import setLogLevel, info, warn, error, debug
from time import sleep, time
import multiprocessing
from subprocess import Popen, PIPE
import re
import termcolor as T
import argparse

from random import choice, shuffle,randint,randrange,uniform
import random



import os
from util.monitor import monitor_cpu, monitor_qlen, monitor_devs_ng

parser = argparse.ArgumentParser(description="DCTCP tester (Star topology)")
parser.add_argument('--bw', '-B',
                    dest="bw",
                    action="store",
                    help="Bandwidth of links",
                    required=True)

parser.add_argument('--dir', '-d',
                    dest="dir",
                    action="store",
                    help="Directory to store outputs",
                    required=True)

parser.add_argument('-n',
                    dest="n",
                    action="store",
                    help="Number of nodes in star.  Must be >= 3",
                    required=True)

parser.add_argument('-t',
                    dest="t",
                    action="store",
                    help="Seconds to run the experiment",
                    default=30)

parser.add_argument('-u', '--udp',
                    dest="udp",
                    action="store_true",
                    help="Run UDP test",
                    default=False)

parser.add_argument('--use-hfsc',
                    dest="use_hfsc",
                    action="store_true",
                    help="Use HFSC qdisc",
                    default=False)

parser.add_argument('--maxq',
                    dest="maxq",
                    action="store",
                    help="Max buffer size of each interface",
                    default=425)

parser.add_argument('--speedup-bw',
                    dest="speedup_bw",
                    action="store",
                    help="Speedup bw for switch interfaces",
                    default=-1)

parser.add_argument('--dctcp',
                    dest="dctcp",
                    action="store_true",
                    help="Enable DCTCP (net.ipv4.tcp_dctcp_enable)",
                    default=False)
parser.add_argument('--mptcp',
                    dest="mptcp",
                    action="store_true",
                    help="Enable MPTCP ",
                    default=False)

parser.add_argument('--mdtcp',
                    dest="mdtcp",
                    action="store_true",
                    help="Enable MDTCP ",
                    default=False)

parser.add_argument('--ecn',
                    dest="ecn",
                    action="store_true",
                    help="Enable ECN (net.ipv4.tcp_ecn)",
                    default=False)

parser.add_argument('--use-bridge',
                    dest="use_bridge",
                    action="store_true",
                    help="Use Linux Bridge as switch",
                    default=False)

parser.add_argument('--tcpdump',
                    dest="tcpdump",
                    action="store_true",
                    help="Run tcpdump on host interfaces",
                    default=False)

parser.add_argument('--tcp_reddctcp',
                    dest="tcp_reddctcp",
                    action="store_true",
                    help="test tcp with red config as DCTCP",
                    default=False)

parser.add_argument('--qmaxhost',
                    dest="qmaxhost",
                    type=int,
                    help="maximum host interace queue limit",
                    default=200)

parser.add_argument('--fct',
                    dest="fct",
                    type=int,
                    help="flow completion test ",
                    default=0)




parser.add_argument('--delay',dest="delay",default="0.075ms  0.05ms distribution normal  ")

args = parser.parse_args()
args.n = int(args.n)
args.bw = float(args.bw)
if args.speedup_bw == -1:
    args.speedup_bw = args.bw
args.n = max(args.n, 2)

if not os.path.exists(args.dir):
    os.makedirs(args.dir)

if args.use_bridge:
    from mininet.node import Bridge as Switch
else:
    from mininet.node import OVSKernelSwitch as Switch

lg.setLogLevel('output')

class StarTopo(Topo):

    def __init__(self, n=3, bw=100):
        # Add default members to class.
        super(StarTopo, self ).__init__()

        # Host and link configuration
        hconfig = {'cpu': 0.1}
        ldelay_config = {'bw': 1000, 'delay': args.delay,'max_queue_size': args.qmaxhost} 

        if args.dctcp  or args.mdtcp or args.tcp_reddctcp :
            lconfig = {'bw': bw,
               'delay': 0,
    	       'max_queue_size': int(args.maxq),
    	       'enable_ecn': True,
               'red_burst': 30,
               'red_limit':100000,
               'red_min':30000,
               'red_max':31000,
               'red_avpkt':1000,
               'red_prob':1.0,
    		   'use_hfsc': args.use_hfsc,
    		   'speedup': float(args.speedup_bw)
               }
        elif args.ecn  :
            lconfig = {'bw':bw,
               'delay': 0,
    	       'max_queue_size': int(args.maxq),
    	       'enable_ecn': True,
               'red_burst': 53,
               'red_limit':120000,
               'red_min':30000,
               'red_max':100000,
               'red_prob':0.01,
                'red_avpkt':1000,
    		   'use_hfsc': args.use_hfsc,
    		   'speedup': float(args.speedup_bw)
               }
           
        else:
            lconfig = {'bw': bw,
               'delay': 0, 
               'max_queue_size': int(args.maxq),
               'enable_red': True,
               'red_burst': 53,
               'red_limit':120000,
               'red_min':30000,
               'red_max':100000,
               'red_prob':0.01,
               'red_avpkt':1000,
               'use_hfsc': args.use_hfsc,
               'speedup': float(args.speedup_bw)
               }
            


        print '~~~~~~~~~~~~~~~~~> BW = %s' % bw

        # Create switch and host nodes
        for i in xrange(n):
            self.addHost('h%d' % (i+1), **hconfig)

        self.addSwitch('s1')

        # add link b/n receiver and switch (swith interface will be s1-eth1)
        
        self.addLink('s1', 'h1',intf=TCIntf,params1=lconfig, params2=lconfig)

        #self.addLink('h1', 's1', **lconfig)
	for i in xrange(1, n):
		if args.mptcp or args.mdtcp:
			for k in range (4):
				self.addLink('h%d' % (i+1), 's1',intf=TCIntf,params1=ldelay_config, params2=ldelay_config)
		self.addLink('h%d' % (i+1), 's1',intf=TCIntf,params1=ldelay_config, params2=ldelay_config)

            # self.addLink('h%d' % (i+1), 's1', **ldelay_config)

def waitListening(client, server, port):
    "Wait until server is listening on port"
    if not 'telnet' in client.cmd('which telnet'):
        raise Exception('Could not find telnet')
    cmd = ('sh -c "echo A | telnet -e A %s %s"' %
           (server.IP(), port))
    # print(client.cmd(cmd))
    while 'Connected' not in client.cmd(cmd):
        print('waiting for', server,
               'to listen on port', port, '\n')
        sleep(.5)

def progress(t):
    while t > 0:
        print T.colored('  %3d seconds left  \r' % (t), 'cyan'),
        t -= 1
        sys.stdout.flush()
        sleep(1)
    print '\r\n'

def enable_tcp_ecn():
    Popen("sysctl -w net.ipv4.tcp_ecn=1", shell=True).wait()
    Popen("sudo sysctl -w net.mptcp.mptcp_enabled=0",shell=True).wait()
    Popen("sysctl -w net.ipv4.tcp_congestion_control=reno", shell=True).wait()

def disable_tcp_ecn():
    os.system("sysctl -w net.ipv4.tcp_ecn=0")
    os.system("sysctl -w net.mptcp.mptcp_enabled=0")
    


def enableMPTCP(subflows):
    Popen("sysctl -w net.ipv4.tcp_ecn=0",shell=True).wait()
    Popen("sysctl -w net.mptcp.mptcp_enabled=1",shell=True).wait()
    Popen("sysctl -w net.mptcp.mptcp_debug=1",shell=True).wait()
    
    Popen("sysctl -w net.mptcp.mptcp_path_manager=ndiffports",shell=True).wait
    Popen("echo -n %i > /sys/module/mptcp_ndiffports/parameters/num_subflows" % int(subflows),shell=True).wait()
    # os.system("sudo sysctl -w net.mptcp.mptcp_path_manager=fullmesh")
    Popen("sysctl -w net.ipv4.tcp_congestion_control=olia",shell=True).wait()

def enableMDTCP(subflows):
    Popen("sysctl -w net.ipv4.tcp_ecn=1",shell=True).wait()
    Popen("sysctl -w net.mptcp.mptcp_enabled=1",shell=True).wait()
    Popen("sysctl -w net.mptcp.mptcp_debug=1",shell=True).wait()
    Popen("sysctl -w net.mptcp.mptcp_path_manager=ndiffports",shell=True).wait()
    Popen("echo -n %i > /sys/module/mptcp_ndiffports/parameters/num_subflows" % int(subflows),shell=True).wait()
    # os.system("sudo sysctl -w net.mptcp.mptcp_path_manager=fullmesh")
    Popen("sysctl -w net.ipv4.tcp_congestion_control=mdtcp",shell=True).wait()


def enable_dctcp():
    # enable_tcp_ecn()
    # Popen("sysctl -w net.mptcp.mptcp_enabled=0",shell=True).wait()
    os.system("sysctl -w net.ipv4.tcp_ecn=1")
    os.system("sysctl -w net.ipv4.tcp_congestion_control=dctcp")
    # Popen("echo dctcp > /proc/sys/net/ipv4/tcp_congestion_control",shell=True).wait()
    # Popen("echo 1 > /proc/sys/net/ipv4/tcp_ecn",shell=True).wait()
    
    

def disable_dctcp():
    disable_tcp_ecn()
    # Popen("sysctl -w net.ipv4.tcp_congestion_control=reno", shell=True).wait()
    # Popen("sysctl -w net.mptcp.mptcp_enabled=0",shell=True).wait()

def main():
    seconds = int(args.t)
    setLogLevel('output')
    # Reset to known state
    # disable_dctcp()
    disable_tcp_ecn()
    sleep(2)

    # enable_dctcp()
    cong_ctrl="reno"
    if args.ecn:
        enable_tcp_ecn()
        cong_ctrl="reno"
    elif args.dctcp:
        # enable_tcp_ecn()
        enable_dctcp()
        cong_ctrl="dctcp"

    elif args.tcp_reddctcp:
        enable_tcp_ecn()
        cong_ctrl="reno"

    elif args.mptcp:
        enableMPTCP(4)
        cong_ctrl="olia"
    elif args.mdtcp:
        enableMDTCP(4)
        cong_ctrl="mdtcp"
    else:
         os.system("sysctl -w net.ipv4.tcp_congestion_control=reno")


    topo = StarTopo(n=args.n, bw=args.bw)
    net = Mininet(topo=topo, host=CPULimitedHost,switch=Switch,
	    autoStaticArp=True)
    net.start()
   

    nodes = net.hosts + net.switches
    for node in nodes:
        node.cmd("sysctl -w net.ipv6.conf.all.disable_ipv6=1")
        node.cmd("sysctl -w net.ipv6.conf.default.disable_ipv6=1")
        node.cmd("sysctl -w net.ipv6.conf.lo.disable_ipv6=1")
        for port in node.ports:
            if str.format('{}', port) != 'lo':
                #node.cmd(str.format('ethtool --offload {} tx off rx off gro off tso off', port))
                node.cmd(str.format('ethtool -K {} gso off tso off gro off tx off rx off', port))
    s1= net.getNodeByName('s1')
    for port in s1.ports:
        if str.format('{}', port) == 's1-eth1':
            

            node.cmd(str.format('tc qdisc del dev {} root',port))
                        
            if args.mdtcp or args.dctcp or args.tcp_reddctcp:
                node.cmd(str.format('sudo ip link set txqueuelen {} dev {}',args.maxq,port))
                node.cmd(str.format('tc qdisc replace dev {} root handle 5:0 htb default 1', port))
                node.cmd(str.format('tc class replace dev {} parent 5:0 classid 5:1 htb rate {}Mbit ceil {}Mbit burst 1516', port,args.bw,args.bw))

                node.cmd(str.format('tc qdisc replace dev {} parent 5:1 handle 10: red limit 100000 min 30000 max 31000 avpkt 1000 burst 30 \
                    ecn bandwidth {} probability 1.0 ', port,args.bw))
                                     
            else:
                node.cmd(str.format('sudo ip link set txqueuelen {} dev {}',args.maxq,port))
                node.cmd(str.format('tc qdisc replace dev {} root handle 5:0 htb default 1', port))
                node.cmd(str.format('tc class replace dev {} parent 5:0 classid 5:1 htb rate {}Mbit ceil {}Mbit burst 1516', port,args.bw,args.bw))

                node.cmd(str.format('tc qdisc replace dev {} parent 5:1 handle 10: red limit 120000 min 30000 max 100000 avpkt 1000 burst 53 \
                         bandwidth {} probability 0.01',port,args.bw))

            #node.cmd(str.format('tc qdisc replace dev {} parent 10:1 handle 20: netem delay {} limit {} ', port,args.delay, args.maxq))
                
    # CLI(net)
    for i in xrange(1,args.n):
	h=net.getNodeByName('h%d'%(i+1))
	cmd="./tcp_server/tcp_server >> test_log  &"
	h.cmd(cmd,shell=True)
	print(h.IP())

    sleep(2)
    

    h1 = net.getNodeByName('h1')
   
    #clients = [net.getNodeByName('h%d' % (i+1)) for i in xrange(1, args.n)]
    #waitListening(clients[0], h1, 5001)

    monitors = []

    # monitor = multiprocessing.Process(target=monitor_cpu, args=('%s/cpu.txt' % args.dir,))
    # monitor.start()
    # monitors.append(monitor)

    monitor = multiprocessing.Process(target=monitor_qlen, args=('s1-eth1', 0.01, '%s/qlen_s1-eth1.txt' % (args.dir)))
    monitor.start()
    monitors.append(monitor)
    # sleep(2)

    # monitor = multiprocessing.Process(target=monitor_devs_ng, args=('%s/txrate.txt' % args.dir, 0.01))
    # monitor.start()
    # monitors.append(monitor)

    Popen("rmmod tcp_probe; modprobe tcp_probe port=5001; cat /proc/net/tcpprobe > %s/tcp_probe.txt" % args.dir, shell=True)
    Popen("tcpdump -i s1-eth1 -w %s/log.pcap -s 96  & " % args.dir, shell=True)
     
    
    for i in xrange(args.n-1,args.n):
	print ("./tcp_client conf/"+str(i)+"servers.conf t.csv")
	clnt_cmd="./tcp_client/tcp_client tcp_client/conf/"+str(i)+"servers.conf "+args.dir+"/fct_fanout"+str(i)+".csv"
	h1.cmd(clnt_cmd,shell=True)
    print("after Client")         
    
    wtime=seconds
    sleep(wtime)
    

    # progress(10)
    for monitor in monitors:
        monitor.terminate()
    
    # for h in net.hosts:
    #     h.cmd("netstat -s > %s/nstat_%s.txt" % (args.dir,h.IP()), shell=True)
    

    net.stop()
    # disable_dctcp()
    disable_tcp_ecn()
    Popen("killall -9 cat ping top iperf bwm-ng tcpprobe ", shell=True).wait()

if __name__ == '__main__':
    main()
