# Helper method for autogenerating contour levels
def get_contours(low,high):
  from math import log10, ceil, floor
  import numpy as np

  true_low = low
  true_high = high

#  print '?? low/high:', low, high
  # Make the numbers nice
  dx = high-low
#  print '?? dx:', dx
  digits = int(floor(log10(dx)))
#  print '?? digits:', digits
  # Adjust the low/high to the proper # of digits
  low  = floor(low /10**digits * 10) * 10**digits / 10
  high =  ceil(high/10**digits * 10) * 10**digits / 10
#  print '?? low/high:', low, high
  # Adjust so that dx is divisible into 20 units
  dx = high-low
#  print '?? dx:', dx

  count = dx / 10**digits * 10
#  print '?? count:', count
  count = int(round(count))
#  print '?? count:', count
  # Want a range that's divisible into a reasonable number of contours
  min_contours = 16
  max_contours = 24
  valid_contours = range(min_contours,max_contours+1)
  while not any(count%n == 0 for n in valid_contours):
    # Which end should we extend?
    if abs(low-true_low) < abs(high-true_high):
      low -= 10**digits / 10.
    else:
      high += 10**digits / 10.
    count += 1
#  print '?? count:', count
#  print '?? low/high:', low, high

  for n in valid_contours:
    if count%n == 0:
      contours = np.linspace(low,high,n+1)
#      print '?? contours:', contours
      return contours

# Helper method - determine a good high and low value for the given data
# (discard the bottom and top 0.1%, so our range at least covers 99.8% of the plot)
def get_range (var):
  import numpy as np
  #NOTE: these ranges are already handled in the data cache
  return var.atts['low'], var.atts['high']

# Get a global range that covers multiple fields
def get_global_range (*vars):
  low = min(var.atts['low'] for var in vars)
  high = max(var.atts['high'] for var in vars)
  return low, high
