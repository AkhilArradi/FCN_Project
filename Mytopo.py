#!/usr/bin/python
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Node
from mininet.log import setLogLevel, info
from mininet.cli import CLI


class LinuxRouter(Node):
    def config(self, **params):
        super(LinuxRouter, self).config(**params)
        self.cmd('sysctl net.ipv4.ip_forward=1')

    def terminate(self):
        self.cmd('sysctl net.ipv4.ip_forward=0')
        super(LinuxRouter, self).terminate()


class NetworkTopo(Topo):
    def build(self, **_opts):

        # Add 2 routers in two different subnets
        r1 = self.addHost('r1', cls=LinuxRouter, ip='150.0.0.1/24')
        r2 = self.addHost('r2', cls=LinuxRouter, ip='150.1.0.1/24')
        r3 = self.addHost('r3', cls=LinuxRouter, ip='150.2.0.1/24')
        r4 = self.addHost('r4', cls=LinuxRouter, ip='150.3.0.1/24')

        # Adding hosts specifying the default route
        h1 = self.addHost(name='h1',
                          ip='150.0.0.251/24',
                          defaultRoute = 'via 150.0.0.1')
        h2 = self.addHost(name='h2',
                          ip='150.3.0.252/24',
                          defaultRoute = 'via 150.3.0.1')

        # Add host-switch links in the same subnet
        self.addLink(h1,r1, intfName2 = 'r1-eth1', param2={'ip': '150.0.0.1/24'})
        self.addLink(h2,r4, intfName2 = 'r4-eth1', param2={'ip': '150.3.0.1/24'})

        # Add router-router link in a new subnet for the router-router connection
        self.addLink(r2,
                     r4,
                     intfName1='r2-eth2',
                     intfName2='r4-eth3',
                     params1={'ip': '150.1.0.1/24'},
                     params2={'ip': '150.1.0.2/24'})

        self.addLink(r3,
                     r4,
                     intfName1='r3-eth2',
                     intfName2='r4-eth2',
                     params1={'ip': '150.2.0.1/24'},
                     params2={'ip': '150.2.0.2/24'})

        self.addLink(r1,
                     r2,
                     intfName1='r1-eth2',
                     intfName2='r2-eth1',
                     params1={'ip': '150.20.0.1/24'},
                     params2={'ip': '150.20.0.2/24'})

        self.addLink(r1,
                     r3,
                     intfName1='r1-eth3',
                     intfName2='r3-eth1',
                     params1={'ip': '150.30.0.1/24'},
                     params2={'ip': '150.30.0.2/24'})


def run():
    topo = NetworkTopo()
    net = Mininet(topo=topo)

    # Add routing for reaching networks that aren't directly connected
    info(net['r1'].cmd("ip route add 150.1.0.0/24 via 150.20.0.2"))
    info(net['r1'].cmd("ip route add 150.2.0.0/24 via 150.30.0.2"))
    info(net['r1'].cmd("ip route add 150.3.0.0/24 via 150.20.0.2"))

    info(net['r2'].cmd("ip route add 150.2.0.0/24 via 150.1.0.2"))
    info(net['r2'].cmd("ip route add 150.3.0.0/24 via 150.1.0.2"))
    info(net['r2'].cmd("ip route add 150.0.0.0/24 via 150.20.0.1"))

    info(net['r3'].cmd("ip route add 150.0.0.0/24 via 150.30.0.1"))
    info(net['r3'].cmd("ip route add 150.1.0.0/24 via 150.2.0.2"))
    info(net['r3'].cmd("ip route add 150.3.0.0/24 via 150.2.0.2"))

    info(net['r4'].cmd("ip route add 150.0.0.0/24 via 150.1.0.1"))
    info(net['r4'].cmd("ip route add 150.20.0.0/24 via 150.1.0.1"))
    info(net['r4'].cmd("ip route add 150.30.0.0/24 via 150.2.0.1"))

    info(net['r1'].cmd("route"))
    info(net['r2'].cmd("route"))
    info(net['r3'].cmd("route"))
    info(net['r4'].cmd("route"))

    net.start()
    CLI(net)
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    run()

