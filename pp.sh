#!/bin/env bash


############################################
# NOTES
######################
# pp.sh parameters:
#       NOMAIL ........ to prevent sending an email, e.g. for debugging
#       MAX_BACKUPS ... default is 5 but can be changed if necessary
#
#       additional script parameters can be given after ./pp.sh
#
# examples:
#       NOMAIL=1 ./pp.sh
#       NOMAIL=1 ./pp.sh -f UsbRelaisInterfaceWd
#       MAX_BACKUPS=10 NOMAIL=1 ./pp.sh -f UsbRelaisInterfaceWd
#       MAX_BACKUPS=10 NOMAIL=1 ./pp.sh -f UsbRelaisInterfaceWd -s 20
#       TURN=0; for TURN in {1..100}; do MAX_BACKUPS=100 NOMAIL=1 ./pp.sh -s 20; echo "turns so far $TURN"; sleep 100; done
#       NOMAIL=1 nohup ./pp.sh &
#           #tail -f nohup.out
#           #kill -s SIGINT %1
#
# pp.sh variables (see SETTINGS section):
#       SECRETS_FILE    file where secret values can be found, e.g. json/secure.sh
#       MAX_BACKUPS     amount of backup copies of the error log until they will be deleted (a smaller value will not make remove backups with higher numbers!)
#       EXECUTE         the powerplant script execution command with necessary parameters
#
# content of the SECRETS_FILE:
#       ZIP_PASSWORD        ensure mail password doesn't contain a # sign
#       SENDER_EMAIL        sender's mail address
#       RECIPIENT_EMAIL     mail address of the recipient
#       PROJECT_NAME        project name that will be used in the email subject and body
######################


############################################
# ATTENTION
######################
# mutt and some other necessary packages are needed
#       sudo apt-get install ssmtp mailutils mutt
# ensure /etc/ssmtp/ssmtp.conf is configured correctly
#   this works for GMX but POP/IMAP access has to be enabled via GMX web interface
#       root=postmaster
#       mailhub=mail.gmx.net:587
#       hostname=homeassistant
#       FromLineOverride=YES
#       AuthUser=<YOUR_EMAIL>@gmx.de
#       AuthPass=<YOUR_PASSWORD>
#       UseSTARTTLS=YES
#       UseTLS=YES
#       AuthMethod=DIGEST-MD5
######################


############################################
# SETTINGS
######################
SECRETS_FILE=json/secure.sh

if [ -z $MAX_BACKUPS ]; then
    MAX_BACKUPS=5
fi

# start parameters
EXECUTE='__main__.py -w -l=5 -p=3 --json-dump'
#EXECUTE="__main__.py -w -l=5 -p=3 --json-dump --json-dump-filter user|password|\+49"
    # from command line you have to execute:
    #   python3 __main__.py -w -l=5 -p=3 --json-dump --json-dump-filter "user|password|\+49"
    # but here the quotation marks are not allowed, otherwise they will become part of the regex!
#EXECUTE='__main__.py -w -l=5 -p=3 --json-dump --json-dump-filter-none'
#EXECUTE="__main__.py -w -l=5 -p=3"
#EXECUTE="__main__.py -w -l=5 -p=5 -f BmsInterfaceAccu #--json-dump"
#EXECUTE="__main__.py -w -l=5 -p=5 -f BmsInterfaceAccu --json-dump"
############################################


clear

# try to get secrets form secrets file
if [ -e "$SECRETS_FILE" ]; then
    source "$SECRETS_FILE"
fi

# further command line arguments given -> add them to EXECUTE variable
if [ "$#" -gt 0 ]; then
    EXECUTE=$EXECUTE $@
fi

echo "#####################################"
echo "# ${PROJECT_NAME}"
echo "# execute python3 $EXECUTE"
echo "#####################################"

# start powerplant
python3 $EXECUTE

# move all backup files to next index (MAX_BACKUP-1 overwrites MAX_BACKUP, there will be not more backup files than MAX_BACKUP)
let newIndex=${MAX_BACKUPS}-1
while [ $newIndex -gt 1 ]; do
    let oldIndex=$newIndex-1
    if [ -e logger_${oldIndex}.7z ]; then
        mv logger_${oldIndex}.7z logger_${newIndex}.7z
    fi
    let newIndex=$newIndex-1
done
if [ -e logger.7z ]; then
    mv logger.7z logger_1.7z
fi

# compress new log file with $ZIP_PASSWORD
7z a logger.7z logger.txt -p"$ZIP_PASSWORD"

# now send archive to given email address
if [ -z "$NOMAIL" ]; then
    echo sending mail
    echo -e "${PROJECT_NAME} Error Log to be found in the attachment" | mutt -e 'my_hdr From:"'"${PROJECT_NAME}"'" <'"${SENDER_EMAIL}"'>' -s "${PROJECT_NAME} Error Log" -a logger.7z -- "${RECIPIENT_EMAIL}"
else
    echo sending mail DISABLED
fi

