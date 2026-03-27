#!/usr/bin/env python3
import csv
import time
from mininet.net import Mininet
from mininet.node import OVSController, OVSKernelSwitch
from mininet.log import setLogLevel, info
from mininet.link import TCLink
from mininet.clean import cleanup

def run_automated_test():
    info("*** Cleaning up any previous Mininet state\n")
    cleanup()

    net = Mininet(controller=OVSController, switch=OVSKernelSwitch, link=TCLink, autoSetMacs=True)
    net.addController("c0")

    # Adding Hosts
    hA = net.addHost("hA", ip="10.0.0.1/24")
    hB = net.addHost("hB", ip="10.0.0.2/24")
    hC = net.addHost("hC", ip="10.0.0.3/24")
    hD = net.addHost("hD", ip="10.0.0.4/24")
    hE = net.addHost("hE", ip="10.0.0.5/24")
    hF = net.addHost("hF", ip="10.0.0.6/24")
    hG = net.addHost("hG", ip="10.0.0.7/24")

    # Adding Switches
    s1, s2, s3 = net.addSwitch("s1"), net.addSwitch("s2"), net.addSwitch("s3")
    s4, s5, s6 = net.addSwitch("s4"), net.addSwitch("s5"), net.addSwitch("s6")

    # Adding Links
    net.addLink(hA, s1, bw=20, delay="5ms", loss=1, max_queue_size=100)
    net.addLink(hB, s1, bw=15, delay="2ms", loss=0, max_queue_size=50)
    net.addLink(hC, s1, bw=10, delay="8ms", loss=2, max_queue_size=80)
    net.addLink(s1, s2, bw=10, delay="8ms", loss=2, max_queue_size=80)
    net.addLink(s2, s3, bw=40, delay="12ms", loss=1, max_queue_size=180)
    net.addLink(hD, s3, bw=25, delay="3ms", loss=1, max_queue_size=120)
    net.addLink(s2, s4, bw=60, delay="7ms", loss=35, max_queue_size=250)
    net.addLink(s4, s5, bw=45, delay="9ms", loss=2, max_queue_size=160)
    net.addLink(hE, s5, bw=30, delay="1ms", loss=0, max_queue_size=150)
    net.addLink(hF, s5, bw=18, delay="4ms", loss=1, max_queue_size=90)
    net.addLink(s5, s6, bw=10, delay="8ms", loss=2, max_queue_size=80)
    net.addLink(hG, s6, bw=35, delay="15ms", loss=10, max_queue_size=140)

    info("*** Starting network\n")
    net.start()
    
    # host d to e
    info("*** Starting automated traffic generation for QoE/QoS metrics...\n")
    
    csv_filename = 'qoe_network_metrics_hD_to_hE.csv'
    info(f"*** Saving receiver-side results to {csv_filename}\n")

    with open(csv_filename, mode='w') as file:
        file.write("Timestamp,Src_IP,Src_Port,Dst_IP,Dst_Port,ID,Interval,Transferred_Bytes,Bits_per_Second,Jitter_ms,Lost_Datagrams,Total_Datagrams,Loss_Percentage,Out_of_Order\n")

    # Starting the iperf server on Host E
    # Redirect standard output (>>) directly into our CSV file in the background
    hE.cmd(f'iperf -s -u -y C >> {csv_filename} &')
    time.sleep(1) # Give the server a moment to spin up

    tests = [
        {'src': hD, 'dst': '10.0.0.5', 'bw': '10M', 'time': 15, 'name': 'hD_to_hE_10M'},
        {'src': hD, 'dst': '10.0.0.5', 'bw': '15M', 'time': 15, 'name': 'hD_to_hE_15M'},
        {'src': hD, 'dst': '10.0.0.5', 'bw': '20M', 'time': 15, 'name': 'hD_to_hE_20M'}
    ]

    for test in tests:
        info(f" -> Running {test['name']} from {test['src'].IP()} at {test['bw']}...\n")
        cmd = f"iperf -c {test['dst']} -u -b {test['bw']} -t {test['time']}"
        test['src'].cmd(cmd) 
        time.sleep(2) # Cool down between tests

    info("*** Automated testing complete!\n")
    
    hE.cmd('kill %iperf')



    # host g
    info("*** Starting automated traffic generation for QoE/QoS metrics...\n")
    
    csv_filename = 'qoe_network_metrics.csv'
    info(f"*** Saving receiver-side results to {csv_filename}\n")

    with open(csv_filename, mode='w') as file:
        file.write("Timestamp,Src_IP,Src_Port,Dst_IP,Dst_Port,ID,Interval,Transferred_Bytes,Bits_per_Second,Jitter_ms,Lost_Datagrams,Total_Datagrams,Loss_Percentage,Out_of_Order\n")

    # 2. Start the iperf server on Host G
    # -s (server), -u (UDP), -y C (CSV format)
    # Redirect standard output (>>) directly into our CSV file in the background
    hG.cmd(f'iperf -s -u -y C >> {csv_filename} &')
    time.sleep(1) # Give the server a moment to spin up

    # 3. Define test scenarios
    tests = [
        {'src': hA, 'dst': '10.0.0.7', 'bw': '10M', 'time': 15, 'name': 'hA_Normal_Load'},
        {'src': hB, 'dst': '10.0.0.7', 'bw': '20M', 'time': 15, 'name': 'hB_High_Load'},
        {'src': hD, 'dst': '10.0.0.7', 'bw': '30M', 'time': 15, 'name': 'hD_Overload_Test'}
    ]

    # 4. Run the clients
    for test in tests:
        info(f" -> Running {test['name']} from {test['src'].IP()} at {test['bw']}...\n")
        # The client just sends the traffic; we don't need to parse its output anymore
        cmd = f"iperf -c {test['dst']} -u -b {test['bw']} -t {test['time']}"
        test['src'].cmd(cmd) 
        time.sleep(2) # Cool down between tests

    info("*** Automated testing complete!\n")
    
    # 5. Clean up the background server process
    hG.cmd('kill %iperf')

    # host a to d
    info("*** Host A & D...\n")
    
    csv_filename = 'qoe_network_metrics_atod.csv'
    info(f"*** Saving receiver-side results to {csv_filename}\n")

    with open(csv_filename, mode='w') as file:
        file.write("Timestamp,Src_IP,Src_Port,Dst_IP,Dst_Port,ID,Interval,Transferred_Bytes,Bits_per_Second,Jitter_ms,Lost_Datagrams,Total_Datagrams,Loss_Percentage,Out_of_Order\n")

    # 2. Start the iperf server on Host G
    # -s (server), -u (UDP), -y C (CSV format)
    # Redirect standard output (>>) directly into our CSV file in the background
    hD.cmd(f'iperf -s -u -y C >> {csv_filename} &')
    time.sleep(1) # Give the server a moment to spin up

    # 3. Define test scenarios
    tests = [
        {'src': hA, 'dst': '10.0.0.4', 'bw': '10M', 'time': 15, 'name': 'hA_Normal_Load'},
        {'src': hB, 'dst': '10.0.0.4', 'bw': '10M', 'time': 15, 'name': 'hB_High_Load'},
        {'src': hC, 'dst': '10.0.0.4', 'bw': '10M', 'time': 15, 'name': 'hC_Overload_Test'}
    ]

    # 4. Run the clients
    for test in tests:
        info(f" -> Running {test['name']} from {test['src'].IP()} at {test['bw']}...\n")
        # The client just sends the traffic; we don't need to parse its output anymore
        cmd = f"iperf -c {test['dst']} -u -b {test['bw']} -t {test['time']}"
        test['src'].cmd(cmd) 
        time.sleep(2) # Cool down between tests

    info("*** Automated testing complete!\n")
    
    # 5. Clean up the background server process
    hD.cmd('kill %iperf')
    net.stop()

if __name__ == "__main__":
    setLogLevel("info")
    run_automated_test()
