#!/usr/bin/env python
"""

NOTE:
This gist has been moved to EZmomi:

   https://github.com/snobear/ezmomi


(Notes from the original gist start here)
Example usage:
  ./clone.py --hostname test01 --template CentOS65 --ips 172.9.9.11 172.12.120.22 --cpus 2 --mem 4

Pip requirements:
-----------------
ecdsa==0.10
netaddr==0.7.10
pycrypto==2.6.1
pyvmomi==5.5.0
wsgiref==0.1.2
"""


from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
# from pyVim import vmodl
import MySQLdb
import datetime
from MySQLdb import Error as MySqlError
import uuid
import time
import atexit
import getpass
import telnetlib
# import os
import sys
# from netaddr import IPNetwork, IPAddress
import argparse
# from copy import deepcopy

# DEFIND VMWARE VCENTER SERVER
vserver = "172.16.0.2"
port = 443
username = "administrator"
password = "P@$$w0rd"
vcenter = {
    "vserver": vserver,
    "port": port,
    "username": username,
    "password": password,
    }


# DEFIND VMWARE VCENTER DATABASE
datacenter_name = "JQ"
cluster_name = ""
compute_resource = "172.16.0.11"
datastore_name = "datastore1"
network_name = "Mgmt"
default_datacenter = {
    "datacenter_name": datacenter_name,
    "cluster_name": cluster_name,
    "compute_resource": compute_resource,
    "datastore_name": datastore_name,
    "network_name": network_name,
    }


# DEFIND TEMPLATE HOST
TEMPLATE_HOST = "172.16.0.201"
custom_dns = "172.16.0.1"
custom_gateway = '172.16.0.254'
custom_username = "root"
custom_password = "123456"


# DEFIND DATABASE CONFIGURE
db_host = "localhost"
db_username = "admin"
db_password = "123456"
db_name = "apicloud"
db_port = 3306

################################################
# defind ubuntu eth0 configure
################################################
ubuntu_eth0 = """
auto lo
iface lo inet loopback

auto eth0
iface eth0 inet static
address %s
netmask 255.255.255.0
network 172.16.0.0
broadcast 172.16.0.255
dns-nameservers %s
gateway %s
"""
ubuntu_configure = "echo \"%s\" > /etc/network/interfaces\n"

################################################
# defind fedora eth0 configure
################################################
fedora_eth0 = """
NAME=eth0
ONBOOT=yes
TYPE=Ethernet
BOOTPROTO=static
DEFROUTE=yes
PREFIX0=24
IPADDR0=%s
DNS1=%s
GATEWAY0=%s
"""
fedora_configure = "echo \"%s\" > /etc/sysconfig/network-scripts/ifcfg-eth0\n"

################################################
# defind centos eth0 configure
################################################
centos_eth0 = """
DEVICE=eth0
TYPE=Ethernet
ONBOOT=yes
NM_CONTROLLED=yes
BOOTPROTO=static
IPADDR=%s
NETMASK=255.255.255.0
GATEWAY=%s
DNS=%s
"""
centos_configure = "echo \"%s\" > /etc/sysconfig/network-scripts/ifcfg-eth0\n"


centos_hostname_cfg = """
NETWORKING=yes
HOSTNAME=%s
"""

ubuntu_hostname = "hostname %s"
fedora_hostname = "hostname %s"
centos_hostname = "echo \"%s\" > /etc/sysconfig/network\n"

os_type = {'ubuntu': {'ifcfg_eth0': ubuntu_eth0,
                      'configure': ubuntu_configure,
                      # 'reboot': '/etc/init.d/networking restart\n'},
                      'reboot': 'reboot\n',
                      'poweroff': 'poweroff\n',
                      'hostname': ubuntu_hostname,
                      'close_23': 'chkconfig telent off\n'},
           'fedora': {'ifcfg_eth0': fedora_eth0,
                      'configure': fedora_configure,
                      'reboot': '/etc/init.d/network restart\n',
                      'poweroff': 'poweroff\n',
                      'hostname': fedora_hostname,
                      'close_23': 'chkconfig telent off\n'},
           'centos': {'ifcfg_eth0': centos_eth0,
                      'configure': centos_configure,
                      'reboot': '/etc/init.d/network restart\n',
                      'hostname': centos_hostname,
                      'poweroff': 'poweroff\n',
                      'close_23': 'chkconfig telent off\n'},
           'win7': {},
           'winxp': {}}


class TLogin(object):
    def __init__(self, host, username, password, port=23, timeout=5):
        self.tn = telnetlib.Telnet(host, port, timeout)
        self.username = username
        if not password:
            raise Exception('not input password')
        self.password = password
        self.login(username, password)

    def login(self, username, password):
        self.tn.read_until("login: ")
        self.tn.write(username + "\n")
        self.tn.read_until("Password: ")
        self.tn.write(password + "\n")

    def close(self):
        self.tn.close()

    def flush(self, cmdlist):
        for cmd in cmdlist:
            print cmd
            self.tn.write(cmd)
        self.tn.write("exit\n")
        self.tn.read_all()


class _MysqlBase(object):
    def __init__(self):
        try:
            self.conn = self._conn()
            self.cur = None
            self.set()
        except MySQLdb.Error, e:
            print str(e)

    def _conn(self):
        try:
            return MySQLdb.Connection(
                host=db_host,
                user=db_username,
                passwd=db_password,
                db=db_name,
                port=db_port)
        except MySQLdb.Error, e:
            print "XXXXXXXXX "
            print str(e)
            return None

    def set(self):
        try:
            if self.conn:
                self.cur = self.conn.cursor()
        except MySQLdb.Error, e:
            self.conn = None
            self.cur = None
            print str(e)

    def reconn(self):
        self.conn = self._conn()
        self.set()

    def refresh(self):
        self.clear()
        self.reconn()
        self.set()

    def clear(self):
        if self.cur:
            self.cur.close()
            self.cur = None
        if self.conn:
            self.conn.close()
            self.conn = None

    def runCommand(self, cmd):
        try:
            if not self.conn or not self.cur:
                raise MySqlError('Not Connect DB')
            self.cur.execute(cmd)
            return self.cur.fetchall()
        except Exception, e:
            print str(e)
            raise MySqlError(str(e))

    def _isfound(self, id):
        raise NotImplementedError('_MysqlBase _isfound Not Implemented')


class Instance(object):

    instances = "instances"
    iptable = "iptable"
    CREATE_CMD = "insert into instances (\
    instance_uuid,\
    name,\
    ip,\
    status,\
    os_type,\
    username,\
    passwd,\
    template_type,\
    instance_type,\
    iaas_type,\
    is_alloc,\
    create_time,\
    online_time,\
    off_time) values(\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\
    \"%s\",\"%s\",\"%s\",\"%s\",\"%d\",\"%s\",\"%s\",\"%s\")"
    TITLE = "instance-%s"
    DEFAULT_IAAS_TYPE = "vsphere"
    DEFAULT_CUSTOMERS = "1hao"
    DEFAULT_USERNAME = "test"
    DEFAULT_PASSWD = "123456"

    def __init__(self):
        self.conn = _MysqlBase()

    def found(self):
        pass

    def _get_cmd(self, instance_name, ip, model_type="8-8192-40", template_type="centos6.4"):
        instance_uuid = str(uuid.uuid1())
        name = instance_name
        ts = time.time()
        timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        ip = ip
        status = "stop"
        username = custom_username
        passwd = custom_password
        os_type = template_type
        instance_type = model_type
        iaas_type = "vsphere"
        is_alloc = 0
        create_time = online_time = off_time = timestamp
        return self.CREATE_CMD % (instance_uuid, name,
                                  ip,
                                  status,
                                  os_type,
                                  username,
                                  passwd,
                                  template_type,
                                  instance_type,
                                  iaas_type,
                                  is_alloc,
                                  create_time,
                                  online_time,
                                  off_time), ip

    def alloc_ip(self, ip):
        print 'alloc ip : %s' % ip
        cmd = "update %s set is_alloc=1 where ipaddress=\"%s\"" % (self.iptable, ip.strip())
        self._commit(cmd)

    def _commit(self, cmd):
        self.conn.runCommand(cmd)
        self.conn.conn.commit()

    def get_idle_ip(self):
        cmd = "select ipaddress from %s where is_alloc=0" % (self.iptable)
        ips = self.conn.runCommand(cmd)
        if ips:
            print "ipaddress: %s" % str(ips[0][0])
            return ips[0][0]
        return None


# reconfigure host
def reconfigure(instance, name, ip):
    try:
        # set system type
        yhd_os_type = "centos"
        cmdlist = []
        system = os_type.get(yhd_os_type, None)
        if not system:
            raise Exception('ERROR: not support %s system' % yhd_os_type)

        # set reconfigure ip and poweroff command
        ifcfg_eth0 = system['ifcfg_eth0'] % (ip, custom_gateway, custom_dns)
        configure = system['configure'] % ifcfg_eth0

        # set host name
        hostname = 'instance-%s' % ip.replace('.', '-')
        cfg = centos_hostname_cfg % hostname
        hostname_configure = system['hostname'] % cfg

        # set close Telnet command
        close_telnet = system['close_23']

        # set poweroff command
        poweroff = system['poweroff']

        cmdlist.append(configure)
        cmdlist.append(hostname_configure)
        cmdlist.append(close_telnet)
        cmdlist.append(poweroff)

        # login host pass Telnet
        tl = TLogin(TEMPLATE_HOST, custom_username, custom_password, timeout=20)
        instance.alloc_ip(ip)
        cmd, ip = instance._get_cmd(name, ip)
        print cmd
        instance._commit(cmd)
        tl.flush(cmdlist)
        tl.close()
    except Exception, e:
        print str(e)


def WaitTask(task, actionName='job', hideResult=False):
    print 'Waiting for %s to complete.' % actionName

    while task.info.state == vim.TaskInfo.State.running:
        time.sleep(2)

    if task.info.state == vim.TaskInfo.State.success:
        if task.info.result is not None and not hideResult:
            out = '%s completed successfully, result: %s' % (actionName, task.info.result)
        else:
            out = '%s completed successfully.' % actionName
    else:
        out = '%s did not complete successfully: %s' % (actionName, unicode(task.info.error))
        print out
        # should be a Fault... check XXX
        raise task.info.error

    # may not always be applicable, but can't hurt.
    return task.info.result


# Get the vsphere object associated with a given text name
def get_obj(content, vimtype, name):
    obj = None
    container = content.viewManager.CreateContainerView(content.rootFolder, vimtype, True)
    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj


# Connect to vCenter server and deploy a VM from template
def clone(instance, instance_name, template_name, ip):

    # connect to vCenter server
    try:
        si = SmartConnect(
            host=vcenter['vserver'],
            user=vcenter["username"],
            pwd=vcenter["password"],
            port=vcenter["port"])
    except IOError, e:
        sys.exit("Unable to connect to vsphere server. Error message: %s" % e)

    # add a clean up routine
    atexit.register(Disconnect, si)

    content = si.RetrieveContent()

    # get the vSphere objects associated with the human-friendly labels we supply
    datacenter = get_obj(content,
                         [vim.Datacenter],
                         default_datacenter["datacenter_name"])
    print datacenter
    # get the folder where VMs are kept for this datacenter
    destfolder = datacenter.vmFolder
    print destfolder

    # get cluster
    cluster = get_obj(
        content,
        [vim.ClusterComputeResource],
        default_datacenter["compute_resource"])
    print cluster

    compute = get_obj(content, [vim.ComputeResource], default_datacenter["compute_resource"])
    print type(compute)

    # use same root resource pool that my desired cluster uses
    print compute.resourcePool
    # resource_pool = cluster.resourcePool
    resource_pool = compute.resourcePool
    # datastore = get_obj(content, [vim.Datastore], default_datacenter["datastore_name"])
    template_vm = get_obj(content, [vim.VirtualMachine], template_name)

    # Relocation spec
    relospec = vim.vm.RelocateSpec()
    # relospec.datastore = datastore
    relospec.pool = resource_pool

    # VM config spec
    vmconf = vim.vm.ConfigSpec()

    # Hostname settings
    ident = vim.vm.customization.LinuxPrep()
    print type(ident)
    ident.hostName = vim.vm.customization.FixedName()
    ident.hostName.name = instance_name
    print type(ident.hostName)

    # Clone spec
    clonespec = vim.vm.CloneSpec()
    clonespec.location = relospec
    clonespec.config = vmconf
    clonespec.powerOn = True
    clonespec.template = False

    # fire the clone task
    task = template_vm.Clone(
        folder=destfolder,
        name=instance_name.title(),
        spec=clonespec)
    WaitTask(task, 'VM clone task')
    time.sleep(60)

    # reconfigure host
    reconfigure(instance, instance_name, ip)


def main(**kwargs):

    # what VM template to use
    template_name = kwargs['template']

    # get idle ip from db
    instance = Instance()

    # clone template to a new VM
    for i in range(0, kwargs['number']):
        print "START create [%d] instance..." % (i+1)
        ip = instance.get_idle_ip()
        print ip
        if not ip:
            raise Exception("not alloc ip")

        ipname = ip.replace('.', '-')
        name = "instance-%s-%s" % (str(uuid.uuid1()), ipname)
        clone(instance, name, template_name, ip)
        print name
        time.sleep(3)


"""
 Main program
"""
if __name__ == "__main__":
    if getpass.getuser() != 'root':
        sys.exit("You must be root to run this.  Quitting.")

    # Define command line arguments
    parser = argparse.ArgumentParser(
        description='Deploy a new VM in vSphere')

    parser.add_argument(
        '--template',
        type=str,
        help='template to clone',
        default='centos6.4',
        required=True)

    parser.add_argument(
        '--number',
        type=int,
        help='Number of CPUs',
        default=2)

    # Parse arguments and hand off to main()
    args = parser.parse_args()
    main(**vars(args))
