# Unit conversion routines

# Standard prefixes for scaling
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

# Define some built-in units that can be prefixed
_prefixable_units = [
  ('g', 'grams', ''),
  ('m', 'metres', ''),
  ('s', 'seconds', ''),
  ('mol', 'moles', ''),
  ('N', 'newtons', 'kg m s-2'),
  ('Pa', 'pascals', 'N m-2'),
  ('bar', 'bars', '1000 hPa'),
  ('J', 'joules', 'kg m2 s-2'),
]

# Other built-in units (that don't work with the standard prefixes)
_unprefixable_units = [
  ('molefraction', 'mole fraction', ''),
  ('ppm', 'parts per million', '1E-6 molefraction'),
  ('ppb', 'parts per billion', '1E-9 molefraction'),
  ('ppt', 'parts per trillion', '1E-12 molefraction'),
  ('h', 'hours', '3600 s'),
  ('day', 'days', '24 h'),
]

# Container for defining a unit
class Unit(object):
  def __init__ (self, longname, conversion, context_conversions):
    self.longname = str(longname)
    self.conversion = str(conversion)
    self.context_conversions = dict(context_conversions)


# Fast lookup table for unit names
units = {}

def define_unit (name, longname, conversion=''):
  '''
    Register a unit with this module.
  '''
  units[name] = Unit(longname,conversion,{})

def define_prefixable_unit (name, longname, conversion=''):
  '''
    Register a new prefixable unit with this module.
    All combinations of standard prefixes will be registered at the same time.
  '''
  define_unit (name, longname, conversion)
  for prefix, longprefix, scale in standard_prefixes:
    define_unit(prefix+name, longprefix+longname, repr(scale)+' '+name)


def define_conversion (name, conversion):
  '''
    Define a conversion from one unit to another, valid under a particular
    context.

    Example:
      define_conversion ('mol(air)', '28.97 g(air)')

    Would tell the unit convertor how to convert from moles of air to grams
    of air.
  '''
  from re import match
  m = match(r'^(?P<name>[^()]+)(\((?P<context>.*)\))?$', name)
  if m is None:
    raise ValueError ("Can't parse unit '%s'"%name)
  m = m.groupdict()
  name = m['name']
  context = m['context']
  if name not in units:
    raise ValueError ("Unrecognized unit '%s'"%name)
  if context is None:
    units[name].conversion = conversion
  else:
    units[name].context_conversions[context] = conversion


# Initialize the units
map (define_prefixable_unit, *zip(*_prefixable_units))
map (define_unit, *zip(*_unprefixable_units))
del _prefixable_units, _unprefixable_units


def parse_units (s, global_context=None):
  '''
    Parse a unit string into its basic building blocks.
    Returns scale, [numerator], [denominator]
  '''
  from re import match, sub
  from collections import Counter

  # First, preprocess the string to attach '/' symbols to the next term
  s = sub(' / ', ' /', s)

  scale = 1.0
  numerator = []
  denominator = []
  for term in s.split(' '):
    # Scale factor?
    try:
      scale *= float(term)
      continue
    except ValueError: pass

    m = match(r"^(?P<invert>/)?(?P<name>[a-zA-Z]+)(\((?P<context>.*)\))?(?P<exponent>-?[0-9]+)?$", term)
    if m is None:
      raise ValueError ("Unparseable unit string '%s'"%term)
    m = m.groupdict()
    name = m['name']
    if name not in units:
      raise ValueError ("Unrecognized unit: %s"%name)
    exponent = int(m['exponent'] or '1')
    if m['invert']: exponent = -exponent
    context = m['context'] or global_context

    conversion = units[name].conversion
    if context in units[name].context_conversions:
      conversion = units[name].context_conversions[context]

    # Base unit or derived unit?
    if conversion != '':
      # Recursively parse the derived units
      sc, n, d = parse_units(conversion,context)
    # Final reduction?
    else:
      if context is None:
        sc, n, d = 1, [name], []
      else:
        sc, n, d = 1, [name+'('+context+')'], []

    # Apply the scale factor from this term
    scale *= sc**exponent

    # Apply the numerator / deomonator factors from this term
    if exponent < 0:
      n, d = d, n
      exponent = -exponent
    numerator.extend(n*exponent)
    denominator.extend(d*exponent)

  # Eliminate common base units between numerator and denominator
  numerator = Counter(numerator)
  denominator = Counter(denominator)
  numerator, denominator = numerator-denominator, denominator-numerator
  numerator = numerator.elements()
  denominator = denominator.elements()

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
  else: s = [repr(scale)]
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
  return scale1 / scale2

