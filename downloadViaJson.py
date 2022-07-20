#!/usr/bin/env python2
# copied from https://twiki.cern.ch/twiki/bin/view/CMS/DQMToJSON

import os
import sys
import urllib2
import httplib
import json
import glob
import re
import subprocess

from ROOT import *
from array import *

serverurl = 'https://cmsweb.cern.ch/dqm/offline'
ident = "DQMToJson/1.0 python/%d.%d.%d" % sys.version_info[:3]
HTTPS = httplib.HTTPSConnection


def getGridCertificat():
    # Reads in PW from text file ~/.globus/pw, which you have to create yourself
    out = subprocess.check_output(["cat ~/.globus/pw | voms-proxy-init --voms cms --valid 192:00"], shell=True)
    proxyName = out.split("\n")[4][17:-1]
    return proxyName

proxyName = getGridCertificat()

class X509CertAuth(HTTPS):
    ssl_key_file = None
    ssl_cert_file = None

    def __init__(self, host, *args, **kwargs):
        HTTPS.__init__(self, host,
                     key_file = X509CertAuth.ssl_key_file,
                     cert_file = X509CertAuth.ssl_cert_file,
                     **kwargs)

class X509CertOpen(urllib2.AbstractHTTPHandler):
    def default_open(self, req):
        return self.do_open(X509CertAuth, req)

def x509_params():
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
        print >>sys.stderr, "no certificate private key file found"
        sys.exit(1)

    if not cert_file or not os.path.exists(cert_file):
        print >>sys.stderr, "no certificate public key file found"
        sys.exit(1)

    return key_file, cert_file

def dqm_get_json(server, run, dataset, path):
    X509CertAuth.ssl_key_file, X509CertAuth.ssl_cert_file = x509_params()
    datareq = urllib2.Request('%s/data/json/archive/%s%s/%s?rootcontent=1'
                % (server, run, dataset, path))
    datareq.add_header('User-agent', ident)
    # return json.load(urllib2.build_opener(X509CertOpen()).open(datareq))
    return eval(urllib2.build_opener(X509CertOpen()).open(datareq).read(),
            { "__builtins__": None }, {})

def saveAsFile(data, run, path="./"):
    f = TFile(os.path.join(path,"Run{}.root".format(run)),"recreate")
    for item in data['contents']:
        if 'obj' in item.keys() and 'rootobj' in item.keys():
            a = array('B')
            a.fromstring(item['rootobj'].decode('hex'))
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
    print len(out.split("\n"))
    if len(out.split("\n"))<=1:
		os.system("./acronExe.sh")
		sys.exit()
    return sorted([int(r) for r in out.split("\n") if r])

def getLastRun(path="./"):
    maxRun = -1
    for f in glob.glob(os.path.join(path,"Run*.root")):
        m = re.match(".*Run(\d+).root", f)
        if m:
            run = int(m.group(1))
            if run > maxRun:
                maxRun = run
    return maxRun

#  ~def getNewestDataset(pattern="/StreamExpress/Run2018*-PromptCalibProdSiPixelAli-Express-v*/ALCAPROMPT"):		#Proton runs
#  ~def getNewestDataset(pattern="/StreamHIExpress/HIRun2018*-PromptCalibProdSiPixelAli-Express-v*/ALCAPROMPT"):	#Ion runs
#  ~def getNewestDataset(pattern="/StreamExpress/Commissioning2021-PromptCalibProdSiPixelAli-Express-v1/ALCAPROMPT"):	
#  ~def getNewestDataset(pattern="/StreamExpress/Run2022A-PromptCalibProdSiPixelAli-Express-v1/ALCAPROMPT"):	#Comissioning
def getNewestDataset(pattern="/StreamExpress/Run2022C-PromptCalibProdSiPixelAli-Express-v1/ALCAPROMPT"):	#Proton runs 2022
    out = subprocess.check_output(["dasgoclient -query='dataset={}'".format(pattern)], shell=True)
    return out.split("\n")[-2]

def downloadViaJson():
    # downloads files for runs, which are not already present in root-files folders and returns their run numbers
    dataset = "" or getNewestDataset()
    print dataset
    path = "/AlCaReco/SiPixelAli"

    outputFolder = "root-files"
    if not os.path.exists(outputFolder):
        os.mkdir(outputFolder)

    runs = getRuns(dataset)
    maxRun = getLastRun(outputFolder)
    print "Last Run:",maxRun
    #~ maxRun = 327449
    runs = [r for r in runs if r>maxRun]

    for run in runs:
        print "Get run", run
        data = dqm_get_json(serverurl, str(run), dataset, path)
        
        if len(data['contents'])>0:     # store only, if result already present in DQM file
            saveAsFile(data, run, outputFolder)
    return runs

if __name__ == "__main__":
    downloadViaJson()
