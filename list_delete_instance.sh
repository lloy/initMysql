#!/bin/sh

#set global variable

USERNAME="admin"
PASSWD="123456"

DELETE_FLAG="error"


list_delete_instance(){
echo "delete instances"
    mysql -u $USERNAME -p$PASSWD -e "
        use apicloud;
        select name from instances where status=\"$DELETE_FLAG\"
    "
    sleep 0.05
}

main(){

    list_delete_instance
}


### CDS MAIN ###
main
exit 0
