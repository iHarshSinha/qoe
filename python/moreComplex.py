from mininet.net import Mininet
from mininet.node import OVSController, OVSKernelSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info


def createTopo():
    net = Mininet(controller=OVSController, switch=OVSKernelSwitch)

    info("*** Adding controller\n")
    net.addController('c0')

    info("*** Adding switches\n")
    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')
    s3 = net.addSwitch('s3')
    s4 = net.addSwitch('s4')
    s5 = net.addSwitch('s5')
    s6 = net.addSwitch('s6')

    info("*** Adding hosts\n")
    hA = net.addHost('hA', ip='10.0.0.1/24')
    hB = net.addHost('hB', ip='10.0.0.2/24')
    hC = net.addHost('hC', ip='10.0.0.3/24')
    hD = net.addHost('hD', ip='10.0.0.4/24')
    hE = net.addHost('hE', ip='10.0.0.5/24')
    hF = net.addHost('hF', ip='10.0.0.6/24')
    hG = net.addHost('hG', ip='10.0.0.7/24')

    info("*** Creating host-switch links\n")
    # s1 host connections
    net.addLink(hA, s1, bw=20, delay='5ms',  loss=1, max_queue_size=100)
    net.addLink(hB, s1, bw=15, delay='2ms',  loss=0, max_queue_size=50)
    net.addLink(hC, s1, bw=10, delay='8ms',  loss=2, max_queue_size=80)

    # s3 host connections
    net.addLink(hD, s3, bw=25, delay='3ms',  loss=1, max_queue_size=120)

    # s5 host connections
    net.addLink(hE, s5, bw=30, delay='1ms',  loss=0, max_queue_size=150)
    net.addLink(hF, s5, bw=18, delay='4ms',  loss=1, max_queue_size=90)

    # s6 host connections
    net.addLink(hG, s6, bw=12, delay='6ms',  loss=3, max_queue_size=70)

    info("*** Creating switch-switch links\n")
    net.addLink(s1, s2, bw=50, delay='10ms', loss=0, max_queue_size=200)
    net.addLink(s3, s2, bw=40, delay='12ms', loss=1, max_queue_size=180)
    net.addLink(s2, s4, bw=60, delay='7ms',  loss=35, max_queue_size=250)
    net.addLink(s4, s5, bw=45, delay='9ms',  loss=2, max_queue_size=160)
    net.addLink(s5, s6, bw=35, delay='15ms', loss=10, max_queue_size=140)

    info("*** Starting network\n")
    net.start()

    info("*** Running CLI\n")
    CLI(net)

    info("*** Stopping network\n")
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    createTopo()

