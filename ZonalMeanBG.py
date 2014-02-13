import numpy as np
import matplotlib.pyplot as plt
from pygeode import Var
import math

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
 
def bargraph(X,Height):
	X=np.squeeze(X)
	Range=[round(X.shape[1]/180.0*60),round(X.shape[1]/180.0*120)]
	SA,TrA,NA=np.split(np.squeeze(X[Height]),Range)	
	
	SAweights=latsweights[~np.isnan(SA)]
	SA=SA[~np.isnan(SA)]    #Remove nan values
	TrAweights=latsweights[~np.isnan(TrA)]
	TrA=TrA[~np.isnan(TrA)]
	NAweights=latsweights[~np.isnan(NA)]
	NA=NA[~np.isnan(NA)]
	
	N=np.average(NA,weights=NAweights)     #Take weighted average of each hemisphere
	S=np.average(SA,weights=SAweights) 
	Tr=np.average(TrA,weights=TrAweights) 
	
	yaxmax=400
	yaxmin=370
	
	plt.bar((0,2,4),(N,Tr,S),width=1,color='k')    #Bar graph plot
	
	plt.ylim(ymax=yaxmax,ymin=yaxmin)
	title='Average CO$_{2}$ Concentration at height %s'%(Height)
	plt.title(title)
	plt.ylabel('CO$_{2}$ Concentration (ppm)')
	plt.xticks((.5,2.5,4.5),('Northern\nExtratropics','Tropics','Southern\nExtratropics'))
	plt.xlim(0,5)
	yspan=yaxmax-yaxmin

	plt.text(0,N+yspan/200.0,round(N,2))    #Adds and formats the y value labels for each bar
	plt.text(2,Tr+yspan/200.0,round(Tr,2))
	plt.text(4,S+yspan/200.0,round(S,2))

	plt.plot((1.5,1.5),(max(N,S,Tr),min(N,S,Tr)),'b')    #Creates comparison bar
	plt.plot((1.45,1.55),(max(N,S,Tr),max(N,S,Tr)),'b')
	plt.plot((1.45,1.55),(min(N,S,Tr),min(N,S,Tr)),'b')
	
	plt.grid(axis='y',which='both')
	plt.text(1.25,(max(N,S,Tr)+min(N,S,Tr))/2.0,round(max(N,S,Tr)-min(N,S,Tr),2),rotation='vertical')    #Names comparison bar
	
def plotBG(height, field1,field2=None, field3=None, title1='plot1', title2='plot2', title3='plot3', palette=None, norm=None, preview=False, outdir='images'):
	
	from plot_wrapper import Colorbar, Plot, Overlay, Multiplot
	from plot_shortcuts import pcolor, contour, contourf, Map
	from os.path import exists
	from os import makedirs

	from pygeode.progress import PBar

	# Create output directory?
	if not exists(outdir): makedirs(outdir)

	print 'Saving Zonal Comparison %s images'%field1.name
	pbar = PBar()
	
	data = field1(i_time=1)
	year = data.time.year[0]
	month = data.time.month[0]
	day = data.time.day[0]
	hour = data.time.hour[0]
	
	data = field1(year=year,month=month,day=day,hour=hour)
	
	lats=data.lat.get()
	
	global latsweights
	latsweights=np.cos(np.radians(lats))

	
	
	# Loop over all available times
	for i,t in enumerate(range(len(field1.time))):
		
		data = field1(i_time=t)
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
		
		if field2 is None:
			fig = plt.figure(figsize=(4,8))  # single plot
			
			plt.subplot(111)
			data = field1(year=year,month=month,day=day,hour=hour)
			assert len(data.time) == 1
			bargraph(data,height)
			plt.text(2.5,399,'%s/%s/%s'%(str(day).zfill(2),str(month).zfill(2),year),horizontalalignment='center')

		elif field3 is None:
			fig = plt.figure(figsize=(8,8))  # double plot
			
			# 1st plot
			plt.subplot(121)
			data = field1(year=year,month=month,day=day,hour=hour)
			assert len(data.time) == 1
			bargraph(data,height)
			plt.text(2.5,399,'%s/%s/%s'%(str(day).zfill(2),str(month).zfill(2),year),horizontalalignment='center')

			# 2nd plot
			ax2=plt.subplot(122)
			data = field2(year=year,month=month,day=day,hour=hour)
			bargraph(data,height)
			plt.setp( ax2.get_yticklabels(), visible=False)
			plt.ylabel('')
			plt.title('')
			plt.text(2.5,399,'%s/%s/%s'%(str(day).zfill(2),str(month).zfill(2),year),horizontalalignment='center')
	
		else:
			fig = plt.figure(figsize=(12,8))  # triple plot
			
			# 1st plot
			plt.subplot(131)
			data = field1(year=year,month=month,day=day,hour=hour)
			assert len(data.time) == 1
			bargraph(data,height)
			plt.text(2.5,399,'%s/%s/%s'%(str(day).zfill(2),str(month).zfill(2),year),horizontalalignment='center')

			# 2nd plot
			plt.subplot(132)
			data = field2(year=year,month=month,day=day,hour=hour)
			ax2=bargraph(data,height)
			plt.text(2.5,399,'%s/%s/%s'%(str(day).zfill(2),str(month).zfill(2),year),horizontalalignment='center')
			plt.setp( ax2.get_yticklabels(), visible=False)
			plt.ylabel('')
			plt.title('')

			# 3rd plot
			plt.subplot(133)
			data = field3(year=year,month=month,day=day,hour=hour)
			ax3=bargraph(data,height)
			plt.text(2.5,399,'%s/%s/%s'%(str(day).zfill(2),str(month).zfill(2),year),horizontalalignment='center')
			plt.setp( ax3.get_yticklabels(), visible=False)
			plt.ylabel('')
			plt.title('')

		if preview is False:
			fig.savefig(fname)
			fig.clear()
			pbar.update(i*100/len(field1.time))
		else:
			break

def movie_bargraph (models, height, fieldname, units, outdir, stat='mean'):

	from common import unit_scale

	assert len(models) > 0
	assert len(models) <= 3  # too many things to plot
	models = [m for m in models if m is not None]

	imagedir=outdir+"/images_%s_flux%s"%('_'.join(m.name for m in models), fieldname)
	if stat != 'mean':
		imagedir += '_' + stat

	fields = [m.get_data('zonalmean_gph',fieldname,stat=stat) for m in models]
	
	# Unit conversion
	fields = [rescale(f,units) for f in fields]

	titles = [m.title for m in models]

	while len(fields) < 3: fields += [None]
	while len(titles) < 3: titles += [None]

	plotBG(height, field1=fields[0], field2=fields[1], field3=fields[2], title1=titles[0], title2=titles[1], title3=titles[2],preview=False, outdir=imagedir)

	moviefile = "%s/%s_zonalmeanBG%s_%s.avi"%(outdir, '_'.join(m.name for m in models), fieldname, stat)
	

	from os import system
	from os.path import exists
	if not exists(moviefile):
		system("mencoder -o %s mf://%s/*.png -ovc lavc -lavcopts vcodec=msmpeg4v2"%(moviefile, imagedir))

