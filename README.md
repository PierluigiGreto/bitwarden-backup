# bitwarden to keepass db with google drive backup
This script will download all the item, folder and attachments from you bitwarden and it will create a keepass db which can be upload to Google Drive for backup.

## Prerequisite
You must install:
* [bw cli](https://github.com/bitwarden/cli)
* [Pydrive authentication](https://pythonhosted.org/PyDrive/)

Install python3 libraries:
```
pip3 install -r requirements.txt
```

## Configuration
Edit the config.ini

###  main section
``bw_server`` your bitwarden server url


``bw_username`` your bitwarden username


``temp_db`` name of the keepass temp db


``temp_attachments_folder`` folder where to download the attachments

### after section

``delete_temp_database`` True if you want to delete the keepass temp db at the end


``delete_attachments_folder`` True if you want to delete the temp attchement folder at the end


``upload_to_drive`` True if you want to upload the keepass db into Google Drive


## Run
To execute the script run:
```
python3 bitwarden_backup.py
```