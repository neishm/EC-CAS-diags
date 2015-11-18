# Interface for CT2013B molefraction data.
# Pretty much the same thing, except some preprocessing for
# pressure at the boundaries to get dp.

from .carbontracker import CT_Data
class CT2013B_Data(CT_Data):


  # Method to open a single file
  @staticmethod
  def open_file (filename):
    from pygeode.formats.netcdf import open
    import warnings
    # Ignore warnings about the vertical axis.
    # PyGeode complains because it sees a hybrid axis, but doesn't find
    # A and B coefficients to properly define it.
    with warnings.catch_warnings():
      warnings.filterwarnings("ignore", "Cannot create a proper Hybrid vertical axis")
      data = open(filename)
    # Add a dp and surface pressure product, based on the pressure interfaces.
    #NOTE: this modifies what the data_scanner sees when opening the file, so
    # the manifest will expect to have access to these fields.  If things
    # are added/removed in the lines below, the manifest(s) will have to be
    # manually deleted so they can be reconstructed with the new fields.
    if 'pressure' in data:
      p = data['pressure']
      p0 = p.slice[:,0,:,:].squeeze('boundary')
      p0.name = 'surface_pressure'
      p0.atts['units'] = 'Pa'
      p_p = p.slice[:,:-1,:,:].replace_axes(boundary=data.level)
      p_m = p.slice[:,1:,:,:].replace_axes(boundary=data.level)
      dp = p_p - p_m
      dp.name = 'dp'
      dp.atts['units'] = 'Pa'
      data = data + p0 + dp
    return data


# Add this interface to the table.
from . import table
table['ct2013b'] = CT2013B_Data



