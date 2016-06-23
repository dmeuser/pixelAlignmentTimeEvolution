#!/usr/bin/env python2

import ROOT
import subprocess
import re
import os
import glob
import pickle

def runFromFilename(filename):
    m = re.match(".*Run(\d+).root", filename)
    if m:
        return int(m.group(1))
    else:
        print "Could not find run number"
        return 0

def getRunStartTime(run):
    #returs a string similar to 2016-06-16 23:30:32
    return subprocess.check_output(["das_client.py --limit=0 --query=\"run={} | grep run.start_time\"".format(run)], shell=True)

def isValid(filename):
    f = ROOT.TFile(filename)
    valid = len(f.GetListOfKeys()) == 6
    f.Close()
    return valid

def updateDB():
    dbName = "runInfo.pkl"
    infos = {}
    if os.path.exists(dbName):
        with open(dbName) as f:
            infos = pickle.load(f)

    for f in glob.glob("root-files/Run*.root"):
        run = runFromFilename(f)
        if run not in infos:
            infos[run] = {}
            infos[run]["start_time"] = getRunStartTime(run)
            infos["isValid"] = isValid(f)

    with open(dbName, "wb") as f:
        pickle.dump(infos, f)

if __name__ == "__main__":
    updateDB()

