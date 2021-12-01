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
    info(net['r1'].cmd("cd r1;bird -l"))
    info(net['r2'].cmd("cd r2;bird -l"))
    info(net['r3'].cmd("cd r3;bird -l"))
    info(net['r4'].cmd("cd r4;bird -l"))
    info(net['h1'].cmd("cd h1;bird -l"))
    info(net['h2'].cmd("cd h2;bird -l"))
    info(net['r1'].cmd("route"))
    info(net['r2'].cmd("route"))
    info(net['r3'].cmd("route"))
    info(net['r4'].cmd("route"))

    #info(net["h2"].cmd("iperf3 -s -p 8787 > partc.out &"))
    info(net["r1"].cmd("tc qdisc add dev r1-eth1 root handle 1: tbf rate 100mbit limit 10000 buffer 10000"))
    info(net["r1"].cmd("tc qdisc add dev r1-eth2 root handle 1: tbf rate 100mbit limit 10000 buffer 10000"))
    info(net["r1"].cmd("tc qdisc add dev r1-eth3 root handle 1: tbf rate 100mbit limit 10000 buffer 10000"))
    info(net["r1"].cmd("tc qdisc add dev r1-eth1 parent 1:1 handle 10: netem delay 30ms"))
    info(net["r1"].cmd("tc qdisc add dev r1-eth2 parent 1:1 handle 10: netem delay 30ms"))
    info(net["r1"].cmd("tc qdisc add dev r1-eth3 parent 1:1 handle 10: netem delay 30ms"))


    info(net["r2"].cmd("tc qdisc add dev r2-eth1 root handle 1: tbf rate 100mbit limit 10000 buffer 10000"))
    info(net["r2"].cmd("tc qdisc add dev r2-eth2 root handle 1: tbf rate 100mbit limit 10000 buffer 10000"))
    info(net["r2"].cmd("tc qdisc add dev r2-eth1 parent 1:1 handle 10: netem delay 30ms"))
    info(net["r2"].cmd("tc qdisc add dev r2-eth2 parent 1:1 handle 10: netem delay 30ms"))



    info(net["r3"].cmd("tc qdisc add dev r3-eth1 root handle 1: tbf rate 100mbit limit 10000 buffer 10000"))
    info(net["r3"].cmd("tc qdisc add dev r3-eth2 root handle 1: tbf rate 100mbit limit 10000 buffer 10000"))
    info(net["r3"].cmd("tc qdisc add dev r3-eth1 parent 1:1 handle 10: netem delay 30ms"))
    info(net["r3"].cmd("tc qdisc add dev r3-eth2 parent 1:1 handle 10: netem delay 30ms"))


    info(net["r4"].cmd("tc qdisc add dev r4-eth1 root handle 1: tbf rate 100mbit limit 10000 buffer 10000"))
    info(net["r4"].cmd("tc qdisc add dev r4-eth2 root handle 1: tbf rate 100mbit limit 10000 buffer 10000"))
    info(net["r4"].cmd("tc qdisc add dev r4-eth3 root handle 1: tbf rate 100mbit limit 10000 buffer 10000"))
    info(net["r4"].cmd("tc qdisc add dev r4-eth1 parent 1:1 handle 10: netem delay 30ms"))
    info(net["r4"].cmd("tc qdisc add dev r4-eth2 parent 1:1 handle 10: netem delay 30ms"))
    info(net["r4"].cmd("tc qdisc add dev r4-eth3 parent 1:1 handle 10: netem delay 30ms"))
    #info(net["h1"].cmd("iperf3 -c 150.3.0.252 -p 8787 -t 10"))
    #info(net["h2"].cmd("cat partc.out"))

    net.start()
    CLI(net)
    net.stop()

setLogLevel('info')
run()
