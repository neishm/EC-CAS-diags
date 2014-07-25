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
  ('bar', 'bars', '1E3 hPa'),
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

# Fast lookup table for unit names
units = {}

# Additional contexts for units
# (if unit conversion depends on the matrial/substance in question, etc.)
contexts = {}

def register_unit (name, longname, conversion):
  '''
    Register a unit with this module.
  '''
  units[name] = (longname,conversion)

def register_prefixable_unit (name, longname, conversion):
  '''
    Register a new prefixable unit with this module.
    All combinations of standard prefixes will be registered at the same time.
  '''
  register_unit (name, longname, conversion)
  for prefix, longprefix, scale in standard_prefixes:
    register_unit(prefix+name, longprefix+longname, repr(scale)+' '+name)


def register_context (name, **conversions):
  '''
    Register a new context for a unit.  Some units need a specific context
    (e.g. a material/substance) in order to do some kinds of conversions.
  '''
  contexts[name] = conversions


# Initialize the units
map (register_prefixable_unit, *zip(*_prefixable_units))
map (register_unit, *zip(*_unprefixable_units))
del _prefixable_units, _unprefixable_units


def parse_units (s, context=None):
  '''
    Parse a unit string into its basic building blocks.
    Returns scale, [numerator], [denominator]

    Optionally, you can pass a context to the unit parser, to enable some
    context-sensitive unit reductions.
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
    exponent = int(m['exponent'] or '1')
    if m['invert']: exponent = -exponent
    context = m['context'] or context
    if context is None:
      context_conversions = {}
    elif context not in contexts:
      raise KeyError("Unrecognized unit context '%s'"%context)
    else:
      context_conversions = contexts[context]

    if name not in units:
      raise KeyError ("Unrecognized unit: %s"%name)
    longname, conversion = units[name]
    # Base unit or derived unit?
    if conversion != '':
      # Recursively parse the derived units
      sc, n, d = parse_units(conversion, context=context)
    # Final reduction?
    elif name not in context_conversions:
      sc, n, d = 1, [name], []
    # Explicitly keep the context name in reduced unit?
    elif context_conversions[name] == '':
      sc, n, d = 1, [name+'('+context+')'], []
    else:
      sc, n, d = parse_units(context_conversions[name], context=context)

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

