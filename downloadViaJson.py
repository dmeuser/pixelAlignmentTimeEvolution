#!/usr/bin/env python3
# copied from https://twiki.cern.ch/twiki/bin/view/CMS/DQMToJSON

import os
import sys
import subprocess
import http.client
import urllib.request
import json
import glob
import re

from ROOT import *
from array import *

serverurl = 'https://cmsweb.cern.ch/dqm/offline'
ident = "DQMToJson/1.0 python/%d.%d.%d" % sys.version_info[:3]
HTTPS = http.client.HTTPSConnection


def getGridCertificat():
    out = subprocess.check_output(["cat ~/.globus/pw | voms-proxy-init --voms cms --valid 192:00"], shell=True)
    proxyName = out.split(b"\n")[4][17:-1].decode("utf-8")
    return proxyName


class X509CertAuth(http.client.HTTPSConnection):
    ssl_key_file = None
    ssl_cert_file = None

    def __init__(self, host, *args, **kwargs):
        super().__init__(host,
                         key_file=X509CertAuth.ssl_key_file,
                         cert_file=X509CertAuth.ssl_cert_file,
                         **kwargs)


class X509CertOpen(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(X509CertAuth, req)


def x509_params(proxyName):
    key_file = cert_file = None

    x509_path = os.getenv("X509_USER_PROXY", None)
    if not x509_path:
        x509_path = proxyName
        os.environ["X509_USER_PROXY"] = x509_path
    if x509_path and os.path.exists(x509_path):
        key_file = cert_file = x509_path

    if not key_file:
        x509_path = os.getenv("X509_USER_KEY", None)
        if x509_path and os.path.exists(x509_path):
            key_file = x509_path

    if not cert_file:
        x509_path = os.getenv("X509_USER_CERT", None)
        if x509_path and os.path.exists(x509_path):
            cert_file = x509_path

    if not key_file:
        x509_path = os.getenv("HOME") + "/.globus/userkey.pem"
        if os.path.exists(x509_path):
            key_file = x509_path

    if not cert_file:
        x509_path = os.getenv("HOME") + "/.globus/usercert.pem"
        if os.path.exists(x509_path):
            cert_file = x509_path

    if not key_file or not os.path.exists(key_file):
        print("no certificate private key file found", file=sys.stderr)
        sys.exit(1)

    if not cert_file or not os.path.exists(cert_file):
        print("no certificate public key file found", file=sys.stderr)
        sys.exit(1)

    return key_file, cert_file


def dqm_get_json(server, run, dataset, path):
    proxyName = getGridCertificat()
    X509CertAuth.ssl_key_file, X509CertAuth.ssl_cert_file = x509_params(proxyName)
    datareq = urllib.request.Request('%s/data/json/archive/%s%s/%s?rootcontent=1'
                                     % (server, run, dataset, path))
    datareq.add_header('User-agent', ident)
    with urllib.request.build_opener(X509CertOpen()).open(datareq) as response:
        return eval(response.read().decode('utf-8'),
                    {"__builtins__": None}, {})


def saveAsFile(data, run, path="./"):
    f = TFile(os.path.join(path, "Run{}.root".format(run)), "recreate")
    for item in data['contents']:
        if 'obj' in item.keys() and 'rootobj' in item.keys():
            a = array('B')
            a.frombytes(bytes.fromhex(item['rootobj']))
            t = TBufferFile(TBufferFile.kRead, len(a), a, kFALSE)
            rootType = item['properties']['type']
            if rootType == 'TPROF':
                rootType = 'TProfile'
            h = t.ReadObject(eval(rootType+'.Class()'))
            h.Write(item['obj'])
        if 'obj' in item.keys() and item['obj'] == "PedeExitCode":
            temp = TObjString(item['value'])
            temp.Write(item['obj'])
    f.Close()


def getRuns(dataset):
    out = subprocess.check_output(["dasgoclient --limit 0 --query='run dataset={}'".format(dataset)], shell=True)
    print(len(out.split(b"\n")))
    if len(out.split(b"\n")) <= 1:
        os.system("./acronExe.sh")
        sys.exit()
    return sorted([int(r) for r in out.split(b"\n") if r])


def getLastRun(path="./"):
    maxRun = -1
    for f in glob.glob(os.path.join(path, "Run*.root")):
        m = re.match(".*Run(\d+).root", f)
        if m:
            run = int(m.group(1))
            if run > maxRun:
                maxRun = run
    return maxRun


def listAllObjectPaths(file_, output, path=""):
    file_.cd(path)
    for key in gDirectory.GetListOfKeys():
        if key.IsFolder():
            listAllObjectPaths(file_, output, path+"/"+key.GetName())
        else:
            output.append(path+"/"+key.GetName())


def downloadViaEOS(run, dataset, outputPath):
    path = "/eos/cms/store/group/comm_dqm/DQMGUI_data/Run2024/{}/000{}xx/".format(dataset.split("/")[1], run[0:4])
    filename = "DQM_V0001_R000{}__{}__{}__ALCAPROMPT.root".format(run, dataset.split("/")[1], dataset.split("/")[2])
    if os.path.exists(path+filename):
        inputFile = TFile(path+filename, "READ")
        histNames = []
        rootObjects = {}
        listAllObjectPaths(inputFile, histNames)
        for histName in histNames:
            if histName.find("SiPixelAli") >= 0:
                if histName.find("<") == -1:
                    rootObjects[histName] = inputFile.Get(histName)
                elif histName.find("PedeExitCode") >= 0:
                    rootObjects[histName.split("<")[0]+"PedeExitCode"] = TObjString(histName.split("=")[-1].split("<")[0])
        outputFile = TFile(os.path.join(outputPath, "Run{}.root".format(run)), "recreate")
        outputFile.cd()
        for obj in rootObjects.keys():
            rootObjects[obj].Write(obj.split("/")[-1])

        inputFile.Close()
        outputFile.Close()
    else:
        print("DQM file not available under"+path+filename)


def getNewestDataset(pattern="/StreamExpress/Run2024*-PromptCalibProdSiPixelAli-Express-v*/ALCAPROMPT"):  # Proton runs 2024
    out = subprocess.check_output(["dasgoclient -query='dataset={}'".format(pattern)], shell=True)
    return out.split(b"\n")[-2].decode("utf-8")


def downloadViaJson():
    dataset = "" or getNewestDataset()
    print(dataset)
    path = "/AlCaReco/SiPixelAli"

    outputFolder = "root-files"
    if not os.path.exists(outputFolder):
        os.mkdir(outputFolder)

    runs = getRuns(dataset)
    maxRun = getLastRun(outputFolder)
    print("Last Run:", maxRun)
    runs = [r for r in runs if r > maxRun]

    for run in runs:
        print("Get run", run)
        data = dqm_get_json(serverurl, str(run), dataset, path)

        print(len(data['contents']))
        if len(data['contents']) > 1:  # store only, if result already present in DQM file
            saveAsFile(data, run, outputFolder)
        else:
            print("Download from eos")
            downloadViaEOS(str(run), dataset, outputFolder)
    return runs


if __name__ == "__main__":
    downloadViaJson()
