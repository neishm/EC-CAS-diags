from totalmass import compute_totalmass
from xcol import find_applicable_models

def do_all (datasets, fieldname, units, outdir, **kwargs):
  models = find_applicable_models(datasets, fieldname)
  n = len(models)
  for i in range(n):
    for j in range(i+1,n):
      totalmass_diff([models[i],models[j]], fieldname, units, outdir, **kwargs)


def totalmass_diff (models, fieldname, units, outdir, normalize_air_mass=False):
  from os.path import exists
  from common import convert, same_times
  from matplotlib import pyplot as pl
  from pygeode.plot import plotvar

  models = [m for m in models if m is not None]
  if len(models) != 2:
    raise ValueError ("Expected 2 datasets")

  fields = [compute_totalmass(m,fieldname) for m in models]

  # Unit conversion
  fields = [convert(f,units) for f in fields]

  # Use only the common timesteps between the fields
  fields = same_times (*fields)
  diff = fields[0]-fields[1]

  # Get model air mass, if we are normalizing the tracer mass.
  if normalize_air_mass:
    airmass = compute_totalmass(models[0],'air')
    diff, airmass = same_times(diff,airmass)
    airmass0 = float(airmass[0])
    diff = diff / airmass * airmass0

  diff.name=fieldname+'_diff'

  outfile = outdir + "/%s_totalmass_diff_%s%s.png"%('_'.join(m.name for m in models if m is not None),fieldname,'_normalized' if normalize_air_mass else '')
  if not exists(outfile):
    fig = pl.figure(figsize=(15,12))
    ax = pl.subplot(111)
    plotvar (diff, ax=ax)
    ax.set_title("%s total mass difference (%s-%s)"%(fieldname,models[0].name,models[1].name))
    fig.savefig(outfile)

