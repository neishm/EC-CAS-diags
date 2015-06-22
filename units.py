# Unit conversion routines

# Standard prefixes for scaling
standard_prefixes = [
  ('Y', 'yotta', 1E24),
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
  ('molecules', 'molecules', repr(1/6.02214129E23)+'mol'),
  ('molefraction', 'mole fraction', ''),
  ('ppm', 'parts per million', '1E-6 molefraction'),
  ('ppb', 'parts per billion', '1E-9 molefraction'),
  ('ppt', 'parts per trillion', '1E-12 molefraction'),
  ('h', 'hours', '3600 s'),
  ('day', 'days', '24 h'),
]

# Container for defining a unit
class Unit(object):
  def __init__ (self, longname, conversion):
    self.longname = longname      # Description of the unit
    # Set default conversion (when no context is specified)
    self.conversions = {None:conversion}

# Fast lookup table for unit names
units = {}

def define_unit (name, longname, conversion=None, table=units):
  '''
    Register a unit with this module.
  '''
  # Interpret a blank conversion as no conversion specified
  if conversion == '': conversion = None

  table[name] = Unit(longname,conversion)

def define_prefixable_unit (name, longname, conversion='', table=units):
  '''
    Register a new prefixable unit with this module.
    All combinations of standard prefixes will be registered at the same time.
  '''
  define_unit (name, longname, conversion, table)
  for prefix, longprefix, scale in standard_prefixes:
    define_unit(prefix+name, longprefix+longname, repr(scale)+' '+name, table)


def define_conversion (unit, conversion, table=units):
  '''
    Define a conversion from one unit to another, valid under a particular
    context.

    Example:
      define_conversion ('mol(dry_air)', '28.97 g(dry_air)')

    Would tell the unit convertor how to convert from moles of air to grams
    of air.
  '''
  # Extract the input information (unit name and context)
  unit = list(parse_units(unit,table))
  if len(unit) > 1:
    raise ValueError ("Expected a single unit to be provided, got %s."%unit)
  unit = unit[0]
  if isinstance(unit,float):
    raise ValueError ("Expected a unit, got '%s'."%unit)
  name, context, exponent = unit
  if exponent != 1:
    raise ValueError ("Unexpected exponent on input unit.")
  if name not in table:
    raise ValueError ("Unrecognized unit '%s'"%name)

  table[name].conversions[context] = conversion


# Initialize the units
map (define_prefixable_unit, *zip(*_prefixable_units))
map (define_unit, *zip(*_unprefixable_units))
del _prefixable_units, _unprefixable_units

def copy_default_table():
  '''
    Return a copy of the default lookup table of units.
    Useful if you want to change certain conversions manually.
  '''
  from copy import copy
  table = dict()
  for n, u in units.iteritems():
    u = copy(u)
    u.conversions = u.conversions.copy()
    table[n] = u
  return table

def parse_units(s,table=units):
  '''
  Iterates over a unit string, parsing each term into a tuple of:
    1) name of the unit
    2) context of the unit (or None)
    3) exponent on the unit

  If the unit string starts with a scale factor, then a float will be returned
  as the first unit name.

  Examples:

    parse_units('m s-2') will yield ('m',None,1), ('s',None,-2).

    parse_units('100 ppm') will yield (100.0,None,1), ('ppm',None,1)

    parse_units('kg(H2O) kg(dry_air)-1') will yield ('kg','H2O',1), ('kg','dry_air',-1)

  Note: You can omit the spaces between each term, if it does not create any
  ambiguity.
  '''
  from re import match

  # From Python regular expression documentation
  scale_pattern = r'[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?'

  # Look for a scale factor at the start of the string
  m = match(scale_pattern, s)
  if m is not None:
    yield (float(m.group(0)),None,1)
    s = s[m.end():].lstrip()

  # Match a unit with an optional context and exponent
  # E.g. "m", "m2", "kg(CO2)"
  # First, get a list of all valid unit names (preferencing long names over short names)
  unit_names = sorted(table.iterkeys(), key=len, reverse=True)
  unit_pattern = r'(?P<name>%s)(\((?P<context>[^()]*)\))?(?P<exponent>-?[0-9]+)? *'%('|'.join(unit_names))
  while len(s) > 0:
    m = match(unit_pattern, s)
    if m is None:
      raise ValueError ("Unable to parse unit substring '%s'"%s)
    d = m.groupdict()
    name = d['name']
    context = d['context']
    exponent = int(d['exponent'] or 1)
    yield (name,context,exponent)
    s = s[m.end():]


# Recursively apply conversions to the given unit.
# (Used internally only)
def _reduce_units (term, global_context=None, table=units):

  if isinstance(term,(str,list)):
    if isinstance(term,str):
      terms = parse_units(term, table)
    else: terms = term
    for term in terms:
      for o in _reduce_units (term, global_context, table):
        yield o
    return

  name, context, exponent = term
  if isinstance(name,float):
    yield name, context, exponent
    return

  if name not in table:
    raise ValueError ("Unrecognized unit: %s"%name)

  if context in table[name].conversions:
    conversion = table[name].conversions[context]
    # Swallow up the local context (to allow the conversion to specify any new context it wants to apply)
    context = None
  else:
    # Fall back to default conversion if this context is unapplicable
    conversion = table[name].conversions[None]

  # Convert the unit, applying the local context
  if conversion is None:
    output = [(name, context, exponent)]
  else:
    # Apply the reduction (using the local context)
    output = _reduce_units(conversion,context,table)
    # Update the exponents
    output = [(n,c,e*exponent) for n,c,e in output]

  # Further convert the unit, applying the global context
  if global_context is not None:
    output = [list(_reduce_units((n,(c or global_context),e),table=table)) for n,c,e in output]
    # Flatten it out
    output = sum(output,[])

  # Return the fully reduced terms, one by one.
  for o in output:
    yield o




# Get a canonical representation of the unit
# This is used as a common ground when trying to convert one unit to another.
# Returns: scale, [terms]
# Note: only used internally
def _canonical_form (unit, global_context=None, table=units):
  # Get all terms (fully evaluated to their reduced form)
  terms = list(_reduce_units(unit,global_context,table))
  # Separate out the scale factor and the unit terms.
  # Gather all exponents for each type of unit
  scale = 1.0
  unit_exp = dict()
  for n,c,e in terms:
    if isinstance(n,float): scale *= (n**e)
    else:
      unit_exp[(n,c)] = unit_exp.setdefault((n,c),0) + e

  # Filter out terms that are cancelled out (exponenent is reduced to 0)
  terms = [(n,c,e) for (n,c),e in sorted(unit_exp.items()) if e != 0]
  return scale, terms


def conversion_factor (from_units, to_units, context=None, table=units):
  '''
    Return the scale factor to convert from one set of units to another.
  '''
  scale1, terms1 = _canonical_form(from_units,context,table)
  scale2, terms2 = _canonical_form(to_units,context,table)
  if (terms1 != terms2):
    raise ValueError ("Units '%s' and '%s' are not compatible"%(from_units,to_units))
  return scale1 / scale2

