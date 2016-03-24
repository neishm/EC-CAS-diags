# Generic interface for a diagnostic, to be sub-classed by each particular
# diagnostic.
class Diagnostic(object):
  @staticmethod
  # Method to add extra command-line arguments needed for this diagnostic.
  def add_args (parser):
    return  # Nothing needed by default.

  # Method to collect the above command-line arguments into key/value pairs.
  # The output from this will be passed on to the diagnostic.
  @staticmethod
  def handle_args (args):
    return {}  # Nothing needed by default.

# Find all available diagnostics
table = {}
def _load_diagnostics ():
  import pkgutil
  import importlib
  for loader, name, ispkg in pkgutil.walk_packages(__path__):
    if ispkg: continue
    importlib.import_module(__name__+'.'+name)
_load_diagnostics()  # Allow the diagnostics to add their entries to this table


