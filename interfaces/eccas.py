from gem import GEM_Data

class ECCAS_Data(GEM_Data):

  field_list = GEM_Data.field_list + (
    ('CO2', 'CO2', 'ug(C) kg(air)-1'),
    ('CBB', 'CO2_fire', 'ug(C) kg(air)-1'),
    ('CFF', 'CO2_fossil', 'ug(C) kg(air)-1'),
    ('COC', 'CO2_ocean', 'ug(C) kg(air)-1'),
    ('CLA', 'CO2_bio', 'ug(C) kg(air)-1'),
    ('CO2B', 'CO2_background', 'ug(C) kg(air)-1'),
    ('CH4', 'CH4', 'ug kg(air)-1'),
    ('CH4B', 'CH4_background', 'ug kg(air)-1'),
    ('CHFF', 'CH4_fossil', 'ug kg(air)-1'),
    ('CHBB', 'CH4_fire', 'ug kg(air)-1'),
    ('CHOC', 'CH4_ocean', 'ug kg(air)-1'),
    ('CHNA', 'CH4_natural', 'ug kg(air)-1'),
    ('CHAG', 'CH4_agriculture', 'ug kg(air)-1'),
    ('OH', 'OH', 'molecules m-3'),
  )

  # Method to decode an opened dataset (standardize variable names, and add any
  # extra info needed (pressure values, cell area, etc.)
  @classmethod
  def decode (cls,dataset):
    from common import conversion_factor
    from gem import GEM_Data

    # Do generic GEM field decoding
    dataset = GEM_Data.decode.__func__(cls,dataset)

    # Determine if we have ensemble spread data from EC-CAS
    chmstd = False
    for var in dataset:
      if var.atts.get('etiket') == 'STDDEV':
        chmstd = True

    # Add a suffix to the variable names, if we have ensemble spread data.
    if chmstd:
      for var in dataset:
        var.name += "_ensemblespread"

    # Convert to a dictionary (for referencing by variable name)
    data = dict((var.name,var) for var in dataset)

    # Offset the ocean and land fields by 100ppm
    if 'CO2_ocean' in data:
      data['CO2_ocean'] -= conversion_factor('100 ppm', 'ug(C) kg(air)-1', context='CO2')
    if 'CO2_bio' in data:
      data['CO2_bio'] -= conversion_factor('100 ppm', 'ug(C) kg(air)-1', context='CO2')

    # Add species name for all products (to assist in things like unit conversion)
    for varname in data:
      if varname.startswith('CO2'):
        data[varname].atts['specie'] = 'CO2'
      elif varname.startswith('CH4'):
        data[varname].atts['specie'] = 'CH4'


    # Convert froma dictionary back to a list
    dataset = list(data.values())

    return dataset


  # Method to re-encode data into the source context
  # (e.g., rename fields to what would be originally in these kinds of files)
  @classmethod
  def encode (cls, dataset):
    from common import conversion_factor
    from gem import GEM_Data
    # Call the generic GEM encoder to convert to the right units and field names
    dataset = GEM_Data.encode.__func__(cls,dataset)
    # Do some extra stuff to offset COC / CLA fields
    for i, var in enumerate(dataset):
      if var.name in ('COC','CLA'):
        dataset[i] = (var + conversion_factor('100 ppm', 'ug(C) kg(air)-1', context='CO2')).as_type('float32')
    return dataset

  # For our forward cycles, we need to hard-code the ig1/ig2 of the tracers.
  # This is so we match the ip1/ip2 of the wind archive we're injecting
  # into the "analysis" files.
  @staticmethod
  def _fstd_tweak_records (records):
    # Select non-coordinate records (things that aren't already using IP2)
    ind = (records['ip2'] == 0)
    # Hard code the ig1 / ig2
    records['ig1'][ind] = 88320
    records['ig2'][ind] = 57863
    # Update the coordinate records to be consistent.
    records['ip1'][~ind] = 88320
    records['ip2'][~ind] = 57863
    # Just for completion, set the typvar and deet as well.
    records['typvar'][ind] = 'A'
    records['deet'][ind] = 0


# Give this class a standard reference name, to make it easier to auto-discover.
interface = ECCAS_Data
