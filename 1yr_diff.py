from model import co2
from pygeode.volatile.plot_wrapper import Colorbar
from pygeode.volatile.plot_shortcuts import contourf, pcolor, Map

co2_start = co2(year=2009,month=1,day=2,hour=0).squeeze()
co2_end = co2(year=2010,month=1,day=1,hour=0).squeeze()

diff = co2_end - co2_start

plot = contourf(diff, range(-30,30+5,5), title="CO2 difference (2009-01-02 00:00 - 2010-01-01 00:00)")
plot = Colorbar(plot)
plot = Map(plot)
#plot.render()
print diff.mean(weights=True)
quit()

from matplotlib.pyplot import show
show()
