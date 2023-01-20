## Canadian Census Analyzer
Create interactive chloropeth maps using data from multiple years of the Canadian Census.

**Median age of the population over the 2011, 2016, and 2021 censuses:**
<p align="center">
  <img src="https://github.com/slehmann1/Canadian-Census-Analyzer/blob/main/Supporting%20Info/medianPopulationAge.gif?raw=true" />
</p>

**Average size of census families over the 2011, 2016, and 2021 censuses:**
<p align="center">
  <img src="https://github.com/slehmann1/Canadian-Census-Analyzer/blob/main/Supporting%20Info/averageSizeCensFams.gif?raw=true" />
</p>

**Functionality**
When running the program for the first time it will download census data from Statistics Canada. The files it will download are large (*several GB*). Once these files are processed, a user interface will launch:

<p align="center">
  <img src="https://raw.githubusercontent.com/slehmann1/Canadian-Census-Analyzer/blob/main/Supporting%20Info/GUI.png?raw=true" />
</p>

This interface allows any data within the census to be displayed, at multiple levels of geographical refinement, and with differences between different years shown. Outliers may also be removed with an interquartile range methodology. 

Plots will be output within an interactive HTML file. An example of a map output by the program is [here](https://github.com/slehmann1/Canadian-Census-Analyzer/raw/main/Supporting%20Info/SampleMap-Age.html).


**Dependencies:**
Written in Python with the following dependencies: Pandas, Tkinter, GeoPandas, Folium, numpy, and Anytree
