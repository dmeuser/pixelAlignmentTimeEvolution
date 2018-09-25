#!/bin/bash
# acrontab -e
# enter: 0 6 * * * lxplus.cern.ch /afs/cern.ch/user/d/dmeuser/alignment/pixelAlignmentTimeEvolution/acronExe.sh

logFile=/afs/cern.ch/user/d/dmeuser/alignment/pixelAlignmentTimeEvolution/acron.log
echo >> $logFile 2>&1
date >> $logFile 2>&1
export SCRAM_ARCH=slc6_amd64_gcc453 >> $logFile 2>&1
export VO_CMS_SW_DIR=/cvmfs/cms.cern.ch >> $logFile 2>&1
source $VO_CMS_SW_DIR/cmsset_default.sh >> $logFile 2>&1

cd /cvmfs/cms.cern.ch/slc6_amd64_gcc630/cms/cmssw/CMSSW_10_1_2 >> $logFile 2>&1
eval `scramv1 runtime -sh` >> $logFile 2>&1
cd /afs/cern.ch/user/d/dmeuser/alignment/pixelAlignmentTimeEvolution >> $logFile 2>&1
python makePlots.py >> $logFile 2>&1

