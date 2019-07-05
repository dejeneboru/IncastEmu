# references:
# https://www.wireshark.org/docs/dfref/t/tcp.html
# http://serverfault.com/questions/336588/how-to-calculate-packet-loss-from-a-binary-tcpdump-file
# http://www.tcpdump.org/manpages/pcap-filter.7.html

if [ "$#" -ne 2 ] || [ -z $1 ]; then
    echo "Usage: cap_pktloss.sh <outfile.pcap> interval"
    exit 0
fi

sudo touch $1
sudo tshark -i eth11 -f "host 10.10.3.1 and tcp" -q -z io,stat,$2,"COUNT(tcp.analysis.retransmission) tcp.analysis.retransmission","COUNT(tcp.analysis.duplicate_ack)tcp.analysis.duplicate_ack","COUNT(tcp.analysis.lost_segment) tcp.analysis.lost_segment","COUNT(tcp.analysis.fast_retransmission) tcp.analysis.fast_retransmission","COUNT(tcp.analysis.out_of_order) tcp.analysis.out_of_order","COUNT(tcp.analysis.window_update) tcp.analysis.window_update" -w $1 

