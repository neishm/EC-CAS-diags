
# A movie interface.
# Handles the logistics of looping over each frame, saving image files, and
# collecting the images into a movie.
# To use this class, create a sub-class and define an appropriate 'render'
# method.
class Movie(object):
  def __init__ (self, fields, figsize=None):
    self.fields = fields
    # Determine the range of values for each field being rendered
    # (range is over the whole time period).
    # This information is useful for setting up consistent axis ranges for each
    # frame being rendered.
    self.ranges = [(field.atts['low'],field.atts['high']) for field in fields]
    # Also, determine a global range for each kind of field
    # (useful if you're comparing similar data in side-by-side panels).
    self.global_range = {}
    for field,(low,high) in zip(fields,self.ranges):
      if field.name not in self.global_range:
        self.global_range[field.name] = (low,high)
      else:
        low1, high1 = self.global_range[field.name]
        self.global_range[field.name] = (min(low1,low),max(high1,high))
    self.figsize = figsize

  # Save the movie.
  def save (self, outdir, prefix):
    import matplotlib.pyplot as pl
    from os.path import exists
    from os import makedirs
    from pygeode.progress import PBar

    # Find a common time range
    # NOTE: assuming all time axes have the same reference date
    start = max(f.time[0] for f in self.fields if f.hasaxis('time'))
    end = min(f.time[-1] for f in self.fields if f.hasaxis('time'))

    if start > end:
      raise ValueError ("No common time period for %s"%prefix)

    fig = pl.figure(figsize=self.figsize)

    imagedir = outdir + "/images_%s"%prefix
    if not exists(imagedir): makedirs(imagedir)

    # Use the first field to define the frames
    taxis = self.fields[0].time(time=(start,end))
    pbar = PBar()
    print "Saving %s images"%prefix
    for i,t in enumerate(taxis):

      # Sample the fields at the current time
      fields = [f(time=t) for f in self.fields]

      year = fields[0].time.year[0]
      month = fields[0].time.month[0]
      day = fields[0].time.day[0]
      hour = fields[0].time.hour[0]
      minute = fields[0].time.minute[0]
      outfile = imagedir + "/%04d%02d%02d%02d%02d.png"%(year,month,day,hour,minute)

#      datestring = taxis.formatvalue(t, fmt="$Y-$m-$d ${H}:${M}")
      datestring = "%04d-%02d-%02d %02d:%02d"%(year,month,day,hour,minute)

      if not exists(outfile):
        fig.clear()
        self.render (fig, fields, datestring)
        fig.savefig(outfile)

      pbar.update(i*100./len(taxis))

    pbar.update(100)

    # Generate the movie
    moviefile = "%s/%s.avi"%(outdir,prefix)
    from os import system
    if not exists(moviefile):
      system("mencoder -o %s mf://%s/*.png -ovc lavc -lavcopts vcodec=msmpeg4v2"%(moviefile, imagedir))

  # Render the given field snapshots into the figure, producing one frame of
  # the movie.
  # NOTE: This method is a stub.  It needs to be implemented in a sub-class
  # with the appropriate plotting routines.
  def render (self, fig, fields, datestring):
    raise NotImplementedError


# A movie with tiled subplots.
# There will be a different subtitle for each panel.
class TiledMovie(Movie):
  def __init__ (self, fields, title, subtitles, shape, aspect_ratio, **kwargs):
    assert len(subtitles) == len(fields)
    # Check that we have a proper shape
    assert reduce(int.__mul__,shape,1) == len(fields)

    # Determine the best figure size
    max_width = 10.
    max_height = 10.
    figure_aspect_ratio = shape[0]*float(aspect_ratio) / shape[1]
    if figure_aspect_ratio * max_width <= max_height:
      width = max_width
      height = figure_aspect_ratio * max_width
    else:
      width = max_height / figure_aspect_ratio
      height = max_height

    Movie.__init__(self, fields, figsize=(width,height), **kwargs)
    self.title = title
    self.subtitles = subtitles
    self.shape = tuple(shape)
    self.width = width
    self.height = height

  def render (self, fig, fields, datestring):
    # Need to allocate space at the top for the title
    title_size = 20
    # Assume we need about 2.5 times the font height
    fig.subplots_adjust (top = 1-2.5*title_size/72./self.height)

    for k,field in enumerate(fields):
      shape = self.shape+(k+1,)
      ax = fig.add_subplot(*shape)
      self.render_panel (ax, field, k)
    fig.suptitle(self.title+'  -  '+datestring, fontsize=title_size)

  # Implement this method for each subclass.
  def render_panel (self, axis, field, n):
    raise NotImplementedError


# A movie with filled contour plots.
class ContourMovie(TiledMovie):
  def __init__ (self, *args, **kwargs):
    from contouring import get_contours
    TiledMovie.__init__(self, *args, **kwargs)
    # Determine the best contour intervals to use for the plots.
    self.clevs = {}
    for name, (low,high) in self.global_range.iteritems():
      self.clevs[name] = get_contours(low, high)

  def render_panel (self, axis, field, n):
    from pygeode.plot import plotvar
    clevs = self.clevs[field.name]
    plotvar (field, ax=axis, clevs=clevs, title=self.subtitles[n])

