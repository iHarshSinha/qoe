import os
from mininet.net import Mininet
from mininet.node import OVSController
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.node import Controller

def buildTopo():
    net = Mininet(controller=OVSController)

    print("*** Adding controller")
    c0 = net.addController('c0', controller=Controller, command='ovs-testcontroller', port=6633)

    print("*** Adding hosts")
    h1 = net.addHost('h1')
    h2 = net.addHost('h2')
    h3 = net.addHost('h3')
    h4 = net.addHost('h4')

    print("*** Adding switches")
    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')

    print("*** Creating links")
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(s1, s2)
    net.addLink(h3, s2)
    net.addLink(h4, s2)

    print("*** Starting network")
    net.start()

    print("*** Testing connectivity")
    net.pingAll()

    CLI(net)
    net.stop()

if __name__ == '__main__':
    os.system("mn -c")
    setLogLevel('info')
    buildTopo()

