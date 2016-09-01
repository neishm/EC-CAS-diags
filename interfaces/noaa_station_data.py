# NOAA station data

from . import StationObsProduct
class NOAA_Station_Data(StationObsProduct):
  """
  Greenhouse gas measurments from NOAA.
  """

  # Define all the possible variables we might have in this dataset.
  # (original_name, standard_name, units)
  field_list = (
    ('CO', 'CO', 'ppb'),
  )

  # Method to open a single file
  @staticmethod
  def open_file (filename):
    from pygeode.var import Var
    from pygeode.timeaxis import StandardTime
    from pygeode.dataset import Dataset
    from ..station_data import Station
    import numpy as np

    try:
      data = np.genfromtxt(filename,dtype=None,names="sample_site_code sample_year sample_month sample_day sample_hour sample_minute sample_seconds sample_id sample_method parameter_formula analysis_group_abbr analysis_value analysis_uncertainty analysis_flag analysis_instrument analysis_year analysis_month analysis_day analysis_hour analysis_minute analysis_seconds sample_latitude sample_longitude sample_altitude event_number".split())
      station_name = data['sample_site_code'][0]
      year = data['sample_year']
      month = data['sample_month']
      day = data['sample_day']
      hour = data['sample_hour']
      fieldname = data['parameter_formula'][0].upper()
      values = data['analysis_value']
      values[values<0] = float('nan')
      uncertainty = data['analysis_uncertainty']
      uncertainty[uncertainty<0] = float('nan')
      lat = data['sample_latitude'][0]
      lon = data['sample_longitude'][0]
      altitude = data['sample_altitude'][0]

    except (ValueError,AttributeError) as e:
      print 'skipping %s - bad formatting'%filename
      print 'message:', e.message
      return Dataset([])

    # Define the time axis.  Use a consistent start date, so the various
    # station records can be more easily compared.
    time = StandardTime(year=year, month=month, day=day, hour=hour, units='hours', startdate={'year':1980,'month':1,'day':1})
    # Define the station axis.
    station = Station([station_name], lat=[lat], lon=[lon], altitude=[altitude])

    # Wrap in PyGeode Vars
    values = Var([time,station], values=np.asarray(values).reshape(-1,1), name=fieldname)
    uncertainty = Var([time,station], values=np.asarray(uncertainty).reshape(-1,1), name=fieldname+'_uncertainty')

    return Dataset([values,uncertainty])


  # Method to find all files in the given directory, which can be accessed
  # through this interface.
  @staticmethod
  def find_files (dirname):
    from glob import glob
    return glob(dirname+'/surface/*_event.txt')

  # Method to find a unique identifying string for this dataset, from the
  # given directory name.
  @staticmethod
  def get_dataname (dirname):
    import os
    for d in reversed(dirname.split(os.sep)):
      if d in ('','surface'):
        continue
      return d


# Add this interface to the table.
from . import table
table['noaa-station-obs'] = NOAA_Station_Data

