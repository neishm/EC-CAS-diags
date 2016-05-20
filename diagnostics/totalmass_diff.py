
from .totalmass import Totalmass
class TotalmassDiff(Totalmass):
  """
  Plot the difference in mass for the same field between two datasets.
  """
  def _input_combos (self, inputs):
    fieldname = self.fieldname
    n = len(inputs)
    for i in range(n):
      # Note: this will exclude integrated flux products, since they will have
      # '_flux' appended to their name.
      if not inputs[i].have(fieldname): continue
      for j in range(i+1,n):
        if not inputs[j].have(fieldname): continue
        yield inputs[i], inputs[j]

  def do (self, inputs):
    totalmass_diff(inputs, fieldname=self.fieldname, units=self.units, outdir=self.outdir, format=self.image_format, suffix=self.suffix)


if True:

  def totalmass_diff (models, fieldname, units, outdir, format='png', suffix=""):
    from os.path import exists
    from ..common import convert, same_times
    from matplotlib import pyplot as pl
    from pygeode.plot import plotvar

    if len(models) != 2:
      raise ValueError ("Expected 2 datasets")

    fields = [m.find_best(fieldname) for m in models]

    # Unit conversion
    fields = [convert(f,units) for f in fields]

    # Use only the common timesteps between the fields
    fields = same_times (*fields)
    diff = fields[0]-fields[1]

    diff.name=fieldname+'_diff'

    outfile = outdir + "/%s_totalmass_diff_%s%s.%s"%('_'.join(m.name for m in models),fieldname,suffix, format)
    if not exists(outfile):
      fig = pl.figure(figsize=(15,12))
      ax = pl.subplot(111)
      plotvar (diff, ax=ax)
      ax.set_title("%s total mass difference (%s-%s)"%(fieldname,models[0].name,models[1].name))
      fig.savefig(outfile)

from . import table
table['totalmass-diff'] = TotalmassDiff

