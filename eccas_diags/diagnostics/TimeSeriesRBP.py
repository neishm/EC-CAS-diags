###############################################################################
# Copyright 2016 - Climate Research Division
#                  Environment and Climate Change Canada
#
# This file is part of the "EC-CAS diags" package.
#
# "EC-CAS diags" is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# "EC-CAS diags" is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with "EC-CAS diags".  If not, see <http://www.gnu.org/licenses/>.
###############################################################################


# regional bar plots

from .timeseries import Timeseries
class TimeseriesRBP(Timeseries):
  """
  Bin data into regions (country or zone), and produce a histogram of the
  result.
  """
  def __init__ (self, ymin=350, ymax=420, **kwargs):
    super(TimeseriesRBP,self).__init__(**kwargs)
    self.ymin = ymin
    self.ymax = ymax
  # Only use very particular obs datasets, where we know the regions.
  def _input_combos (self, inputs):
    for inputs in super(TimeseriesRBP,self)._input_combos(inputs):
      if inputs[-1].name == 'GAW-2014-hourly':
        yield inputs
  def do (self, inputs):
    import numpy as np
    import matplotlib.pyplot as pl
    from os.path import exists

    fig = pl.figure(figsize=(8,8))

    #Format image directory
    outdir = self.outdir + '/TimeSeriesRBP-images_%s_%s%s'%('_'.join(d.name for d in inputs),self.fieldname,self.suffix)
    if not exists(outdir):
      from os import makedirs
      makedirs(outdir)

    outfile = "%s/%s_timeseries_%s%s.%s"%(outdir,'_'.join(d.name for d in inputs),self.fieldname,self.suffix+self.end_suffix,self.image_format)

    # Skip plots that have already been generated.
    if exists(outfile): return

    Zones = np.zeros((5,len(inputs)))
    Stds = np.zeros((5,len(inputs)))

    #List of stations within the two continents in question
    NorthAmList = ['Alert','Barrow','Candle Lake','Chibougamau','East Trout Lake','Egbert','Estevan Point','Fraserdale',
      'Lac La Biche (Alberta)','Mauna Loa','Sable Island',]
    EuropeList = ['BEO Moussala','Jungfraujoch','Kollumerwaard','Monte Cimone','Neuglobsow','Pallas-Sammaltunturi','Plateau Rosa',
      'Puszcza Borecka/Diabla Gora','Schauinsland','Sonnblick','Westerland','Zeppelinfjellet (Ny-Alesund)','Zugspitze / Schneefernerhaus']

    #List for counting the number of stations in each group
    Count = np.zeros((5,len(inputs)),dtype=int)

    nstations = len(inputs[0].datasets)
    for j in range(nstations):
      station_axis = inputs[0].datasets[j].vars[0].station
      assert len(station_axis) == 1, "Unable to handle multi-station datasets"
      location = station_axis.station[0]

      station_info = station_axis(station=location)
      lat = station_info.lat[0]
      lon = station_info.lon[0]

      #-----Record Data------
      for i,inp in enumerate(inputs):
        d = inp.datasets[j][self.fieldname].get().flatten()
        mean = np.mean(d[~np.isnan(d)])
        std = np.std(d[~np.isnan(d)])
        if np.isnan(mean): continue  # Check if there's any data to include
        #Average values and standard deviations of each station's timeseries
        if lat > 30:
          #Add 1 to the region count on first run through
          Zones[0,i] += mean
          Stds[0,i] += std
          Count[0,i] += 1
        elif lat < -30:
          Zones[1,i] += mean
          Stds[1,i] += std
          Count[1,i] += 1
        else:
          Zones[2,i] += mean
          Stds[2,i] += std
          Count[2,i] += 1

        #Sort for Europe and NA stations
        if location in NorthAmList:
          Zones[3,i] += mean
          Stds[3,i] += std
          Count[3,i] += 1
        elif location in EuropeList:
          Zones[4,i] += mean
          Stds[4,i] += std
          Count[4,i] += 1

    #---------Process/Plot Data--------

    #Average the values of each Zone's dataset's station average
    Zones /= Count
    Stds /= Count
    rects = []

    for i in range(len(inputs)):

      xvalues = np.arange(5)*(len(inputs)+1)+i

      height = list(Zones[:,i])
      yerr = list(Stds[:,i])

      rect = pl.bar(xvalues,height,yerr = yerr,color = inputs[i].color, width = 1,lw = 2, ecolor= 'black',capsize = 5)
      rects.append(rect)

    for i in range(len(Zones)):
      for j in range(len(inputs)):
        textx = i*(len(inputs)+1)+j+0.5
        texty = (Zones[i,j]+self.ymin)/2.0
        if np.isfinite(texty):
          pl.text(textx,texty,Count[i,j],horizontalalignment = 'center', color='white')

    pl.xlim(-1,len(Zones)*(len(inputs)+1))

    pl.title('Average %s Concentrations'%(self.fieldname))
    pl.ylim(ymin=self.ymin,ymax=self.ymax)
    pl.ylabel('%s (%s)'%(self.fieldname,self.units))
    pl.xticks(np.arange(5)*(len(inputs)+1)+len(inputs)/2.0,
      ['Northern\nHemisphere','Southern\nHemisphere','Tropics','North\nAmerica','Europe']
      ,horizontalalignment = 'center')
    pl.legend(rects, [d.title for d in inputs],prop={'size':12})
    pl.text(.02,.96,'One standard deviation shown',transform = pl.gca().transAxes)

    fig.savefig(outfile)

    pl.close(fig)

from . import table
table['regional-bargraph'] = TimeseriesRBP

