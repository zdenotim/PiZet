#!/usr/bin/env python

import re
import subprocess
import time
import sys

start_time = time.clock()
# First version of my monitoring tool for Raspberry Pi running Raspbian
# Update to 2016a0.4 introduce arguments and help
#
# All information are available like in version 2016a0.4 but now you can also choose what info do you want to see
# on screen by using arguments
#
# -a all info               -
# -c CPU info               -
# -d Device info            -
# -m Memory info            -
# -n Networking info        -
# -s Storage info           -
# -u Interface utilization  -
#
# -h Help and script usage info


# returns device hostname
def host_name():
    name = subprocess.Popen(['hostname'], stdout=subprocess.PIPE)
    host = name.stdout.read()
    hostname = re.search(r"(\S*)", host).group(1)
    return hostname


def serial_nr():
    path = "/proc/cpuinfo"
    with open(path, "r") as f:
        cpuinfo = f.read()
        serial = re.search(r"Serial[ \t]*:[ \t]*(.+)", cpuinfo).group(1)
        hardware = re.search(r"Hardware[ \t]*:[ \t]*(.+)", cpuinfo).group(1)
        revision = re.search(r"Revision[ \t]*:[ \t]*(.+)", cpuinfo).group(1)
        return serial, hardware, revision


# returns CPU temperature in Celsius and Fahrenheit
def cpu_temp():
    temperature = subprocess.Popen(['sudo', '/opt/vc/bin/vcgencmd', 'measure_temp'], stdout=subprocess.PIPE)
    out_temperature = temperature.stdout.read()
    out_temp = re.search(b"=(\S*)'", out_temperature)
    temp_celsius = float(out_temp.group(1))
    temp_fahrenheit = (temp_celsius * 1.8) + 32

    return temp_celsius, '{0:.2f}'.format(temp_fahrenheit)

# returns ARM processor frequency, core frequency, core firmware version and processor model name


def cpu_info():
    # arm frequency
    arm_freq = subprocess.Popen(['/opt/vc/bin/vcgencmd', 'measure_clock', 'arm'], stdout=subprocess.PIPE)
    out_arm_freq = arm_freq.stdout.read()
    out_arm_f = re.search(b"=(.+$)", out_arm_freq)
    # core frequency
    core_freq = subprocess.Popen(['/opt/vc/bin/vcgencmd', 'measure_clock', 'core'], stdout=subprocess.PIPE)
    out_core_freq = core_freq.stdout.read()
    out_core_f = re.search(b"=(.+$)", out_core_freq)
    # core volt
    core_volt = subprocess.Popen(['/opt/vc/bin/vcgencmd', 'measure_volts'], stdout=subprocess.PIPE)
    out_core_volt = core_volt.stdout.read()
    out_core_v = re.search(b"=(.+)V", out_core_volt)
    # firmware
    firmware = subprocess.Popen(['/opt/vc/bin/vcgencmd', 'version'], stdout=subprocess.PIPE)
    out_firmware = firmware.stdout.read()
    out_f = re.search(b"version\s(\S*)", out_firmware)
    # cpu model
    model = subprocess.Popen(['lscpu'], stdout=subprocess.PIPE)
    out_model = model.stdout.read()
    out_m = re.search(b"Model\sname:\s*(.+)", out_model)

    arm_f = int(out_arm_f.group(1)) / 1000000
    core_f = int(out_core_f.group(1)) / 1000000
    core_v = '{0:.2f}'.format(float(out_core_v.group(1)))
    firmware_c = out_f.group(1)
    model = out_m.group(1)

    return arm_f, core_f, core_v, firmware_c, model


def cpu_util():
    # cpu load per 1,5,15 minutes
    cpu_utilization = subprocess.Popen(['uptime'], stdout=subprocess.PIPE)
    out_cpu_utilization = cpu_utilization.stdout.read()
    cpu_load = re.search(r"load\saverage:\s(\S*),\s(\S*),\s(\S*)", out_cpu_utilization)

    min1 = float(cpu_load.group(1))
    min5 = float(cpu_load.group(2))
    min15 = float(cpu_load.group(3))

    # number of CPU's (cores)
    lscpu = subprocess.Popen(['lscpu'], stdout=subprocess.PIPE)
    cpu_core_nr = lscpu.stdout.read()
    cpu_cores = float(re.search(r"CPU\S*\s*(\d)", cpu_core_nr).group(1))

    util1 = min1 / (cpu_cores / 100)
    util5 = min5 / (cpu_cores / 100)
    util15 = min15 / (cpu_cores / 100)

    return util1, util5, util15


# returns memory info
def memory():
    mem_info = subprocess.Popen(['free', '-m'], stdout=subprocess.PIPE)
    out_meminfo = mem_info.stdout.read()
    mem = re.search(r"Mem:\s*(\S*)\s*(\S*)\s*(\S*)\s*(\S*)\s*(\S*)\s*(\S*)", out_meminfo)
    swap = re.search(r"Swap:\s*(\S*)\s*(\S*)\s*(\S*)", out_meminfo)

    total = mem.group(1)
    used = mem.group(2)
    free = mem.group(3)
    shared = mem.group(4)
    buffers = mem.group(5)
    cached = mem.group(6)
    swap_total = swap.group(1)
    swap_used = swap.group(2)

    return total, used, free, shared, buffers, cached, swap_total, swap_used


# returns network information
def net_info():
    ip4 = subprocess.Popen(['ip', '-4', '-o', 'a'], stdout=subprocess.PIPE)
    ip_int = ip4.stdout.readlines()[:]
    # print ip_int
    l = len(ip_int)
    # print l
    int_names = []
    for i in range(l):
        line = re.search(r"\S*\s(\S+)\s*(\S*)\s*(\S*)/", ip_int[i])
        int_names.append(line.group(1))

    int_names.remove('lo')
    unique_int_names = list(set(int_names))

    # print unique_int_names
    # print int_names

    for i in unique_int_names:
        int_h = subprocess.Popen(['ifconfig', i], stdout=subprocess.PIPE)
        out = int_h.stdout.read()
        open('int_info_' + i, 'w').write(out)
    # print out

    # parse info from separate help interface files
    print "{:10}".format("Interface"), "{:18}".format("MAC"), "{:15}".format("IP"), "{:10}".format("RX"),\
        "{:10}".format("TX")

    for int_name in unique_int_names:
        with open("int_info_" + int_name, "r") as f:
            read_data = f.read()

            mac_addr = re.search(r"HWaddr\s(\S*)", read_data).group(1)
            ip_addr = re.search(r"inet\saddr\S(\S*)", read_data).group(1)
            # bytes converted to Megabytes
            rx = (float(re.search(r"RX\sbytes:(\S*)", read_data).group(1))) / 1048576
            # value in bytes
            tx = (float(re.search(r"TX\sbytes:(\S*)", read_data).group(1))) / 1048576

            print "{:10}".format(int_name), "{:18}".format(mac_addr), "{:15}".format(ip_addr), '{:5.2f}'.format(rx),\
                "{:4}".format("MiB"), '{:5.2f}'.format(tx), "MiB"

    # remove help files after parsing is complete
    for i in unique_int_names:
        subprocess.call(["rm", "-r", "int_info_" + i])


# returns disk usage and partitions
def disk_usage():
    diskusage = subprocess.Popen(['df', '-h'], stdout=subprocess.PIPE)
    out_diskusage = diskusage.stdout.read()
    return out_diskusage


# returns information about processor like serial number, processor type and revision
def serial_nr():
    path = "/proc/cpuinfo"
    with open(path, "r") as f:
        cpuinfo = f.read()
        serial = re.search(r"Serial[ \t]*:[ \t]*(.+)", cpuinfo).group(1)
        hardware = re.search(r"Hardware[ \t]*:[ \t]*(.+)", cpuinfo).group(1)
        revision = re.search(r"Revision[ \t]*:[ \t]*(.+)", cpuinfo).group(1)
        return serial, hardware, revision


# returns distribution info
def os_distribution():
    distribution = subprocess.Popen(['cat', '/etc/os-release'], stdout=subprocess.PIPE)
    out_distro = distribution.stdout.read()
    distro = re.search(r'PRETTY_NAME="(.+)"', out_distro).group(1)
    return distro


# returns uptime in human readable form
def up_time():
    # read /proc/uptime and extract needed time
    f = open("/proc/uptime", "r")
    uptime = f.read()
    up = re.search(r"(\S*)\.", uptime)
    time_up_sec = int(up.group(1))
    f.close()
    # up time conversion from seconds to D:H:M:S format
    days = time_up_sec / 86400
    hours = (time_up_sec - (days * 86400)) / 3600
    minutes = (time_up_sec - (days*86400) - (hours*3600)) / 60
    seconds = (time_up_sec - (days*86400) - (hours*3600) - (minutes*60))
    # output formatted
    time_up = '{:d} {:d}:{:d}:{:d}'.format(days, hours, minutes, seconds)
    return time_up_sec, time_up


# calculates and returns interface utilization
def speed():
    interval = float(sys.argv[3])

    iface = sys.argv[2]
    speed_eth0_rx1 = subprocess.Popen(['cat', '/sys/class/net/' + iface + '/statistics/rx_bytes'], stdout=subprocess.PIPE)
    rx1 = float(speed_eth0_rx1.stdout.read())

    speed_eth0_tx1 = subprocess.Popen(['cat', '/sys/class/net/' + iface + '/statistics/tx_bytes'], stdout=subprocess.PIPE)
    tx1 = float(speed_eth0_tx1.stdout.read())

    time.sleep(interval)

    speed_eth0_rx2 = subprocess.Popen(['cat', '/sys/class/net/' + iface + '/statistics/rx_bytes'], stdout=subprocess.PIPE)
    rx2 = float(speed_eth0_rx2.stdout.read())

    speed_eth0_tx2 = subprocess.Popen(['cat', '/sys/class/net/' + iface + '/statistics/tx_bytes'], stdout=subprocess.PIPE)
    tx2 = float(speed_eth0_tx2.stdout.read())

    # print rx1, rx2

    rx = (rx2 - rx1) / (interval * 1024 * 1024)
    tx = (tx2 - tx1) / (interval * 1024 * 1024)

    rx_p = (((rx2 - rx1) + (tx2 - tx1)) / (interval * 1024 * 1024))

    print "Current interface", iface, "utilization:"
    print "{:8.4f}".format(rx), 'Mbps RX'
    print "{:8.4f}".format(tx), 'Mbps TX'

    print "{:8.4f}".format(rx_p), '%'


# returns time when was script executed
def current_time():
    return time.ctime()


# help will
def pizethelp():
    print """
     ####      ######           #
     #   #  #      #    ####    #
     ####         #    #    #  ####
     #      #    #     #####    #
     #      #   #      #        #
     #      #  ######   ####    ##    usage information:

    python alpha_pi_zet0_4.py [-a, -c, -d, -m, -n, -s] for help [-h or --help]

    python alpha_pi_zet0_4.py -u [eth0 | wlan0] n

    n - time interval for which is interface utilization calculated

    Available arguments with short description and usage
      -a all info               - PiZet shows all bellow described information except Interface utilization (-u).
                                  Argument -u must be run separately

      -c CPU info               - shows CPU temperature in Celsius and Fahrenheit, CPU utilization for 1 and 15 minute
                                  average, then processor model, type and revision. Next shows processor frequency,
                                  core frequency, core voltage and firmware.

      -d Device info            - shows device serial number, operating system distribution and system up time

      -m Memory info            - shows memory usage information like total, free and used memory...

      -n Networking info        - display interface name its MAC address, IP address, received and transmitted data

      -s Storage info           - shows storage information, same output like "df -h"

      -u Interface utilization  - calculates utilization for selected interface for specified time interval

      -h or --help              - script usage info

        """


print "Hostname:", host_name()

if len(sys.argv) <= 1:
    pizethelp()
elif sys.argv[1] == "-c":
    print "\nProcessor Info\n--------------"
    print "CPU Temperature in Celsius / Fahrenheit:", cpu_temp()[0], "C /", cpu_temp()[1], "F\n"
    print "CPU utilization:", "{:>3.2f}".format(cpu_util()[0]), "% (1 min average)"
    print "{:>21.2f}".format(cpu_util()[2]), "% (15 min average)"
    print "\nProcessor model:", cpu_info()[4]
    print "Processor type:", serial_nr()[1], ", Revision:", serial_nr()[2]
    print "\nARM Frequency:", cpu_info()[0], "Mhz"
    print "CORE Frequency:", cpu_info()[1], "Mhz"
    print "CORE Volt:", cpu_info()[2], "V"
    print "Firmware:", cpu_info()[3]
elif sys.argv[1] == "-m":
    print "\nMemory Info\n-----------"
    print "Free memory:", memory()[2], "M\n\nTotal memory:", memory()[0], "M\nUsed memory:", memory()[
        1], "M\nShared memory:", memory()[3], "M\nBuffers:", memory()[4], "M\nCached:", memory()[5], "M\n"
    print "Swap:"
    print "Total:", memory()[6], "M\nUsed:", memory()[7], "M"
elif sys.argv[1] == "-n":
    print "\nNetworking Info\n---------------"
    net_info()
elif sys.argv[1] == "-s":
    print "\nDisk Usage\n----------"
    print disk_usage()
elif sys.argv[1] == "-d":
    print "\nDevice Info\n-----------"
    print "Serial number:", serial_nr()[0]
    print "Distribution:", os_distribution()
    print "\nUp time:", up_time()[1]
elif sys.argv[1] == "-u" and len(sys.argv) < 4:
    pizethelp()
elif sys.argv[1] == "-u":
    speed()
elif sys.argv[1] == "-a":
    print "Serial number:", serial_nr()[0]
    print "Distribution:", os_distribution()
    print "\nUptime:", up_time()[1], "\n"
    print "Processor Info\n--------------"
    print "CPU Temperature in Celsius / Fahrenheit:", cpu_temp()[0], "C /", cpu_temp()[1], "F\n"
    print "CPU utilization:", "{:>3.2f}".format(cpu_util()[0]), "% (1 min average)"
    print "{:>21.2f}".format(cpu_util()[2]), "% (15 min average)"
    print "\nProcessor model:", cpu_info()[4]
    print "Processor type:", serial_nr()[1], ", Revision:", serial_nr()[2]
    print "\nARM Frequency:", cpu_info()[0], "Mhz"
    print "CORE Frequency:", cpu_info()[1], "Mhz"
    print "CORE Volt:", cpu_info()[2], "V"
    print "Firmware:", cpu_info()[3]
    print "\nMemory Info\n-----------"
    print "Free memory:", memory()[2], "M\n\nTotal memory:", memory()[0], "M\nUsed memory:", memory()[
        1], "M\nShared memory:", memory()[3], "M\nBuffers:", memory()[4], "M\nCached:", memory()[5], "M\n"
    print "Swap:"
    print "Total:", memory()[6], "M\nUsed:", memory()[7], "M\n"
    print "Network Info\n------------"
    net_info()
    print "\nDisk Usage\n----------"
    print disk_usage()
elif sys.argv[1] == "-h" or sys.argv[1] == "--help":
    pizethelp()

print "\nLast Refresh:", current_time()
print "\nAlpha version of PiZet (2016a0.4)"
print "Code made by zdenotim (c) 2016"
print "--- %s seconds ---" %(time.clock() - start_time)
