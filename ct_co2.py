# Converter for CarbonTracker CO2 data

# This routine is called from the 'regrid' script.
def convert (infile, lat, lon):

  from pygeode.formats import netcdf
  from pygeode.timeutils import reltime
  from common_regrid import regrid, get_area

  infile = netcdf.open(infile)
  # Adjust the time axis (the mid-point is encoded, but want the beginning of
  # the flux validity. (-1.5 hours)
  days =infile.date.values
  days = days - 1.5 / 24.
  infile = infile.replace_axes(date = infile.date.withnewvalues(days))

  # Extract the CarbonTracker data
  fossil = infile.fossil_imp
  bio = infile.bio_flux_opt
  ocn = infile.ocn_flux_opt
  fire = infile.fire_flux_imp

  # Regrid the data
  fossil = regrid(fossil, lat, lon)
  bio = regrid(bio, lat, lon)
  ocn = regrid(ocn, lat, lon)
  fire = regrid(fire, lat, lon)

  # Scale the data
  area = get_area(lat,lon)
  scale = area * 12.01  # moles to grams of carbon atoms
  fossil *= scale
  bio *= scale
  ocn *= scale
  fire *= scale

  # Compute total flux
  total = fossil + bio + ocn + fire

  # Set the nomvars
  fossil.name = "ECFF"
  bio.name = "ECLA"
  ocn.name = "ECOC"
  fire.name = "ECBB"
  total.name = "ECO2"

  # Set the etiket
  for field in fossil, bio, ocn, fire, total:
    field.atts['etiket'] = "CTEMISSI"

  # Return the converted data (to be finalized by the calling script).
  return [fire, fossil, bio, ocn, total]

