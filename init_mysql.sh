#!/bin/sh

#set global variable

USERNAME="admin"
PASSWD="123456"
#vsphere image template
VSPHERE="centos6.0 centos6.1 ubuntu12.04 ubuntu14.01 window7 windowxp"
#ip range
ip_start="10.55.1"

function init_template_table(){

    echo "init template table"
    #init vsphere image template 
    for template_name in $VSPHERE
    do
        mysql -u $USERNAME -p$PASSWD -e "
        use apicloud;
        insert into templatetype (name, iaas_type) values(\"$template_name\", \"vsphere\");
        "
    done
    #init openstack image template
}

#init ip table
function init_ip_table(){
    echo "init ip table"
    for i in $(seq 1 253)
    do
        sleep 0.05
        ipaddress=$ip_start.$i
        mysql -u $USERNAME -p$PASSWD -e "
            use apicloud;
            insert into iptable (ipaddress, vlan_id, is_alloc) values (\"$ipaddress\", 4, 0)
        "
    done
}

function init_instancetype(){
    echo "init instances type"
    mysql -u $USERNAME -p$PASSWD -e "
        use apicloud;
        insert into instancetype (name, core_num, ram, disk, extend_disk) values (\"large\", 8, 8192, 60, 0)
    "
    sleep 0.05
    mysql -u $USERNAME -p$PASSWD -e "
        use apicloud;
        insert into instancetype (name, core_num, ram, disk, extend_disk) values (\"small\", 1, 1024, 60, 0)
    "
}

function create_db(){

    echo "Create apicloud database..."
    mysql -u $USERNAME -p$PASSWD -e "
        drop database if exists apicloud;
        create database apicloud;

        use apicloud;

        drop table if exists tasks; 
        create table tasks(
            task_id varchar(40) NOT NULL,
            create_time DATETIME NOT NULL,
            template_type varchar(16) NOT NULL,
            model_type varchar(16) NOT NULL,
            status varchar(16) NOT NULL,
            instances_num INT UNSIGNED NOT NULL,
            PRIMARY KEY (task_id)
        );

        drop table if exists instances; 
        create table instances(
            instance_uuid varchar(40) NOT NULL,
            task_id varchar(40) NOT NULL,
            name varchar(40) NOT NULL,
            ip varchar(40) NOT NULL,
            status varchar(40) NOT NULL,
            os_type varchar(40) NOT NULL,
            username varchar(40) NOT NULL,
            passwd varchar(40) NOT NULL,
            template_type varchar(16) NOT NULL,
            instance_type varchar(16) NOT NULL,
            iaas_type varchar(16) NOT NULL,
            customers varchar(16) NOT NULL,
            create_time DATETIME NOT NULL,
            online_time DATETIME NOT NULL,
            off_time DATETIME,
            PRIMARY KEY (instance_uuid)
        );

        drop table if exists instancetype; 
        create table instancetype(
            name varchar(24) NOT NULL,
            core_num INT UNSIGNED NOT NULL,
            ram INT UNSIGNED NOT NULL,
            disk INT UNSIGNED NOT NULL,
            extend_disk INT UNSIGNED NOT NULL,
            PRIMARY KEY (name)
        );

        drop table if exists templatetype; 
        create table templatetype(
            name varchar(24) NOT NULL,
            iaas_type varchar(24) NOT NULL,
            PRIMARY KEY (name)
        );


        drop table if exists iptable; 
        create table iptable(
            ipaddress varchar(24) NOT NULL,
            vlan_id INT UNSIGNED,
            is_alloc TINYINT(1) NOT NULL,
            PRIMARY KEY(ipaddress)
        );
        show tables;
    "
}

function main(){

    create_db
    init_template_table
    init_instancetype
    init_ip_table
}


### CDS MAIN ###
main
exit 0
