# Unit conversion routines

# Standard prefixes for scaling
"test"
standard_prefixes = [
  ('Y', 'yotta', 1E21),
  ('Z', 'zetta', 1E21),
  ('E', 'exa', 1E18),
  ('P', 'peta', 1E15),
  ('T', 'tera', 1E12),
  ('G', 'giga', 1E9),
  ('M', 'mega', 1E6),
  ('k', 'kilo', 1E3),
  ('h', 'hecto', 1E2),
  ('da', 'deca', 1E1),
  ('d', 'deci', 1E-1),
  ('c', 'centi', 1E-2),
  ('m', 'milli', 1E-3),
  ('u', 'micro', 1E-6),
  ('n', 'nano', 1E-9),
  ('p', 'pico', 1E-12),
  ('f', 'femto', 1E-15),
  ('a', 'atto', 1E-18),
  ('z', 'zepto', 1E-21),
  ('y', 'yocto', 1E-24),
]

# Define the standard units (that can be prefixed)
prefixable_units = [
  ('g', 'grams', ''),
  ('m', 'metres', ''),
  ('s', 'seconds', ''),
  ('mol', 'moles', ''),
  ('N', 'newtons', 'kg m s-2'),
  ('Pa', 'pascals', 'N m-2'),
  ('bar', 'bars', '1E3 hPa'),
  ('J', 'joules', 'kg m2 s-2'),
]

# Other units (that don't work with the standard prefixes)
unprefixable_units = [
  ('ppm', 'parts per million', '1E-6 mol mol-1'),
  ('ppb', 'parts per billion', '1E-9 mol mol-1'),
  ('ppt', 'parts per trillion', '1E-12 mol mol-1'),
  ('h', 'hours', '3600 s'),
  ('day', 'days', '24 h'),
]

# Compile a final list of units
units = []
_lookup = {}
def _finalize_units():
  # Clear out any existing entries
  while len(units) > 0: units.pop()
  # Combine all prefixes and prefixable units
  for name, longname, conversion in prefixable_units:
    units.append((name, longname, conversion))
    for prefix, longprefix, scale in standard_prefixes:
      units.append((prefix+name, longprefix+longname, str(scale)+' '+name))
  # Add other _non-prefixable) units
  units.extend(unprefixable_units)
  _lookup.update((name,(name,longname,conversion)) for name,longname,conversion in units)
_finalize_units()


def parse_units (s, keep=[]):
  '''
    Parse a unit string into its basic building blocks.
    Returns scale, [numerator], [denominator]

    Optionally, you can pass a list of base units in the 'keep' parameter,
    which will stop these units from being reduced out.
  '''
  from re import match
  from collections import Counter
  if isinstance(keep,str): keep = [keep]

  scale = 1.0
  numerator = []
  denominator = []
  for term in s.split(' '):
    # Scale factor?
    try:
      scale *= float(term)
      continue
    except ValueError: pass

    name, exponent = match("^(.*[^-0-9])(|-?[0-9]+)$", term).groups()

    name, longname, conversion = _lookup[name]
    # Base unit or derived unit?
    if isinstance(conversion,str) and len(conversion) > 0:
      # Recursively parse the derived units
      sc, n, d = parse_units(conversion)
    else:
      sc, n, d = 1, [name], []

    if len(exponent) == 0: exponent = '1'
    exponent = int(exponent)

    # Apply the scale factor from this term
    scale *= sc**exponent

    # Apply the numerator / deomonator factors from this term
    if exponent < 0:
      n, d = d, n
      exponent = -exponent
    numerator.extend(n*exponent)
    denominator.extend(d*exponent)

  # Eliminate common base units between numerator and denominator
  # (ignore units that require further information for evaluation)
  is_reducible_unit = lambda x: isinstance(_lookup[x][2],str) and x not in keep
  reducible_numerator = Counter(filter(is_reducible_unit,numerator))
  reducible_denominator = Counter(filter(is_reducible_unit,denominator))
  numerator = [n for n in numerator if n not in reducible_numerator]
  denominator = [n for n in denominator if n not in reducible_denominator]
  # Reduce the numerator / denominator
  reducible_numerator, reducible_denominator = reducible_numerator-reducible_denominator, reducible_denominator-reducible_numerator
  # Stick it all together again
  numerator.extend(reducible_numerator.elements())
  denominator.extend(reducible_denominator.elements())

  # Sort the terms, to simplify comparisons against these units
  numerator = sorted(numerator)
  denominator = sorted(denominator)

  return scale, numerator, denominator


# Opposite of parse_units - get a string representation
# Inputs: scale, [numerator], [denominator]
def unparse_units (scale, numerator, denominator):
  '''
    Get a string representation from parsed units (opposite of parse_units).
  '''
  from collections import Counter
  if scale == 1: s = []
  else: s = [str(scale)]
  for x,i in sorted(Counter(numerator).items()):
    if i == 1: s.append(x)
    else: s.append('%s%d'%(x,i))
  for x,i in sorted(Counter(denominator).items()):
    s.append('%s-%d'%(x,i))
  return ' '.join(s)


def conversion_factor (from_units, to_units):
  '''
    Return the scale factor to convert from one set of units to another.
  '''
  scale1, numerator1, denominator1 = parse_units(from_units)
  scale2, numerator2, denominator2 = parse_units(to_units)
  if (numerator1 != numerator2) or (denominator1 != denominator2):
    raise ValueError ("Units '%s' and '%s' are not compatible"%(from_units,to_units))
  return scale2 / scale1


