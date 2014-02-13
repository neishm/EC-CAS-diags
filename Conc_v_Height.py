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
 
def CvHgraph(X):
	X=np.squeeze(X)
	MaxHeight=X.shape[0]-1

	RegionHeights=np.zeros((3,MaxHeight))
	RegionStds=np.zeros((3,MaxHeight))

	for i in range(MaxHeight):
		Range=[round(X.shape[1]/180.0*70),round(X.shape[1]/180.0*110)]
		SA,TrA,NA=np.split(np.squeeze(X[i]),Range)
		lwSA,lwTrA,lwNA=np.split(latsweights,Range)
		
		SAweights=lwSA[~np.isnan(SA)]
		SA=SA[~np.isnan(SA)]    #Remove nan values
		TrAweights=lwTrA[~np.isnan(TrA)]
		TrA=TrA[~np.isnan(TrA)]
		NAweights=lwNA[~np.isnan(NA)]
		NA=NA[~np.isnan(NA)]
		
		if NA.shape[0]!=0:
			RegionHeights[0][i]=np.average(NA,weights=NAweights)

		if TrA.shape[0]!=0:
			RegionHeights[1][i]=Tr=np.average(TrA,weights=TrAweights)

		if SA.shape[0]!=0:
			RegionHeights[2][i]=np.average(SA,weights=SAweights)
		
		RegionStds[0][i]=np.std(NA)
		RegionStds[1][i]=np.std(TrA)
		RegionStds[2][i]=np.std(SA)

	NHeight=np.ma.masked_where(RegionHeights[0]==0,np.arange(0,MaxHeight,1))    #Mask height values with no conc value
	TrHeight=np.ma.masked_where(RegionHeights[1]==0,np.arange(0,MaxHeight,1))
	SHeight=np.ma.masked_where(RegionHeights[2]==0,np.arange(0,MaxHeight,1))
	
	RegionHeights=np.ma.masked_equal(RegionHeights,0)
	RegionStds=np.ma.masked_where(RegionHeights==0,RegionStds)
	
	NL=plt.errorbar(RegionHeights[0],NHeight,xerr=RegionStds[0],color='b',linestyle='solid')
	TrL=plt.errorbar(RegionHeights[1],TrHeight,xerr=RegionStds[1],color='g')
	SL=plt.errorbar(RegionHeights[2],SHeight,xerr=RegionStds[2],color='r')
	plt.title('Average CO$_{2}$ Concentration')
	plt.xlabel('CO$_{2}$ Concentration (ppm)')
	plt.ylabel('Height (km)')
	plt.grid(b=None, which='major', axis='both')    #Add grid
	plt.xlim(375,395)

	plt.legend([NL,SL,TrL], ['North Extratropics','South Extratropics','Tropics'],prop={'size':11})

def plotCvH(field1,field2=None, field3=None, title1='plot1', title2='plot2', title3='plot3', palette=None, norm=None, preview=False, outdir='images'):
	
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
			fig = plt.figure(figsize=(5,8))  # single plot
			ax=plt.subplot(111)
			data = field1(year=year,month=month,day=day,hour=hour)
			assert len(data.time) == 1
			CvHgraph(data)
			plt.text(.75,.83,'%s/%s/%s'%(str(day).zfill(2),str(month).zfill(2),year),horizontalalignment='center',transform=ax.transAxes)

		elif field3 is None:
			fig = plt.figure(figsize=(8,8))  # double plot
			
			# 1st plot
			plt.subplot(121)
			data = field1(year=year,month=month,day=day,hour=hour)
			assert len(data.time) == 1
			CvHgraph(data)
			plt.text(.75,.83,'%s/%s/%s'%(str(day).zfill(2),str(month).zfill(2),year),horizontalalignment='center',transform=ax.transAxes)			

			# 2nd plot
			plt.subplot(122)
			data = field2(year=year,month=month,day=day,hour=hour)
			CvHgraph(data)
			plt.text(.75,.83,'%s/%s/%s'%(str(day).zfill(2),str(month).zfill(2),year),horizontalalignment='center',transform=ax.transAxes)
				
		else:
			fig = plt.figure(figsize=(12,8))  # triple plot
			
			# 1st plot
			plt.subplot(131)
			data = field1(year=year,month=month,day=day,hour=hour)
			assert len(data.time) == 1
			CvHgraph(data)
			plt.text(.75,.83,'%s/%s/%s'%(str(day).zfill(2),str(month).zfill(2),year),horizontalalignment='center',transform=ax.transAxes)
			
			# 2nd plot
			plt.subplot(132)
			data = field2(year=year,month=month,day=day,hour=hour)
			CvHgraph(data)
			plt.text(.75,.83,'%s/%s/%s'%(str(day).zfill(2),str(month).zfill(2),year),horizontalalignment='center',transform=ax.transAxes)
			
			# 3rd plot
			plt.subplot(133)
			data = field3(year=year,month=month,day=day,hour=hour)
			CvHgraph(data)
			plt.text(.75,.83,'%s/%s/%s'%(str(day).zfill(2),str(month).zfill(2),year),horizontalalignment='center',transform=ax.transAxes)
			
		if preview is False:
			fig.savefig(fname)
			fig.clear()
			pbar.update(i*100/len(field1.time))
		else:
			break

def movie_CvH (models, fieldname, units, outdir, stat='mean'):

	from common import unit_scale

	assert len(models) > 0
	assert len(models) <= 3  # too many things to plot
	models = [m for m in models if m is not None]

	imagedir=outdir+"/images_%s_CvH%s"%('_'.join(m.name for m in models), fieldname)
	if stat != 'mean':
		imagedir += '_' + stat

	fields = [m.get_data('zonalmean_gph',fieldname,stat=stat) for m in models]

	# Unit conversion
	fields = [rescale(f,units) for f in fields]

	titles = [m.title for m in models]

	while len(fields) < 3: fields += [None]
	while len(titles) < 3: titles += [None]

	plotCvH(field1=fields[0], field2=fields[1], field3=fields[2], title1=titles[0], title2=titles[1], title3=titles[2],preview=False, outdir=imagedir)

	moviefile = "%s/%s_CvH%s_%s.avi"%(outdir, '_'.join(m.name for m in models), fieldname, stat)

	from os import system
	from os.path import exists
	if not exists(moviefile):
	  system("mencoder -o %s mf://%s/*.png -ovc lavc -lavcopts vcodec=msmpeg4v2"%(moviefile, imagedir))
