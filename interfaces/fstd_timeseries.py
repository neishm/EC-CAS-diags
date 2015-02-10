# Generic interface for FSTD timeseries files.

from interfaces import ModelData

class FSTD_Timeseries(ModelData):

  # Method to open a single file
  @staticmethod
  def open_file (filename):
    from pygeode.formats import fstd, fstd_core
    from station_data import Station
    from pygeode.dataset import Dataset
    # Read the raw records from the fstd file (no decoding done yet)
    raw = fstd_core.read_records(filename)
    nomvar = raw['nomvar']
    # Get forecast times
    forecast = fstd.Forecast(raw[nomvar=='HH  ']['data_func'][0]().flatten())
    # Get station locations
    station_names = raw[nomvar=='STNS']['data_func'][0]().squeeze()
    station_names = map(''.join, station_names)
    station_names = map(str.rstrip, station_names)
    station_lats = raw[nomvar=='^^  ']['data_func'][0]().flatten()
    station_lons = raw[nomvar=='>>  ']['data_func'][0]().flatten()
    station = Station(station_names, lat=station_lats, lon=station_lons)
    # Get vertical levels
    # NOTE: assuming thermodynamic levels - will not work for things defined
    # on momentum levels!
    fstd.LogHybrid.plotatts['plotscale']='log'
    fstd.LogHybrid.plotatts['plotorder']=-1
    zeta = raw[nomvar=='SH  ']['data_func'][0]().flatten()
    vcoord_table = fstd_core.decode_loghybrid_table(raw[nomvar=='!!  ']['data_func'][0]())
    # Remove extra level at top of model (not saved in profiles), and extra
    # level at bottom for A/B (diagnostic level, not saved in profiles).
    zeta = fstd.LogHybrid(zeta[1:], A=vcoord_table['a_t'][1:-1], B=vcoord_table['b_t'][1:-1], atts=vcoord_table)
    # Hack the ip3 (station) value into ip1, so we can let FSTD_Var concatenate
    # records together.  Don't try this at home!
    raw['ip1'] = raw['ip3']

    # Find all timeseries data, and group by variable name.
    data_record = (raw['grtyp'] == '+')
    data = []
    for data_nomvar in set(raw[data_record]['nomvar']):
      # Get an initial array of data
      var = fstd.FSTD_Var(raw[(nomvar==data_nomvar)*data_record])
      # Force the 'j' axis to be the forecast axis.
      # Force the hacked 'ip1' axis to be the station axis.
      # Force the 'i' axis to be the vertical axis.
      if len(var.i) == 1:
        var = var.squeeze('forecast','i','k')
        var = var.replace_axes(j=forecast,ip1=station)
        var = var.transpose('time','forecast','station')
      else:
        var = var.squeeze('forecast','k')
        var = var.replace_axes(j=forecast,ip1=station,i=zeta)
        var = var.transpose('time','forecast','station','zeta')
      data.append(var)

    return Dataset(data)

