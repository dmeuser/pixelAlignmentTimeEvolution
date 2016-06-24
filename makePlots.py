#!/usr/bin/env python2

import collections
import glob
import re
import os
import copy
import numpy
import datetime
import string
import shutil
import subprocess
import math

import ROOT

def style():
    ROOT.gStyle.SetOptStat(0)
    ROOT.gROOT.SetBatch()
    st = ROOT.gStyle
    st.SetPadTopMargin(0.08)
    st.SetPadBottomMargin(0.1)
    st.SetPadLeftMargin(0.09)
    st.SetPadRightMargin(0.00)
    textSize = 0.05
    st.SetLabelSize(textSize, "xyz")
    st.SetTitleSize(textSize, "xyz")
    st.SetTextFont(st.GetLabelFont())
    st.SetTextSize(.8*st.GetLabelSize())
    st.SetTitleOffset(1.1, "x")
    st.SetTitleOffset(.9, "y")
    st.SetPadTickX(1)
    st.SetPadTickY(1)
    ROOT.TGaxis.SetMaxDigits(6)

class Parameter:
    name = ""
    label = ""
    cut = 0
    minDraw = 0
    maxDraw = 0
    def __init__(self, n, l, c, minDraw, maxDraw):
        self.name = n
        self.label = l
        self.cut = c
        self.minDraw = minDraw
        self.maxDraw = maxDraw
parameters = [
    Parameter("Xpos", "#Deltax (#mum)", 5, -30, 10 ), \
    Parameter("Ypos", "#Deltay (#mum)", 10, -30, 11 ), \
    Parameter("Zpos", "#Deltaz (#mum)", 15, -100, 16 ), \
    Parameter("Xrot", "#Delta#theta_{x} (#murad)", 30, -50, 50 ), \
    Parameter("Yrot", "#Delta#theta_{y} (#murad)", 30, -50, 50 ), \
    Parameter("Zrot", "#Delta#theta_{z} (#murad)", 30, -70, 70 )
    ]
parDict = collections.OrderedDict( (p.name, p) for p in parameters )
objects = [
    ("FPIX(x+,z-)", ROOT.kBlack),
    ("FPIX(x-,z-)", ROOT.kRed),
    ("BPIX(x+)", ROOT.kBlue),
    ("BPIX(x-)", ROOT.kCyan),
    ("FPIX(x+,z+)", ROOT.kGreen+2),
    ("FPIX(x-,z+)", ROOT.kMagenta),
]


def save(name):
    ROOT.gPad.SaveAs("plots/{}.pdf".format(name))

def randomName():
    """
    Generate a random string. This function is useful to give ROOT objects
    different names to avoid overwriting.
    """
    from random import randint
    from sys import maxint
    return "%x"%(randint(0, maxint))

def runFromFilename(filename):
    m = re.match(".*Run(\d+).root", filename)
    if m:
        return int(m.group(1))
    m2 = re.match(".*/Results(\d+)/.*", filename) # for pseudo
    if m2:
        return int(m2.group(1))
    else:
        print "Could not find run number for file", filename
        return 0

def getFromFile(filename, objectname):
    f = ROOT.TFile(filename)
    if f.GetSize()<5000: # DQM files sometimes are empty
        return None
    h = f.Get(objectname)
    h = ROOT.gROOT.CloneObject(h)
    return h

def sortedDict(d):
    return collections.OrderedDict(sorted(d.items(), key=lambda t: t[0]))

def getInputHists(searchPath="root-files/Run*.root"):
    hists = {}
    for filename in glob.glob(searchPath):
        runNr = runFromFilename(filename)
        newHists = {}
        if searchPath.endswith("PCL_SiPixAl_DQM.root"):
            c = getFromFile(filename, "PCL_SiPixAl_Expert")
            for pad in c.GetListOfPrimitives():
                pad.cd()
                for x in pad.GetListOfPrimitives():
                    if isinstance(x, ROOT.TH1F):
                        newHists[x.GetName()] = x.Clone()
                        break
        else: # dqm plots
            for p in parameters:
                h = getFromFile(filename, p.name)
                if h:
                    newHists[p.name] = h
        if newHists: hists[runNr] = newHists
    return sortedDict(hists)

def drawHistsVsRun(hmap, savename):
    line = ROOT.TLine()
    line.SetLineColor(ROOT.kRed)
    c = ROOT.TCanvas(randomName(),"",1200,600)
    c.Divide(3,2)
    for ip, p in enumerate(parameters):
        c.cd(ip+1)
        for ih,h in enumerate(hmap[p.name]):
            h.SetYTitle(p.label)
            h.GetYaxis().SetRangeUser(p.minDraw, p.maxDraw)
            h.SetMarkerColor(objects[ih][1])
            h.SetLineColor(objects[ih][1])
            h.Draw( "e same" if ih>0 else "e")
        line.DrawLine(h.GetXaxis().GetXmin(),-p.cut,h.GetXaxis().GetXmax(),-p.cut)
        line.DrawLine(h.GetXaxis().GetXmin(),+p.cut,h.GetXaxis().GetXmax(),+p.cut)
    c.cd(0)
    text = ROOT.TLatex(.47,.96, " ".join( ["#color[{}]{{{}}}".format(objects[i][1],objects[i][0]) for i in range(6)] ) )
    text.Draw()
    textCMS = ROOT.TLatex(.05,.96, "#font[61]{CMS} #scale[0.76]{#font[52]{Private Work}}")
    textCMS.Draw()
    save(savename)

def getHistsVsRun(inputHists, minRun=-1):
    inputHists = sortedDict(dict((key,value) for key, value in inputHists.iteritems() if key >= minRun))
    hdefault = ROOT.TH1F("", ";;#Delta blub", len(inputHists), 0, len(inputHists))
    hdefault.SetLabelSize(.04)
    for bin, runNr in enumerate(inputHists.keys()):
        if len(inputHists) < 20 or not bin%int(len(inputHists)/20) or bin+1==len(inputHists):
            hdefault.GetXaxis().SetBinLabel(bin+1, str(runNr))
    histsVsRun = {}
    for iRun, (runNr, hmap) in enumerate(inputHists.iteritems()):
        for hname, h in hmap.iteritems():
            if hname not in histsVsRun: histsVsRun[hname] = [ hdefault.Clone() for i in range(6) ]
            for bin in range(1,7):
                c = h.GetBinContent(bin)
                e = h.GetBinError(bin)
                histsVsRun[hname][bin-1].SetBinContent(iRun+1,c)
                histsVsRun[hname][bin-1].SetBinError(iRun+1,e)
    return histsVsRun

def diffHistsVsRun(inputHists, inputHists2, minRun=-1):
    inputHists = sortedDict(dict((key,value) for key, value in inputHists.iteritems() if key >= minRun))
    inputHists2 = sortedDict(dict((key,value) for key, value in inputHists2.iteritems() if key >= minRun))

    hdefault = ROOT.TH1F("", ";;#Delta blub", len(inputHists), 0, len(inputHists))
    hdefault.SetLabelSize(.04)
    for bin, runNr in enumerate(inputHists.keys()):
        if len(inputHists) < 20 or not bin%int(len(inputHists)/20) or bin+1==len(inputHists):
            hdefault.GetXaxis().SetBinLabel(bin+1, str(runNr))
    histsVsRun = {}
    allRuns = sorted(list(set(inputHists.keys()) | set(inputHists2.keys())))
    for iRun, runNr in enumerate(allRuns):
        if runNr in inputHists:
            if runNr in inputHists2:
                for hname, h in inputHists[runNr].iteritems():
                    h2 = inputHists2[runNr][hname]
                    if hname not in histsVsRun: histsVsRun[hname] = [ hdefault.Clone() for i in range(6) ]
                    for bin in range(1,7):
                        c = h.GetBinContent(bin)
                        e = h.GetBinError(bin)
                        c2 = h2.GetBinContent(bin)
                        e2 = h2.GetBinError(bin)
                        histsVsRun[hname][bin-1].SetBinContent(iRun+1, c-c2)
                        histsVsRun[hname][bin-1].SetBinError(iRun+1, math.sqrt(e**2+e2**2))
    return histsVsRun

def updateFile(source, dest, changes={}):
    with open(source) as f:
        x = string.Template(f.read())
    with open(dest, "w") as f:
        f.write(x.safe_substitute(changes))

def copyToWebSpace(files=[]):
    dest = "/afs/cern.ch/user/k/kiesel/www/"
    for f in files:
        subprocess.call(["convert", "plots/{}.pdf".format(f), "-trim", "plots/{}.png".format(f)])
        shutil.copyfile("plots/{}.pdf".format(f), dest+f+".pdf")
        shutil.copyfile("plots/{}.png".format(f), dest+f+".png")

def main():
    todayStr = datetime.date.today().isoformat()
    inputHists = getInputHists()
    inputHistsPseudo = getInputHists("/afs/cern.ch/user/k/kiesel/public/pp3.8T_PCL_Alignment/Results*/MinBias_2016/PCL_SiPixAl_DQM.root")
    sortedRuns = sorted(inputHists.keys())
    firstNewRun = sortedRuns[-min(10, len(sortedRuns))]

    drawHistsVsRun(getHistsVsRun(inputHists), "pixAlignment_pcl_all_{}".format(todayStr))
    drawHistsVsRun(getHistsVsRun(inputHists, firstNewRun), "pixAlignment_pcl_newest_{}".format(todayStr))
    drawHistsVsRun(getHistsVsRun(inputHistsPseudo), "pixAlignment_pseudo_all_{}".format(todayStr))
    drawHistsVsRun(getHistsVsRun(inputHistsPseudo, firstNewRun), "pixAlignment_pseudo_newest_{}".format(todayStr))
    drawHistsVsRun(diffHistsVsRun(inputHists, inputHistsPseudo), "pixAlignment_diff_all_{}".format(todayStr))

    drawHistsVsRun(diffHistsVsRun(inputHists, inputHistsPseudo, firstNewRun), "pixAlignment_diff_newest_{}".format(todayStr))



def copyToWeb():
    updateFile(
        "/afs/cern.ch/user/k/kiesel/www/indexTemplate.html",
        "/afs/cern.ch/user/k/kiesel/www/index.html",
        {"date": todayStr,
         "f1": "pixAlignment_pcl_all_{}".format(todayStr),
         "f2": "pixAlignment_pcl_newest_{}".format(todayStr),
         "f3": "pixAlignment_pseudo_all_{}".format(todayStr),
         "f4": "pixAlignment_pseudo_newest_{}".format(todayStr),
         "f5": "pixAlignment_diff_all_{}".format(todayStr),
         "f6": "pixAlignment_diff_newest_{}".format(todayStr),
        }
    )
    copyToWebSpace([
        "pixAlignment_pcl_all_{}".format(todayStr),
        "pixAlignment_pcl_newest_{}".format(todayStr),
        "pixAlignment_pseudo_all_{}".format(todayStr),
        "pixAlignment_pseudo_newest_{}".format(todayStr),
        "pixAlignment_diff_all_{}".format(todayStr),
        "pixAlignment_diff_newest_{}".format(todayStr),
        ]
    )

style()
todayStr = datetime.date.today().isoformat()
main()
copyToWeb()
