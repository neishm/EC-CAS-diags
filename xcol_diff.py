# Average column diagnostic with extra panel for differences

# Note: we aren't using any averaging kernal for this, so it's not directly
# comparable to satellite observations.

# Compute total column of a tracer
# (in kg/m2)

from xcol import get_xcol

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

