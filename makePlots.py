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
import pickle
import math
import json
import ast

import suppressor
#with suppressor.suppress_stdout_stderr(): 
import ROOT
from ROOT import gPad, gStyle
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
    Parameter("Xpos", "#Deltax (#mum)", 5, -30, 30 ), \
    Parameter("Ypos", "#Deltay (#mum)", 10, -30, 30 ), \
    Parameter("Zpos", "#Deltaz (#mum)", 15, -30, 30 ), \
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

plotDir = "/eos/project/c/cmsweb/www/pixAlignSurv/plots"
#  ~plotDir = "/afs/cern.ch/user/d/dmeuser/alignment/pixelAlignmentTimeEvolution/plots"

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
    
def getPedeExitCodes(searchPath="root-files/Run*.root"):
    exitCodes = {}
    for filename in glob.glob(searchPath):
        runNr = runFromFilename(filename)
        exitCode = getFromFile(filename,"PedeExitCode")
        exitCodes[runNr] = exitCode
    return sortedDict(exitCodes)
    
def getStatusPlots(searchPath="root-files/Run*.root"):
    statusPlots = {}
    for filename in glob.glob(searchPath):
        runNr = runFromFilename(filename)
        statusPlot = getFromFile(filename,"statusResults")
        statusPlots[runNr] = statusPlot
    return sortedDict(statusPlots)

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

def getRunEndTime(run):
    foundtimestr = "0"
    currentRun = run
    while foundtimestr == "0":
        try:
            #returs a string similar to 2016-06-16 23:30:32
            output = subprocess.check_output(["conddb listRuns --match {} | grep \"{} \"".format(currentRun,currentRun)], shell=True)
            output = output.split("  ")
            output = output[4].split(".")[0]
            foundtimestr = output
            datetime.datetime.strptime(foundtimestr, "%Y-%m-%d %H:%M:%S")
        except KeyboardInterrupt:
            raise
        except:
            currentRun -= 1
    return foundtimestr
    		

def getLuminosity(minRun):
    """Expects something like
    +-------+------+--------+--------+-------------------+------------------+
    | nfill | nrun | nls    | ncms   | totdelivered(/fb) | totrecorded(/fb) |
    +-------+------+--------+--------+-------------------+------------------+
    | 73    | 327  | 142418 | 138935 | 19.562            | 18.036           |
    +-------+------+--------+--------+-------------------+------------------+
    And extracts the total recorded luminosity (/fb).
    """
    output = subprocess.check_output(["/afs/cern.ch/user/d/dmeuser/.local/bin/brilcalc", "lumi", "-b", "STABLE BEAMS", "--normtag=/afs/cern.ch/user/l/lumipro/public/normtag_file/normtag_BRIL.json", "-u", "/fb", "--begin", str(minRun)])
    return float(output.split("\n")[-3].split("|")[-2])

def getTime(run, dbName="runTime.pkl"):
    db = {}
    if os.path.exists(dbName):
        with open(dbName) as f:
            db = pickle.load(f)
    if run not in db or db[run] == "\n" or db[run] == "0":
        db[run] = getRunEndTime(run)
        db[run] = db[run].replace('"','')
        print "Get Time for run {}: {}".format(run, db[run])
    with open(dbName, "wb") as f:
        pickle.dump(db, f)
     
    return db[run]

def sendMail(adress, subject="", body=""):
    os.system("echo \"{}\" | mail -s \"{}\" {}".format(body, subject, adress))

def drawHists(hmap, savename, run):
    hnames = ["Xpos", "Ypos","Zpos", "Xrot", "Yrot", "Zrot"]
    line = ROOT.TLine()
    line.SetLineColor(ROOT.kRed)
    c = ROOT.TCanvas(randomName(),"",1200,600)
    c.Divide(3,2)
    dbUpdated = False
    gStyle.SetLineScalePS(1.5)
    for ih, hname in enumerate(hnames):
        c.cd(ih+1)
        h = hmap[hname]
        h.SetLineColor(ROOT.kBlack)
        h.SetFillColor(ROOT.kGreen-7)
        h.SetMarkerSize(0)
        cutStatus = exceedsCuts(h)
        if cutStatus == "update":
            h.SetFillColor(ROOT.kOrange-9)
            dbUpdated = True
        elif cutStatus == "fail":
            h.SetFillColor(ROOT.kRed)
        for bin in range(1,7):
            h.GetXaxis().SetBinLabel(bin,objects[bin-1][0])
        h.GetXaxis().SetRange(1,6)
        h.GetYaxis().SetRangeUser(-50,50)
        h.SetTitle("")
        h.GetYaxis().SetTitle(parameters[ih].label)
        h.Draw("histe")
        h.Draw("same e")
        cut = h.GetBinContent(8)
        if not cut:
            cuts = {"Xpos":5, "Ypos":10, "Zpos":15, "Xrot":30, "Yrot":30, "Zrot":30}
            cut = cuts[h.GetName().split("_")[0]]
        line.DrawLine(0,-cut,6,-cut)
        line.DrawLine(0,+cut,6,+cut)
        gPad.RedrawAxis()
    c.cd(0)
    text = ROOT.TLatex()
    text.SetTextSize(.75*text.GetTextSize())
    text.DrawLatexNDC(.06, .967, "#scale[1.2]{#font[61]{CMS}} #font[52]{Private Work}")
    #  ~text.DrawLatexNDC(.82, .967, "Run {} (13TeV)".format(run))
    text.DrawLatexNDC(.82, .967, "Run {}".format(run))
    save(savename, plotDir, [".pdf",".png", ".root"])
    if dbUpdated:
        #  ~sendMail("danilo.meuser@rwth-aachen.de cms-tracker-alignment-conveners@cern.ch", "[PCL] Cuts exceeded", "Run: {}\nSee http://cern.ch/cmsPixAlignSurv".format(run))
        sendMail("danilo.meuser@rwth-aachen.de", "[PCL] Cuts exceeded", "Run: {}\nSee http://cern.ch/cmsPixAlignSurv".format(run))

def drawGraphsVsX(gmap, xaxis, savename, specialRuns=[], specialRuns2=[]):
    """ Options for xaxis: time, run"""
    if not gmap: return
    line = ROOT.TLine()
    line.SetLineColor(ROOT.kGray)
    updateLine = ROOT.TLine()
    updateLine.SetLineStyle(2)
    leg = ROOT.TLegend(.2, .65, .55, .9)
    leg.SetNColumns(2)
    leg.AddEntry(line, "Limit", "l")
    leg.AddEntry(updateLine, "New alignment", "l")
    for ip, p in enumerate(parameters):
        c = ROOT.TCanvas(randomName(),"",1200,600)
        for ig,g in enumerate(gmap[p.name]):
            if xaxis == "time":
                g.SetTitle(";Time;{}".format(p.label))
                g.GetXaxis().SetTimeDisplay(1)
                g.GetXaxis().SetTimeOffset(25)
                g.GetXaxis().SetTimeFormat("%Y-%m-%d")
                g.GetXaxis().SetNdivisions(6,0,0)
            elif xaxis == "run":
                g.SetTitle(";Run;{}".format(p.label))
                g.GetXaxis().SetNoExponent()
                g.GetXaxis().SetNdivisions(7,0,0)
            else:
                print "No idea what to do with x-axis", xaxis
            g.GetYaxis().SetRangeUser(p.minDraw, p.maxDraw)
            g.SetMarkerColor(objects[ig][1])
            g.SetLineColor(objects[ig][1])
            g.Draw( "same p" if ig>0 else "ap")
            leg.AddEntry(g, objects[ig][0], "l")
            if not ig:
                xax = g.GetXaxis()
                xmin, xmax = xax.GetXmin(), xax.GetXmax()
        line.DrawLine(xmin, -p.cut, xmax, -p.cut)
        line.DrawLine(xmin, +p.cut, xmax, +p.cut)
        for r in specialRuns:
            updateLine.SetLineColor(ROOT.kGray)
            updateLine.DrawLine(r, p.minDraw, r, p.maxDraw)
        #for r in specialRuns2:
        #    updateLine.SetLineColor(ROOT.kGreen)
        #    updateLine.DrawLine(r, p.minDraw, r, p.maxDraw)
        text = ROOT.TLatex()
        text.DrawLatexNDC(.155, .955, "#scale[1.2]{#font[61]{CMS}} #font[52]{Private Work}")
        #  ~text.DrawLatexNDC(.79, .945, "Year 2018 (13TeV)")
        text.DrawLatexNDC(.73, .96, "Commissioning 2021")
        if ip == 0: leg.Draw()
        save(savename+"_"+p.name, plotDir, endings=[".pdf",".png", ".root"])
        
def drawDetails(hmap, statusPlot, exitCode, savename, run):
    steps = ["DB update triggered", "significant movement","DB update vetoed", "within max movement", "within max error", "above significance"]
    c = ROOT.TCanvas(randomName(),"",700,500)
    text = ROOT.TLatex()
    text.SetTextSize(0.04)
    text.DrawLatexNDC(.02, .955, "Details on PCL Alignment for Run "+str(run))
    text.DrawLatexNDC(.02, .855, "PedeExitCode: "+exitCode.GetString().Data())
    for bin in range(1,statusPlot.GetNbinsX()+1):
        text.SetTextColor(ROOT.kGreen-7)
        if statusPlot.GetBinContent(bin,1)==0:
            text.SetTextColor(ROOT.kRed)
        text.DrawLatexNDC(.02, .855-bin*0.1, steps[bin-1])
    save(savename, plotDir, [".pdf"])


def string2Time(timeStr):
    return ROOT.TDatime(timeStr).Convert(0)

def getGraphsVsRun(inputHists, minRun=-1, convertToTime=False):
    inputHists = sortedDict(dict((key,value) for key, value in inputHists.iteritems() if key >= minRun))
    gdefault = ROOT.TGraphErrors()
    graphsVsRun = {}
    for iRun, (runNr, hmap) in enumerate(inputHists.iteritems()):
        if convertToTime and getTime(runNr)=="0": continue #remove runs with no valid time stamp from plot vs time
        xVar = string2Time(getTime(runNr)) if convertToTime else runNr
        for hname, h in hmap.iteritems():
            if hname not in graphsVsRun: graphsVsRun[hname] = [ gdefault.Clone() for i in range(6) ]
            for bin in range(1,7):
                c = h.GetBinContent(bin)
                e = h.GetBinError(bin)
                #if abs(c) < 1e-15 or abs(e) > 5: continue
                n = graphsVsRun[hname][0].GetN()
                graphsVsRun[hname][bin-1].SetPoint(n, xVar, c)
                graphsVsRun[hname][bin-1].SetPointError(n, 0, e)
    return graphsVsRun

def updateFile(source, dest, changes={}):
    with open(source) as f:
        x = string.Template(f.read())
    with open(dest, "w") as f:
        f.write(x.safe_substitute(changes))

def getNthLastRun(inputHists, N):
    sortedRuns = sorted(inputHists.keys())
    return sortedRuns[-min(N, len(sortedRuns))]

def isFilledRun(hmap):
    globalMax = 0
    for k, v in hmap.iteritems():
        for bin in range(1,7):
            globalMax = max(globalMax, v.GetBinContent(bin))
    return abs(globalMax) > 1e-6

def getTableString(inputHists, maxPlots=5):
    inputHists = collections.OrderedDict(reversed(list(inputHists.items())))
    outString = "<table style='text-align:center'>\n<tr> <td> Run </td> <td> End time </td> <td> Details </td> <td> Parameters </td> </tr>"
    for run, hmap in inputHists.iteritems():
        link = "<td style='text-align:left'>No results"
        linkDet = "<a href=plots/detailsRun{0}.pdf>details</a>".format(run)
        if isFilledRun(hmap):
            if maxPlots > 0:
                link = "<td><a href=plots/Run{0}.pdf><img src='plots/Run{0}.png' border='0'/></a>".format(run)
                maxPlots -= 1
            else:
                link = "<td style='text-align:left'><a href=plots/Run{0}.pdf>pdf</a>".format(run)
        outString += "\n<tr> <td>{0}</td> <td>{1}</td> <td>{2}</td> {3}</td> </tr>".format(run, getTime(run), linkDet, link)
    outString += "\n</table>"
    return outString

def getUpdateRuns(tag):
    out = subprocess.check_output(["conddb", "list", tag])
    return [int(x.split()[0]) for x in out.split("\n")[2:-2] if x]

if __name__ == "__main__":
    downloadViaJson.getGridCertificat()
    downloadViaJson.downloadViaJson()
    inputHists = getInputHists()
    exitCodes = getPedeExitCodes()
    statusPlots = getStatusPlots()

    # draw new runs:
    alreadyPlotted = [ int(x[3:9]) for x in os.listdir(plotDir) if x.endswith(".pdf") and x.startswith("Run")]
    for run, hmap in inputHists.iteritems():
        if run not in alreadyPlotted:
            drawHists(hmap, "Run{}".format(run), run)
            drawDetails(hmap, statusPlots[run], exitCodes[run], "detailsRun{}".format(run), run)

		
    # vs run
    #~ updateRuns = [x for x in getUpdateRuns("TrackerAlignment_PCL_byRun_v1_express") if x >= 273000]
    #updateRuns2 = [x for x in getUpdateRuns("TrackerAlignment_PCL_byRun_v0_express") if x >= 273000]
    #  ~updateRuns  = [x for x in getUpdateRuns("SiPixelLorentzAngle_fromAlignment_v1_hlt") if x >= 315252]
    #  ~updateRuns  = [x for x in getUpdateRuns("SiPixelTemplateDBObject_38T_v1_prompt") if x >= 315252]
    updateRuns  = [x for x in getUpdateRuns("SiPixelTemplateDBObject_38T_v1_prompt") if x >= 327575]
    #  ~updateRuns  = []
    #updateRuns2 = [x for x in getUpdateRuns("101X_dataRun2_Queue") if x >= 315000]
    updateRuns2 = []
    graphsVsRun = getGraphsVsRun(inputHists)
    
    print "Starting with plots vs run number:"
    drawGraphsVsX(graphsVsRun, "run", "vsRun", updateRuns, updateRuns2)

    # vs time
    print "Starting with plots vs time:"
    updateTimes = [string2Time(getTime(x)) for x in updateRuns]
    updateTimes2 = [] #[string2Time(getTime(x)) for x in updateRuns2]
    graphsVsTime = getGraphsVsRun(inputHists, convertToTime=True)
    drawGraphsVsX(graphsVsTime, "time", "vsTime", updateTimes, updateTimes2)
    #  ~updateFile("indexTemplate.html", "index.html",
        #  ~{
            #  ~"date": datetime.datetime.today().isoformat(' '),
            #  ~"table": getTableString(inputHists)
        #  ~})
    updateFile("indexTemplate.html", "/eos/project/c/cmsweb/www/pixAlignSurv/index.html",
        {
            "date": datetime.datetime.today().isoformat(' '),
            "table": getTableString(inputHists)
        })


