#!/usr/bin/env python
"""

NOTE:

(Notes from the original gist start here)
Example usage:
  ./sudo python destroy.py

Pip requirements:
-----------------
pycrypto==2.6.1
pyvmomi==5.5.0
"""


import MySQLdb
import time
import atexit
import getpass
import sys
from MySQLdb import Error as MySqlError
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
# import os

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

    def __init__(self):
        self.conn = _MysqlBase()

    def found(self):
        pass

    def _commit(self, cmd):
        self.conn.runCommand(cmd)
        self.conn.conn.commit()


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
def destroy(instance, instance_name):

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
    vm = get_obj(content, [vim.VirtualMachine], instance_name)
    if not vm:
        print "Not Found %s" % instance_name
        return

    # poweroff = wm.PowerOff()
    # WaitTask(poweroff, 'VM poweroff task')

    delete = vm.Destroy()
    if not delete:
        print "Cloud not delete %s" % instance_name

    WaitTask(delete, 'VM delete task')
    delete_instances(instance, instance_name)


def delete_instances(instance, instance_name):
    cmd = "delete from instances where name=\"%s\"" % instance_name
    instance._commit(cmd)


def get_delete_instances(instance):
    cmd = "select name from instances where status=\"error\""
    return instance.conn.runCommand(cmd)


def main():

    # what VM template to use

    # get idle ip from db
    instance = Instance()
    instances = get_delete_instances(instance)
    print instances
    if not instances:
        print "Not any instance was deleted"
        return
    for ins in instances:
        instance_name = ins[0].title()
        print instance_name
        destroy(instance, instance_name)
        time.sleep(3)


"""
 Main program
"""
if __name__ == "__main__":
    if getpass.getuser() != 'root':
        sys.exit("You must be root to run this.  Quitting.")
    main()
