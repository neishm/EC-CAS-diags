###############################################################################
# Copyright 2016 - Climate Research Division
#                  Environment and Climate Change Canada
#
# This file is part of the "EC-CAS diags" package.
#
# "EC-CAS diags" is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# "EC-CAS diags" is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with "EC-CAS diags".  If not, see <http://www.gnu.org/licenses/>.
###############################################################################


# Generic interface for a diagnostic, to be sub-classed by each particular
# diagnostic.
class Diagnostic(object):

  # String representation of the diagnostic (for filenames, etc.)
  # Note: doesn't include fieldname or particular inputs.
  def __str__(self):
    # Default is the name of the class itself.
    return self.__class__.__name__.lower()

  @classmethod
  # Method to add extra command-line arguments needed for this diagnostic.
  def add_args (cls, parser):
    return  # Nothing needed by default.

  # Attach the command-line arguments to this object for later use.
  def __init__ (self, fieldname, units, outdir, **kwargs):
    self.fieldname = fieldname
    # Override this if you want to allow alternate fieldnames besides the
    # given one (e.g. can derive a 'CO2' mass field from 'CO2_flux').
    self.require_fieldname = True
    self.units = units
    self.outdir = outdir

  # Check preconditions for using some particular data.
  # Given a dataset, determine if we can use the data.
  def _check_dataset(self, dataset):
    if not self.require_fieldname: return True
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

  # Apply a transformation to an individual input.
  def _transform_input (self, input):
    return input  # By default, nothing to transform.

  # Split the data into batches to be fed into the diagnostic.
  def _input_combos (self, inputs):
    yield inputs  # By default, use all the inputs at the same time.

  # Further transformations across a series of input combos.
  def _transform_inputs (self, inputs):
    return inputs  # Nothing to transform at this level of abstraction.

  # Apply the diagnostic to all valid input combos.
  def do_all (self, inputs):
    inputs = self._select_inputs(inputs)
    inputs = map(self._transform_input,inputs)
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

  # Additional suffix to append to summary files (e.g. movies, plots).
  end_suffix = ""

# Diagnostics that deal with static figures (no movies).
# Provides command-line arguments for controlling image output.
class ImageDiagnostic(Diagnostic):
  # Control image format through command-line parameter
  @classmethod
  def add_args (cls, parser, handled=[]):
    super(ImageDiagnostic,cls).add_args(parser)
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
  def __init__(self,hour0_only=False,start=None,end=None,year=None,**kwargs):
    from datetime import datetime, timedelta
    super(TimeVaryingDiagnostic,self).__init__(**kwargs)
    # Parse start and end dates
    if start is not None:
      start = datetime.strptime(start, self.date_format)
    if end is not None:
      end = datetime.strptime(end, self.date_format)
    # Apply year filter
    if year is not None:
      start = datetime(year=year,month=1,day=1)
      end = datetime(year=year+1,month=1,day=1) - timedelta(days=1)
    self.date_range = (start,end)
    self.hour0_only = hour0_only
    end_suffix = []
    datestr = ''
    if start is not None:
      datestr += start.strftime("%Y%m%d")
    datestr += '-'
    if end is not None:
      datestr += end.strftime("%Y%m%d")
    if datestr != '-':
      end_suffix.append(datestr)
    if hour0_only is True:
      end_suffix.append("hour0-only")
    if len(end_suffix) > 0:
      self.end_suffix += '_' + '_'.join(end_suffix)

  def _check_dataset (self, dataset):
    if not super(TimeVaryingDiagnostic,self)._check_dataset(dataset):
      return False
    # Select data products that have a time axis
    return 'time' in dataset


  # Limit the time range for the data.
  def _transform_input (self, model):
    from ..interfaces import DerivedProduct
    from ..common import fix_timeaxis
    from pygeode.timeutils import reltime
    from math import floor
    model = super(TimeVaryingDiagnostic,self)._transform_input(model)
    # Don't need to do anything if no time modifiers are used.
    if self.date_range == (None,None) and self.hour0_only is False:
      return model
    date_range = self.date_range

    out_datasets = []
    for d in model.datasets:
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
        hours = set(reltime(d.time,units='hours')%24)
        # Ignore empty datasets (e.g. datasets that don't fall in the
        # above start & end dates).
        # Also, ignore datasets where the hours don't fall on regular intervals.
        if len(hours) > 0 and len(hours) < len(d.time):
          hour_float = min(hours)
          hour = int(floor(hour_float))
          minute = int((hour_float-hour)*60)
          d = d(hour=hour,minute=minute)
      # Use the same start date & units for all time axes.
      d = fix_timeaxis(d)
      out_datasets.append(d)
    model = DerivedProduct(out_datasets, source=model)

    return model

# Find all available diagnostics
table = {}
def _load_diagnostics ():
  import pkgutil
  import importlib
  for loader, name, ispkg in pkgutil.walk_packages(__path__):
    if ispkg: continue
    importlib.import_module(__name__+'.'+name)
_load_diagnostics()  # Allow the diagnostics to add their entries to this table


