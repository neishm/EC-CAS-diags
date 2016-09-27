from numpy.distutils.core import setup, Extension

regrid_horz = Extension ('eccas_diags.regrid_horz', sources=['eccas_diags/fvdasregridmodule.f90'])
regrid_vert = Extension ('eccas_diags.regrid_vert', sources=['eccas_diags/regrid_vert.f90'])
setup (
  name="eccas-diags",
  version="0-20150831",
  scripts=["eccas-diags","eccas-met-diags","eccas-regrid","eccas-check-interface"],
  packages=["eccas_diags","eccas_diags.interfaces","eccas_diags.diagnostics","eccas_diags.calculations"],
  ext_modules=[regrid_horz, regrid_vert],
)

