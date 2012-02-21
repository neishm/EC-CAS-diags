from model import co2

# Count the number of grid points that go down to ~0 ppmV (?!)

print 'shape:', co2.shape
print 'total gridpoints:', co2.size
print 'number of holes:', ((co2<1)*1).sum()
print 'number of near holes:', ((co2<=10)*1).sum()
print 'number of really low values:', ((co2<=100)*1).sum()
