from numpy.distutils.core import setup, Extension

regrid_horz = Extension ('eccas_diags.regrid_horz', sources=['fvdasregridmodule.f90'])
regrid_vert = Extension ('eccas_diags.regrid_vert', sources=['regrid_vert.f90'])
setup (
  name="eccas-diags",
  version="0-20150429",
  packages=["eccas_diags","eccas_diags.interfaces","eccas_diags.diagnostics"],
  ext_modules=[regrid_horz, regrid_vert],
)

