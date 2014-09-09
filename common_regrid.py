# Some generic functions that may be useful for the regridding / converting code.

# Rotate a field so the longitudes range from 0..360
# Input: PyGeode object
# Output: PyGeode object
def rotate_grid (field):
  from pygeode.var import Var
  from pygeode.axis import Lon
  import numpy as np
  in_data = np.array(field.get())
  in_lon = np.array(field.lon.get())
  out_data = np.empty(in_data.shape, dtype=in_data.dtype)
  out_lon = np.empty(in_lon.shape, dtype=in_lon.dtype)
  # Determine index of first positive longitude
  i = np.where(in_lon>=0)[0][0]
  if i == 0: return field  # Already from 0..360
  # Positive longitudes
  out_data[...,:-i] = in_data[...,i:]
  out_lon[:-i] = in_lon[i:]
  # Negative longtiudes
  out_data[...,-i:] = in_data[...,:i]
  out_lon[-i:] = in_lon[:i] + 360.

  axes = list(field.axes)
  axes[-1] = Lon(out_lon)

  return Var(axes=axes, values=out_data, name=field.name, atts=field.atts)


# Determine latitude bounds
# Assume a global grid (end points are -90 and +90).
# Assume we can just take the mid-points of the latitudes for the inner
# boundaries.
def get_latbounds (lat):
  import numpy as np
  lat = np.array(lat)
  bounds = np.empty([len(lat)+1], dtype=lat.dtype)
  bounds[1:-1] = (lat[0:-1] + lat[1:]) / 2
  # Increasing lats?
  if lat[1] > lat[0]:
    bounds[0] = -90.
    bounds[-1] = 90.
  # Decreasing lats?
  else:
    bounds[0] = 90.
    bounds[-1] = -90.
  return bounds 

# Determine longitude bounds
# Assume a global grid, with equispaced longitudes.
# Also assume the longitudes are monotonically increasing.
def get_lonbounds (lon):
  import numpy as np
  lon = np.array(lon)
  bounds = np.empty([len(lon)+1], dtype=lon.dtype)
  bounds[1:-1] = (lon[0:-1] + lon[1:]) / 2
  bounds[0] = lon[0] - 0.5*(lon[1]-lon[0])
  bounds[-1] = lon[-1] + 0.5*(lon[-1]-lon[-2])
  return bounds

# Regrid a field
# Inputs:
#   field - The input field (PyGeode object)
#   lat   - The output latitudes (PyGeode object)
#   lon   - The output longitudes (PyGeode object)
# Output:
#   The regridded field (PyGeode object)
def regrid (field, lat, lon):
  from regrid import regridmodule
  import numpy as np
  from pygeode.var import Var
  from math import pi

  # Rotate the field so it's from 0 to 360
  field = rotate_grid(field)

  # Input coords
  lon1 = get_lonbounds(field.lon)
  sin1 = np.sin(get_latbounds(field.lat)/180.*pi)

  # Output coords
  lon2 = get_lonbounds(lon)
  sin2 = np.sin(get_latbounds(lat)/180.*pi)

  nt = field.shape[0]

  # Input data
  in_data = field.get()

  # Output data
  out_data = np.empty([nt,len(lat),len(lon)], dtype=in_data.dtype)


  # Loop over each time step, do the regridding
  for t in range(nt):
    q1 = in_data[t,:,:].T
    q2 = regridmodule.map_a2a (lon1, sin1, q1, lon2, sin2, ig=0, iv=0)
    out_data[t,:,:] = q2.T

  # Return the array (with coordinate metadata)
  axes = [field.axes[0], lat, lon]
  return Var(axes=axes, values=out_data, name=field.name)


# Compute the area of a given lat/lon field
#TODO: consolidate this with EC-CAS_diags.common.get_area()
def get_area (lat, lon):
  r = 6371220.  # Radius of Earth (in metres)
  from math import pi
  import numpy as np
  from pygeode.var import Var
  lonbounds = get_lonbounds(lon) / 180. * pi
  dlon = np.diff(lonbounds)
  latbounds = get_latbounds(lat) / 180. * pi
  dsinlat = np.diff(np.sin(latbounds))

  dsinlat = dsinlat.reshape([-1,1])
  dlon = dlon.reshape([1,-1])

  area = r**2 * dsinlat * dlon
  return Var(axes=[lat,lon], values=area)


