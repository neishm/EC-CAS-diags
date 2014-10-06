! $Id $
MODULE FvdasRegridModule

  !====================================================================
  ! Module "FvdasRegridModule" contains arrays and variables used
  ! to regrid the GEOS-4 data from 1 x 1 --> 2 x 2.5 and also from
  ! 1 x 1 --> 4 x 5 resolution. (bmy, 4/9/02)
  !
  ! NOTES:
  ! (1 ) Renamed to "fvdasRegridModule"; now also include lon and
  !       lat edges for the GEOS-4/fvDAS 1 x 1.25 grid (bmy, 4/8/02)
  ! (2 ) Contains regridding code written by S-J Lin from DAO, and
  !       converted to F90 freeform format. (bmy, 4/8/02)
  !====================================================================
  !USE TypeModule

  IMPLICIT NONE

  PRIVATE :: XMAP
  PRIVATE :: YMAP
!
! !PUBLIC MEMBER FUNCTIONS:
!
  PUBLIC  :: MAP_A2A

  ! Size parameters for the GEM horizontal grid
  INTEGER, PARAMETER  :: IGEM=400, JGEM=200, LGEM=47    

  ! Size parameters for the GEOS-3, 1 x 1 grid
  INTEGER, PARAMETER  :: I1x1=360,   J1x1=181,   L1x1=55    

  ! Size parameters for the GEOS-4/fvDAS 1 x 1.25 grid
  INTEGER, PARAMETER  :: I1x125=288, J1x125=181, L1x125=55

  ! Size parameters for the GEOS 2 x 2.5 grid
  INTEGER, PARAMETER  :: I2x25=144,  J2x25=91,   L2x25=55

  ! Size parameters for the GEOS 4 x 5 grid
  INTEGER, PARAMETER  :: I4x5=72,    J4x5=46,    L4x5=55 

  ! Latitude edges, GEM 0.9 x 0.9 grid 
  REAL*8   :: yedge_GEM(JGEM+1) = (/              &
  & -90.000,  -88.865,  -87.975,  -87.080,  -86.180, &
  & -85.285,  -84.390,  -83.490,  -82.590,  -81.695, &
  & -80.800,  -79.900,  -79.000,  -78.105,  -77.210, &
  & -76.310,  -75.410,  -74.510,  -73.615,  -72.720, &
  & -71.820,  -70.920,  -70.025,  -69.130,  -68.230, &
  & -67.330,  -66.430,  -65.535,  -64.640,  -63.740, &
  & -62.840,  -61.945,  -61.050,  -60.150,  -59.250, &
  & -58.350,  -57.455,  -56.560,  -55.660,  -54.760, &
  & -53.865,  -52.970,  -52.070,  -51.170,  -50.275, &
  & -49.380,  -48.480,  -47.580,  -46.680,  -45.785, &
  & -44.890,  -43.990,  -43.090,  -42.195,  -41.300, &
  & -40.400,  -39.500,  -38.600,  -37.705,  -36.810, &
  & -35.910,  -35.010,  -34.115,  -33.220,  -32.320, &
  & -31.420,  -30.520,  -29.625,  -28.730,  -27.830, &
  & -26.930,  -26.035,  -25.140,  -24.240,  -23.340, &
  & -22.440,  -21.545,  -20.650,  -19.750,  -18.850, &
  & -17.955,  -17.060,  -16.160,  -15.260,  -14.365, &
  & -13.470,  -12.570,  -11.670,  -10.770,   -9.875, &
  &  -8.980,   -8.080,   -7.180,   -6.285,   -5.390, &
  &  -4.490,   -3.590,   -2.690,   -1.795,   -0.900, &
  &   0.000,    0.900,    1.795,    2.690,    3.590, &
  &   4.490,    5.390,    6.285,    7.180,    8.080, &
  &   8.980,    9.875,   10.770,   11.670,   12.570, &
  &  13.470,   14.365,   15.260,   16.160,   17.060, &
  &  17.955,   18.850,   19.750,   20.650,   21.545, &
  &  22.440,   23.340,   24.240,   25.140,   26.035, &
  &  26.930,   27.830,   28.730,   29.625,   30.520, &
  &  31.420,   32.320,   33.220,   34.115,   35.010, &
  &  35.910,   36.810,   37.705,   38.600,   39.500, &
  &  40.400,   41.300,   42.195,   43.090,   43.990, &
  &  44.890,   45.785,   46.680,   47.580,   48.480, &
  &  49.380,   50.275,   51.170,   52.070,   52.970, &
  &  53.865,   54.760,   55.660,   56.560,   57.455, &
  &  58.350,   59.250,   60.150,   61.050,   61.945, &
  &  62.840,   63.740,   64.640,   65.535,   66.430, &
  &  67.330,   68.230,   69.130,   70.025,   70.920, &
  &  71.820,   72.720,   73.615,   74.510,   75.410, &
  &  76.310,   77.210,   78.105,   79.000,   79.900, &
  &  80.800,   81.695,   82.590,   83.490,   84.390, &
  &  85.285,   86.180,   87.080,   87.975,   88.865, &
  &  90.000 /)

  REAL*8 :: xedge_GEM(IGEM+1) = (/               &
  & -180.450, -179.550, -178.650, -177.750, -176.850, &
  & -175.950, -175.050, -174.150, -173.250, -172.350, &
  & -171.450, -170.550, -169.650, -168.750, -167.850, &
  & -166.950, -166.050, -165.150, -164.250, -163.350, &
  & -162.450, -161.550, -160.650, -159.750, -158.850, &
  & -157.950, -157.050, -156.150, -155.250, -154.350, &
  & -153.450, -152.550, -151.650, -150.750, -149.850, &
  & -148.950, -148.050, -147.150, -146.250, -145.350, &
  & -144.450, -143.550, -142.650, -141.750, -140.850, &
  & -139.950, -139.050, -138.150, -137.250, -136.350, &
  & -135.450, -134.550, -133.650, -132.750, -131.850, &
  & -130.950, -130.050, -129.150, -128.250, -127.350, &
  & -126.450, -125.550, -124.650, -123.750, -122.850, &
  & -121.950, -121.050, -120.150, -119.250, -118.350, &
  & -117.450, -116.550, -115.650, -114.750, -113.850, &
  & -112.950, -112.050, -111.150, -110.250, -109.350, &
  & -108.450, -107.550, -106.650, -105.750, -104.850, &
  & -103.950, -103.050, -102.150, -101.250, -100.350, &
  &  -99.450,  -98.550,  -97.650,  -96.750,  -95.850, &
  &  -94.950,  -94.050,  -93.150,  -92.250,  -91.350, &
  &  -90.450,  -89.550,  -88.650,  -87.750,  -86.850, &
  &  -85.950,  -85.050,  -84.150,  -83.250,  -82.350, &
  &  -81.450,  -80.550,  -79.650,  -78.750,  -77.850, &
  &  -76.950,  -76.050,  -75.150,  -74.250,  -73.350, &
  &  -72.450,  -71.550,  -70.650,  -69.750,  -68.850, &
  &  -67.950,  -67.050,  -66.150,  -65.250,  -64.350, &
  &  -63.450,  -62.550,  -61.650,  -60.750,  -59.850, &
  &  -58.950,  -58.050,  -57.150,  -56.250,  -55.350, &
  &  -54.450,  -53.550,  -52.650,  -51.750,  -50.850, &
  &  -49.950,  -49.050,  -48.150,  -47.250,  -46.350, &
  &  -45.450,  -44.550,  -43.650,  -42.750,  -41.850, &
  &  -40.950,  -40.050,  -39.150,  -38.250,  -37.350, &
  &  -36.450,  -35.550,  -34.650,  -33.750,  -32.850, &
  &  -31.950,  -31.050,  -30.150,  -29.250,  -28.350, &
  &  -27.450,  -26.550,  -25.650,  -24.750,  -23.850, &
  &  -22.950,  -22.050,  -21.150,  -20.250,  -19.350, &
  &  -18.450,  -17.550,  -16.650,  -15.750,  -14.850, &
  &  -13.950,  -13.050,  -12.150,  -11.250,  -10.350, &
  &   -9.450,   -8.550,   -7.650,   -6.750,   -5.850, &
  &   -4.950,   -4.050,   -3.150,   -2.250,   -1.350, &
  &   -0.450,    0.450,    1.350,    2.250,    3.150, &
  &    4.050,    4.950,    5.850,    6.750,    7.650, &
  &    8.550,    9.450,   10.350,   11.250,   12.150, &
  &   13.050,   13.950,   14.850,   15.750,   16.650, &
  &   17.550,   18.450,   19.350,   20.250,   21.150, &
  &   22.050,   22.950,   23.850,   24.750,   25.650, &
  &   26.550,   27.450,   28.350,   29.250,   30.150, &
  &   31.050,   31.950,   32.850,   33.750,   34.650, &
  &   35.550,   36.450,   37.350,   38.250,   39.150, &
  &   40.050,   40.950,   41.850,   42.750,   43.650, &
  &   44.550,   45.450,   46.350,   47.250,   48.150, &
  &   49.050,   49.950,   50.850,   51.750,   52.650, &
  &   53.550,   54.450,   55.350,   56.250,   57.150, &
  &   58.050,   58.950,   59.850,   60.750,   61.650, &
  &   62.550,   63.450,   64.350,   65.250,   66.150, &
  &   67.050,   67.950,   68.850,   69.750,   70.650, &
  &   71.550,   72.450,   73.350,   74.250,   75.150, &
  &   76.050,   76.950,   77.850,   78.750,   79.650, &
  &   80.550,   81.450,   82.350,   83.250,   84.150, &
  &   85.050,   85.950,   86.850,   87.750,   88.650, &
  &   89.550,   90.450,   91.350,   92.250,   93.150, &
  &   94.050,   94.950,   95.850,   96.750,   97.650, &
  &   98.550,   99.450,  100.350,  101.250,  102.150, &
  &  103.050,  103.950,  104.850,  105.750,  106.650, &
  &  107.550,  108.450,  109.350,  110.250,  111.150, &
  &  112.050,  112.950,  113.850,  114.750,  115.650, &
  &  116.550,  117.450,  118.350,  119.250,  120.150, &
  &  121.050,  121.950,  122.850,  123.750,  124.650, &
  &  125.550,  126.450,  127.350,  128.250,  129.150, &
  &  130.050,  130.950,  131.850,  132.750,  133.650, &
  &  134.550,  135.450,  136.350,  137.250,  138.150, &
  &  139.050,  139.950,  140.850,  141.750,  142.650, &
  &  143.550,  144.450,  145.350,  146.250,  147.150, &
  &  148.050,  148.950,  149.850,  150.750,  151.650, &
  &  152.550,  153.450,  154.350,  155.250,  156.150, &
  &  157.050,  157.950,  158.850,  159.750,  160.650, &
  &  161.550,  162.450,  163.350,  164.250,  165.150, &
  &  166.050,  166.950,  167.850,  168.750,  169.650, &
  &  170.550,  171.450,  172.350,  173.250,  174.150, &
  &  175.050,  175.950,  176.850,  177.750,  178.650, &
  &  179.550 /)

  ! Longitude edges for GEOS-4/fvDAS 1 x 1.25 grid
  REAL*8 :: xedge_1x125(I1x125+1) = (/              &
  & -180.625, -179.375, -178.125, -176.875, -175.625, & 
  & -174.375, -173.125, -171.875, -170.625, -169.375, & 
  & -168.125, -166.875, -165.625, -164.375, -163.125, & 
  & -161.875, -160.625, -159.375, -158.125, -156.875, & 
  & -155.625, -154.375, -153.125, -151.875, -150.625, & 
  & -149.375, -148.125, -146.875, -145.625, -144.375, & 
  & -143.125, -141.875, -140.625, -139.375, -138.125, & 
  & -136.875, -135.625, -134.375, -133.125, -131.875, & 
  & -130.625, -129.375, -128.125, -126.875, -125.625, & 
  & -124.375, -123.125, -121.875, -120.625, -119.375, & 
  & -118.125, -116.875, -115.625, -114.375, -113.125, & 
  & -111.875, -110.625, -109.375, -108.125, -106.875, & 
  & -105.625, -104.375, -103.125, -101.875, -100.625, & 
  &  -99.375,  -98.125,  -96.875,  -95.625,  -94.375, & 
  &  -93.125,  -91.875,  -90.625,  -89.375,  -88.125, & 
  &  -86.875,  -85.625,  -84.375,  -83.125,  -81.875, & 
  &  -80.625,  -79.375,  -78.125,  -76.875,  -75.625, & 
  &  -74.375,  -73.125,  -71.875,  -70.625,  -69.375, & 
  &  -68.125,  -66.875,  -65.625,  -64.375,  -63.125, & 
  &  -61.875,  -60.625,  -59.375,  -58.125,  -56.875, & 
  &  -55.625,  -54.375,  -53.125,  -51.875,  -50.625, & 
  &  -49.375,  -48.125,  -46.875,  -45.625,  -44.375, & 
  &  -43.125,  -41.875,  -40.625,  -39.375,  -38.125, & 
  &  -36.875,  -35.625,  -34.375,  -33.125,  -31.875, & 
  &  -30.625,  -29.375,  -28.125,  -26.875,  -25.625, & 
  &  -24.375,  -23.125,  -21.875,  -20.625,  -19.375, & 
  &  -18.125,  -16.875,  -15.625,  -14.375,  -13.125, & 
  &  -11.875,  -10.625,   -9.375,   -8.125,   -6.875, & 
  &   -5.625,   -4.375,   -3.125,   -1.875,   -0.625, & 
  &    0.625,    1.875,    3.125,    4.375,    5.625, & 
  &    6.875,    8.125,    9.375,   10.625,   11.875, & 
  &   13.125,   14.375,   15.625,   16.875,   18.125, & 
  &   19.375,   20.625,   21.875,   23.125,   24.375, & 
  &   25.625,   26.875,   28.125,   29.375,   30.625, & 
  &   31.875,   33.125,   34.375,   35.625,   36.875, & 
  &   38.125,   39.375,   40.625,   41.875,   43.125, & 
  &   44.375,   45.625,   46.875,   48.125,   49.375, & 
  &   50.625,   51.875,   53.125,   54.375,   55.625, & 
  &   56.875,   58.125,   59.375,   60.625,   61.875, & 
  &   63.125,   64.375,   65.625,   66.875,   68.125, & 
  &   69.375,   70.625,   71.875,   73.125,   74.375, & 
  &   75.625,   76.875,   78.125,   79.375,   80.625, & 
  &   81.875,   83.125,   84.375,   85.625,   86.875, & 
  &   88.125,   89.375,   90.625,   91.875,   93.125, & 
  &   94.375,   95.625,   96.875,   98.125,   99.375, & 
  &  100.625,  101.875,  103.125,  104.375,  105.625, & 
  &  106.875,  108.125,  109.375,  110.625,  111.875, & 
  &  113.125,  114.375,  115.625,  116.875,  118.125, & 
  &  119.375,  120.625,  121.875,  123.125,  124.375, & 
  &  125.625,  126.875,  128.125,  129.375,  130.625, & 
  &  131.875,  133.125,  134.375,  135.625,  136.875, & 
  &  138.125,  139.375,  140.625,  141.875,  143.125, & 
  &  144.375,  145.625,  146.875,  148.125,  149.375, & 
  &  150.625,  151.875,  153.125,  154.375,  155.625, & 
  &  156.875,  158.125,  159.375,  160.625,  161.875, & 
  &  163.125,  164.375,  165.625,  166.875,  168.125, & 
  &  169.375,  170.625,  171.875,  173.125,  174.375, & 
  &  175.625,  176.875,  178.125,  179.375 /) 

  ! Latitude edges, GEOS-4/fvDAS 1 x 1.25 grid
  REAL*8  :: yedge_1x125(J1x125+1) = (/            &
  &  -90.00,  -89.50,  -88.50,  -87.50,  -86.50,   &
  &  -85.50,  -84.50,  -83.50,  -82.50,  -81.50,   &
  &  -80.50,  -79.50,  -78.50,  -77.50,  -76.50,   &
  &  -75.50,  -74.50,  -73.50,  -72.50,  -71.50,   & 
  &  -70.50,  -69.50,  -68.50,  -67.50,  -66.50,   & 
  &  -65.50,  -64.50,  -63.50,  -62.50,  -61.50,   & 
  &  -60.50,  -59.50,  -58.50,  -57.50,  -56.50,   & 
  &  -55.50,  -54.50,  -53.50,  -52.50,  -51.50,   & 
  &  -50.50,  -49.50,  -48.50,  -47.50,  -46.50,   &  
  &  -45.50,  -44.50,  -43.50,  -42.50,  -41.50,   & 
  &  -40.50,  -39.50,  -38.50,  -37.50,  -36.50,   & 
  &  -35.50,  -34.50,  -33.50,  -32.50,  -31.50,   & 
  &  -30.50,  -29.50,  -28.50,  -27.50,  -26.50,   & 
  &  -25.50,  -24.50,  -23.50,  -22.50,  -21.50,   & 
  &  -20.50,  -19.50,  -18.50,  -17.50,  -16.50,   & 
  &  -15.50,  -14.50,  -13.50,  -12.50,  -11.50,   & 
  &  -10.50,   -9.50,   -8.50,   -7.50,   -6.50,   & 
  &   -5.50,   -4.50,   -3.50,   -2.50,   -1.50,   & 
  &   -0.50,    0.50,    1.50,    2.50,    3.50,   & 
  &    4.50,    5.50,    6.50,    7.50,    8.50,   & 
  &    9.50,   10.50,   11.50,   12.50,   13.50,   & 
  &   14.50,   15.50,   16.50,   17.50,   18.50,   & 
  &   19.50,   20.50,   21.50,   22.50,   23.50,   & 
  &   24.50,   25.50,   26.50,   27.50,   28.50,   &  
  &   29.50,   30.50,   31.50,   32.50,   33.50,   & 
  &   34.50,   35.50,   36.50,   37.50,   38.50,   & 
  &   39.50,   40.50,   41.50,   42.50,   43.50,   &
  &   44.50,   45.50,   46.50,   47.50,   48.50,   &
  &   49.50,   50.50,   51.50,   52.50,   53.50,   &
  &   54.50,   55.50,   56.50,   57.50,   58.50,   &
  &   59.50,   60.50,   61.50,   62.50,   63.50,   & 
  &   64.50,   65.50,   66.50,   67.50,   68.50,   & 
  &   69.50,   70.50,   71.50,   72.50,   73.50,   & 
  &   74.50,   75.50,   76.50,   77.50,   78.50,   & 
  &   79.50,   80.50,   81.50,   82.50,   83.50,   & 
  &   84.50,   85.50,   86.50,   87.50,   88.50,   & 
  &   89.50,   90.00 /)

  ! Longitude edges, GEOS 2 x 2.5 grid
  REAL*8  :: xedge_2x25(I2x25+1) = (/            &
  & -181.25, -178.75, -176.25, -173.75, -171.25, &
  & -168.75, -166.25, -163.75, -161.25, -158.75, &
  & -156.25, -153.75, -151.25, -148.75, -146.25, &
  & -143.75, -141.25, -138.75, -136.25, -133.75, &
  & -131.25, -128.75, -126.25, -123.75, -121.25, &
  & -118.75, -116.25, -113.75, -111.25, -108.75, &
  & -106.25, -103.75, -101.25,  -98.75,  -96.25, &
  &  -93.75,  -91.25,  -88.75,  -86.25,  -83.75, &
  &  -81.25,  -78.75,  -76.25,  -73.75,  -71.25, & 
  &  -68.75,  -66.25,  -63.75,  -61.25,  -58.75, &
  &  -56.25,  -53.75,  -51.25,  -48.75,  -46.25, &
  &  -43.75,  -41.25,  -38.75,  -36.25,  -33.75, &
  &  -31.25,  -28.75,  -26.25,  -23.75,  -21.25, &
  &  -18.75,  -16.25,  -13.75,  -11.25,   -8.75, &
  &   -6.25,   -3.75,   -1.25,    1.25,    3.75, &
  &    6.25,    8.75,   11.25,   13.75,   16.25, & 
  &   18.75,   21.25,   23.75,   26.25,   28.75, &
  &   31.25,   33.75,   36.25,   38.75,   41.25, &
  &   43.75,   46.25,   48.75,   51.25,   53.75, &
  &   56.25,   58.75,   61.25,   63.75,   66.25, &
  &   68.75,   71.25,   73.75,   76.25,   78.75, &
  &   81.25,   83.75,   86.25,   88.75,   91.25, &
  &   93.75,   96.25,   98.75,  101.25,  103.75, &
  &  106.25,  108.75,  111.25,  113.75,  116.25, &
  &  118.75,  121.25,  123.75,  126.25,  128.75, &
  &  131.25,  133.75,  136.25,  138.75,  141.25, &
  &  143.75,  146.25,  148.75,  151.25,  153.75, &
  &  156.25,  158.75,  161.25,  163.75,  166.25, &
  &  168.75,  171.25,  173.75,  176.25,  178.75 /)

  ! Latitude edges, GEOS 2 x 2.5 grid 
  REAL*8 :: yedge_2x25(J2x25+1) = (/            &
  &  -90.00,  -89.00,  -87.00,  -85.00,  -83.00, &
  &  -81.00,  -79.00,  -77.00,  -75.00,  -73.00, &
  &  -71.00,  -69.00,  -67.00,  -65.00,  -63.00, &
  &  -61.00,  -59.00,  -57.00,  -55.00,  -53.00, &
  &  -51.00,  -49.00,  -47.00,  -45.00,  -43.00, &
  &  -41.00,  -39.00,  -37.00,  -35.00,  -33.00, &
  &  -31.00,  -29.00,  -27.00,  -25.00,  -23.00, &
  &  -21.00,  -19.00,  -17.00,  -15.00,  -13.00, &
  &  -11.00,   -9.00,   -7.00,   -5.00,   -3.00, &
  &   -1.00,    1.00,    3.00,    5.00,    7.00, &
  &    9.00,   11.00,   13.00,   15.00,   17.00, &
  &   19.00,   21.00,   23.00,   25.00,   27.00, &
  &   29.00,   31.00,   33.00,   35.00,   37.00, &
  &   39.00,   41.00,   43.00,   45.00,   47.00, &
  &   49.00,   51.00,   53.00,   55.00,   57.00, &
  &   59.00,   61.00,   63.00,   65.00,   67.00, &
  &   69.00,   71.00,   73.00,   75.00,   77.00, &
  &   79.00,   81.00,   83.00,   85.00,   87.00, &
  &   89.00,   90.00 /)

  ! Longitude edges, GEOS 4 x 5 grid 
  REAL*8 :: xedge_4x5(I4x5+1) = (/              &
  & -182.50, -177.50, -172.50, -167.50, -162.50, &  
  & -157.50, -152.50, -147.50, -142.50, -137.50, &
  & -132.50, -127.50, -122.50, -117.50, -112.50, &
  & -107.50, -102.50,  -97.50,  -92.50,  -87.50, &
  &  -82.50,  -77.50,  -72.50,  -67.50,  -62.50, &
  &  -57.50,  -52.50,  -47.50,  -42.50,  -37.50, &
  &  -32.50,  -27.50,  -22.50,  -17.50,  -12.50, &
  &   -7.50,   -2.50,    2.50,    7.50,   12.50, & 
  &   17.50,   22.50,   27.50,   32.50,   37.50, & 
  &   42.50,   47.50,   52.50,   57.50,   62.50, & 
  &   67.50,   72.50,   77.50,   82.50,   87.50, & 
  &   92.50,   97.50,  102.50,  107.50,  112.50, &
  &  117.50,  122.50,  127.50,  132.50,  137.50, &
  &  142.50,  147.50,  152.50,  157.50,  162.50, & 
  &  167.50,  172.50,  177.50 /)

  ! Latitude edges, GEOS 4 x 5 grid
  REAL*8  :: yedge_4x5(J4x5+1) = (/              &
  &  -90.00,  -88.00,  -84.00,  -80.00,  -76.00, &   
  &  -72.00,  -68.00,  -64.00,  -60.00,  -56.00, & 
  &  -52.00,  -48.00,  -44.00,  -40.00,  -36.00, & 
  &  -32.00,  -28.00,  -24.00,  -20.00,  -16.00, & 
  &  -12.00,   -8.00,   -4.00,    0.00,    4.00, & 
  &    8.00,   12.00,   16.00,   20.00,   24.00, & 
  &   28.00,   32.00,   36.00,   40.00,   44.00, & 
  &   48.00,   52.00,   56.00,   60.00,   64.00, & 
  &   68.00,   72.00,   76.00,   80.00,   84.00, & 
  &   88.00,   90.00 /)

CONTAINS

!------------------------------------------------------------------------------

  SUBROUTINE regrid_GEMto4x5( iv, q1, q2 )

    !===================================================================
    ! Subroutine regrid1x125to4x5 is a wrapper for MAP_A2A, which 
    ! regrids from the GEOS-4/fvdAS 1 x 1.25 grid to the GEOS 4 x 5
    ! grid. (bmy, 4/8/02)
    !  
    ! Arguments as Input:
    ! ------------------------------------------------------------------
    ! (1) IV (INTEGER) : IV = 0 is scalar field; IV = 1 is vector field
    ! (2) Q1 (REAL*4 ) : Input data on 1 x 1.25 grid
    !
    !  Arguments as Input:
    ! ------------------------------------------------------------------
    ! (3) Q2 (REAL*4 ) : Output data on 4 x 5 grid
    !===================================================================

    ! Arguments
    INTEGER,  INTENT(IN)  :: iv
    REAL*8, INTENT(IN)  :: q1(IGEM,JGEM)
    REAL*8, INTENT(OUT) :: q2(I4x5,J4x5)

    ! Local variables
    INTEGER               :: j
    REAL*8                :: sin1(JGEM+1), sin2(J4x5+1)
    REAL*8, PARAMETER   :: D2R = 3.141592658979323d0 / 180d0

    ! REGRIDGEOS begins here!
    ! Compute sine of GEM lat edges
    DO J = 1, JGEM+1
       sin1(j) = DSIN( yedge_GEM(j) * D2R )
    ENDDO

    ! Compute sine of 2 x 2.5 lat edges
    DO J = 1, J4x5+1
       sin2(j) = DSIN( yedge_4x5(j) * D2R )
    ENDDO

    ! Call MAP_A2A to do the horizontal regridding
    CALL map_a2a( IGEM, JGEM, xedge_GEM, sin1, q1, &
                  I4x5,   J4x5,   xedge_4x5,   sin2, q2, 0, iv )

  END SUBROUTINE regrid_GEMto4x5

!------------------------------------------------------------------------------
!          Harvard University Atmospheric Chemistry Modeling Group            !
!------------------------------------------------------------------------------
!BOP
!
! !IROUTINE: map_a2a
!
! !DESCRIPTION: Subroutine MAP\_A2A is a horizontal arbitrary grid to arbitrary
!  grid conservative high-order mapping regridding routine by S-J Lin.
!\\
!\\
! !INTERFACE:
!
!  (1 ) INLON   (REAL*8   ) : Longitude edges of input grid
!  (2 ) INSIN   (REAL*8   ) : Sine of input grid latitude edges
!  (3 ) INGRID  (REAL*8   ) : Data array to be regridded

  SUBROUTINE map_a2a( im, jm, lon1, sin1, q1, &
                      in, jn, lon2, sin2, q2, ig, iv)
!
! !INPUT PARAMETERS:
!
    ! Longitude and Latitude dimensions of INPUT grid
    INTEGER, INTENT(IN)  :: im, jm

    ! Longitude and Latitude dimensions of OUTPUT grid
    INTEGER, INTENT(IN)  :: in, jn

    ! IG=0: pole to pole; 
    ! IG=1 J=1 is half-dy north of south pole
    INTEGER, INTENT(IN)  :: ig

    ! IV=0: Regrid scalar quantity
    ! IV=1: Regrid vector quantity
    INTEGER, INTENT(IN)  :: iv

    ! Longitude edges (degrees) of INPUT and OUTPUT grids
    REAL*8,  INTENT(IN)  :: lon1(im+1), lon2(in+1)

    ! Sine of Latitude Edges (radians) of INPUT and OUTPUT grids
    REAL*8,  INTENT(IN)  :: sin1(jm+1), sin2(jn+1)

    ! Quantity on INPUT grid
    REAL*8,  INTENT(IN)  :: q1(im,jm)
!
! !OUTPUT PARAMETERS:
!
    ! Regridded quantity on OUTPUT grid
    REAL*8,  INTENT(OUT) :: q2(in,jn)
!
!  !REVISION HISTORY:
!  (1) Original subroutine by S-J Lin.  Converted to F90 freeform format
!      and inserted into "Geos3RegridModule" by Bob Yantosca (9/21/00)
!  (2) Added F90 type declarations to be consistent w/ TypeModule.f90.
!      Also updated comments. (bmy, 9/21/00)
!  21 Sep 2000 - R. Yantosca - Initial version
!  27 Aug 2012 - R. Yantosca - Add parallel DO loops
!EOP
!------------------------------------------------------------------------------
!BOC
!
! !LOCAL VARIABLES:
!
    INTEGER :: i,j,k
    REAL*8  :: qtmp(in,jm)

    !===================================================================
    ! E-W regridding
    !===================================================================    
    IF ( im .eq. in ) THEN

       ! Don't call XMAP if both grids have the same # of longitudes
       ! but save the input data in the QTMP array
       !$OMP PARALLEL DO       &
       !$OMP DEFAULT( SHARED ) &
       !$OMP PRIVATE( I, J )
       DO j=1,jm-ig
       DO i=1,im
          qtmp(i,j+ig) = q1(i,j+ig)
       ENDDO
       ENDDO
       !$OMP END PARALLEL DO

    ELSE

       ! Otherwise, call XMAP to regrid in the E-W direction
       CALL xmap(im, jm-ig, lon1, q1(1,1+ig),in, lon2, qtmp(1,1+ig) )

    ENDIF
    
    !===================================================================
    ! N-S regridding
    !===================================================================    
    IF ( jm .eq. jn ) THEN

       ! Don't call XMAP if both grids have the same # of longitudes,
       ! but assign the value of QTMP to the output Q2 array
       !$OMP PARALLEL DO       &
       !$OMP DEFAULT( SHARED ) &
       !$OMP PRIVATE( I, J )      
       DO j=1,jm-ig
       DO i=1,in
          q2(i,j+ig) = qtmp(i,j+ig)
       ENDDO
       ENDDO
       !$OMP END PARALLEL DO

    ELSE

       ! Otherwise, call YMAP to regrid in the N-S direction
       CALL ymap(in, jm, sin1, qtmp(1,1+ig), jn, sin2, q2(1,1+ig), ig, iv)

    ENDIF

  END SUBROUTINE map_a2a
!EOC
!------------------------------------------------------------------------------
!                   Prasad Kasibhatla - Duke University                       !
!------------------------------------------------------------------------------
!BOP
!
! !IROUTINE: ymap
!
! !DESCRIPTION: Routine to perform area preserving mapping in N-S from an 
!  arbitrary resolution to another.
!\\
!\\
! !INTERFACE:
!
  SUBROUTINE ymap(im, jm, sin1, q1, jn, sin2, q2, ig, iv)
!
! !INPUT PARAMETERS:
!

    ! original E-W dimension
    INTEGER, INTENT(IN)  :: im            
    
    ! original N-S dimension
    INTEGER, INTENT(IN)  :: jm            

    ! Target N-S dimension
    INTEGER, INTENT(IN)  :: jn           
    
    ! IG=0: scalars from SP to NP (D-grid v-wind is also IG=0)
    ! IG=1: D-grid u-wind
    INTEGER, INTENT(IN)  :: ig            
  
    ! IV=0: scalar; 
    ! IV=1: vector
    INTEGER, INTENT(IN)  :: iv            
  
    ! Original southern edge of the cell sin(lat1)  
    REAL*8,  INTENT(IN)  :: sin1(jm+1-ig) 
    
    ! Original data at center of the cell
    REAL*8,  INTENT(IN)  :: q1(im,jm)      
    
    ! Target cell's southern edge sin(lat2)
    REAL*8,  INTENT(IN)  :: sin2(jn+1-ig) 
!
! !OUTPUT PARAMETERS:
!
    ! Mapped data at the target resolution
    REAL*8,  INTENT(OUT) :: q2(im,jn)     
!
! !REMARKS:
!
!   sin1 (1) = -1 must be south pole; sin1(jm+1)=1 must be N pole.
!
!   sin1(1) < sin1(2) < sin1(3) < ... < sin1(jm) < sin1(jm+1)
!   sin2(1) < sin2(2) < sin2(3) < ... < sin2(jn) < sin2(jn+1)!
!
! !AUTHOR:
!   Developer: Prasad Kasibhatla
!   March 6, 2012
!
! !REVISION HISTORY
!  06 Mar 2012 - P. Kasibhatla - Initial version
!  27 Aug 2012 - R. Yantosca   - Added parallel DO loops
!  27 Aug 2012 - R. Yantosca   - Change REAL*4 variables to REAL*8 to better
!                                ensure numerical stability
!EOP
!------------------------------------------------------------------------------
!BOC
!
! !LOCAL VARIABLES:
!
    INTEGER              :: i, j0, m, mm, j
    REAL*8               :: dy1(jm)
    REAL*8               :: dy
!------------------------------------------------------------------------------
! Prior to 8/27/12:
! Change REAL*4 to REAL*8, to eliminate numerical noise (bmy, 8/27/12)
!    REAL*4               :: qsum, sum
!------------------------------------------------------------------------------
    REAL*8               :: qsum, sum
    
    ! YMAP begins here!
    do j=1,jm-ig
       dy1(j) = sin1(j+1) - sin1(j)
    enddo

    !===============================================================
    ! Area preserving mapping
    !===============================================================
    
    !$OMP PARALLEL DO                          &
    !$OMP DEFAULT( SHARED                    ) &
    !$OMP PRIVATE( I, J0, J, M, QSUM, MM, DY )
    do 1000 i=1,im
       j0 = 1
       do 555 j=1,jn-ig
       do 100 m=j0,jm-ig
             
          !=========================================================
          ! locate the southern edge: sin2(i)
          !=========================================================
          if(sin2(j) .ge. sin1(m) .and. sin2(j) .le. sin1(m+1)) then
             
             if(sin2(j+1) .le. sin1(m+1)) then
                
                ! entire new cell is within the original cell
                q2(i,j)=q1(i,m)
                j0 = m
                goto 555
             else
                
                ! South most fractional area
                qsum=(sin1(m+1)-sin2(j))*q1(i,m)
                
                do mm=m+1,jm-ig
                   
                   ! locate the northern edge: sin2(j+1)
                   if(sin2(j+1) .gt. sin1(mm+1) ) then
                      
                      ! Whole layer
                      qsum = qsum + dy1(mm)*q1(i,mm)
                   else
                      
                      ! North most fractional area
                      dy = sin2(j+1)-sin1(mm)
                      qsum=qsum+dy*q1(i,mm)
                      j0 = mm
                      goto 123
                   endif
                enddo
                goto 123
             endif
          endif
100    continue
123    q2(i,j) = qsum / ( sin2(j+1) - sin2(j) )
555    continue
1000 continue
     !$OMP END PARALLEL DO

     !===================================================================
     ! Final processing for poles
     !===================================================================
     if ( ig .eq. 0 .and. iv .eq. 0 ) then
         
!------------------------------------------------------------------------------
! Prior to 8/27/12:
! Change REAL*4 to REAL*8, to eliminate numerical noise (bmy, 8/27/12)
!        ! South pole
!        sum = 0.
!        do i=1,im
!           sum = sum + q2(i,1)
!        enddo
!
!        sum = sum / float(im)
!        do i=1,im
!           q2(i,1) = sum
!        enddo
!
!        ! North pole:
!        sum = 0.
!        do i=1,im
!           sum = sum + q2(i,jn)
!        enddo
!
!        sum = sum / float(im)
!        do i=1,im
!           q2(i,jn) = sum
!        enddo
!------------------------------------------------------------------------------
        ! South pole
        sum = 0.d0
        do i=1,im
           sum = sum + q2(i,1)
        enddo

        sum = sum / DBLE( im )
        do i=1,im
           q2(i,1) = sum
        enddo

        ! North pole:
        sum = 0.d0
        do i=1,im
           sum = sum + q2(i,jn)
        enddo

        sum = sum / DBLE( im )
        do i=1,im
           q2(i,jn) = sum
        enddo

     endif

   END SUBROUTINE YMAP
!EOC
!------------------------------------------------------------------------------
!                   Prasad Kasibhatla - Duke University                       !
!------------------------------------------------------------------------------
!BOP
!
! !IROUTINE: xmap
!
! !DESCRIPTION: Routine to perform area preserving mapping in E-W from an 
!  arbitrary resolution to another.
!  Periodic domain will be assumed, i.e., the eastern wall bounding cell
!  im is lon1(im+1) = lon1(1); Note the equal sign is true geographysically.
!\\
!\\
! !INTERFACE:
!
  SUBROUTINE xmap(im, jm, lon1, q1, in, lon2, q2)
!
! !INPUT PARAMETERS:
!
    ! Original E-W dimension
    INTEGER, INTENT(IN)  :: im           

    ! Target E-W dimension
    INTEGER, INTENT(IN)  :: in           
  
    ! Original N-S dimension
    INTEGER, INTENT(IN)  :: jm           
  
    ! Original western edge of the cell
    REAL*8,  INTENT(IN)  :: lon1(im+1)   
  
    ! Original data at center of the cell
    REAL*8,  INTENT(IN)  :: q1(im,jm)    
  
    ! Target cell's western edge
    REAL*8,  INTENT(IN)  :: lon2(in+1)   
!
! !OUTPUT PARAMETERS:
!
    ! Mapped data at the target resolution
    REAL*8,  INTENT(OUT) :: q2(in,jm)    
!
! !REMARKS:
!   lon1(1) < lon1(2) < lon1(3) < ... < lon1(im) < lon1(im+1)
!   lon2(1) < lon2(2) < lon2(3) < ... < lon2(in) < lon2(in+1)
!
! !AUTHOR:
!   Developer: Prasad Kasibhatla
!   March 6, 2012
!
! !REVISION HISTORY
!  06 Mar 2012 - P. Kasibhatla - Initial version
!  27 Aug 2012 - R. Yantosca   - Added parallel DO loops
!  27 Aug 2012 - R. Yantosca   - Change REAL*4 variables to REAL*8 to better
!                                ensure numerical stability
!EOP
!------------------------------------------------------------------------------
!BOC
!
! !LOCAL VARIABLES:
!
    INTEGER              :: i1, i2, i, i0, m, mm, j
    REAL*8               :: qtmp(-im:im+im)
    REAL*8               :: x1(-im:im+im+1)
    REAL*8               :: dx1(-im:im+im)
    REAL*8               :: dx
!------------------------------------------------------------------------------
! Prior to 8/27/12:
! Change REAL*4 to REAL*8, to eliminate numerical noise (bmy, 8/27/12)
!    REAL*4               :: qsum
!------------------------------------------------------------------------------
    REAL*8               :: qsum
    LOGICAL              :: found

    ! XMAP begins here!
    do i=1,im+1
       x1(i) = lon1(i)
    enddo
  
    do i=1,im
       dx1(i) = x1(i+1) - x1(i)
    enddo
    
    !===================================================================
    ! check to see if ghosting is necessary
    ! Western edge:
    !===================================================================
    found = .false.
    i1 = 1
    do while ( .not. found )
       if( lon2(1) .ge. x1(i1) ) then
          found = .true.
       else
          i1 = i1 - 1
          if (i1 .lt. -im) then
             write(6,*) 'failed in xmap'
             stop
          else
             x1(i1) = x1(i1+1) - dx1(im+i1)
             dx1(i1) = dx1(im+i1)
          endif
       endif
    enddo
    
    !===================================================================
    ! Eastern edge:
    !===================================================================
    found = .false.
    i2 = im+1
    do while ( .not. found )
       if( lon2(in+1) .le. x1(i2) ) then
          found = .true.
       else
          i2 = i2 + 1
          if (i2 .gt. 2*im) then
             write(6,*) 'failed in xmap'
             stop
          else
             dx1(i2-1) = dx1(i2-1-im)
             x1(i2) = x1(i2-1) + dx1(i2-1)
          endif
       endif
    enddo

    !$OMP PARALLEL DO                                &
    !$OMP DEFAULT( SHARED                          ) &
    !$OMP PRIVATE( J, QTMP, I, I0, M, QSUM, MM, DX )
    do 1000 j=1,jm
       
       !=================================================================
       ! Area preserving mapping
       !================================================================
       
       qtmp(0)=q1(im,j)
       do i=1,im
          qtmp(i)=q1(i,j)
       enddo
       qtmp(im+1)=q1(1,j)

       ! check to see if ghosting is necessary
       ! Western edge
       if ( i1 .le. 0 ) then
          do i=i1,0
             qtmp(i) = qtmp(im+i)
          enddo
       endif
       
       ! Eastern edge:
       if ( i2 .gt. im+1 ) then
          do i=im+1,i2-1
             qtmp(i) = qtmp(i-im)
          enddo
       endif
        
       i0 = i1

       do 555 i=1,in
       do 100 m=i0,i2-1

          !=============================================================  
          ! locate the western edge: lon2(i)
          !=============================================================  
          if(lon2(i) .ge. x1(m) .and. lon2(i) .le. x1(m+1)) then
             
             if(lon2(i+1) .le. x1(m+1)) then
                
                ! entire new grid is within the original grid
                q2(i,j)=qtmp(m)
                i0 = m
                goto 555
             else
  
                ! Left most fractional area
                qsum=(x1(m+1)-lon2(i))*qtmp(m)
                do mm=m+1,i2-1
                   
                   ! locate the eastern edge: lon2(i+1)
                   if(lon2(i+1) .gt. x1(mm+1) ) then
                      
                      ! Whole layer
                      qsum = qsum + dx1(mm)*qtmp(mm)
                      
                   else
                      ! Right most fractional area
                      dx = lon2(i+1)-x1(mm)
                      qsum=qsum+dx*qtmp(mm)
                      i0 = mm
                      goto 123
                   endif
                enddo
                goto 123
             endif
          endif
100    continue
123    q2(i,j) = qsum / ( lon2(i+1) - lon2(i) )
555    continue
1000 continue
     !$OMP END PARALLEL DO

  END SUBROUTINE xmap


!-----------------------------------------------------------------------------

END MODULE FvdasRegridModule
