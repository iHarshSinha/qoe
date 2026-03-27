#!/usr/bin/env python3
import time
import os
from mininet.net import Mininet
from mininet.node import OVSController, OVSKernelSwitch
from mininet.log import setLogLevel, info
from mininet.link import TCLink
from mininet.clean import cleanup

def run_ditg_simulation():
    info("*** Cleaning up any previous Mininet state\n")
    cleanup()

    net = Mininet(controller=OVSController, switch=OVSKernelSwitch, link=TCLink, autoSetMacs=True)
    net.addController("c0")

    # --- Adding Hosts ---
    hA = net.addHost("hA", ip="10.0.0.1/24")
    hB = net.addHost("hB", ip="10.0.0.2/24")
    hC = net.addHost("hC", ip="10.0.0.3/24")
    hD = net.addHost("hD", ip="10.0.0.4/24")
    hE = net.addHost("hE", ip="10.0.0.5/24")
    hF = net.addHost("hF", ip="10.0.0.6/24")
    hG = net.addHost("hG", ip="10.0.0.7/24")

    # --- Adding Switches ---
    s1, s2, s3 = net.addSwitch("s1"), net.addSwitch("s2"), net.addSwitch("s3")
    s4, s5, s6 = net.addSwitch("s4"), net.addSwitch("s5"), net.addSwitch("s6")

    # --- Adding Links ---
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
    
    # --- 1. Start ITGRecv on Destination Hosts ---
    info("*** Starting D-ITG Receivers on hE, hF, and hG...\n")
    hE.cmd('ITGRecv &')
    hF.cmd('ITGRecv &')
    hG.cmd('ITGRecv &')
    time.sleep(2) # Allow receivers to initialize

    # --- 2. Create the Multi-flow Script ---
    info("*** Generating D-ITG multi-flow script...\n")
    duration_ms = 30000 # 30 seconds for the test
    
    # Simulating the exact scenario from your PDF (Listing 4)
    script_content = f"""
-a 10.0.0.5 -T UDP -E 50 -e 160 -t {duration_ms} -l sender_voip.log
-a 10.0.0.6 -T TCP -t {duration_ms} -l sender_ftp.log
-a 10.0.0.7 -T UDP -E 25 -e 1200 -t {duration_ms} -l sender_video.log
"""
    with open("itg_script.txt", "w") as f:
        f.write(script_content.strip())

    # --- 3. Execute Traffic Generation ---
    info(f"*** Sending multi-class traffic from hA for {duration_ms/1000} seconds...\n")
    # This runs all 3 flows concurrently from Host A
    hA.cmd('ITGSend -f itg_script.txt')
    
    info("*** Traffic generation complete. Decoding logs...\n")

    # --- 4. Decode Logs to Extract QoS Features ---
    # ITGDec parses the binary logs into human-readable text files
    os.system('ITGDec sender_voip.log > qos_voip_results.txt')
    os.system('ITGDec sender_ftp.log > qos_ftp_results.txt')
    os.system('ITGDec sender_video.log > qos_video_results.txt')

    info("*** Logs decoded. Check qos_*_results.txt for Bandwidth, Delay, Jitter, and Loss.\n")

    # --- 5. Clean up ---
    hE.cmd('killall ITGRecv')
    hF.cmd('killall ITGRecv')
    hG.cmd('killall ITGRecv')
    net.stop()

if __name__ == "__main__":
    setLogLevel("info")
    run_ditg_simulation()
