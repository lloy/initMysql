#!/bin/sh

#set global variable

USERNAME="admin"
PASSWD="123456"


test(){

    task_id="3e8a5db4-5350-11e4-a391-28d2443e3468"
    instance_uuid_01="4042ffda-5350-11e4-8f3d-28d2443e3468"
    instance_uuid_02="404df34a-5350-11e4-8f3d-28d2443e3468"

    echo "update tasks"
    mysql -u $USERNAME -p$PASSWD -e "
        use apicloud;
        update tasks set status=\"PROCESSING\", is_run=0, instances_num=2 where task_id=\"$task_id\" 
    " >/dev/null 2>&1
    sleep 0.05

    echo "update instances test01"
    mysql -u $USERNAME -p$PASSWD -e "
        use apicloud;
        update instances set is_alloc=0, name=\"test01\",status=\"stop\" where instance_uuid=\"$instance_uuid_01\"
    " >/dev/null 2>&1
    sleep 0.05

    echo "update instances test02"
    mysql -u $USERNAME -p$PASSWD -e "
        use apicloud;
        update instances set is_alloc=0,name=\"test02\",status=\"stop\" where instance_uuid=\"$instance_uuid_02\"
    " >/dev/null 2>&1
    sleep 0.05
}

main(){

    test
}


### CDS MAIN ###
main
exit 0
