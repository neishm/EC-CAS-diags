# Find all available diagnostics
table = {}
def _load_diagnostics ():
  import pkgutil
  import importlib
  for loader, name, ispkg in pkgutil.walk_packages(__path__):
    if ispkg: continue
    importlib.import_module(__name__+'.'+name)
_load_diagnostics()  # Allow the diagnostics to add their entries to this table


