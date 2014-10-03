all: regrid_horz.so regrid_vert.so

# Wrap the map_a2a horizontal regridder into a Python module.
regrid_horz.so: typemodule.mod regridmodule.mod
	f2py -c -m regrid_horz --fcompiler=gnu95 regridmodule.f90

regrid_vert.so: regrid_vert.f90
	f2py -c -m regrid_vert --fcompiler=gnu95 $<

%.mod: %.f90
	gfortran -c $<

clean:
	rm -f *.mod *.o *.so

