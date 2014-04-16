# Interface for CarbonTracker data

# Invariant data
import numpy as np
A_interface = [0., 6.575628, 336.772369, 1297.656128, 3010.146973, 5422.802734, 8356.252930000001, 11543.166992, 14665.645508, 17385.595703, 19348.775391, 20319.011719, 20348.916016, 19919.796875, 19184.544922, 18191.029297, 16990.623047, 15638.053711, 14192.009766, 12713.897461, 11262.484375, 9873.560546999999, 8564.624023, 7341.469727, 6199.839355, 4663.776367, 3358.425781, 2292.155518, 1463.16394, 857.945801, 450.685791, 204.637451, 76.16765599999999, 21.413612, 0.]
A_interface = np.array(A_interface)

B_interface = [1., 0.994204, 0.9734660000000001, 0.935157, 0.875518, 0.795385, 0.698224, 0.589317, 0.475016, 0.362203, 0.259554, 0.176091, 0.112979, 0.080777, 0.055474, 0.036227, 0.022189, 0.012508, 0.006322, 0.002765, 0.001, 0.000279, 5.5e-05, 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]
B_interface = np.array(B_interface)



# Helper methods

def ct_file2date(filename):
  from re import search
  date = search("(?P<year>\d{4})-?(?P<month>\d{2})-?(?P<day>\d{2})\.nc$", filename).groupdict()
  date['year']  = int(date['year'])
  date['month'] = int(date['month'])
  date['day']   = int(date['day'])
  return date

def ct_opener (filename):
  from pygeode.formats import netcdf
  data = netcdf.open(filename)
  # The time axis in the file is wrong!
  # Override the year, month, and day
  filedate = ct_file2date(filename)
  year = [filedate['year']]*len(data.time)
  month = [filedate['month']]*len(data.time)
  day = [filedate['day']]*len(data.time)
  hour= data.time.hour
  minute = data.time.minute
  from pygeode.timeaxis import StandardTime
  taxis = StandardTime(startdate=data.time.startdate, year=year, month=month, day=day, hour=hour, minute=minute, units='days')
  data = data.replace_axes(time=taxis)
  return data

def ct_open (files):
  from pygeode.formats.multifile import open_multi
  from pygeode.formats import netcdf as nc
  from common import fix_timeaxis
  data = open_multi(files=files, opener=ct_opener, file2date=ct_file2date)
  data = fix_timeaxis(data)
  return data

# Method for calculating zonal mean on-the-fly
def ct_zonal (field):
  from pygeode.climat import dailymean
  import numpy as np

  # Interpolate to geopotential height
  from pygeode.interp import interpolate
  from pygeode.axis import Height
  height = Height(range(68))
  ct_ch4 = interpolate(field, inaxis='level', outaxis=height, inx = molefractions.gph/1000)
  ct_ch4 = ct_ch4.nanmean('lon')
  ct_ch4 = ct_ch4.transpose(0,2,1)
  ct_ch4 = dailymean(ct_ch4)

  return ct_ch4

# Similar to above, but use an average of the 22:30 and 1:30 to get
# a 00:00 field
def ct_zonal_24h (field,gph):
  import numpy as np

  # Interpolate to geopotential height
  from pygeode.interp import interpolate
  from pygeode.axis import Height
  height = Height(range(68))
  ct_ch4 = interpolate(field, inaxis='level', outaxis=height, inx = gph/1000)
  ct_ch4 = ct_ch4.nanmean('lon')
  ct_ch4 = ct_ch4.transpose(0,2,1)

  ch4_2230 = ct_ch4(hour=22,minute=30)(i_time = (0,364))

  ch4_0130 = ct_ch4(hour=1, minute=30)(i_time = (1,365))

  # New time axis
  from pygeode.timeaxis import StandardTime
  taxis = ct_ch4.time
  taxis = StandardTime((ch4_2230.time.values+ch4_0130.time.values)/2, startdate=taxis.startdate, units=taxis.units)
  ch4_2230 = ch4_2230.replace_axes(time=taxis)
  ch4_0130 = ch4_0130.replace_axes(time=taxis)

  ct_ch4 = ((ch4_2230 + ch4_0130)/2).rename(ct_ch4.name)

  return ct_ch4


# Define the data interface for CarbonTracker

class CarbonTracker_CH4 (object):

  def __init__ (self, tmpdir=None):

    from cache import Cache

    # Higher-level information about the data
    self.name = 'CTCH42010'
    self.title = 'CarbonTracker'

    cachedir = '/wrk6/eltonc/ct_ch4/molefractions/nc_cache'
    fallback_dirs = [tmpdir] if tmpdir is not None else []
    self.cache = Cache (dir=cachedir, fallback_dirs=fallback_dirs, global_prefix=self.name+'_')

    molefractions = ct_open("/wrk6/eltonc/ct_ch4/molefractions/2009????.nc")
    molefractions = molefractions - 'decimal_date' - 'idate_start' - 'idate_end'

    # Find the total CH4 (sum of components)
    ch4 = molefractions.bgrnd + molefractions.fossil + molefractions.agwaste + molefractions.ocean + molefractions.bioburn + molefractions.natural
    ch4 = ch4.rename('CH4')
    # Pretend it's another CarbonTracker product
    molefractions = molefractions + ch4

    self.molefractions = molefractions

    """
    # Fluxes
    fluxes = ct_open("/wrk1/EC-CAS/CarbonTracker/fluxes/CT2010.flux1x1.????????.nc")
    fluxes = fluxes - 'date_components' - 'decimal_date'

    # Create a total flux product
    co2_flux = fluxes.fossil_imp + fluxes.bio_flux_opt + fluxes.ocn_flux_opt + fluxes.fire_flux_imp
    co2_flux = co2_flux.rename('CO2')
    fluxes = fluxes + co2_flux

    self.fluxes = fluxes
    """

    # Other (more heavily derived) products

    # Surface pressure
    # Get pressure at the bottom mid-level
    pmid = self.molefractions['pressure'].slice[:,0,:,:].squeeze()

    # Compute surface pressure from this
    # p1 = A1 + B1*Ps
    # pmid = (ps + A1 + B1*Ps) / 2 = Ps(1+B1)/2 + (0+A1)/2
    # Ps = (2*pmid - A1)/(1+B1)
    P0 = (2*pmid - A_interface[1])/(B_interface[1]+1)
    P0 = P0.rename('P0')
    self.P0 = P0

  # Translate CarbonTracker variable names into some "standard" naming convention.
  local_names = {
    'CH4':'CH4',
    'air':'air'
  }

  # Data interface
  def get_data (self, domain, standard_name, stat='mean'):

    if stat != 'mean':
      raise KeyError("No '%s' stat available for CarbonTracker"%stat)

    try:
      field = self.local_names[standard_name]
    except KeyError:
      raise KeyError ("No representation of '%s' in the CarbonTracker data."%standard_name)

    # Zonal mean (over geopotential height)
    if domain == 'zonalmean_gph':
      data = self.molefractions[field]
      data = ct_zonal_24h(data,self.molefractions.gph)
      data.atts['units'] = 'ppb'

    # "surface" data (lowest level of molefractions dataset)
    elif domain == 'sfc':
      data = self.molefractions[field](i_lev=0)
      data.atts['units'] = 'ppb'

    # Total column
    elif domain == 'totalcolumn':
      import numpy as np
      from pygeode.var import Var
      from common import molecular_weight as mw, grav as g

      Ps = self.P0

      # Compute sigma at interfaces
      dA = -np.diff(A_interface)
      dA = Var([self.molefractions.level], values=dA)
      dB = -np.diff(B_interface)
      dB = Var([self.molefractions.level], values=dB)
      dsigma = dA / Ps + dB
      dsigma = dsigma.transpose('time', 'level', 'lat', 'lon')

      sigma_top = A_interface[-1]/Ps + B_interface[-1]
      sigma_bottom = 1

      if field == 'air': c = 1
      else:
        # Convert ppb to kg/kg
        conversion = 1E-9 * mw['CH4'] / mw['air']
        c = self.molefractions[field] * conversion

      data = Ps / g * (c*dsigma).sum('level')
      data.name = field

    # Column averages
    elif domain == 'avgcolumn':
      from common import molecular_weight as mw
      tc = self.get_data('totalcolumn', standard_name)
      tc_air = self.get_data('totalcolumn','air')
      data = tc / tc_air
      # Convert kg/kg to ppb
      data *= mw['air']/mw['CH4'] * 1E9

      data.name = field
      data.atts['units'] = 'ppb'

    # Total mass
    elif domain == 'totalmass':
      from common import get_area
      dxdy = get_area(self.molefractions.lat, self.molefractions.lon).rename('dxdy')
      totalcol = self.get_data('totalcolumn', standard_name)
      totalmass = (totalcol*dxdy).sum('lat','lon')
      # Convert from kg to Pg
      totalmass *= 1E-12
      totalmass.name = field
      data = totalmass

    # Integrated fluxes (moles s-1)
    elif domain == 'totalflux':
      from common import get_area
      fluxes_dxdy = get_area (self.fluxes.lat, self.fluxes.lon)
      fluxvar = self.fluxes[field]
      data = (fluxvar*fluxes_dxdy).sum('lat','lon')
      data.name = field
      # The time is the *midpoint* of the flux period.
      # Rewind to the *start* of the flux period (-1.5 hours)
      time = data.time
      assert time.units == 'days'
      time = time.__class__(values=time.values - 0.0625, units='days', startdate=time.startdate)
      data = data.replace_axes(time=time)

    elif domain == 'flux':
      data = self.fluxes[field]
      # The time is the *midpoint* of the flux period.
      # Rewind to the *start* of the flux period (-1.5 hours)
      time = data.time
      assert time.units == 'days'
      time = time.__class__(values=time.values - 0.0625, units='days', startdate=time.startdate)
      data = data.replace_axes(time=time)
      return data   # No caching

    else: raise ValueError ("Unknown domain '%s'"%domain)

    units = data.atts.get('units',None)
    data = self.cache.write(data,prefix='%s_%s'%(domain,field))
    return data
