# Set up constants
import json
import os
# Get the session id
import re
import shutil
import subprocess
from configparser import ConfigParser
from datetime import datetime
# Get the passwords
from getpass import getpass

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from pykeepass import PyKeePass, create_database

config_parser = ConfigParser()

config_parser.read('config.ini')

bw_server = config_parser.get('main', 'bw_server')
bw_username = config_parser.get('main', 'bw_username')
temp_db = config_parser.get('main', 'temp_db')
temp_attachments_folder = os.path.join(config_parser.get('main', 'temp_attachments_folder'), '')

delete_temp_database = config_parser.getboolean('after', 'delete_temp_database')
delete_attachments_folder = config_parser.getboolean('after', 'delete_attachments_folder')
upload_to_drive = config_parser.getboolean('after', 'upload_to_drive')


config = subprocess.check_output(['bw', 'config', 'server', bw_server])
session = re.search("Saved setting `config`.", str(config))[0]
print("Server configured")

bw_password = getpass(prompt="Bitwarden master password: ")

try:
    logout = subprocess.check_output(['bw', 'logout'])
    session = re.search("You have logged out.", str(logout))[0]
    print("You have logged out.")
except:
    print("You have logged out.")


os.makedirs(temp_attachments_folder, exist_ok=True) 



login = subprocess.check_output(['bw', 'login', bw_username, bw_password])

session = re.search('You are logged in', str(login))[0]
print("You have logged in.")




unlock = subprocess.check_output(['bw', 'unlock', bw_password])
session = re.search('BW_SESSION="(.*)"', str(unlock))[1]
print("Your vault is unlocked")

# Export the vault
out = subprocess.check_output(['bw', 'list', 'items','--session', session, bw_password])
bw_items = json.loads(out)

out = subprocess.check_output(['bw', 'list', 'folders','--session', session, bw_password])
bw_folders = json.loads(out)

out = subprocess.check_output(['bw', 'list', 'organizations','--session', session, bw_password])
bw_organizations = json.loads(out)

kp = create_database(temp_db, password=bw_password)

print("Folders:")
folders = {}
for i in bw_folders:
    print(i)
    folders[i['id']] = i['name']

print("Organizations:")
organizations = {}
for i in bw_organizations:
    print(i)
    organizations[i['id']] = i['name']

print("Items:")
for i in bw_items:
    folder_name = 'General'
    if i['folderId'] is not None:
        folder_name = folders[i['folderId']]
    
    group = kp.find_groups(name=folder_name, first=True)
    if group is None:
        group = kp.add_group(kp.root_group, folder_name)
    
    if 'login' in i:
        #print(i)

        urls = []
        if 'uris' in i['login']:
            for u in i['login']['uris']:
                urls.append(u['uri'])
        if i['login']['username'] is None:
            i['login']['username'] = ''
        if i['login']['password'] is None:
            i['login']['password'] = ''
        if 'fields' in i:
            for item in i['fields']:
                if i['notes'] is None:
                    i['notes'] = ''
                i['notes'] += f'\n{item["name"]}: {item["value"]}'

        entry_organization = organizations.get(i['organizationId'], None)
        entry_name = i['name'] if entry_organization is None else f"{i['name']}_{entry_organization}"
        entry = kp.add_entry(group, entry_name, i['login']['username'], i['login']['password'], notes=i['notes'], url=','.join(urls))
    
        attachments = [] 
        if 'attachments' in i:
            for att in i['attachments']:
                out = subprocess.check_output(['bw', 'get', 'attachment', att['id'], '--itemid', i['id'], '--output',temp_attachments_folder , '--session', session, bw_password])
                with open(f'{temp_attachments_folder}{att["fileName"]}', mode='rb') as file:
                    fileContent = file.read()
                    binary_id = kp.add_binary(fileContent)
                    entry.add_attachment(binary_id, att["fileName"])
    elif 'card' in i:
        notes = ''
        for key, value in i['card'].items():
            notes += f'{key}: {value}\n'

        for item in i['fields']:
            notes += f'{item["name"]}: {item["value"]}\n'

        entry = kp.add_entry(group, i['name'], '', '', notes=notes, url=','.join(urls))
    else:
        # print(f"skipping {i}")
        print("skipping")

kp.save()


# Lock the vault
try:
    print(subprocess.check_output(['bw', 'lock']))
except:
    print("WARNING: Could not lock the vault, session token is still active. Execute '$bw lock' to lock your vault.")



if upload_to_drive:
    gauth = GoogleAuth()
    
    # Creates local webserver and auto
    # handles authentication.
    gauth.LocalWebserverAuth()       
    drive = GoogleDrive(gauth)
    file_list = None
    try:
        file_list = drive.ListFile({'q': f"title = '{temp_db}' and trashed=false"}).GetList()
    except Exception as e:
        print("File not found, upload new one")
    if file_list is not None and len(file_list)>0:
        file1 = drive.CreateFile({'id': file_list[0]['id']})
    else:
        file1 = drive.CreateFile()
    file1.SetContentFile(temp_db)
    file1.Upload()

if delete_temp_database:
    try:
        os.remove(temp_db)
    except:
        print("Could not delete your uncrypted vault file. Please delete this file manually and safely.")


if delete_attachments_folder:
    for filename in os.listdir(temp_attachments_folder):
        file_path = os.path.join(temp_attachments_folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))
    shutil.rmtree(temp_attachments_folder)
    