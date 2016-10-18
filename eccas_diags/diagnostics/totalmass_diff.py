###############################################################################
# Copyright 2016 - Climate Research Division
#                  Environment and Climate Change Canada
#
# This file is part of the "EC-CAS diags" package.
#
# "EC-CAS diags" is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# "EC-CAS diags" is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with "EC-CAS diags".  If not, see <http://www.gnu.org/licenses/>.
###############################################################################



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
    # Compare associated totalmass and integrated flux products.
    for i in range(n-1):
      if inputs[i].have(fieldname):
        if inputs[i+1].have(fieldname+'_flux'):
          yield inputs[i], inputs[i+1]

  def do (self, inputs):
    from os.path import exists
    from ..common import same_times, to_datetimes
    from matplotlib import pyplot as pl

    fig = pl.figure(figsize=(15,12))
    ax = pl.subplot(111)
    pl.title("%s total mass difference (%s-%s) in %s"%(self.fieldname,inputs[0].name,inputs[1].name,self.units))

    fields = [inp.find_best(self.fieldname) for inp in inputs]

    # Use only the common timesteps between the fields
    fields = same_times (*fields)
    diff = fields[0]-fields[1]
    diff.name=self.fieldname+'_diff'
    diff = inputs[0].cache.write(diff, prefix=inputs[0].name+'_totamass_diff_'+inputs[1].name+'_'+self.fieldname+self.suffix, suffix=self.end_suffix)
    dates = to_datetimes(diff.time)

    pl.plot(dates, diff.get(), color=inputs[0].color, linestyle=inputs[0].linestyle, marker=inputs[0].marker, markeredgecolor=inputs[0].color)

    outfile = self.outdir + "/%s_totalmass_diff_%s%s.%s"%('_'.join(inp.name for inp in inputs),self.fieldname,self.suffix+self.end_suffix, self.image_format)
    if not exists(outfile):
      fig.savefig(outfile)

from . import table
table['totalmass-diff'] = TotalmassDiff

