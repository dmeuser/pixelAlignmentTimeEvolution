#!/bin/bash
#~ export SCRAM_ARCH=slc6_amd64_gcc630
export SCRAM_ARCH=slc7_amd64_gcc900
export VO_CMS_SW_DIR=/cvmfs/cms.cern.ch
source $VO_CMS_SW_DIR/cmsset_default.sh
#~ cd /cvmfs/cms.cern.ch/slc6_amd64_gcc630/cms/cmssw/CMSSW_10_1_2
# ~cd /cvmfs/cms.cern.ch/slc7_amd64_gcc820/cms/cmssw/CMSSW_11_0_1
cd /cvmfs/cms.cern.ch/slc7_amd64_gcc900/cms/cmssw/CMSSW_11_3_0
eval `scramv1 runtime -sh`
cd ~/alignment
#voms-proxy-init --voms cms:/cms/dcms -valid 192:00
cd pixelAlignmentTimeEvolution
