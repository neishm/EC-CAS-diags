def where_holes (experiment, experiment_name, outdir, **unused_args):
  from common import convert_CO2
  from pygeode.formats import netcdf
  from os.path import exists

  co2 = experiment['dm_sfc']['CO2'] * convert_CO2

  holes = (co2 < 100)

  count = (holes * 1).sum('time')
  count.name = "hole_count"

  outfile = outdir+"/%s_hole_count.nc"%experiment_name
  if not exists(outfile):
    netcdf.save(outfile, count)

