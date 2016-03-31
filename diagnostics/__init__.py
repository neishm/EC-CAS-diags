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
    group.add_argument('--start-date', action='store', help="Specify a start date for the diagnostics.  Format: %s."%date_format)
    group.add_argument('--end-date', action='store', help="Specify an end date for the diagnostics.  Format: %s."%date_format)
    group.add_argument('--year', action='store', type=int, help="Limit the diagnostics to a particular year.")
    group.add_argument('--hour0-only', action='store_true', help="Sample the data once per day, to speed up the diagnostics (useful when sub-daily scales don't matter anyway).")
    handled.append(True)
  def __init__(self,start_date=None,end_date=None,year=None,**kwargs):
    from datetime import datetime, timedelta
    super(TimeVaryingDiagnostic,self).__init__(**kwargs)
    # Parse start and end dates
    start = start_date
    if start is not None:
      start = datetime.strptime(start, self.date_format)
    end = end_date
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
  # Limit the time range for the data.
  def filter_inputs(self, models):
    from ..interfaces import DerivedProduct
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
        out_datasets.append(d)
      m = DerivedProduct(out_datasets, source=m)
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


