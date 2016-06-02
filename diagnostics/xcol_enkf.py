# Average column diagnostic

# Note: we aren't using any averaging kernal for this, so it's not directly
# comparable to satellite observations.


from .xcol import XCol
class XColEnKF(XCol):
  """
  Plot the column average of a field, alongside the column average of the
  ensemble spread.  Only useful for ensemble runs.
  """
  def _select_inputs (self, inputs):
    inputs = super(XColEnKF,self)._select_inputs(inputs)
    selected = []
    for inp in inputs:
      # In addition to the field, we need an ensembled spread.
      try:
        spread = self._avgcolumn(inp,fieldname=self.fieldname+'_ensemblespread',cache=False)
        selected.append(inp)
      except KeyError: pass
   
    return selected

  # Inject ensemble spread calculation
  #TODO: make it easier to specify multiple fields, instead of having the
  # diagnostics always assume there's 1 field of interest?
  def _transform_inputs (self, inputs):
    computed = super(XCol,self)._transform_inputs(inputs)
    for i,inp in enumerate(inputs):
      spread = self._avgcolumn(inp,fieldname=self.fieldname+'_ensemblespread')
      # Add this spread to the dataset in-place.
      computed[i].datasets[0] += spread
    return computed

  # Only look at one dataset at a time.
  def _input_combos (self, inputs):
    for inp in inputs:
      yield [inp]


  def do (self, inputs):
    from .movie import ContourMovie

    model = inputs[0]
    fieldname = self.fieldname

    prefix = model.name + '_' + 'X'+fieldname+self.suffix+self.end_suffix+'_stats'

    fields = model.find_best(fieldname,fieldname+'_ensemblespread')
    subtitles = ['X%s %s (%s)'%(fieldname,stat,model.name) for stat in 'mean','std dev.']
    title = 'X%s stats (in %s)'%(fieldname,self.units)

    aspect_ratio = 0.4  # height / width for each panel

    shape = (len(fields),1)

    movie = ContourMovie(fields, title=title, subtitles=subtitles, shape=shape, aspect_ratio = aspect_ratio)

    movie.save (outdir=self.outdir, prefix=prefix)

from . import table
table['xcol-enkf'] = XColEnKF

