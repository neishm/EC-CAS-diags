# Generic interface for a diagnostic, to be sub-classed by each particular
# diagnostic.
class Diagnostic(object):
  @staticmethod
  # Method to add extra command-line arguments needed for this diagnostic.
  def add_args (parser):
    return  # Nothing needed by default.

  # Attach the command-line arguments to this object for later use.
  def __init__ (self, fieldname, units, outdir, **kwargs):
    self.fieldname = fieldname
    self.units = units
    self.outdir = outdir

  # Check preconditions for using some particular data.
  # Given a dataset, determine if we can use the data.
  def _check_dataset(self, dataset):
    # Check if we have the field required.
    return self.fieldname in dataset

  # Pre-select inputs that satisfy certain conditions.
  def _select_inputs (self, inputs):
    from ..interfaces import DerivedProduct
    selected = []
    for i in inputs:
      datasets = filter(self._check_dataset,i.datasets)
      if len(datasets) == 0: continue  # No matches for this product?
      if list(datasets) == list(i.datasets):
        selected.append(i)
      else:
        selected.append(DerivedProduct(datasets,source=i))
    return selected

  # Split the data into batches to be fed into the diagnostic.
  def _input_combos (self, inputs):
    yield inputs  # By default, use all the inputs at the same time.

  # Transform the data into a form needed by the diagnostic.
  def _transform_inputs (self, inputs):
    return inputs  # Nothing to transform at this level of abstraction.

  # Apply the diagnostic to all valid input combos.
  def do_all (self, inputs):
    inputs = self._select_inputs(inputs)
    for current_inputs in self._input_combos(inputs):
      current_inputs = self._transform_inputs(current_inputs)
      if len(current_inputs) == 0: continue
      self.do(current_inputs)

  # The actual diagnostic to run.
  # Needs to be implemented for each diagnostic class.
  def do (self, inputs):
    raise NotImplementedError

  # Suffix to append to any output files
  suffix = ""

# Diagnostics that deal with static figures (no movies).
# Provides command-line arguments for controlling image output.
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

# Diagnostics that deal with a time range (pretty much all of them!).
# Provides command-line arguments for pre-filtering the time range & frequency
# of the inputs.
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

  def _check_dataset (self, dataset):
    if not super(TimeVaryingDiagnostic,self)._check_dataset(dataset):
      return False
    # Select data products that have a time axis
    return 'time' in dataset


  # Limit the time range for the data.
  def _transform_inputs (self, models):
    from ..interfaces import DerivedProduct
    from pygeode.timeutils import reltime
    from math import floor
    models = super(TimeVaryingDiagnostic,self)._transform_inputs(models)
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


