#!/bin/env bash


############################################
# NOTES
######################
# 1) for debugging ues "NOMAIL=1 ./pp.sh" to prevent mail sending!
# 2) additional parameters can be given, e.g. "./pp.sh -f UsbRelaisInterfaceWd"
######################


############################################
# ATTENTION!
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
# ensure mail password doesn't contain a # sign
# ensure the secrets file contains
#       ZIP_PASSWORD
#       SENDER_EMAIL
#       RECIPIENT_EMAIL
#       PROJECT_NAME
######################


############################################
# SETTINGS
######################
SECRETS_FILE=json/secure.sh
MAX_BACKUPS=5

# start parameters
EXECUTE="__main__.py -w -l=5 -p=3 --json-dump"
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
    EXECUTE="$EXECUTE $@"
fi

echo "#####################################"
echo "# ${PROJECT_NAME}"
echo "# execute python3 $EXECUTE"
echo "#####################################"

# start powerplant
python3 $EXECUTE

# move all backup files to next index (MAX_BACKUP-1 overwrites MAX_BACKUP, there will be not more backup files than MAX_BACKUP)
let newIndex=$MAX_BACKUPS-1
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
