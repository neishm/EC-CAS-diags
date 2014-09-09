#!/bin/bash

# Generate a Python interface for map_a2a subroutine.

# Should be run on a Linux system with gfortran and f2py installed.

gfortran -c typemodule.f90
gfortran -c regridmodule.f90
f2py -c -m regrid --fcompiler=gnu95 regridmodule.f90

