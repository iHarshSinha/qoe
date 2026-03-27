from mininet.net import Mininet
from mininet.node import Controller
from mininet.cli import CLI
from mininet.log import setLogLevel

def buildTopo():
    net = Mininet(controller=Controller)

    c0 = net.addController('c0')

    h1 = net.addHost('h1')
    h2 = net.addHost('h2')
    h3 = net.addHost('h3')
    h4 = net.addHost('h4')

    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')

    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(s1, s2)
    net.addLink(h3, s2)
    net.addLink(h4, s2)

    net.start()
    net.pingAll()

    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    buildTopo()

