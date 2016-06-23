#!/usr/bin/env python2
# copied from https://twiki.cern.ch/twiki/bin/view/CMS/DQMToJSON

import os
import sys
import urllib2
import httplib
import json
import glob
import re

from ROOT import *
from array import *

serverurl = 'https://cmsweb.cern.ch/dqm/offline'
ident = "DQMToJson/1.0 python/%d.%d.%d" % sys.version_info[:3]
HTTPS = httplib.HTTPSConnection

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

def dqm_get_json(server, run, dataset, folder):
    X509CertAuth.ssl_key_file, X509CertAuth.ssl_cert_file = x509_params()
    datareq = urllib2.Request('%s/data/json/archive/%s/%s/%s?rootcontent=1'
                % (server, run, dataset, folder))
    datareq.add_header('User-agent', ident)
    # return json.load(urllib2.build_opener(X509CertOpen()).open(datareq))
    return eval(urllib2.build_opener(X509CertOpen()).open(datareq).read(),
            { "__builtins__": None }, {})

def saveAsFile(data, run, folder="./"):
    f = TFile(folder+"Run%s.root"%run,"recreate")
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
    f.Close()

def getRuns(dataset):
    import subprocess
    out = subprocess.check_output(["das_client --limit 0 --query='run dataset=/StreamExpress/Run2016B-PromptCalibProdSiPixelAli-Express-v2/ALCAPROMPT | sort run.run_number'"], shell=True)
    return [int(r) for r in out.split("\n") if r]

def getLastRun(folder="./"):
    maxRun = -1
    for f in glob.glob(folder+"Run*.root"):
        m = re.match(".*Run(\d+).root", f)
        if m:
            run = int(m.group(1))
            if run > maxRun:
                maxRun = run
    return maxRun

if __name__ == "__main__":
    dataset = "StreamExpress/Run2016B-PromptCalibProdSiPixelAli-Express-v2/ALCAPROMPT"
    folder = "/AlCaReco/SiPixelAli"

    outputFolder = "root-files"

    runs = getRuns(dataset)
    maxRun = getLastRun(outputFolder)
    runs = [r for r in runs if r>maxRun]

    for run in runs:
        print "Get run", run
        data = dqm_get_json(serverurl, str(run), dataset, folder)
        saveAsFile(data, run, ouputFolder)

