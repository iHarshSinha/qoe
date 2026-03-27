#!/usr/bin/env python3
"""
Mininet topology based on the provided network diagram.

Topology overview:
  Hosts:   hA, hB, hC, hD, hE, hF, hG
  Switches: s1, s2, s3, s4, s5, s6

Links (with tc parameters):
  Host A  -- Switch 1  : bw=20,  delay='5ms',  loss=1,  max_queue_size=100
  Host B  -- Switch 1  : bw=15,  delay='2ms',  loss=0,  max_queue_size=50
  Host C  -- Switch 1  : bw=10,  delay='8ms',  loss=2,  max_queue_size=80
  Switch 1 -- Switch 2 : bw=10,  delay='8ms',  loss=2,  max_queue_size=80
  Switch 3 -- Switch 2 : bw=40,  delay='12ms', loss=1,  max_queue_size=180
  Host D  -- Switch 3  : bw=25,  delay='3ms',  loss=1,  max_queue_size=120
  Switch 2 -- Switch 4 : bw=60,  delay='7ms',  loss=35, max_queue_size=250
  Switch 4 -- Switch 5 : bw=45,  delay='9ms',  loss=2,  max_queue_size=160
  Host E  -- Switch 5  : bw=30,  delay='1ms',  loss=0,  max_queue_size=150
  Host F  -- Switch 5  : bw=18,  delay='4ms',  loss=1,  max_queue_size=90
  Switch 5 -- Switch 6 : bw=10,  delay='8ms',  loss=2,  max_queue_size=80
  Host G  -- Switch 6  : bw=35,  delay='15ms', loss=10, max_queue_size=140

Usage:
  sudo mn -c             # clean up any leftover state first (recommended)
  sudo python3 topology.py
"""

from mininet.net import Mininet
from mininet.node import OVSController, OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink
from mininet.clean import cleanup


def build_topology():
    # Always clean up leftover Mininet state before starting
    info("*** Cleaning up any previous Mininet state\n")
    cleanup()

    net = Mininet(
        controller=OVSController,
        switch=OVSKernelSwitch,
        link=TCLink,
        autoSetMacs=True,
    )

    info("*** Adding controller\n")
    net.addController("c0")

    # ------------------------------------------------------------------
    # Hosts
    # ------------------------------------------------------------------
    info("*** Adding hosts\n")
    hA = net.addHost("hA", ip="10.0.0.1/24")
    hB = net.addHost("hB", ip="10.0.0.2/24")
    hC = net.addHost("hC", ip="10.0.0.3/24")
    hD = net.addHost("hD", ip="10.0.0.4/24")
    hE = net.addHost("hE", ip="10.0.0.5/24")
    hF = net.addHost("hF", ip="10.0.0.6/24")
    hG = net.addHost("hG", ip="10.0.0.7/24")

    # ------------------------------------------------------------------
    # Switches
    # ------------------------------------------------------------------
    info("*** Adding switches\n")
    s1 = net.addSwitch("s1")
    s2 = net.addSwitch("s2")
    s3 = net.addSwitch("s3")
    s4 = net.addSwitch("s4")
    s5 = net.addSwitch("s5")
    s6 = net.addSwitch("s6")

    # ------------------------------------------------------------------
    # Links — explicit intfName on both ends prevents "File exists"
    # errors when Mininet is restarted without a full mn -c cleanup.
    # ------------------------------------------------------------------
    info("*** Adding links\n")

    # Host A -- Switch 1
    net.addLink(
        hA, s1,
        intfName1="hA-eth0", intfName2="s1-eth1",
        bw=20, delay="5ms", loss=1, max_queue_size=100,
    )

    # Host B -- Switch 1
    net.addLink(
        hB, s1,
        intfName1="hB-eth0", intfName2="s1-eth2",
        bw=15, delay="2ms", loss=0, max_queue_size=50,
    )

    # Host C -- Switch 1
    net.addLink(
        hC, s1,
        intfName1="hC-eth0", intfName2="s1-eth3",
        bw=10, delay="8ms", loss=2, max_queue_size=80,
    )

    # Switch 1 -- Switch 2
    net.addLink(
        s1, s2,
        intfName1="s1-eth4", intfName2="s2-eth1",
        bw=10, delay="8ms", loss=2, max_queue_size=80,
    )

    # Switch 2 -- Switch 3
    net.addLink(
        s2, s3,
        intfName1="s2-eth2", intfName2="s3-eth1",
        bw=40, delay="12ms", loss=1, max_queue_size=180,
    )

    # Host D -- Switch 3
    net.addLink(
        hD, s3,
        intfName1="hD-eth0", intfName2="s3-eth2",
        bw=25, delay="3ms", loss=1, max_queue_size=120,
    )

    # Switch 2 -- Switch 4
    net.addLink(
        s2, s4,
        intfName1="s2-eth3", intfName2="s4-eth1",
        bw=60, delay="7ms", loss=35, max_queue_size=250,
    )

    # Switch 4 -- Switch 5
    net.addLink(
        s4, s5,
        intfName1="s4-eth2", intfName2="s5-eth1",
        bw=45, delay="9ms", loss=2, max_queue_size=160,
    )

    # Host E -- Switch 5
    net.addLink(
        hE, s5,
        intfName1="hE-eth0", intfName2="s5-eth2",
        bw=30, delay="1ms", loss=0, max_queue_size=150,
    )

    # Host F -- Switch 5
    net.addLink(
        hF, s5,
        intfName1="hF-eth0", intfName2="s5-eth3",
        bw=18, delay="4ms", loss=1, max_queue_size=90,
    )

    # Switch 5 -- Switch 6
    net.addLink(
        s5, s6,
        intfName1="s5-eth4", intfName2="s6-eth1",
        bw=10, delay="8ms", loss=2, max_queue_size=80,
    )

    # Host G -- Switch 6
    net.addLink(
        hG, s6,
        intfName1="hG-eth0", intfName2="s6-eth2",
        bw=35, delay="15ms", loss=10, max_queue_size=140,
    )

    # ------------------------------------------------------------------
    # Start network
    # ------------------------------------------------------------------
    info("*** Starting network\n")
    net.start()

    info("*** Running CLI  (type 'exit' or Ctrl-D to quit)\n")
    CLI(net)

    info("*** Stopping network\n")
    net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    build_topology()
