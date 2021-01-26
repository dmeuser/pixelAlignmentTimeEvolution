#!/bin/bash
# acrontab -e
# enter: 0 6 * * * lxplus.cern.ch /afs/cern.ch/user/d/dmeuser/alignment/pixelAlignmentTimeEvolution/acronExe.sh

logFile=/afs/cern.ch/user/d/dmeuser/alignment/pixelAlignmentTimeEvolution/acron.log
echo >> $logFile 2>&1
date >> $logFile 2>&1
export SCRAM_ARCH=slc7_amd64_gcc820 >> $logFile 2>&1
export VO_CMS_SW_DIR=/cvmfs/cms.cern.ch >> $logFile 2>&1
source $VO_CMS_SW_DIR/cmsset_default.sh >> $logFile 2>&1

cd /cvmfs/cms.cern.ch/slc7_amd64_gcc820/cms/cmssw/CMSSW_11_0_1 >> $logFile 2>&1
eval `scramv1 runtime -sh` >> $logFile 2>&1
cd /afs/cern.ch/user/d/dmeuser/alignment/pixelAlignmentTimeEvolution >> $logFile 2>&1
python makePlots.py >> $logFile 2>&1

