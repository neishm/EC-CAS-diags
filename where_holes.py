def where_holes (outdir):
  from interfaces import experiment, experiment_name
  from common import convert_CO2
  from pygeode.formats import netcdf
  from os.path import exists

  co2 = experiment['sfc']['CO2'] * convert_CO2

  holes = (co2 < 100)

  count = (holes * 1).sum('time')
  count.name = "hole_count"

  outfile = outdir+"/%s_hole_count.nc"%experiment_name
  if not exists(outfile):
    netcdf.save(outfile, count)

if __name__ == '__main__':
  from interfaces import experiment_name
  outdir = experiment_name
  where_holes (outdir=outdir)
