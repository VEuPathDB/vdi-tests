import sys
import requests
import json
from tinydb import TinyDB, Query
from datetime import datetime
import time
import urllib
import os
import tarfile
import datetime

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
ORIGINATING_USER_HEADER_KEY = "originating-user-id"

SSL_VERIFY = False

# types
GENE_LIST = "GeneList"
RNA_SEQ = "RnaSeq"
BIOM = "BIOM"
ISA = "ISA"
BIGWIG = "BigwigFiles"

authTkt = "auth_tkt=" + os.getenv("UD_AUTH_TKT")


class Migrator:

    def migrate(self, tinyDbJsonFile, legacyUdJsonFile, workingDir, udServiceUrl, vdiServiceUrl, vdiAdminAuthKey,
                countLimit, *targetProjects):

        UD_HEADERS_FILE = {"Auth-Key": "dontcare", "originating-user-id": "dontcare", "Cookie": authTkt}
        VDI_HEADERS = {"Accept": "application/json", "Admin-Token": vdiAdminAuthKey, "User-ID": "?", "Cookie": authTkt}

        """
          In TinyDB we'll have two types of records.  Here are examples:

          {'type': 'owner', 'udId': 345993, 'vdiId': '9uer9g9sj3d', 'msg': 'invalid because blah blah (this is optional)'}
          {'type': 'recipient', 'udId': 345993, 'vdiId': '9uer9g9sj3d', 'recipientUdUserId': 98765555}

        """

        tinyDb = TinyDB(tinyDbJsonFile)

        a = [tinyDbJsonFile, workingDir, udServiceUrl, vdiServiceUrl, vdiAdminAuthKey, countLimit, str(targetProjects)]
        print("cmdline args: " + ', '.join(a), file=sys.stderr)

        vdiDatasetsUrl = vdiServiceUrl + "/vdi-datasets"

        # first pass: for UD owner.  Get json with all UDs.  Then iterate.
        udsJson = {}
        with open(legacyUdJsonFile) as file:
            udsJson = json.loads(file.read())

        sortedUdsJson = sorted(udsJson, key=lambda d: d["id"])  # import in order of UD creation
        count = 0
        alreadyCount = 0
        ignoreCount = 0

        # Index of UDs that failed to import.  This is used to skip share
        # attempts on datasets that are guaranteed to get an error code back
        # from VDI.
        invalid = {}

        for udJson in sortedUdsJson:
            udType = udJson["type"]["name"]
            udId = udJson["id"]
            udUserId = int(udJson["userId"])
            ownerID = udJson["ownerUserId"]

            if len(udJson["projects"]) == 0:
                print("Ignoring UD " + str(udId) + " NO PROJECT", file=sys.stderr)
                ignoreCount += 1
                continue

            if len(targetProjects) != 0 and udJson["projects"][0] not in targetProjects:
                print("Ignoring UD " + str(udId) + " from project: " + udJson["projects"][0], file=sys.stderr)
                ignoreCount += 1
                continue

            if udJson["ownerUserId"] != udUserId:
                continue

            if alreadyMigrated(tinyDb, udId):
                print("Skipping UD.  Already migrated: " + str(udId), file=sys.stderr)
                alreadyCount += 1
                continue

            if count >= int(countLimit):
                break

            count += 1

            print(
                "Migrating UD: " + str(ownerID) + "/" + str(udId) + " " + udJson["projects"][0] + " " + udJson["type"][
                    "name"], file=sys.stderr)
            importFileNames = findFilesToMigrate(udId, udJson["type"]["name"], udJson["datafiles"])
            downloadDir = createDownloadDir(workingDir + "/download")
            downloadFiles(importFileNames, udUserId, udId, downloadDir, udServiceUrl, UD_HEADERS_FILE)
            tarballName = "happy.tgz"
            createTarball(downloadDir, tarballName)
            postBody = createBodyForPost(udJson)
            vdiHeaders = VDI_HEADERS
            vdiHeaders["User-ID"] = str(udUserId)
            vdiId = postMetadataAndData(vdiDatasetsUrl, postBody, os.path.join(downloadDir, tarballName), vdiHeaders)
            invalidMessage = pollForUploadComplete(vdiDatasetsUrl, vdiId, vdiHeaders)  # teriminates if system  error

            # If we got an invalid message then we should not attempt to share
            # the dataset.
            if invalidMessage is not None:
                invalid[vdiId] = True
            else:
                putShareOffers(vdiId, udJson, vdiDatasetsUrl, vdiHeaders)

            write_owner_ud_to_tiny_db(tinyDb, ownerID, udId, vdiId, udType, invalidMessage)
            print("Completed upload " + str(count), file=sys.stderr)

        print("DONE WITH FIRST PASS. Uploaded: " + str(count) + " Already migrated: " + str(
            alreadyCount) + " Ignored: " + str(ignoreCount), file=sys.stderr)

        # second pass for share recipients
        shareCount = 0
        for udJson in udsJson:
            udId = udJson["id"]
            udUserId = udJson["userId"]  # recipient ID
            udOwnerId = udJson["ownerUserId"]
            dataset_type = udJson["type"]["name"]

            # If the ud failed import then attempting to share the dataset will
            # result in an error code from the VDI service.
            if udId in invalid:
                print(f"Skipping shares for dataset {udOwnerId}/{udId} as it failed import.")
                continue

            if udOwnerId == udUserId:
                continue
            if not alreadyMigrated(tinyDb, udId):
                print("Skipping UD share.  Not migrated yet: " + str(udId), file=sys.stderr)
                continue
            if already_shared(tinyDb, udId, udUserId):
                print("Skipping UD share.  Already shared: " + str(udId), file=sys.stderr)
                continue
            vdiHeaders = VDI_HEADERS
            vdiHeaders["User-ID"] = str(udOwnerId)
            print("Sharing UD ID " + str(udId) + " with user " + udUserId + " owner " + str(udOwnerId), file=sys.stderr)
            putShareReceipt(vdiId, udUserId, vdiDatasetsUrl, vdiHeaders)
            write_recipient_ud_to_tiny_db(tinyDb, udOwnerId, udId, vdiId, dataset_type, udUserId)
            shareCount += 1
            if shareCount >= int(countLimit):
                break
        print("DONE WITH SECOND PASS", file=sys.stderr)
        print("SUMMARY  Shared: " + str(shareCount) + "  Uploaded: " + str(count) + " Already migrated: " + str(
            alreadyCount) + " Ignored: " + str(ignoreCount), file=sys.stderr)


def write_owner_ud_to_tiny_db(tiny_db: TinyDB, owner_id, ud_id, vdi_id, dataset_type, invalid_message):
    t = datetime.datetime.now()
    tiny_db.insert({
        'type': 'owner',
        'udId': ud_id,
        'vdiId': vdi_id,
        'msg': invalid_message,
        'time': t.ctime(),
        'ownerId': owner_id,
        'datasetType': dataset_type,
    })


def write_recipient_ud_to_tiny_db(tiny_db: TinyDB, owner_id, ud_id, vdi_id, dataset_type, user_id):
    t = datetime.datetime.now()
    tiny_db.insert({
        'type': 'recipient',
        'udId': ud_id,
        'vdiId': vdi_id,
        'recipientUserId': user_id,
        'time': t.ctime(),
        'ownerId': owner_id,
        'datasetType': dataset_type,
    })


def alreadyMigrated(tinyDb, udId):
    Record = Query()
    # print("Tiny: " + str(tinyDb.search((Record.type == 'owner') & (Record.udId == udId))))
    return len(tinyDb.search((Record.type == 'owner') & (Record.udId == udId))) > 0


def already_shared(tiny_db: TinyDB, ud_id, user_id):
    record = Query()
    return len(
        tiny_db.search((record.type == 'recipient') & (record.udId == ud_id) & (record.recipientUserId == user_id))) > 0


# return None if the files look weird
def findFilesToMigrate(udId, udType, dataFileInfos):
    dataFileNames = list(map(lambda dataFileInfo: dataFileInfo["name"], dataFileInfos))
    if udType == GENE_LIST:
        if len(dataFileNames) != 1 or dataFileNames[0] != "genelist.txt":
            printBumUd(udId, udType, dataFileNames)
            return None
        return dataFileNames
    elif udType == RNA_SEQ:
        if len(dataFileNames) < 1 or "manifest.txt" not in dataFileNames:
            printBumUd(udId, udType, dataFileNames)
            return None
        return dataFileNames
    elif udType == BIOM:
        return dataFileNames
    elif udType == ISA:
        return dataFileNames
    elif udType == BIGWIG:
        return dataFileNames
    else:
        print("Unexpected UD type: " + udType, file=sys.stderr)
        exit(1)


def printBumUd(udId, udType, dataFileNames):
    print("BUM UD: " + udId + "\t" + udType + "\t" + ', '.join(dataFileNames), file=sys.stdout)


def createDownloadDir(dirName):
    # clear out dir if exists
    if os.path.exists(dirName):
        for file in os.listdir(dirName):
            os.remove(dirName + "/" + file)
    else:
        os.makedirs(dirName)
    return dirName


# https://dgaldi.plasmodb.org/plasmo.dgaldi/service/users/current/user-datasets/admin/{user-id}/{dataset-id}/user-datafiles/{filename}
def downloadFiles(fileNames, userId, udId, downloadDir, udServiceUrl, udHeaders):
    print("Download files: " + ', '.join(fileNames), file=sys.stderr)
    for fileName in fileNames:
        try:
            url = udServiceUrl + "/users/current/user-datasets/admin/" + str(userId) + "/" + str(
                udId) + "/user-datafiles/" + urllib.parse.quote(fileName)
            request = urllib.request.Request(url, None, udHeaders)
            response = urllib.request.urlopen(request, timeout=360)
            data = response.read()
            file_ = open(downloadDir + "/" + fileName, 'wb')
            file_.write(data)
            file_.close()
            response.close()
        except urllib.error.HTTPError as e:
            print("Died trying to download from UD service: " + str(e.code) + " " + e.reason, file=sys.stderr)
            exit(1)
    print("Done downloading files", file=sys.stderr)


def createTarball(dirpath, tarFileName):
    oldPath = os.getcwd()
    print(f"changing cwd to ./{dirpath}")
    os.chdir(dirpath)
    try:
        os.remove(tarFileName)
    except FileNotFoundError:
        pass
    with tarfile.open(tarFileName, "x:gz") as tarball:
        for filename in os.listdir(os.getcwd()):
            if filename != tarFileName:
                print("Adding file to tarball: " + filename, file=sys.stderr)
                tarball.add(filename)
    print(f"changing cwd to {oldPath}")
    os.chdir(oldPath)


def createBodyForPost(udJson):
    origin = "direct-upload"

    if udJson["type"]["name"] == "BigwigFiles" or udJson["type"]["name"] == "RnaSeq":
        origin = "galaxy"

    dependencies = udJson["dependencies"].copy()

    createdSeconds = udJson["created"] / 1000
    dt = datetime.datetime.fromtimestamp(createdSeconds).astimezone()
    createdStr = dt.isoformat()

    for dependency in dependencies:
        del dependency["compatibilityInfo"]  # we don't use this in VDI

    patchDatasetType(udJson)

    return {
        "name": udJson["meta"]["name"],
        "createdOn": createdStr,
        "summary": udJson["meta"]["summary"],
        "dependencies": dependencies,
        "description": udJson["meta"]["description"],
        "datasetType": {"name": udJson["type"]["name"], "version": udJson["type"]["version"]},
        "projects": udJson["projects"],
        "visibility": "private",
        "origin": origin
    }


def patchDatasetType(udJson) -> None:
    if udJson["type"]["name"].lower() == "isa":
        udJson["type"]["name"] = "isasimple"
        udJson["type"]["version"] = "1.0"
    if udJson["type"]["name"].lower() == "biom":
        udJson["type"]["version"] = "1.0"


def postMetadataAndData(vdiDatasetsUrl, json_blob, tarball_name, vdi_headers):
    try:
        url = vdiDatasetsUrl + "/admin/proxy-upload"
        print("Posting to VDI: " + url, file=sys.stderr)
        form_fields = {"file": open(tarball_name, "rb"), "meta": json.dumps(json_blob)}
        response = requests.post(url, files=form_fields, headers=vdi_headers, verify=SSL_VERIFY)
        response.raise_for_status()
        datasetId = response.json()['datasetId']
        response.close()
        return datasetId
    except requests.exceptions.RequestException as e:
        handleRequestException(e, url, "Posting metadata and data to VDI")


def pollForUploadComplete(vdiDatasetsUrl, vdiId, vdiHeaders):
    start_time = time.time()
    poll_interval_seconds = 1
    print("Polling for status", file=sys.stderr)
    while (True):
        (done, message) = checkUploadInprogress(vdiDatasetsUrl, vdiId,
                                                vdiHeaders)  # message is None unless the import failed validation
        if done:
            print("Polled for " + str(int(time.time() - start_time)) + " seconds", file=sys.stderr)
            return message
        time.sleep(poll_interval_seconds)  # sleep for specified seconds
        if poll_interval_seconds < POLLING_INTERVAL_MAX:
            poll_interval_seconds *= POLLING_FACTOR


# return True if still in progress; False if success.  Fail and terminate if system or validation error
def checkUploadInprogress(vdiDatasetsUrl, vdiId, vdiHeaders):
    try:
        url = vdiDatasetsUrl + "/" + vdiId
        response = requests.get(url, headers=vdiHeaders, verify=SSL_VERIFY)
        response.raise_for_status()
        json_blob = response.json()
        message = None
        if json_blob["status"]["import"] == "complete":
            print("Upload complete: " + vdiId, file=sys.stderr)
            return (True, None)
        if json_blob["status"]["import"] == "invalid":
            print("Upload invalid: " + vdiId, file=sys.stderr)
            return (True, handle_job_invalid_status(json_blob))
        if json_blob["status"]["import"] == "failed":
            print("Upload failed: " + vdiId, file=sys.stderr)
            return (True, handle_job_invalid_status(json_blob))
        return (False, None)  # status is awaiting or in progress
    except requests.exceptions.RequestException as e:
        handleRequestException(e, url, "Polling VDI for upload status")


def handle_job_invalid_status(response_json):
    msgLines = []
    for msg in response_json["importMessages"]:
        msgLines.append(msg)
    return ', '.join(msgLines)


# /vdi-datasets/{vd-id}/shares/{recipient-user-id}/offer
def putShareOffers(vdiId, udJson, vdiDatasetsUrl, vdiHeaders):
    jsonBody = {"action": "grant"}
    for share in udJson["sharedWith"]:
        recipientId = share["user"]
        try:
            url = vdiDatasetsUrl + "/" + vdiId + "/shares/" + str(recipientId) + "/offer"
            response = requests.put(url, json=jsonBody, headers=vdiHeaders, verify=SSL_VERIFY)
            response.raise_for_status()
            response.close()
            print("Granted share of " + vdiId + " with " + str(recipientId), file=sys.stderr)
        except requests.exceptions.RequestException as e:
            handleRequestException(e, url, "Put share offer to VDI")


def putShareReceipt(vdiId, recipientId, vdiDatasetsUrl, vdiHeaders):
    jsonBody = {"action": "accept"}
    try:
        url = vdiDatasetsUrl + "/" + vdiId + "/shares/" + str(recipientId) + "/receipt"
        print("PUT share: " + url, file=sys.stderr)
        response = requests.put(url, json=jsonBody, headers=vdiHeaders, verify=SSL_VERIFY)
        response.raise_for_status()
        response.close()
        print("Accepted share of " + vdiId + " by " + str(recipientId), file=sys.stderr)
    except requests.exceptions.RequestException as e:
        handleRequestException(e, url, "Put share offer to VDI")


def handleRequestException(e, url, msg):
    print("Error " + msg + ". Exception type: " + str(type(e)), file=sys.stderr)
    print("HTTP Code: " + str(e.response.status_code) + " " + e.response.text, file=sys.stderr)
    print("URL: " + url, file=sys.stderr)
    exit(1)
