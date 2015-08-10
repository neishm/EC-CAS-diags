# Average column diagnostic with extra panel for differences

# Note: we aren't using any averaging kernal for this, so it's not directly
# comparable to satellite observations.

# Compute total column of a tracer
# (in kg/m2)

from xcol import get_xcol
from movie_zonal_diff import get_lats

def get_lons (model):
  if len(model.data.datasets) == 0:
    raise ValueError("No data in %s"%model.name)
  lons = set(tuple(v.lon.values) for d in model.data.datasets for v in d if v.hasaxis('lon'))
  if len(lons) == 0: raise ValueError("No gridded data in %s"%model.name)
  if len(lons) > 1: raise ValueError("Multiple grids found in %s"%model.name)
  return lons.pop()

from xcol import find_applicable_models

def do_all (datasets, fieldname, units, outdir, **kwargs):
  models = find_applicable_models(datasets, fieldname)
  n = len(models)
  for i in range(n):
    for j in range(i+1,n):
      if get_lats(models[i]) == get_lats(models[j]) and get_lons(models[i]) == get_lons(models[j]):
        xcol_diff([models[i],models[j]], fieldname, units, outdir, **kwargs)


def xcol_diff (models, fieldname, units, outdir):
  from movie import ContourMovie
  from common import same_times

  plotname = 'X'+fieldname
  models = [m for m in models if m is not None]
  prefix = '_'.join(m.name for m in models) + '_diff_' + plotname

  fields = [get_xcol(m,fieldname,units) for m in models]
  subtitles = [m.title for m in models]
  title = '%s (in %s)'%(plotname,units)

  aspect_ratio = 0.4  # height / width for each panel

  shape = (len(fields)+1,1)
 
  # Use only the common timesteps between the fields
  fields = same_times (*fields)

  # Plot a difference field as well.
  if fields[0].axes != fields[1].axes:
    raise ValueError ("The axes of the fields are not identical")
  diff = fields[0]-fields[1]
  diff.name=fieldname+'_diff'
  # Cache the difference (so we get a global high/low for the colourbar)
  diff = models[0].cache.write(diff, prefix='xcol_diff_'+models[1].name+'_'+fieldname)
  fields.append(diff)
  subtitles.append('difference')

  movie = ContourMovie(fields, title=title, subtitles=subtitles, shape=shape, aspect_ratio = aspect_ratio)

  movie.save (outdir=outdir, prefix=prefix)

