Introduction
============

This package generates plots & movies for the **EC-CAS** project at *Environment and Climate Change Canada*.


Basic usage
===========


Define your data
----------------

First, you need to come up with a *config file* describing the data you want to process (what type of data, where to find it, and how it should look in the plots).  See the included `eccas.cfg` file for an example of how a config file is structured.

If you're not sure which interfaces to use for your data, try running `eccas-diags --list-interfaces` to see all available options.  If you don't see the appropriate interface there, you could try making a new interface and adding it to the `interfaces/` directory (or request that it be added).


Run the diagnostics
-------------------

Now that you defined your data, you can try running the diagnostics:

```
eccas-diags -f your_data.cfg
```

Additional arguments may be required, such as `--tmpdir` to specify where to put intermediate files.  To get a full list of options available, run `eccas-diags --help`.

The final diagnostics will go in a `diags/` subdirectory from your first entry in your config file.


Dependencies
============


This package requires the [PyGeode](http://pygeode.github.io/), [numpy](http://www.numpy.org/), and [matplotlib](http://matplotlib.org/) Python packages in order to work.


