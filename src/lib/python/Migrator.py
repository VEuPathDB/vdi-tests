from pathlib import Path
import sys
import requests
import json
from tinydb import TinyDB, Query
from datetime import datetime
import urllib
import os
import tarfile

"""
- Maintains a private mapping of UD IDs to VDI IDs, using python's tinydb as storage system.
- is idempotent.  
- for each UD to migrate
  - call a hard-coded migrate function for that type
  - identify user's original files, or approximation thereof, and place in tarball
  - extract meta-info and add into POST body
  - use admin user to import this UD into VDI
  - record the UD-VDI ID mapping in tinydb
  - write to STDOUT UDs that have weird files, so could not be migrated
"""

POLLING_FACTOR = 1.5  # multiplier for progressive polling of status endpoint
POLLING_INTERVAL_MAX = 60
POLLING_TIMEOUT = 10 * POLLING_INTERVAL_MAX 
ORIGIN = "standard" # indicate to the service that Galaxy is the point of origin for this user dataset.
ORIGINATING_USER_HEADER_KEY = "originating-user-id"

SSL_VERIFY = False

# types
GENE_LIST = "GeneList"
RNA_SEQ = "RNASeq"
BIOM = "BIOM"
ISA = "ISA"
BIGWIG = "BigwigFiles"

class Migrator():


    def migrate(self, tinyDbJsonFile, udServiceUrl, vdiServiceUrl, vdiAdminUserId, vdiAdminToken, countLimit, *targetProjects):

        UD_HEADERS = {"Accept": "application/json", "Auth-Key": "dontcare", "originating-user-id": "dontcare", "Cookie": "auth_tkt=ZTcxOWFlNGQyYzgzN2E1M2ExN2QzMDg4MTdmNDNlYTk2NGJmZWY1Y2FwaWRiIWFwaWRiITE2OTAzMDAyNTI6"}
        UD_HEADERS_FILE = {"Auth-Key": "dontcare", "originating-user-id": "dontcare", "Cookie": "auth_tkt=ZTcxOWFlNGQyYzgzN2E1M2ExN2QzMDg4MTdmNDNlYTk2NGJmZWY1Y2FwaWRiIWFwaWRiITE2OTAzMDAyNTI6"}
        VDI_HEADERS = {"Accept": "application/json", "Auth-Key": vdiAdminToken, "originating-user-id": vdiAdminUserId}     

        """
          In TinyDB we'll have two types of records.  Here are examples:

          {'type': 'owner', 'udId': 345993, 'vdiId': '9uer9g9sj3d', 'msg': 'invalid because blah blah (this is optional)'}
          {'type': 'recipient', 'udId': 345993, 'vdiId': '9uer9g9sj3d', 'recipientUdUserId': 98765555}
          
        """
        tinyDb = TinyDB(tinyDbJsonFile)

        a = [tinyDbJsonFile, udServiceUrl, vdiServiceUrl, vdiAdminUserId, vdiAdminToken]
        print("happy: " + ', '.join(a), file=sys.stderr)
        # first pass: for UD owner
        alreadyMigrated(tinyDb, 34)

        try:
            response = requests.get(udServiceUrl + "/users/current/all-user-datasets", headers=UD_HEADERS, verify=SSL_VERIFY)
            response.raise_for_status()
            udsJson = response.json()
            print("Proj: " + str(targetProjects), file=sys.stderr)
            count = 0
            for udJson in udsJson:
                if count > int(countLimit):
                    break
                count += 1
                udId = udJson["id"]
                udUserId = int(udJson["userId"])            
                if len(udJson["projects"]) == 0:
                    print("Ignoring UD " + str(udId) + " NO PROJECT", file=sys.stderr)
                    continue
                if len(targetProjects) != 0 and udJson["projects"][0] not in targetProjects:
                    print("Ignoring UD " + str(udId) + " from project: " + udJson["projects"][0], file=sys.stderr)
                    continue
                if udJson["ownerUserId"] != udUserId:
                    continue
                if alreadyMigrated(tinyDb, udId):
                    print("Skipping UD.  Already migrated: " + str(udId), file=sys.stderr)
                    continue
                print("Migrating UD: " + str(udId), file=sys.stderr)
                importFileNames = findFilesToMigrate(udId, udJson["type"]["name"], udJson["datafiles"])
                downloadDir = createTmpDir("download")
                downloadFiles(importFileNames, udUserId, udId, downloadDir, udServiceUrl, UD_HEADERS_FILE)
                tarballName = createTarball(downloadDir)
                postBody = createBodyForPost(udJson)
                vdiId = postMetadataAndData(vdiServiceUrl, postBody, tarballName, VDI_HEADERS)
                print_debug("VDI ID: " + vdiId)
                invalidMessage = pollForUploadComplete(vdiId, VDI_HEADERS)   # teriminates if system  error
                putShareOffers(vdId, udJson, vdiServiceUrl, VDI_HEADERS)
                writeOwnerUdToTinyDb(udId, vdiId, invalidMessage)
#        except Exception as e:
        except NameError as e:
            print("POST failed. Code: " + str(response.status_code) + " " + str(e), file=sys.stderr)            
#            print("Reason: " + response.text, file=sys.stderr)
            sys.exit(1)
        print("DONE WITH FIRST PASS", file=sys.stderr)
        sys.exit(1)
        # second pass for share recipients    
        try:
            response = requests.get(udServiceUrl + "/users/current/all-user-datasets", headers=UD_HEADERS, verify=SSL_VERIFY)
            response.raise_for_status()
            udsJson = response.json()
            for udJson in udsJson:
                udId = udJson["id"]
                udUserId = udJson["userId"]  # recipient ID
                if udJson["ownerUserId"] == udUserId:
                    continue
                if not alreadyMigrated(tinyDb, udId):
                    print("Skipping UD share.  Not migrated yet: " + str(udId), file=sys.stderr)
                    continue
                if alreadyShared(tinyDb, udId, udUserId):
                    print("Skipping UD share.  Already shared: " + str(udId), file=sys.stderr)
                    continue
                vdiId = putShareReceipt(vdiId, udUserId, vdiServiceUrl, VDI_HEADERS)
                writeRecipientUdToTinyDb(tinyDb, udId, vdiId, udUserId)
        except Exception as e:
            print("POST failed. Code: " + str(response.status_code) + " " + str(e), file=sys.stderr)            
    #        print("Reason: " + response.text, file=sys.stderr)
            sys.exit(1)
            
def writeOwnerUdToTinyDb(tinyDb, udId, vdiId, invalidMessage):
    t = datetime.now();
    tinyDb.insert({'type': 'owner', 'udId': udId, 'vdiId': vdiId, 'msg': invalidMessage, 'time': t.ctime()})

def writeRecipientUdToTinyDb(tinyDb, udId, vdiId, userId):
    t = datetime.now();
    tinyDb.insert({'type': 'recipient', 'udId': udId, 'vdiId': vdiId, 'recipientUserId': userId, 'time': t.ctime()})

def alreadyMigrated(tinyDb, udId):
    Record = Query()
    return len(tinyDb.search((Record.type == 'owner') & (Record.udId == udId))) > 0

def alreadyShared(tinyDB, udId, userId):
    Record = Query()
    return len(tinyDb.search((Record.type == 'recipient') & (Record.udId == udId) & (Record.recipientUserId == userId) )) > 0         

# return None if the files look weird
def findFilesToMigrate(udId, udType, dataFileInfos):
    dataFileNames = list(map(lambda dataFileInfo: dataFileInfo["name"], dataFileInfos))
    if type == GENE_LIST:
        if len(dataFileNames) != 1 or dataFileNames[0] != "genelist.txt":
            printBumUd(udId, udType, dataFileNames)
            return None
        return dataFileNames
    elif udType == RNA_SEQ:
        if len(dataFileNames) < 1 or not "manifest.txt" in dataFileNames:
            printBumUd(udId, udType, dataFileNames)
            return None
        return dataFileNames
    elif udType == BIOM:
        filtered = filter(lambda file: not (re.search('*.tsv', file) or re.search('*.json', file)), dataFileNames)
        if len(filtered) != 1:
            printBumUd(udId, udType, dataFileNames)
            return None
        return filtered
    elif udType ==  ISA:
        return dataFileNames
    elif udType == BIGWIG:
        return dataFileNames
    else:
        print("Unexpected UD type: " + udType, file=sys.stderr)
        exit(1)

def printBumUd(udId, udType, dataFileNames):
    print("BUM UD: " + udId + "\t" + udType + "\t" + ', '.join(dataFileNames), file=sys.stdout)

def createTmpDir(dirName):
    # clear out dir if exists
    if os.path.exists(dirName):
        for file in os.listdir(dirName):
            os.remove(dirName + "/" + file)            
    else:    
        os.makedirs(dirName)
    return dirName    
        
# https://dgaldi.plasmodb.org/plasmo.dgaldi/service/users/current/user-datasets/admin/{user-id}/{dataset-id}/user-datafiles/{filename}    
def downloadFiles(fileNames, userId, udId, downloadDir, udServiceUrl, udHeaders):
    print ("Download files: " + ', '.join(fileNames), file=sys.stderr)
    for fileName in fileNames:
        try:
            url = udServiceUrl + "/users/current/user-datasets/admin/" + str(userId) + "/" + str(udId) + "/user-datafiles/" + fileName
            print("URL: " + url + " " + str(udHeaders), file=sys.stderr)
            request = urllib.request.Request(url, None, udHeaders)
            response = urllib.request.urlopen(request)
            data = response.read()
            file_ = open(downloadDir + "/" + fileName, 'wb')
            file_.write(data)
            file_.close()
        except urllib.error.HTTPError as e:
           print("Died trying to download from UD service " + e.code + " " + e.reason, file=sys.stderr)
           exit(1)
            
#        except NameError as e:
#           print("Died trying to download from UD service " + e.message, file=sys.stderr)
#           exit(1)

def createTarball(dirpath):
    print("dirpath " + str(dirpath), file=sys.stderr)
    with tarfile.open("happy.tgz", "w:gz") as tarball:
        for filename in os.listdir(dirpath):
            print("Adding file to tarball: " + filename, file=sys.stderr)
            tarball.add(dirpath + "/" + filename)
    return "happy.tgz"

def createBodyForPost(udJson):
    return {
        "datasetName": udJson["meta"]["name"],
        "summary": udJson["meta"]["summary"],
        "description": udJson["meta"]["description"],
        "datasetType": {"name": udJson["type"]["name"], "version": udJson["type"]["version"]},
        "projects": udJson["projects"],
        "origin": ORIGIN
    }

def postMetadataAndData(vdiServiceUrl, json_blob, tarball_name, vdi_headers):
    print_debug("POSTING data.  Tarball name: " + tarball_name)
    try:
        form_fields = {"file": open(tarball_name, "rb"), "uploadMethod":"file"}
        response = requests.post(vdiServiceUrl + "/vdi-datasets", json = json_blob, files=form_fields, headers=vdi_headers, verify=SSL_VERIFY)
        response.raise_for_status()
        print_debug(response.json())
        return response.json()['jobId']
    except Exception as e:
        print("Http Error (" + str(response.status_code) + "): " + str(e), file=sys.stderr)            
        print("Reason: " + response.text, file=sys.stderr)
        sys.exit(1)

def pollForUploadComplete(vdiId, vdiHeaders):
    start_time = time.time()
    poll_interval_seconds = 1
    while (True):
        (done, message) = checkUploadInprogress(vdiId, vdiHeaders)  # message is None unless the import failed validation
        if done:
            return message
        time.sleep(poll_interval_seconds)  # sleep for specified seconds
        if poll_interval_seconds < POLLING_INTERVAL_MAX:
            poll_interval_seconds *= POLLING_FACTOR
        if (time.time() - start_time > POLLING_TIMEOUT):
            print("Timed out polling for upload completion status", file=sys.stderr)
            sys.exit(1)
        
# return True if still in progress; False if success.  Fail and terminate if system or validation error
def checkUploadInprogress(vdiServiceUrl, vdiId, vdiHeaders):
    print_debug("Polling for status")
    try:
        response = requests.get(vdiServiceUrl + "/vdi-datasets/" + vdiId, headers=vdiHeaders, verify=SSL_VERIFY)
        response.raise_for_status()
        json_blob = response.json()
        message = None
        if json_blob["status"]["import"] == "complete":
            return (True, None)
        if json_blob["status"]["import"] == "invalid":
            return (True, handle_job_invalid_status(json_blob))
        return (False, None)  # status is awaiting or in progress
    except Exception as e:
        print("Http Error (" + str(response.status_code) + "): " + str(e), file=sys.stderr)            
        if response != None:
            print("Reason: " + response.text, file=sys.stderr)
            sys.exit(1)

def handle_job_invalid_status(response_json):
    msgLines = []
    for msg in response_json["importMessages"]:
        msgLines.append(msg)
    return join(msgLines)

# /vdi-datasets/{vd-id}/shares/{recipient-user-id}/offer                                          
def putShareOffers(vdId, udJson, vdiServiceUrl, vdiHeaders):
    jsonBody = {"action": "grant"}                                  
    for recipientId in udJson["sharedWith"]:                             
        try:
            response = requests.put(vdiServiceUrl + "/vdi-datasets/" + vdiId + "/shares/" + recipientId + "/offer", json = jsonBody, headers=vdiHeaders, verify=SSL_VERIFY())
            response.raise_for_status()
        except Exception as e:
            print("Http Error (" + str(response.status_code) + "): " + str(e), file=sys.stderr)            
            if response != None:
                print("Reason: " + response.text, file=sys.stderr)
                sys.exit(1)

def putShareReciept(vdId, recipientId, vdiServiceUrl, vdiHeaders):
    jsonBody = {"action": "accept"}                                  
    try:
        response = requests.put(vdiServiceUrl + "/vdi-datasets/" + vdiId + "/shares/" + recipientId + "/receipt", json = jsonBody, headers=vdiHeaders, verify=SSL_VERIFY())
        response.raise_for_status()
    except Exception as e:
        print("Http Error (" + str(response.status_code) + "): " + str(e), file=sys.stderr)            
        if response != None:
            print("Reason: " + response.text, file=sys.stderr)
            sys.exit(1)


"""
https://plasmodb.org/plasmo/service/users/current/user-datasets/4069406

{
owner: "steve fischer",
projects: [
"ClinEpiDB"
],
created: 1666986925503,
isInstalled: false,
questions: [ ],
type: {
data: null,
display: "ISA Simple",
name: "ISA",
version: "0.0"
},
sharedWith: [ ],
dependencies: [ ],
isCompatible: null,
size: 38926,
meta: {
summary: "Lee Gambian with Eigengene Values",
name: "Lee Gambian - HPI",
description: ""
},
quota: 10,
ownerUserId: 119782143,
datafiles: [
{
size: 38926,
name: "metadata_with_eigenvalues.txt"
}
],
percentQuotaUsed: "0.0004",
id: 4069406,
age: 22292101811
}
"""

