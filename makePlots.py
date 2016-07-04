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
import downloadViaJson
import style

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

plotDir = "/afs/cern.ch/user/k/kiesel/www/plots"



def save(name, folder="plots", endings=[".pdf"]):
    for ending in endings:
        ROOT.gPad.GetCanvas().SaveAs(os.path.join(folder,name+ending))

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
    m2 = re.match(".*/Results(\d+)[^\d].*", filename) # for pseudo
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

def exceedsCuts(h, cutDict=False):
    maxErrCut = 10
    sigCut = 2.5
    maxCut = 200
    var = h.GetName().split("_")[0]
    cut = parDict[var].cut

    binInfos = []
    for bin in range(1,h.GetNbinsX()+1):
        c = abs(h.GetBinContent(bin))
        e = h.GetBinError(bin)
        if c > maxCut or e > maxErrCut:
            binInfos.append("fail")
        elif c > cut and e and c/e > sigCut:
            binInfos.append("update")
        else:
            binInfos.append("good")
    if "fail" in binInfos:
        return "fail"
    elif "update" in binInfos:
        return "update"
    else:
        return "good"

def checkNewAlignment(hmap, cutDict):
    infos = [ exceedsCuts(x, cutDict) for x in hmap.values() ]
    return "fail" not in infos and "update" in infos

def align(hmap, hmapAlignSettings):
    hmapNew = {}
    for name, h in hmap.iteritems():
        hSet = hmapAlignSettings[name]
        hmapNew[name] = h.Clone(h.GetName()+"_"+randomName())
        for bin in range(1,7):
            hmapNew[name].SetBinContent(bin,h.GetBinContent(bin)-hSet.GetBinContent(bin))
    return hmapNew

def drawHists(hmap, savename):
    hnames = ["Xpos", "Ypos","Zpos", "Xrot", "Yrot", "Zrot"]
    line = ROOT.TLine()
    line.SetLineColor(ROOT.kRed)
    c = ROOT.TCanvas(randomName(),"",1200,600)
    c.Divide(3,2)
    for ih, hname in enumerate(hnames):
        c.cd(ih+1)
        h = hmap[hname]
        h.SetLineColor(ROOT.kBlack)
        h.SetFillColor(ROOT.kGreen-7)
        cutStatus = exceedsCuts(h)
        if cutStatus == "update":
            h.SetFillColor(ROOT.kOrange-9)
        elif cutStatus == "fail":
            h.SetFillColor(ROOT.kRed)
        for bin in range(1,7):
            h.GetXaxis().SetBinLabel(bin,objects[bin-1][0])
        h.GetXaxis().SetRange(1,6)
        h.GetYaxis().SetRangeUser(-50,50)
        h.Draw("histe")
        cut = h.GetBinContent(8)
        if not cut:
            cuts = {"Xpos":5, "Ypos":10, "Zpos":15, "Xrot":30, "Yrot":30, "Zrot":30}
            cut = cuts[h.GetName().split("_")[0]]
        line.DrawLine(0,-cut,6,-cut)
        line.DrawLine(0,+cut,6,+cut)
    c.cd(0)
    save(savename, plotDir)

def drawHistsVsRun(hmap, savename):
    if not hmap: return
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
    save(savename, plotDir, endings=[".pdf",".png"])

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
    inputHists = sortedDict(dict((key,(value,None)) for key, value in inputHists.iteritems() if key >= minRun))
    for key, value in inputHists2.iteritems():
        if key not in inputHists: inputHists[key] = (None, value)
        else: inputHists[key] = (inputHists[key][0], value)
    inputHists = sortedDict(inputHists)

    hdefault = ROOT.TH1F("", ";;#Delta blub", len(inputHists), 0, len(inputHists))
    hdefault.SetLabelSize(.04)
    for bin, runNr in enumerate(inputHists.keys()):
        if len(inputHists) < 20 or not bin%int(len(inputHists)/20) or bin+1==len(inputHists):
            hdefault.GetXaxis().SetBinLabel(bin+1, str(runNr))
    histsVsRun = {}
    for iRun, (runNr, (hmap1, hmap2))  in enumerate(inputHists.iteritems()):
        if hmap1 and hmap2:
            for hname, h in hmap1.iteritems():
                h2 = hmap2[hname]
                if hname not in histsVsRun: histsVsRun[hname] = [ hdefault.Clone() for i in range(6) ]
                for bin in range(6):
                    c = h.GetBinContent(bin+1)
                    e = h.GetBinError(bin+1)
                    c2 = h2.GetBinContent(bin+1)
                    e2 = h2.GetBinError(bin+1)
                    histsVsRun[hname][bin].SetBinContent(iRun+1, c-c2)
                    histsVsRun[hname][bin].SetBinError(iRun+1, math.sqrt(e**2+e2**2))
#        if hmap1 and not hmap2: print "Run {} not in manual workflow".format(runNr)
#        if not hmap1 and hmap2: print "Run {} not in online workflow".format(runNr)
    return histsVsRun

def pseudoAlignment(inputHists, app=""):
    referenceRun = -1
    for run, hmap in inputHists.iteritems():
        drawHists(hmap, "pre{}".format(run)+app)
        if referenceRun > 0:
            hmap = align(hmap,inputHists[referenceRun])
        if checkNewAlignment(hmap):
            print "updated alignment", run
            referenceRun = run
        drawHists(hmap, "post{}".format(run)+app)

def cutParameterVariation(parName, cuts):
    gr = ROOT.TGraph()
    myCuts = copy.deepcopy(parDict)
    for i, c in enumerate(cuts):
        myCuts[parName].cut = c
        n = len(getHistsVsRun(inputHists, True, myCuts)[1])
        gr.SetPoint(i,c,n)
    unit = "#mum" if "pos" in parName else "^{#circ}"
    gr.SetTitle("{}; limit [{}];number of updates".format(parName,unit))
    gr.SetMarkerStyle(20)
    gr.Draw("ap")
    l = ROOT.TLine()
    origCut = parDict[parName].cut
    yAxis = gr.GetHistogram().GetYaxis()
    l.DrawLine(origCut,yAxis.GetXmin(),origCut,yAxis.GetXmax())
    save("cutParameterVariation_"+parName)

def updateFile(source, dest, changes={}):
    with open(source) as f:
        x = string.Template(f.read())
    with open(dest, "w") as f:
        f.write(x.safe_substitute(changes))

def getNthLastRun(inputHists, N):
    sortedRuns = sorted(inputHists.keys())
    return sortedRuns[-min(N, len(sortedRuns))]

def getTableString(runs):
    return "\n".join(["<tr> <td>{0}</td> <td><a href=plots/Run{0}.pdf>pdf</a></td> <td><a href=plots/Run{0}_pseudo.pdf>pdf</a></td> </tr>".format(r) for r in runs])

def main():
    inputHists = getInputHists()
    inputHistsPseudo = getInputHists("/afs/cern.ch/user/j/jcastle/public/pp3.8T_PCL_Alignment/Results*/MinBias_2015/PCL_SiPixAl_DQM.root")
    inputHistsPseudo.update(getInputHists("/afs/cern.ch/user/j/jschulte/public/pp3.8T_PCL_Alignment/Results*/MinBias_2016/PCL_SiPixAl_DQM.root"))
    inputHistsPseudo.update(getInputHists("/afs/cern.ch/user/k/kiesel/public/pp3.8T_PCL_Alignment/Results*/MinBias_2016/PCL_SiPixAl_DQM.root"))
    firstNewRun = getNthLastRun(inputHists, 10)
    firstNewRunPseudo = getNthLastRun(inputHistsPseudo, 10)
    firstNewRunBoth = min([firstNewRun, firstNewRunPseudo])

    todayStr = datetime.date.today().isoformat()
    drawHistsVsRun(getHistsVsRun(inputHists), "pixAlignment_pcl_all_{}".format(todayStr))
    drawHistsVsRun(getHistsVsRun(inputHists, firstNewRun), "pixAlignment_pcl_newest_{}".format(todayStr))
    drawHistsVsRun(getHistsVsRun(inputHistsPseudo), "pixAlignment_pseudo_all_{}".format(todayStr))
    drawHistsVsRun(getHistsVsRun(inputHistsPseudo, firstNewRunPseudo), "pixAlignment_pseudo_newest_{}".format(todayStr))
    drawHistsVsRun(diffHistsVsRun(inputHists, inputHistsPseudo), "pixAlignment_diff_all_{}".format(todayStr))
    drawHistsVsRun(diffHistsVsRun(inputHists, inputHistsPseudo, firstNewRunBoth), "pixAlignment_diff_newest_{}".format(todayStr))

    for run, hmap in inputHists.iteritems():
        drawHists(hmap, "Run{}".format(run))
    for run, hmap in inputHistsPseudo.iteritems():
        drawHists(hmap, "Run{}_pseudo".format(run))

    updateFile("indexTemplate.html", "/afs/cern.ch/user/k/kiesel/www/index.html",
        {"date": todayStr,
        "table": getTableString(list(set(inputHists.keys())|set(inputHistsPseudo.keys())))})



if __name__ == "__main__":
    #downloadViaJson.downloadViaJson()
    main()
