# Interface for CT2013B molefraction data.
# Pretty much the same thing, except some preprocessing for
# pressure at the boundaries to get dp.

from .carbontracker import CT_Data
class CT2013B_Data(CT_Data):
  """
  CarbonTracker CO2 products (molefractions, fluxes) from CT2013B and later.
  """

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
      # Pressure interpolated to mid-levels
      p_level = (p_p+p_m)/2
      p_level.name = 'air_pressure'
      p_level.atts['units'] = 'Pa'
      # Put in new fields
      data = data + p_level + p0 + dp
    # Same thing with geopotential height (defined on the boundaries, so
    # compute mid-level values).
    if 'gph' in data:
      gph = data['gph']
      gph_p = gph.slice[:,:-1,:,:].replace_axes(boundary=data.level)
      gph_m = gph.slice[:,1:,:,:].replace_axes(boundary=data.level)
      gph_level = (gph_p+gph_m)/2
      gph_level.name = 'geopotential_height'
      gph_level.atts['units'] = 'm'
      data = data + gph_level

    return data


# Add this interface to the table.
from . import table
table['ct2013b'] = CT2013B_Data



