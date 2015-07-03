def movie_zonal_diff (models, fieldname, units, outdir, zaxis='gph'):

  from common import convert, same_times
  from movie_zonal import zonalmean_gph, zonalmean_pres, ZonalMovie

  models = [m for m in models if m is not None]
  prefix = '_'.join(m.name for m in models) + '_zonal_diff'+fieldname+'_on_'+zaxis
  title = 'Zonal mean %s (in %s)'%(fieldname,units)
  aspect_ratio = 1.0
  shape = (1,len(models)+1)

  if zaxis == 'gph':
    fields = [zonalmean_gph(m,fieldname,units) for m in models]
  else:
    fields = [zonalmean_pres(m,fieldname,units) for m in models]

  # Unit conversion
  fields = [convert(f,units) for f in fields]

  subtitles = [m.title for m in models]

  # Use only the common timesteps between the fields
  fields = same_times (*fields)

  # Plot a difference field as well.
  if fields[0].axes != fields[1].axes:
    raise ValueError ("The axes of the fields are not identical")
  diff = fields[0]-fields[1]
  diff.name=fieldname+'_diff'
  # Cache the difference (so we get a global high/low for the colourbar)
  diff = models[0].cache.write(diff, prefix='zonalmean_gph_diff_'+models[1].name+'_'+fieldname)
  fields.append(diff)
  subtitles.append('difference')

  movie = ZonalMovie(fields, title=title, subtitles=subtitles, shape=shape, aspect_ratio=aspect_ratio)

  movie.save (outdir=outdir, prefix=prefix)

