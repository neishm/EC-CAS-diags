from pstats import Stats
stats = Stats('timing.dat')
stats.strip_dirs()
stats.sort_stats('cumulative')
#stats.print_stats()
stats.print_callers()
