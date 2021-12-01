import argparse
from time import sleep, mktime
import subprocess
import csv
from datetime import datetime
import matplotlib
matplotlib.use('Agg')   # Force matplotlib to not use any Xwindows backend.
import matplotlib.pyplot as plt
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink
from mininet.util import dumpNodeConnections, quietRun
from mininet.log import info, lg, setLogLevel
tcpprobe_csv_header = ['time', 'src_addr_port', 'dst_addr_port', 'bytes', 'next_seq', 'unacknowledged', 'cwnd',
                       'slow_start', 'swnd', 'smoothedRTT', 'rwnd']
iperf_csv_header = ['time', 'src_addr', 'src_port', 'dst_addr' ,'dst_port', 'other', 'interval', 'B_sent', 'bps']
class DumbbellTopo(Topo):
    def build(self, delay=2):
        br_params = dict(bw=984, delay='{0}ms'.format(delay), max_queue_size=82*delay,
                         use_htb=True)  
        ar_params = dict(bw=252, delay='0ms', max_queue_size=(21*delay*20)/100,
                         use_htb=True) 
        hi_params = dict(bw=960, delay='0ms', max_queue_size=80*delay, use_htb=True)
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')
        s4 = self.addSwitch('s4')
        self.addLink(s1, s2, cls=TCLink, **br_params)
        self.addLink(s1, s3, cls=TCLink, **ar_params)
        self.addLink(s2, s4, cls=TCLink, **ar_params)
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')
        h4 = self.addHost('h4')
        self.addLink(s3, h1, cls=TCLink, **hi_params)
        self.addLink(s3, h3, cls=TCLink, **hi_params)
        self.addLink(s4, h2, cls=TCLink, **hi_params)
        self.addLink(s4, h4, cls=TCLink, **hi_params)


def clean_tcpprobe_procs():
    print('Killing any running tcpprobe processes...')
    procs = quietRun('pgrep -f /proc/net/tcpprobe').split()
    for proc in procs:
        output = quietRun('sudo kill -KILL {0}'.format(proc.rstrip()))
        if output!='':
            print(output)


def draw_cwnd_plot(time_h1, cwnd_h1, time_h3, cwnd_h3, alg, delay):
    print('*** Drawing the cwnd vs time plot...')
    plt.plot(time_h1, cwnd_h1, label='Source Host 1 (h1)')
    plt.plot(time_h3, cwnd_h3, label='Source Host 2 (h3)')

    plt.xlabel('Time (sec)')
    plt.ylabel('Cwnd (MSS)')

    plt.title("Cwnd vs. Time Graph\n{0} TCP Congestion Control Algorithm Delay={1}ms"
              .format(alg.capitalize(), delay))

    plt.legend()

    plt.savefig('cwnd_vs_time_{0}_{1}ms'.format(alg, delay))
    plt.close()
def draw_fairness_plot(time_h1, bw_h1, time_h3, bw_h3, alg, delay):
    print('*** Drawing the fairness plot...')
    plt.plot(time_h1, bw_h1, label='Source Host 1 (h1)')
    plt.plot(time_h3, bw_h3, label='Source Host 2 (h3)')
    plt.xlabel('Time (sec)')
    plt.ylabel('Bandwidth (Mbps)')

    plt.title("TCP Fairness Graph\n{0} TCP Congestion Control Algorithm Delay={1}ms"
              .format(alg.capitalize(), delay))

    plt.legend()
    plt.savefig('fairness_graph_{0}_{1}ms'.format(alg, delay))
    plt.close()
def dumbbell_test():
    topo = DumbbellTopo(delay=21)
    net = Mininet(topo)
    net.start()
    print("Dumping host connections...")
    dumpNodeConnections(net.hosts)
    print("Testing network connectivity...")
    h1, h2 = net.get('h1', 'h2')
    h3, h4 = net.get('h3', 'h4')
    for i in range(1, 10):
        net.pingFull(hosts=(h1, h2))
    for i in range(1, 10):
        net.pingFull(hosts=(h2, h1))
    for i in range(1, 10):
        net.pingFull(hosts=(h4, h3))
    for i in range(1, 10):
        net.pingFull(hosts=(h3, h4))
    print("Testing bandwidth between h1 and h2...")
    net.iperf(hosts=(h1, h2), fmt='m', seconds=10, port=5001)
    print("Testing bandwidth between h3 and h4...")
    net.iperf(hosts=(h3, h4), fmt='m', seconds=10, port=5001)
    print("Stopping test...")
    net.stop()
def parse_iperf_data(alg, delay, host_addrs):
    print('*** Parsing iperf data...')
    data = dict({'h1': {'Mbps': list(), 'time': list()}, 'h2': {'Mbps': list(), 'time': list()},
                 'h3': {'Mbps': list(), 'time': list()}, 'h4': {'Mbps': list(), 'time': list()}})
    first_row = True
    with open('iperf_{0}_h1-h2_{1}ms.txt'.format(alg, delay), 'r') as fcsv:
        r = csv.DictReader(fcsv, delimiter=',', fieldnames=iperf_csv_header)
        for row in r:
            if host_addrs['h1'] in row['src_addr']:
                time = mktime(datetime.strptime(str(row['time']), '%Y%m%d%H%M%S').timetuple())
                if first_row:
                    time_init = time
                    first_row = False
                    data['h1']['time'].append(time - time_init)
                elif time-time_init == data['h1']['time'][-1]:
                    data['h1']['time'].append(time - time_init + 1)
                else:
                    data['h1']['time'].append(time - time_init)
                data['h1']['Mbps'].append(int(row['bps'])/1000000)
    print('h1: time={0}, bandwidth={1}'.format(data['h1']['time'].pop(), data['h1']['Mbps'].pop()))
    first_row = True
    with open('iperf_{0}_h3-h4_{1}ms.txt'.format(alg, delay), 'r') as fcsv:
        r = csv.DictReader(fcsv, delimiter=',', fieldnames=iperf_csv_header)
        for row in r:
            if host_addrs['h3'] in row['src_addr']:
                time = mktime(datetime.strptime(str(row['time']), '%Y%m%d%H%M%S').timetuple())
                if first_row:
                    first_row = False
                    data['h3']['time'].append(time - time_init)
                elif time-time_init == data['h3']['time'][-1]:
                    data['h3']['time'].append(time - time_init + 1)
                else:
                    data['h3']['time'].append(time - time_init)
                data['h3']['Mbps'].append(int(row['bps'])/1000000)
    print('h3: time={0}, bandwidth={1}'.format(data['h3']['time'].pop(), data['h3']['Mbps'].pop()))
    return data


def parse_tcpprobe_data(alg, delay, host_addrs):
    print('*** Parsing tcpprobe data...')
    data = dict({'h1': {'cwnd': list(), 'time': list()}, 'h2': {'cwnd': list(), 'time': list()},
                 'h3': {'cwnd': list(), 'time': list()}, 'h4': {'cwnd': list(), 'time': list()}})
    first_row = True
    with open('tcpprobe_{0}_{1}ms.txt'.format(alg, delay), 'r') as fcsv:
        r = csv.DictReader(fcsv, delimiter=' ', fieldnames=tcpprobe_csv_header, restval=-1000)
        for row in r:
            if host_addrs['h1'] in row['src_addr_port']:
                time = float(row['time'])
                if first_row:
                    first_row = False
                    time_init = time
                data['h1']['time'].append(time - time_init)
                data['h1']['cwnd'].append(int(row['cwnd']))
            elif host_addrs['h3'] in row['src_addr_port']:
                time = float(row['time'])
                data['h3']['time'].append(time - time_init)
                data['h3']['cwnd'].append(int(row['cwnd']))
    return data


def start_tcpprobe(filename):
    print('Unloading tcp_probe module...')
    clean_tcpprobe_procs()
    output = quietRun('sudo rmmod tcp_probe')
    if output != '':
        print(output.rstrip())
    print('Loading tcp_probe module...')
    output = quietRun('sudo modprobe tcp_probe full=1')
    if output != '':
        print(output.rstrip())
    print('Saving tcpprobe output to: {0}'.format(filename))
    return subprocess.Popen('sudo cat /proc/net/tcpprobe > {0}'.format(filename), shell=True)
def tcp_tests(algs, delays, iperf_runtime, iperf_delayed_start):
    print("*** Tests settings:\n - Algorithms: {0}\n - delays: {1}\n - Iperf runtime: {2}\n - Iperf delayed start: {3}"
          .format(algs, delays, iperf_runtime, iperf_delayed_start))
    for alg in algs:
        print('*** Starting test for algorithm={0}...'.format(alg))
        for delay in delays:
            print('*** Starting test for delay={0}ms...'.format(delay))
            print('*** Starting tcpprobe recording...')
            tcpprobe_proc = start_tcpprobe('tcpprobe_{0}_{1}ms.txt'.format(alg, delay))
            print('*** Creating topology for delay={0}ms...'.format(delay))
            topo = DumbbellTopo(delay=delay)
            net = Mininet(topo)
            net.start()
            h1, h2, h3, h4 = net.get('h1', 'h2', 'h3', 'h4')
            host_addrs = dict({'h1': h1.IP(), 'h2': h2.IP(), 'h3': h3.IP(), 'h4': h4.IP()})
            print('Host addrs: {0}'.format(host_addrs))
            popens = dict()
            print("*** Starting iperf servers h2 and h4...")
            popens[h2] = h2.popen(['iperf', '-s', '-p', '5001', '-w', '16m'])
            popens[h4] = h4.popen(['iperf', '-s', '-p', '5001', '-w', '16m'])
            print("*** Starting iperf client h1...")
            popens[h1] = h1.popen('iperf -c {0} -p 5001 -i 1 -w 16m -M 1460 -N -Z {1} -t {2} -y C > \
                                   iperf_{1}_{3}_{4}ms.txt'
                                  .format(h2.IP(), alg, iperf_runtime, 'h1-h2', delay), shell=True)
            print("*** Waiting for {0}sec...".format(iperf_delayed_start))
            sleep(iperf_delayed_start)

            print("*** Starting iperf client h3...")
            popens[h3] = h3.popen('iperf -c {0} -p 5001 -i 1 -w 16m -M 1460 -N -Z {1} -t {2} -y C > \
                                   iperf_{1}_{3}_{4}ms.txt'
                                  .format(h4.IP(), alg, iperf_runtime, 'h3-h4', delay), shell=True)
            print("*** Waiting {0}sec for iperf clients to finish...".format(iperf_runtime))
            popens[h1].wait()
            popens[h3].wait()
            print('*** Terminate the iperf servers and tcpprobe processes...')
            popens[h2].terminate()
            popens[h4].terminate()
            tcpprobe_proc.terminate()
            popens[h2].wait()
            popens[h4].wait()
            tcpprobe_proc.wait()
            clean_tcpprobe_procs()
            print("*** Stopping test...")
            net.stop()
            print('*** Processing data...')
            data_cwnd = parse_tcpprobe_data(alg, delay, host_addrs)
            data_fairness = parse_iperf_data(alg, delay, host_addrs)

            draw_cwnd_plot(data_cwnd['h1']['time'], data_cwnd['h1']['cwnd'],
                           data_cwnd['h3']['time'], data_cwnd['h3']['cwnd'], alg, delay)
            draw_fairness_plot(data_fairness['h1']['time'], data_fairness['h1']['Mbps'],
                               data_fairness['h3']['time'], data_fairness['h3']['Mbps'], alg, delay)
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='TCP Congestion Control tests in a dumbbell topology.')
    parser.add_argument('-a', '--algorithms', nargs='+', default=['reno', 'cubic'],
                        help='List TCP Congestion Control algorithms to test.')
    parser.add_argument('-d', '--delays', nargs='+', type=int, default=[21, 81, 162],
                        help='List of backbone router one-way propagation delays to test.')
    parser.add_argument('-i', '--iperf-runtime', type=int, default=1000, help='Time to run the iperf clients.')
    parser.add_argument('-j', '--iperf-delayed-start', type=int, default=250,
                        help='Time to wait before starting the second iperf client.')
    parser.add_argument('-l', '--log-level', default='info', help='Verbosity level of the logger. Uses `info` by default.')
    parser.add_argument('-t', '--run-test', action='store_true', help='Run the dumbbell topology test.')
    args = parser.parse_args()
    if args.log_level:
        setLogLevel(args.log_level)
    else:
        setLogLevel('info')

    if args.run_test:
        dumbbell_test()
    else:
        tcp_tests(args.algorithms, args.delays, args.iperf_runtime, args.iperf_delayed_start)
