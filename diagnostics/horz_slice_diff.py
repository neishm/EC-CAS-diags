# Horizontal slice movie.
# Takes a field at the given level from 2 experiments, computes a difference,
# and produces a movie.
# This is/was used for checking the effects of adding convection to tracers.

from .xcol import find_applicable_models


from . import Diagnostic
class HorzSliceDiff(Diagnostic):
  """
  Difference between two data products, sampled at a particular vertical level.
  """
  def do_all (self, datasets, fieldname, units, outdir, **kwargs):
    models = find_applicable_models(datasets, fieldname)
    n = len(models)
    for i in range(n):
      if not models[i].have(fieldname): continue
      for j in range(i+1,n):
        if not models[j].have(fieldname): continue
        f1 = models[i].find_best(fieldname)
        f2 = models[j].find_best(fieldname)
        if f1.lat == f2.lat and f1.lon == f2.lon:
          horz_slice_movie([models[i],models[j]], fieldname, units, outdir, **kwargs)


if True:


  # Cache the slice for faster reading on subsequent diagnostic calls.
  def horz_slice (model, fieldname, level):
    from ..common import number_of_levels, number_of_timesteps

    c = model.find_best(fieldname, maximize=(number_of_levels,number_of_timesteps))

    # Apply the slice
    c = c(zaxis=float(level))

    # Cache the data
    return model.cache.write(c,prefix=model.name+'_'+c.zaxis.name+level+"_"+fieldname)


  # Get the horizontal slice (and prep it for plotting)
  def get_horz_slice (experiment, fieldname, level, units):
    from ..common import rotate_grid, convert

    data = horz_slice(experiment, fieldname, level)

    # Rotate the longitudes to 0,360
    data = rotate_grid(data)

    # Convert to the required units
    data = convert(data,units)

    return data


  def horz_slice_movie (models, fieldname, units, outdir, level):
    from .movie import ContourMovie
    from ..common import same_times

    plotname = fieldname+"_level"+level
    prefix = '_'.join(m.name for m in models) + '_' + plotname

    fields = [get_horz_slice(m,fieldname,level,units) for m in models]
    subtitles = [m.title for m in models]
    title = '%s at level %s'%(fieldname,level)

    aspect_ratio = 0.4  # height / width for each panel

    shape = (len(models)+1,1)

    # Use only the common timesteps between the fields
    fields = same_times (*fields)

    # Plot a difference field as well.
    if fields[0].axes != fields[1].axes:
      raise ValueError ("The axes of the fields are not identical")
    diff = fields[0]-fields[1]
    diff.name=fieldname+'_diff'
    # Cache the difference (so we get a global high/low for the colourbar)
    diff = models[0].cache.write(diff, prefix=models[0].name+'_'+fieldname+'_level'+level+"_diff_"+models[1].name+'_'+fieldname)
    fields.append(diff)
    subtitles.append('difference')
    movie = ContourMovie(fields, title=title, subtitles=subtitles, shape=shape, aspect_ratio = aspect_ratio)

    movie.save (outdir=outdir, prefix=prefix)


from . import table
table['horz-slice-diff'] = HorzSliceDiff

