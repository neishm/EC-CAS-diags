# Average column diagnostic

# Note: we aren't using any averaging kernal for this, so it's not directly
# comparable to satellite observations.

if True:

  def find_applicable_models (inputs, fieldname):
    from ..common import have_gridded_3d_data
    models = []
    for x in inputs:
      if any (fieldname in d and fieldname+'_ensemblespread' in d and have_gridded_3d_data(d) for d in x.datasets):
        models.append(x)
    if len(models) == 0:
      raise ValueError("No inputs match the criteria.")
    return models


from . import Diagnostic
class XColEnKF(Diagnostic):
  """
  Plot the column average of a field, alongside the column average of the
  ensemble spread.  Only useful for ensemble runs.
  """
  def do_all (self, inputs, fieldname, units, outdir):
    models = find_applicable_models(inputs, fieldname)
    models = self.filter_inputs(models)
    xcol_enkf (models, fieldname, units, outdir)



if True:

  def xcol_enkf (model, fieldname, units, outdir):
    from .movie import ContourMovie
    from .xcol import get_xcol

    prefix = model.name + '_' + 'X'+fieldname+'_stats'

    fields = [get_xcol(model,field,units) for field in (fieldname,fieldname+'_ensemblespread')]
    subtitles = ['X%s %s (%s)'%(fieldname,stat,model.name) for stat in 'mean','std dev.']
    title = 'X%s stats (in %s)'%(fieldname,units)

    aspect_ratio = 0.4  # height / width for each panel

    shape = (len(fields),1)

    movie = ContourMovie(fields, title=title, subtitles=subtitles, shape=shape, aspect_ratio = aspect_ratio)

    movie.save (outdir=outdir, prefix=prefix)

from . import table
table['xcol-enkf'] = XColEnKF

