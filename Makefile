all: regrid

# Wrap the map_a2a horizontal regridder into a Python module.
regrid: typemodule.mod regridmodule.mod
	f2py -c -m regrid --fcompiler=gnu95 regridmodule.f90

%.mod: %.f90
	gfortran -c $<

clean:
	rm -f *.mod *.o *.so

