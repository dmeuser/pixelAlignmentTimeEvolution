export SCRAM_ARCH=slc6_amd64_gcc630
export VO_CMS_SW_DIR=/cvmfs/cms.cern.ch
source $VO_CMS_SW_DIR/cmsset_default.sh
cd /cvmfs/cms.cern.ch/slc6_amd64_gcc630/cms/cmssw/CMSSW_10_1_2
eval `scram runtime -sh`
cd ~/alignment
voms-proxy-init --voms cms:/cms/dcms -valid 192:00
cd pixelAlignmentTimeEvolution
