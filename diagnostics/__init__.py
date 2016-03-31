# Generic interface for a diagnostic, to be sub-classed by each particular
# diagnostic.
class Diagnostic(object):
  @staticmethod
  # Method to add extra command-line arguments needed for this diagnostic.
  def add_args (parser):
    return  # Nothing needed by default.

  # Attach the command-line arguments to this object for later use.
  def __init__ (self, **kwargs):
    return  # Don't need any further arguments at this level of abstraction.

  # Filter all input datasets to satisfy any conditions set for this diagnostic.
  def filter_inputs (self, inputs):
    return inputs  # Nothing to filter at this level of abstraction.

  # Suffix to append to any output files
  suffix = ""

# Diagnostics that deal with static figures (no movies).
class ImageDiagnostic(Diagnostic):
  # Control image format through command-line parameter
  @staticmethod
  def add_args (parser, handled=[]):
    super(ImageDiagnostic,ImageDiagnostic).add_args(parser)
    if len(handled) > 0: return  # Only run once
    parser.add_argument('--image-format', action='store', choices=('png','eps','svg','ps','pdf'), default='png', help="Specify the format of output images.  Default is png.")
    handled.append(True)
  def __init__ (self,image_format='png',**kwargs):
    super(ImageDiagnostic,self).__init__(**kwargs)
    self.image_format = image_format

# Diagnostics that deal with a time range (pretty much all of them!)
class TimeVaryingDiagnostic(Diagnostic):
  date_format = '%Y/%m/%d'
  # Select the time range though command-line parameters.
  @classmethod
  def add_args (cls, parser, handled=[]):
    from datetime import datetime
    super(TimeVaryingDiagnostic,cls).add_args(parser)
    if len(handled) > 0: return  # Only run once
    group = parser.add_argument_group('options for specifying the date range')
    date_format = datetime(year=1987,month=11,day=22).strftime(cls.date_format).replace('1987','yyyy').replace('87','yy').replace('11','mm').replace('22','dd')
    group.add_argument('--start', action='store', metavar=date_format.upper(), help="Specify a start date for the diagnostics.")
    group.add_argument('--end', action='store', metavar=date_format.upper(), help="Specify an end date for the diagnostics.")
    group.add_argument('--year', action='store', type=int, help="Limit the diagnostics to a particular year.")
    group.add_argument('--hour0-only', action='store_true', help="Sample the data once per day, to speed up the diagnostics (useful when sub-daily scales don't matter anyway).")
    handled.append(True)
  def __init__(self,hour0_only,start=None,end=None,year=None,**kwargs):
    from datetime import datetime, timedelta
    super(TimeVaryingDiagnostic,self).__init__(**kwargs)
    # Parse start and end dates
    if start is not None:
      start = datetime.strptime(start, self.date_format)
    if end is not None:
      end = datetime.strptime(end, self.date_format)
    # Apply year filter
    if year is not None:
      if start is not None:
        start = start.replace(year=year)
      else:
        start = datetime(year=year,month=1,day=1)
      if end is not None:
        end = end.replace(year=year)
      else:
        end = datetime(year=year+1,month=1,day=1) - timedelta(days=1)
    self.date_range = (start,end)
    suffix = ""
    if start is not None:
      suffix = suffix + "_" + start.strftime("%Y%m%d-")
    if end is not None:
      if len(suffix) == 0: suffix = suffix + "_-"
      suffix = suffix + end.strftime("%Y%m%d")
    self.hour0_only = hour0_only
    if hour0_only is True:
      suffix = suffix + "_hour0-only"
    self.suffix = self.suffix + suffix

  # Limit the time range for the data.
  def filter_inputs(self, models):
    from ..interfaces import DerivedProduct
    from pygeode.timeutils import reltime
    from math import floor
    models = super(TimeVaryingDiagnostic,self).filter_inputs(models)
    date_range = self.date_range
    out_models = []
    for m in models:
      out_datasets = []
      for d in m.datasets:
        start = date_range[0]
        if start is None:
          start = d.time.values[0]
        else:
          start = d.time.str_as_val(key=None,s=start.strftime("%d %b %Y"))
        end = date_range[1]
        if end is None:
          end = d.time.values[-1]
        else:
          end = d.time.str_as_val(key=None,s=end.strftime("%d %b %Y"))
        d = d(time=(start,end))
        if self.hour0_only is True:
          hour_float = min(set(reltime(d.time,units='hours')%24))
          hour = int(floor(hour_float))
          minute = int((hour_float-hour)*60)
          d = d(hour=hour,minute=minute)
        out_datasets.append(d)
      m = DerivedProduct(out_datasets, source=m)
      # if we select hour-0 data, then modify the canonical name of the data.
      # We don't want to collide with the unfiltered (all-hours) cache file,
      # so this uniquifies the cache filename.
      if self.hour0_only is True: m.name = m.name + '_hour0-only'
      out_models.append(m)
    return out_models
# Find all available diagnostics
table = {}
def _load_diagnostics ():
  import pkgutil
  import importlib
  for loader, name, ispkg in pkgutil.walk_packages(__path__):
    if ispkg: continue
    importlib.import_module(__name__+'.'+name)
_load_diagnostics()  # Allow the diagnostics to add their entries to this table


