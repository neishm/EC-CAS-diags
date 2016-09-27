
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

    # Early exit if the final movie file already exists.
    moviefile = "%s/%s.avi"%(outdir,prefix)
    if exists(moviefile): return

    # Find a common time range
    # NOTE: assuming all time axes have the same reference date
    start = max(f.time[0] for f in self.fields if f.hasaxis('time'))
    end = min(f.time[-1] for f in self.fields if f.hasaxis('time'))

    if start > end:
      raise ValueError ("No common time period for %s"%prefix)

    imagedir = outdir + "/images_%s"%prefix
    if not exists(imagedir): makedirs(imagedir)

    # Use the first field to define the frames
    taxis = self.fields[0].time(time=(start,end))
    pbar = PBar()
    print "Saving %s images"%prefix
    for i,t in enumerate(taxis):

      fig = pl.figure(figsize=self.figsize)

      # Sample the fields at the current time
      fields = [f(time=t) for f in self.fields]

      outfile = imagedir + "/"
      datestring = ""
      #TODO: more comprehensive function for mapping different combinations
      # of year/month/day/hour/minute to filename strings and title strings.
      year = getattr(fields[0].time,'year',[None])[0]
      if year is not None:
        outfile += "%04d"%year
        datestring = "%04d"%year
      month = getattr(fields[0].time,'month',[None])[0]
      if month is not None:
        outfile += "%02d"%month
        if datestring != "": datestring += "-"
        datestring += "%02d"%month
      day = getattr(fields[0].time,'day',[None])[0]
      if day is not None:
        outfile += "%02d"%day
        if datestring != "": datestring += "-"
        datestring += "%02d"%day
      hour = getattr(fields[0].time,'hour',[None])[0]
      if hour is not None:
        outfile += "%02d"%hour
        if datestring != "": datestring += " "
        datestring += "%02d"%hour
      minute = getattr(fields[0].time,'minute',[None])[0]
      if minute is not None:
        # If the minutes are all '0', then don't use minutes in the filenames.
        # Allows backwards compatibility with previous version of the diagnostics.
        # Otherwise, need to include minute information to distinguish each
        # timestep.
        if list(set(taxis.minute)) != [0]:
          outfile += "%02d"%minute
        if datestring != "": datestring += ":"
        datestring += "%02d"%minute

      outfile += ".png"

      if not exists(outfile):
        self.render (fig, fields, datestring)
        fig.savefig(outfile)

      pl.close()

      pbar.update(i*100./len(taxis))

    pbar.update(100)

    # Generate the movie
    from os import system
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
    from .contouring import get_contours
    from matplotlib.pyplot import cm
    # Get the colormaps for the contour plots
    cmaps = kwargs.pop('cmaps')
    cmaps = [cm.get_cmap(c) for c in cmaps]
    self.cmaps = cmaps
    # Check whether to cap the colours to stay in the range
    self.cap_extremes = kwargs.pop('cap_extremes',[False]*len(cmaps))
    # Send the rest of the arguments to the parent class init.
    TiledMovie.__init__(self, *args, **kwargs)
    # Determine the best contour intervals to use for the plots.
    self.clevs = {}
    for name, (low,high) in self.global_range.iteritems():
      self.clevs[name] = get_contours(low, high)

  def render_panel (self, axis, field, n):
    from pygeode.plot import plotvar
    clevs = self.clevs[field.name]
    # Cap extreme values, so they don't go off the colour scale?
    if self.cap_extremes[n] is True:
      plotvar (field, ax=axis, clevs=clevs, title=self.subtitles[n], cmap=self.cmaps[n], extend='both')
    else:
      plotvar (field, ax=axis, clevs=clevs, title=self.subtitles[n], cmap=self.cmaps[n])

class ZonalMovie (ContourMovie):
  # Modify the panel rendering to show the y-axis on the first panel,
  # and override the latitude labels
  def render_panel (self, axis, field, n):
    from .movie import ContourMovie
    ContourMovie.render_panel (self, axis, field, n)
    if n == 0:
      axis.set_ylabel(field.zaxis.name)
    else:
      axis.set_ylabel('')
    if self.shape[1] >= 3:
      axis.set_xticks([-90,-60,-30,0,30,60,90])
      axis.set_xticklabels(['90S','','','EQ','','','90N'])

