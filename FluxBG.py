import numpy as np
import matplotlib.pyplot as plt
from pygeode import Var

def rescale (field, units):
  from common import unit_scale
  input_units = field.atts['units']
  if input_units == units: return field
  low = field.atts['low']
  high = field.atts['high']
  name = field.name
  field = field / unit_scale[input_units] * unit_scale[units]
  field.name = name
  field.atts['low'] = low / unit_scale[input_units] * unit_scale[units]
  field.atts['high'] = high / unit_scale[input_units] * unit_scale[units]
  return field

def FluxBG(X):
	X=X.squeeze()	
	X=X.mean('Lon')

	N=X(lat=(30,90)).mean('Lat').get()
	S=X(lat=(-90,-30)).mean('Lat').get()
	Tr=X(lat=(-30,30)).mean('Lat').get()
	
	plt.bar((0,2,4),(N,Tr,S),width=1,lw=2,color='r')    #Bar graph plot
	
	title='Flux'
	plt.title(title)
	plt.xticks((.5,2.5,4.5),('Northern\nExtratropics','Tropics','Southern\nExtratropics'))
	plt.ylabel('Flux (g/m$^{2}$s)')
	plt.xlim(0,5)
	plt.ylim(-6*10**(-7),7*10**(-7))
	
	plt.grid(axis='y',which='both')

def plotFlux(flux1,flux2=None, flux3=None, title1='plot1', title2='plot2', title3='plot3', palette=None, norm=None, preview=False, outdir='images'):
	
	from plot_wrapper import Colorbar, Plot, Overlay, Multiplot
	from plot_shortcuts import pcolor, contour, contourf, Map
	from os.path import exists
	from os import makedirs

	from pygeode.progress import PBar

	# Create output directory?
	if not exists(outdir): makedirs(outdir)

	print 'Saving Flux %s images'%flux1.name
	pbar = PBar()
		
	# Loop over all available times
	for i,t in enumerate(range(len(flux1.time))):

		data = flux1(i_time=t)
		year = data.time.year[0]
		month = data.time.month[0]
		day = data.time.day[0]
		hour = data.time.hour[0]
		
		# Quick kludge to workaround non-monotonic gph in CarbonTracker
		if year==2009 and month==8 and day==7: continue

		date = "%04d-%02d-%02d %02dz"%(year,month,day,hour)
		fname = "%s/%04d%02d%02d%02d.png"%(outdir,year,month,day,hour)
		if exists(fname) and preview is False:
			continue
		
		if flux2 is None:
			fig = plt.figure(figsize=(5,8))  # single plot
			
			ax=plt.subplot(111)
			data = flux1(year=year,month=month,day=day,hour=hour)
			assert len(data.time) == 1
			FluxBG(data)
			plt.text(.85,.95,'%s/%s/%s'%(str(day).zfill(2),str(month).zfill(2),year),horizontalalignment='center',transform=ax.transAxes)

		elif flux3 is None:
			fig = plt.figure(figsize=(8,8))  # double plot
			
			# 1st plot
			plt.subplot(121)
			data = flux1(year=year,month=month,day=day,hour=hour)
			assert len(data.time) == 1
			FluxBG(data)
			plt.text(.85,.95,'%s/%s/%s'%(str(day).zfill(2),str(month).zfill(2),year),horizontalalignment='center',transform=ax.transAxes)

			# 2nd plot
			plt.subplot(122)
			data = flux2(year=year,month=month,day=day,hour=hour)
			FluxBG(data)
			plt.text(.85,.95,'%s/%s/%s'%(str(day).zfill(2),str(month).zfill(2),year),horizontalalignment='center',transform=ax.transAxes)
				
		else:
			fig = plt.figure(figsize=(12,8))  # triple plot
			
			# 1st plot
			plt.subplot(131)
			data = flux1(year=year,month=month,day=day,hour=hour)
			assert len(data.time) == 1
			FluxBG(data)
			plt.text(.85,.95,'%s/%s/%s'%(str(day).zfill(2),str(month).zfill(2),year),horizontalalignment='center',transform=ax.transAxes)
			
			# 2nd plot
			plt.subplot(132)
			data = flux2(year=year,month=month,day=day,hour=hour)
			FluxBG(data)
			plt.text(.85,.95,'%s/%s/%s'%(str(day).zfill(2),str(month).zfill(2),year),horizontalalignment='center',transform=ax.transAxes)
			
			# 3rd plot
			plt.subplot(133)
			data = flux3(year=year,month=month,day=day,hour=hour)
			FluxBG(data)
			plt.text(.85,.95,'%s/%s/%s'%(str(day).zfill(2),str(month).zfill(2),year),horizontalalignment='center',transform=ax.transAxes)
		print i
		if preview is False:
			fig.savefig(fname)
			fig.clear()
			pbar.update(i*100/len(flux1.time))
		else:
			break


def movie_flux (models, fieldname, units, outdir, stat='mean'):

	from common import unit_scale

	assert len(models) > 0
	assert len(models) <= 3  # too many things to plot
	models = [m for m in models if m is not None]

	imagedir=outdir+"/images_%s_flux%s"%('_'.join(m.name for m in models), fieldname)
	if stat != 'mean':
		imagedir += '_' + stat
	
	fluxes = [m.get_data('flux',fieldname,stat=stat) for m in models]

	# Unit conversion
	#fluxes = [rescale(f,units) for f in fields]

	titles = [m.title for m in models]

	while len(fluxes) < 3: fluxes += [None]
	while len(titles) < 3: titles += [None]

	plotFlux(flux1=fluxes[0], flux2=fluxes[1], flux3=fluxes[2], title1=titles[0], title2=titles[1], title3=titles[2],preview=False, outdir=imagedir)

	moviefile = "%s/%s_FluxBG%s_%s.avi"%(outdir, '_'.join(m.name for m in models), fieldname, stat)

	from os import system
	from os.path import exists
	if not exists(moviefile):
	  system("mencoder -o %s mf://%s/*.png -ovc lavc -lavcopts vcodec=msmpeg4v2"%(moviefile, imagedir))

