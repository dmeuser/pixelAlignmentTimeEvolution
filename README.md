### Purpose

This code generates histograms based on the PCL-Alignment for the SIPixel large structures. The histograms can be accessed via a [webpage](http://cmspixalignsurv.web.cern.ch/cmsPixAlignSurv/). This webpage is updated each morning to add the runs of the last day.

### Code

`makePlots.py` is the main script, which is executed while updating the webpage. The following main tasks are fulfilled running this script:

* Dowload of root files containing the PCL-Alignment for each run:
..* For this step the `downloadViaJson.py` script is used.
..* After enabling the Grid-Certificate the newest dataset for a given pattern, e.g. `/StreamExpress/Run2018*-PromptCalibProdSiPixelAli-Express-v*/ALCAPROMPT`, is searched. This pattern has to be manually adapted when changing to a new year or HI runs.
..* The root files for runs not already present in the `root-files` folder are downloaded from dqm.
..* A list of new runs is returned to the main script.

* Plot nominal histograms:
..* For each run not already plotted in `eos/project/c/cmsweb/www/pixAlignSurv/plots` a histogram for each of the six parameters is plotted based on the root file downloaded before.
..* Each plots consist of the first 6 bins of the histograms present in the root files, which correspond to the different large structures.
..* In case one of the entries exceeds a cut value, which are manually set at the top of `makePlots.py`, a mail is sent to the alignment conveners

* Plot alignment VS runNr:
..* For each parameter the alignement is plotted against the runNr, taken from the name of the root file.
..* Vertical lines for new algments given by tags like `SiPixelLorentzAngle_fromAlignment_v1_hlt` can be added.

* Plot alignment VS time:
..* If available the time stamp present in `runTime.pkl` is assigned to the corresponding run.
..* In case of a missing time stamp or new runs this time stamp is taken from the runRegistry using the dasgoclient.

* Update webpage:
..* The html file is based on the structure available in `indexTemplate.html`.
..* The time is updated with the current time stamp.
..* For each run the runNr, EndTime and the corresponding alignment plot for the six parameters are shown.
..* In case the first 6 bins in a root file are empty, "no result" is displayed.

To run this code on a daily base the `acronExe.sh` script has to be added to the own crontab as decribed at the top of this bash script.

### Adaptions to run the code

* The paths present in `acronExe.sh` have to be adapted
* Change access rights (write/read) for the eos directory `eos/project/c/cmsweb/www/pixAlignSurv/plots` 
