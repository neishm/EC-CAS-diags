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

# Interface for reading NEIS-TM CH4 model output.

from pygeode.var import Var
class NIES_TM_Var(Var):
  def __init__ (self, filename):
    import numpy as np
    from datetime import datetime, timedelta
    from os.path import dirname, basename, join
    import re
    from pygeode.var import Var
    from pygeode.axis import Lat, Lon, ZAxis
    from pygeode.timeaxis import StandardTime

    # Parse filename to get fieldname, etc.
    m = re.match(r'(D\d+\.|)(?P<name>\w+?)(mn(?P<month>\d+)|)\.bin', basename(filename))
    if m is None:
      raise ValueError("Unrecognized file %s."%filename)
    name = m.group('name')
    # Find control file (contains axis info).
    controlfile = join(dirname(filename),name+'.ctl')
    control = dict()
    with open(controlfile,'r') as c:
      for line in c:
        line = line.strip().split(None,1)
        if len(line) != 2: continue
        key, value = line
        control[key] = value

    # Get axes
    nlon, lontype, lon0, dlon = control['XDEF'].split()
    nlon = int(nlon)
    assert lontype == 'LINEAR'
    lon0 = float(lon0)
    dlon = float(dlon.replace(',','.'))
    lon = lon0 + np.arange(nlon) * dlon
    lon = Lon(lon)
    nlat, lattype, lat0, dlat = control['YDEF'].split()
    nlat = int(nlat)
    assert lattype == 'LINEAR'
    lat0 = float(lat0)
    dlat = float(dlat)
    lat = lat0 + np.arange(nlat) * dlat
    lat = Lat(lat)
    nlev, levtype, lev = control['ZDEF'].split(None,2)
    nlev = int(nlev)
    assert levtype == 'LEVELS'
    lev = np.array(map(int,lev.split()))/1000.
    lev = lev[:nlev]  # Flux data has an extra 0.0 level for some reason?
    lev = ZAxis(lev)
    lev.atts['positive'] = 'up'
    lev.plotatts['plotorder'] = -1
    lev.plotatts['plotscale'] = 'log'
    nt, ttype, t0, dt = control['TDEF'].split()
    assert ttype == 'LINEAR'
    t0 = datetime.strptime(t0, '%HZ%d%b%Y')
    # Need a consistent reference date, so the times from all the files can be
    # properly stitched together by the diagnostic interface.
    refdate = {'year':2000,'month':1,'day':1}
    # CH4 molefractions
    if dt.endswith('hr'):
      nt = int(nt)
      dt = timedelta(hours=int(dt[:-2]))
      time = t0 + np.arange(int(nt)) * dt
      year = [t.year for t in time]
      month = [t.month for t in time]
      day = [t.day for t in time]
      time = StandardTime(year=year, month=month, day=day, units='days', startdate=refdate)
    # CH4 fluxes
    elif dt.endswith('mo'):
      nt = 1 # Monthly files only actually have 1 month per file, not 12.
      time = StandardTime(year=[t0.year], month=[int(m.group('month'))], units='days', startdate=refdate)
    else:
      raise ValueError("Unrecognized time increment '%s'"%dt)

    Var.__init__(self, axes=(time,lev,lat,lon), name=name, dtype='float32')
    self._filename = filename

  def getvalues (self, start, count):
    import numpy as np
    # Get offset into the file (limit to the selected times).
    nt, nlev, nlat, nlon = self.shape
    offset = start[0]*nlev*nlat*nlon*4
    # Figure out how much data to load for the specified times.
    length = count[0]*nlev*nlat*nlon
    # Special case: only one timestep selected, so can subset directly on levels.
    if count[0] == 1:
      length = count[1]*nlat*nlon
    # Loadthe data
    with open(self._filename,'rb') as f:
      f.seek(offset)
      values = np.fromfile(file=f,dtype='>f4',count=length).reshape(count[0],-1,nlat,nlon)
    # Now, subset the other axes.
    values = values[:,start[1]:start[1]+count[1],start[2]:start[2]+count[2],start[3]+start[3]:count[3]]
    return values

from . import DataProduct
class NIES_TM(DataProduct):
  """
  Methane molefractions and fluxes from NIES-TM model output.
  """

  # Interfaces for the vertical levels.
  sigma_interface = [1.,.990,.960,.930,.900,.870,.845,.825,.795,.700,.615, 
                    .540,.470,.410,.355,.310,.265,.225,.195,.166,.141,.121,
                    .104,.088,.076,.065,.055,.040,.030,.020,.010,.003,.001]

  # List of all possible fields we expect from the data
  # (original_name, standard_name, units)
  field_list = (
    ('ch4vm', 'CH4', 'mol mol(semidry_air)-1'),
    ('PS', 'surface_pressure', 'Pa'),
    ('cag', 'CH4_agwaste_flux', 'g(C) m-2 day-1'),
    ('cbb', 'CH4_bioburn_flux', 'g(C) m-2 day-1'),
    ('cff', 'CH4_fossil_flux', 'g(C) m-2 day-1'),
    ('cna', 'CH4_natural_flux', 'g(C) m-2 day-1'),
    ('coc', 'CH4_ocean_flux', 'g(C) m-2 day-1'),
  )


  # Method to open a single file
  @staticmethod
  def open_file (filename):
    from pygeode.dataset import Dataset

    # Get interface to the data.
    var = NIES_TM_Var(filename)

    # Ugly hack to ensure PS & CH4 have the same times.
    if var.name in ('ch4vm','PS'):
      var = var(year=(2014,2017))

    # Remove degenerate vertical axis for flux & PS data.
    if len(var.lev) == 1:
      var = var.squeeze('lev')

    return Dataset([var])

  # Method to decode an opened dataset (standardize variable names, and add any
  # extra info needed (pressure values, cell area, etc.)
  @classmethod
  def decode (cls,data):
    import numpy as np
    from pygeode.var import Var

    # Get levels
    lev = getattr(data,'lev',None)

    # Apply fieldname conversions
    data = DataProduct.decode.__func__(cls,data)

    # Convert to a dictionary (for referencing by variable name)
    data = dict((var.name,var) for var in data)

    # Add species name for all products (to assist in things like unit conversion)
    for varname in data:
      if varname.startswith('CH4'):
        data[varname].atts['specie'] = 'CH4'

    # Define pressure, dp.
    if 'surface_pressure' in data and lev is not None:
      ps = data['surface_pressure']
      p = (lev * ps).transpose('time','lev','lat','lon')
      p.atts['units'] = 'Pa'
      data['air_pressure'] = p
      dsigma = -np.diff(cls.sigma_interface)
      dsigma = Var(axes=(lev,), name='dsigma', values=dsigma)
      dp = (dsigma * ps).transpose('time','lev','lat','lon')
      dp.atts['units'] = 'Pa'
      data['dp'] = dp

    # General cleanup stuff

    # Make sure the variables have the appropriate names
    for name, var in data.iteritems():  var.name = name

    # Add extra fields that will be useful for the diagnostics.
    data = cls._add_extra_fields(data)

    return data

  # Method to find all files in the given directory, which can be accessed
  # through this interface.
  @staticmethod
  def find_files (dirname):
    from glob import glob
    from os.path import join
    files = []
    files.extend(glob(join(dirname,'*mn*.bin')))
    files.extend(glob(join(dirname,'D140101.ch4vm.bin')))
    files.extend(glob(join(dirname,'D050101.PS.bin')))
    return files

  # Method to find a unique identifying string for this dataset, from the
  # given directory name.
  @staticmethod
  def get_dataname (dirname):
    from os import path
    return path.basename(dirname)

# Add this interface to the table.
from . import table
table['nies-tm-binary'] = NIES_TM

