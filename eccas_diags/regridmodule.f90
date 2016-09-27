! $Id $
MODULE RegridModule

  !====================================================================
  ! Module "RegridModule" contains arrays and variables used
  ! to regrid data to different resolutions.
  !====================================================================

  USE TypeModule

  IMPLICIT NONE

  ! Size parameters for the generic 1 x 1 grid
  INTEGER*4, PARAMETER  :: I1x1gen=360, J1x1gen=180, L1x1gen=55    

  ! Size parameters for the GEOS-3, 1 x 1 grid
  INTEGER*4, PARAMETER  :: I1x1=360,   J1x1=181,   L1x1=55    

  ! Size parameters for the GEOS-4/fvDAS 1 x 1.25 grid
  INTEGER*4, PARAMETER  :: I1x125=288, J1x125=181, L1x125=55

  ! Size parameters for the GEOS 2 x 2.5 grid
  INTEGER*4, PARAMETER  :: I2x25=144,  J2x25=91,   L2x25=55

  ! Size parameters for the GEOS 4 x 5 grid
  INTEGER*4, PARAMETER  :: I4x5=72,    J4x5=46,    L4x5=55 

  ! Size parameters for T47 Gaussian grid (averge of 3.75 x 3.75)
  INTEGER*4, PARAMETER  :: IT47=96,    JT47=48,    LT47=1 

  ! Latitude/Longitude edges, generic 1x1 grid
  REAL*4:: xedge_1x1gen(I1x1gen+1) 
  REAL*4:: yedge_1x1gen(J1x1gen+1)


!  Latitude edges for Guassian T47 grid
  REAL*4:: yedge_T47(JT47+1) = (/  &
  &  -90.0000, -85.3190, -81.6280, -77.9236, -74.2159,           &
  &  -70.5068, -66.7970, -63.0868, -59.3763, -55.6657, -51.9549, &
  &  -48.2441, -44.5331, -40.8221, -37.1111, -33.4001, -29.6890, &
  &  -25.9779, -22.2668, -18.5557, -14.8446, -11.1335,  -7.4223, &
  &   -3.7112,   0.0000,   3.7112,   7.4223,  11.1335,  14.8446, &
  &   18.5557,  22.2668,  25.9779,  29.6890,  33.4001,  37.1111, &
  &   40.8221,  44.5331,  48.2441,  51.9549,  55.6657,  59.3763, &
  &   63.0868,  66.7970,  70.5068,  74.2159,  77.9236,  81.6280, &
  &   85.3190,  90.0000/)

!  Longitude edges for Guassian T47 grid
  REAL*4::  xedge_T47(IT47+1) = (/  &
  & -180.0, -176.25, -172.5, -168.75, -165.0, -161.25, -157.5, -153.75, &
  & -150.0, -146.25, -142.5, -138.75, -135.0, -131.25, -127.5, -123.75, &
  & -120.0, -116.25, -112.5, -108.75, -105.0, -101.25,  -97.5,  -93.75, &
  &  -90.0,  -86.25,  -82.5,  -78.75,  -75.0,  -71.25,  -67.5,  -63.75, &
  &  -60.0,  -56.25,  -52.5,  -48.75,  -45.0,  -41.25,  -37.5,  -33.75, &
  &  -30.0,  -26.25,  -22.5,  -18.75,  -15.0,  -11.25,   -7.5,   -3.75, &
  &    0.0, 3.75, 7.5, 11.25,   15.0,   18.75,   22.5,    26.25, 30.00, &
  &   33.75,  37.50,  41.25,  45.00,  48.75,  52.50,  56.25,  60.00, &
  &   63.75,  67.50,  71.25,  75.00,  78.75,  82.50,  86.25,  90.00, &
  &   93.75,  97.50, 101.25, 105.00, 108.75, 112.50, 116.25, 120.00, &
  &  123.75, 127.50, 131.25, 135.00, 138.75, 142.50, 146.25, 150.00, &
  &  153.75, 157.50, 161.25, 165.00, 168.75, 172.50, 176.25, 180.00/) 
    
  ! Longitude edges for GEOS-4, 1 x 1.25 grid
  REAL*4 :: xedge_1x125(I1x125+1) = (/              &
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

  ! Latitude edges, GEOS-4, 1 x 1.25 grid
  REAL*4:: yedge_1x125(J1x125+1) = (/            &
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
  REAL*4:: xedge_2x25(I2x25+1) = (/            &
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
  REAL*4:: yedge_2x25(J2x25+1) = (/            &
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
  REAL*4:: xedge_4x5(I4x5+1) = (/              &
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
  REAL*4:: yedge_4x5(J4x5+1) = (/              &
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

  SUBROUTINE map_a2a( im, jm, lon1, sin1, q1, &
                      in, jn, lon2, sin2, q2, ig, iv)
!
!******************************************************************************
!  Subroutine MAP_A2A is a horizontal arbitrary grid to arbitrary grid 
!  conservative high-order mapping regridding routine by S-J Lin.
!
!  Arguments as Input:
!  ============================================================================
!  (1-2) IM, JM  (REAL*4 ) : Longitude and Latitude dimensions of INPUT grid
!  (3  ) LON1    (REAL*4 ) : Longitude edges (degrees) of INPUT grid
!  (4  ) SIN1    (REAL*4 ) : Sine of Latitude Edges (radians) of INPUT grid
!  (5  ) Q1      (REAL*4 ) : Quantity on INPUT grid
!  (6-7) IN, JN  (INTEGER) : Longitude and Latitude dimensions of OUTPUT grid
!  (8  ) LON2    (REAL*4 ) : Longitude edges (degrees) of INPUT grid
!  (9  ) SIN2    (REAL*4 ) : Sine of Latitude Edges (radians) of OUTPUT grid
!  (11 ) IG      (INTEGER) : IG=0: pole to pole; 
!                            IG=1 J=1 is half-dy north of south pole
!  (12 ) IV      (INTEGER) : IV=0: Regrid scalar quantity
!                            IV=1: Regrid vector quantity (e.g. U & V winds)
!  Arguments as Output:
!  ============================================================================
!  (10 ) Q1      (REAL*4 ) : Regridded quantity on OUTPUT grid
!
!  NOTES:
!  (1) Original subroutine by S-J Lin.  Converted to F90 freeform format
!      and inserted into "Geos3RegridModule" by Bob Yantosca (9/21/00)
!
!  (2) Added F90 type declarations to be consistent w/ TypeModule.f90.
!      Also updated comments. (bmy, 9/21/00)
!******************************************************************************
!
    ! Arguments
    INTEGER*4, INTENT(IN)  :: im, jm, in, jn, ig, iv
    REAL*4,     INTENT(IN)  :: lon1(im+1), lon2(in+1)
    REAL*4,     INTENT(IN)  :: sin1(jm+1), sin2(jn+1)
    REAL*4,     INTENT(IN)  :: q1(im,jm)
    REAL*4,     INTENT(OUT) :: q2(in,jn)

    ! Local variables
    INTEGER*4              :: i,j,k
    REAL*4                  :: qtmp(in,jm)

    !===================================================================
    ! MAP_A2A begins here!
    !
    ! Mapping in the E-W direction
    ! If both grids have the same longitude dimension, don't call XMAP
    !===================================================================    
    IF ( im .eq. in ) THEN
       DO j=1,jm-ig
       DO i=1,im
          qtmp(i,j+ig) = q1(i,j+ig)
       ENDDO
       ENDDO
    ELSE
       CALL xmap(im, jm-ig, lon1, q1(1,1+ig),in, lon2, qtmp(1,1+ig) )
    ENDIF
    
    !===================================================================
    ! Mapping in the N-S direction
    ! If both grids have the same latitude dimension, don't call YMAP 
    !===================================================================    
    IF ( jm .eq. jn ) THEN
       DO j=1,jm-ig
       DO i=1,in
          q2(i,j+ig) = qtmp(i,j+ig)
       ENDDO
       ENDDO
    ELSE
	 CALL ymap(in, jm, sin1, qtmp(1,1+ig), jn, sin2, q2(1,1+ig), ig, iv)
    ENDIF

  END SUBROUTINE map_a2a

!------------------------------------------------------------------------------

  SUBROUTINE ymap(im, jm, sin1, q1, jn, sin2, q2, ig, iv)
!
!******************************************************************************
!  Routine to perform area preserving mapping in N-S from an arbitrary
!  resolution to another.
!
!  sin1 (1) = -1 must be south pole; sin1(jm+1)=1 must be N pole.
!
!  sin1(1) < sin1(2) < sin1(3) < ... < sin1(jm) < sin1(jm+1)
!  sin2(1) < sin2(2) < sin2(3) < ... < sin2(jn) < sin2(jn+1)
!
!  Developer: S.-J. Lin
!  First version: piece-wise constant mapping
!  Apr 1, 2000
!  Last modified:
!
!  Converted to F90 freeform format and added to "Geos3RegridModule"
!  (bmy, 9/21/00)
!******************************************************************************
!
    ! Arguments
    INTEGER*4, INTENT(IN)  :: im            ! original E-W dimension
    INTEGER*4, INTENT(IN)  :: jm            ! original N-S dimension
    INTEGER*4, INTENT(IN)  :: jn            ! Target N-S dimension
    INTEGER*4, INTENT(IN)  :: ig            ! ig=0: scalars from SP to NP
                                               ! D-grid v-wind is also ig 0
                                               ! ig=1: D-grid u-wind
    INTEGER*4, INTENT(IN)  :: iv            ! iv=0 scalar; iv=1: vector
    REAL*4,     INTENT(IN)  :: sin1(jm+1-ig) ! original southern edge of 
                                               !  the cell sin(lat1)  
    REAL*4,     INTENT(IN)  :: q1(im,jm)     ! original data at center of 
                                               !  the cell
    REAL*4,     INTENT(IN)  :: sin2(jn+1-ig) ! Target cell's southern edge
                                               !  sin(lat2)

    REAL*4,     INTENT(OUT) :: q2(im,jn)     ! Mapped data at the 
                                               !  target resolution

    ! Local Variables
    INTEGER*4              :: i, j0, m, mm, j
    REAL*4                  :: al(im,jm), ar(im,jm), a6(im,jm), dy1(jm)
    REAL*4,     PARAMETER   :: r3 = 1./3., r23 = 2./3. 
    REAL*4                  :: pl, pr, qsum, esl, dy, psum
    
    ! YMAP begins here!
    do j=1,jm-ig
       dy1(j) = sin1(j+1) - sin1(j)
    enddo

    !===============================================================
    ! Area preserving mapping
    !===============================================================

    ! Construct subgrid PP distribution
    call ppm_lat(im, jm, ig, q1, al, ar, a6, 3, iv)
    
    !write(*,*) "MAP A2A q1   ", sum(q1) !RayNassar
    
    do 1000 i=1,im
       j0 = 1
       do 555 j=1,jn-ig
       do 100 m=j0,jm-ig

	    !=========================================================
          ! locate the southern edge: sin2(i)
          !=========================================================
          if(sin2(j) .ge. sin1(m) .and. sin2(j) .le. sin1(m+1)) then
             pl = (sin2(j)-sin1(m)) / dy1(m)
             
             if(sin2(j+1) .le. sin1(m+1)) then
                
                ! entire new cell is within the original cell
                pr = (sin2(j+1)-sin1(m)) / dy1(m)
                q2(i,j) = al(i,m) + 0.5*(a6(i,m)+ar(i,m)-al(i,m)) &
               &        *(pr+pl)-a6(i,m)*r3*(pr*(pr+pl)+pl**2)
                j0 = m
                goto 555
		 
		 else

                ! South most fractional area
                qsum = (sin1(m+1)-sin2(j))*(al(i,m)+0.5*(a6(i,m)+ &
                &              ar(i,m)-al(i,m))*(1.+pl)-a6(i,m)*  &
                &               (r3*(1.+pl*(1.+pl))))

                do mm=m+1,jm-ig

                   ! locate the eastern edge: sin2(j+1)
                   if(sin2(j+1) .gt. sin1(mm+1) ) then

                      ! Whole layer
                      qsum = qsum + dy1(mm)*q1(i,mm)
                   else

                      ! North most fractional area
                      dy = sin2(j+1)-sin1(mm)
                      esl = dy / dy1(mm)
                      qsum = qsum + dy*(al(i,mm)+0.5*esl* &
                     &      (ar(i,mm)-al(i,mm)+a6(i,mm)*(1.-r23*esl)))
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

    !===================================================================
    ! Final processing for poles
    !===================================================================
    if ( ig .eq. 0 .and. iv .eq. 0 ) then
        
       ! South pole
       psum = 0.
       do i=1,im
          psum = psum + q2(i,1)
       enddo
        
       psum = psum / float(im)
       do i=1,im
          q2(i,1) = psum
       enddo
        
       ! North pole:
       psum = 0.
       do i=1,im
          psum = psum + q2(i,jn)
       enddo
        
       psum = psum / float(im)
       do i=1,im
          q2(i,jn) = psum
       enddo

    endif

  END SUBROUTINE YMAP

!------------------------------------------------------------------------------

  SUBROUTINE ppm_lat(im, jm, ig, q, al, ar, a6, jord, iv)
!
!******************************************************************************
!  Subroutine PPM_LAT is called by YMAP.  Written by S-J Lin, and
!  converted to F90 freeform format by Bob Yantosca. (bmy, 9/21/00)
!
!  INPUT
!  ig=0: scalar pole to pole
!  ig=1: D-grid u-wind; not defined at poles because of staggering
!******************************************************************************
!
    ! Arguments
    INTEGER*4        :: im, jm          !  Dimensions
    INTEGER*4        :: ig
    REAL*4            :: q(im,jm-ig)
    REAL*4            :: al(im,jm-ig)
    REAL*4            :: ar(im,jm-ig)
    REAL*4            :: a6(im,jm-ig)
    INTEGER*4        :: jord
    INTEGER*4        :: iv              ! iv=0 scalar
                                           ! iv=1 vector
    ! Local
    REAL*4            :: dm(im,jm-ig)
    REAL*4, PARAMETER :: r3 = 1./3. 
    INTEGER*4        :: i, j, im2, iop, jm1
    REAL*4            :: tmp, qmax, qmin, qop
    
    ! PPM_LAT begins here
    ! Compute dm: linear slope
    do j=2,jm-1-ig
       do i=1,im
          dm(i,j) = 0.25*(q(i,j+1) - q(i,j-1))
          qmax = max(q(i,j-1),q(i,j),q(i,j+1)) - q(i,j)
          qmin = q(i,j) - min(q(i,j-1),q(i,j),q(i,j+1))
          dm(i,j) = sign(min(abs(dm(i,j)),qmin,qmax),dm(i,j))
       enddo
    enddo

    im2 = im/2
    jm1 = jm - 1

    ! Poles:
    if (iv .eq. 1 ) then

       !===============================================================
       ! u-wind (ig=1)
       ! v-wind (ig=0)
       !===============================================================

       ! SP
       do i=1,im
          if( i .le. im2) then
             qop = -q(i+im2,2-ig)
          else
             qop = -q(i-im2,2-ig)
          endif
          tmp = 0.25*(q(i,2) - qop)
          qmax = max(q(i,2),q(i,1), qop) - q(i,1)
          qmin = q(i,1) - min(q(i,2),q(i,1), qop)
          dm(i,1) = sign(min(abs(tmp),qmax,qmin),tmp)
       enddo
       
       ! NP
       do i=1,im
          if( i .le. im2) then
             qop = -q(i+im2,jm1)
          else
             qop = -q(i-im2,jm1)
          endif
          tmp = 0.25*(qop - q(i,jm1-ig))
          qmax = max(qop,q(i,jm-ig), q(i,jm1-ig)) - q(i,jm-ig)
          qmin = q(i,jm-ig) - min(qop,q(i,jm-ig), q(i,jm1-ig))
          dm(i,jm-ig) = sign(min(abs(tmp),qmax,qmin),tmp)
       enddo
    else
        
       !===============================================================
       ! Scalar:
       ! This code segment currently works only if ig=0
       !===============================================================

       ! SP
       do i=1,im2
          tmp = 0.25*(q(i,2)-q(i+im2,2))
          qmax = max(q(i,2),q(i,1), q(i+im2,2)) - q(i,1)
          qmin = q(i,1) - min(q(i,2),q(i,1), q(i+im2,2))
          dm(i,1) = sign(min(abs(tmp),qmax,qmin),tmp)
       enddo
        
       do i=im2+1,im
          dm(i, 1) =  - dm(i-im2, 1)
       enddo

       ! NP
       do i=1,im2
          tmp = 0.25*(q(i+im2,jm1)-q(i,jm1))
          qmax = max(q(i+im2,jm1),q(i,jm), q(i,jm1)) - q(i,jm)
          qmin = q(i,jm) - min(q(i+im2,jm1),q(i,jm), q(i,jm1))
          dm(i,jm) = sign(min(abs(tmp),qmax,qmin),tmp)
       enddo

       do i=im2+1,im
          dm(i,jm) =  - dm(i-im2,jm)
       enddo
     endif
      
     do j=2,jm-ig
        do i=1,im
           al(i,j) = 0.5*(q(i,j-1)+q(i,j)) + r3*(dm(i,j-1) - dm(i,j))
        enddo
     enddo
      
     do j=1,jm-1-ig
        do i=1,im
           ar(i,j) = al(i,j+1)
        enddo
     enddo
     
     if ( iv .eq. 1 ) then
        
        if ( ig .eq. 0 ) then

           !============================================================
           ! Vector: ig=0
           !============================================================
           do i=1,im2
              al(i,    1) = -al(i+im2,2)
              al(i+im2,1) = -al(i,    2)
           enddo
           
           do i=1,im2
              ar(i,    jm) = -ar(i+im2,jm1)
              ar(i+im2,jm) = -ar(i,    jm1)
           enddo
        else

           !============================================================
           ! ig=1 : SP
           !============================================================
           do i=1,im
              if( i .le. im2) then
                 iop = i+im2
              else
                 iop = i-im2
              endif
              al(i,1) = 0.5*(q(i,1)-q(iop,1)) - r3*(dm(iop,1) + dm(i,1))
           enddo

           !============================================================
           ! NP
           !============================================================
           do i=1,im
              if( i .le. im2) then
                 iop = i+im2
              else
                 iop = i-im2
              endif
              ar(i,jm1) = 0.5*(q(i,jm1)-q(iop,jm1)) - &
             &                 r3*(dm(iop,jm1) + dm(i,jm1))
            enddo
        endif
     else

        ! Scalar (works for ig=0 only):
        do i=1,im2
           al(i,    1) = al(i+im2,2)
           al(i+im2,1) = al(i,    2)
        enddo
        
        do i=1,im2
           ar(i,    jm) = ar(i+im2,jm1)
           ar(i+im2,jm) = ar(i,    jm1)
        enddo
     endif
      
     do j=1,jm-ig
        do i=1,im
           a6(i,j) = 3.*(q(i,j)+q(i,j) - (al(i,j)+ar(i,j)))
        enddo
        call lmppm(dm(1,j), a6(1,j), ar(1,j), al(1,j),  q(1,j), im, jord-3)
     enddo

  END SUBROUTINE ppm_lat

!------------------------------------------------------------------------------

  SUBROUTINE xmap(im, jm, lon1, q1, in, lon2, q2)
!
!******************************************************************************
!  Routine to perform area preserving mapping in E-W from an arbitrary
!  resolution to another.
!  Periodic domain will be assumed, i.e., the eastern wall bounding cell
!  im is lon1(im+1) = lon1(1); Note the equal sign is true geographysically.
!
!  lon1(1) < lon1(2) < lon1(3) < ... < lon1(im) < lon1(im+1)
!  lon2(1) < lon2(2) < lon2(3) < ... < lon2(in) < lon2(in+1)
!
!  Developer: S.-J. Lin
!  First version: piece-wise constant mapping
!  Apr 1, 2000
!  Last modified:
!
!  Converted to F90 freeform format and added to "Geos3RegridModule" 
!  (bmy, 9/21/00)
!******************************************************************************
!
    ! Input
    INTEGER*4, INTENT(IN)  :: im           ! original E-W dimension
    INTEGER*4, INTENT(IN)  :: in           ! Target E-W dimension
    INTEGER*4, INTENT(IN)  :: jm           ! original N-S dimension
    REAL*4,     INTENT(IN)  :: lon1(im+1)   ! original western edge of 
                                              !  the cell
    REAL*4,     INTENT(IN)  :: q1(im,jm)    ! original data at center of 
                                              !  the cell
    REAL*4,     INTENT(IN)  :: lon2(in+1)   ! Target cell's western edge
    REAL*4,     INTENT(OUT) :: q2(in,jm)    ! Mapped data at the 
                                              !  target resolution
    ! Local
    INTEGER*4              :: i1, i2, i, i0, m, mm, j

    REAL*4                  :: qtmp(-im:im+im)
    REAL*4                  :: al(-im:im+im)
    REAL*4                  :: ar(-im:im+im)
    REAL*4                  :: a6(-im:im+im)
    REAL*4                  :: x1(-im:im+im+1)
    REAL*4                  :: dx1(-im:im+im)
    REAL*4,     PARAMETER   :: r3 = 1./3., r23 = 2./3. 
    REAL*4                  :: pl, pr, qsum, esl, dx
    INTEGER*4              :: iord = 3
    logical(LGT)              :: found

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
    
    !write(6,*) 'i1,i2=',i1,i2

    do 1000 j=1,jm

       !=================================================================
       ! Area preserving mapping
       !================================================================

       ! Construct subgrid PP distribution
       call ppm_cycle(im, q1(1,j), al(1), ar(1), a6(1), qtmp(0), iord)
       
       ! check to see if ghosting is necessary
       ! Western edge
       if ( i1 .le. 0 ) then
          do i=i1,0
             qtmp(i) = qtmp(im+i)
             al(i) = al(im+i)
             ar(i) = ar(im+i)
             a6(i) = a6(im+i)
          enddo
       endif
       
       ! Eastern edge:
       if ( i2 .gt. im+1 ) then
          do i=im+1,i2-1
             qtmp(i) = qtmp(i-im)
             al(i) =   al(i-im)
             ar(i) =   ar(i-im)
             a6(i) =   a6(i-im)
          enddo
       endif
        
       i0 = i1
        
       do 555 i=1,in
       do 100 m=i0,i2-1

          !=============================================================  
          ! locate the western edge: lon2(i)
          !=============================================================  
          if(lon2(i) .ge. x1(m) .and. lon2(i) .le. x1(m+1)) then
             pl = (lon2(i)-x1(m)) / dx1(m)
             
             if(lon2(i+1) .le. x1(m+1)) then
                
                ! entire new grid is within the original grid
                pr = (lon2(i+1)-x1(m)) / dx1(m)
                q2(i,j) = al(m) + 0.5*(a6(m)+ar(m)-al(m)) &
               &                  *(pr+pl)-a6(m)*r3*(pr*(pr+pl)+pl**2)
                i0 = m
                goto 555
             else

                ! Left most fractional area
                qsum = (x1(m+1)-lon2(i))*(al(m)+0.5*(a6(m)+ &
               &              ar(m)-al(m))*(1.+pl)-a6(m)*   &
               &               (r3*(1.+pl*(1.+pl))))

                do mm=m+1,i2-1

                   ! locate the eastern edge: lon2(i+1)
                   if(lon2(i+1) .gt. x1(mm+1) ) then

                      ! Whole layer
                      qsum = qsum + dx1(mm)*qtmp(mm)

                   else
                      ! Right most fractional area
                      dx = lon2(i+1)-x1(mm)
                      esl = dx / dx1(mm)
                      qsum = qsum + dx*(al(mm)+0.5*esl* &
                     &              (ar(mm)-al(mm)+a6(mm)*(1.-r23*esl)))
                      i0 = mm
                      goto 123
                   endif
                enddo
                goto 123
             endif
          endif
100       continue
123       q2(i,j) = qsum / ( lon2(i+1) - lon2(i) )
555    continue
1000 continue

   END SUBROUTINE xmap

!------------------------------------------------------------------------------

   subroutine ppm_cycle(im, q, al, ar, a6, p, iord)
!
!******************************************************************************
!  PPM_CYCLE is called by XMAP
!  Originally written by S-J Lin -- Converted to F90 Freeform format
!  and added to Module "Geos3RegridModule" by Bob Yantosca (bmy, 9/21/00)
!******************************************************************************
!
     ! Input 
     INTEGER(SP), INTENT(IN)  :: im, iord
     REAL*4,    INTENT(IN)  :: q(1)
 
     ! Output
     REAL*4,    INTENT(OUT) :: al(1), ar(1), a6(1), p(0:im+1)

     ! local
     REAL*4                 :: dm(0:im), tmp, qmax, qmin
     INTEGER*4             :: i, lmt
     REAL*4,    PARAMETER   :: r3 = 1./3. 

     ! PPM_CYCLE begins here!
     p(0) = q(im)
     do i=1,im
        p(i) = q(i)
     enddo
     p(im+1) = q(1)

     ! 2nd order slope
     do i=1,im
        tmp = 0.25*(p(i+1) - p(i-1))
        qmax = max(p(i-1), p(i), p(i+1)) - p(i)
        qmin = p(i) - min(p(i-1), p(i), p(i+1))
        dm(i) = sign(min(abs(tmp),qmax,qmin), tmp)
     enddo
     dm(0) = dm(im)

     do i=1,im
        al(i) = 0.5*(p(i-1)+p(i)) + (dm(i-1) - dm(i))*r3
     enddo

     do i=1,im-1
        ar(i) = al(i+1)
     enddo
     ar(im) = al(1)

     if(iord .le. 6) then
        do i=1,im
           a6(i) = 3.*(p(i)+p(i)  - (al(i)+ar(i)))
        enddo
        lmt = iord - 3
        if(lmt.le.2) call lmppm(dm(1),a6(1),ar(1),al(1),p(1),im,lmt)
     else
        print*, "Doin the huynh!"
	call huynh(im, ar(1), al(1), p(1), a6(1), dm(1))
     endif

   END SUBROUTINE ppm_cycle

!-----------------------------------------------------------------------------

   SUBROUTINE lmppm(dm, a6, ar, al, p, im, lmt)
!
!******************************************************************************
!  Subroutine LMPPM is called by PPM_CYCLE.
!  Originally written by S-J Lin -- Converted to F90 freeform format
!  and added to "Geos3RegridModule" by Bob Yantosca (bmy, 9/21/00)
!
!  LMT = 0: full monotonicity
!  LMT = 1: semi-monotonic constraint (no undershoot)
!  LMT = 2: positive-definite constraint
!******************************************************************************
!
     INTEGER*4        :: im, lmt
     INTEGER*4        :: i

     REAL*4            :: a6(im),ar(im),al(im),p(im),dm(im)
     REAL*4            :: da1, da2, fmin, a6da
     REAL*4, PARAMETER :: r12 = 1./12. 

     ! LMPPM begins here!
     if(lmt.eq.0) then

        ! Full constraint
        do 100 i=1,im
           if(dm(i) .eq. 0.) then
              ar(i) = p(i)
              al(i) = p(i)
              a6(i) = 0.
           else
              da1  = ar(i) - al(i)
              da2  = da1**2
              a6da = a6(i)*da1
              if(a6da .lt. -da2) then
                 a6(i) = 3.*(al(i)-p(i))
                 ar(i) = al(i) - a6(i)
              elseif(a6da .gt. da2) then
                 a6(i) = 3.*(ar(i)-p(i))
                 al(i) = ar(i) - a6(i)
              endif
           endif
100     continue

     elseif(lmt.eq.1) then

        ! Semi-monotonic constraint
        do 150 i=1,im
           if(abs(ar(i)-al(i)) .ge. -a6(i)) go to 150
           if(p(i).lt.ar(i) .and. p(i).lt.al(i)) then
              ar(i) = p(i)
              al(i) = p(i)
              a6(i) = 0.
           elseif(ar(i) .gt. al(i)) then
              a6(i) = 3.*(al(i)-p(i))
              ar(i) = al(i) - a6(i)
           else
              a6(i) = 3.*(ar(i)-p(i))
              al(i) = ar(i) - a6(i)
           endif
150     continue
           
     elseif(lmt.eq.2) then

        ! Positive definite constraint
        do 250 i=1,im
           if(abs(ar(i)-al(i)) .ge. -a6(i)) go to 250
           fmin = p(i) + 0.25*(ar(i)-al(i))**2/a6(i) + a6(i)*r12
           if(fmin.ge.0.) go to 250
           if(p(i).lt.ar(i) .and. p(i).lt.al(i)) then
              ar(i) = p(i)
              al(i) = p(i)
              a6(i) = 0.
           elseif(ar(i) .gt. al(i)) then
              a6(i) = 3.*(al(i)-p(i))
              ar(i) = al(i) - a6(i)
           else
              a6(i) = 3.*(ar(i)-p(i))
              al(i) = ar(i) - a6(i)
           endif
250     continue
     endif

   END SUBROUTINE lmppm

!------------------------------------------------------------------------------

  SUBROUTINE huynh(im, ar, al, p, d2, d1)
!
!******************************************************************************
!  Subroutine HUYNH enforces Huynh's 2nd constraint in 1D periodic domain
!
!  Originally written by S-L Lin -- converted to F90 freeform format
!  and added to "Geos3RegridModule" by Bob Yantosca (bmy, 9/21/00)
!******************************************************************************
!
    INTEGER*4 :: im, i
    REAL*4     :: ar(im), al(im), p(im), d2(im), d1(im)

    ! Local scalars:
    REAL*4     :: pmp, lac, pmin, pmax

    !===================================================================
    ! HUYNH begins here!
    ! Compute d1 and d2
    !===================================================================
    d1(1) = p(1) - p(im)
    do i=2,im
       d1(i) = p(i) - p(i-1)
    enddo
    
    do i=1,im-1
       d2(i) = d1(i+1) - d1(i)
    enddo
    d2(im) = d1(1) - d1(im)

    !===================================================================
    ! Constraint for AR
    ! i = 1
    !===================================================================
    pmp   = p(1) + 2.0 * d1(1)
    lac   = p(1) + 0.5 * (d1(1)+d2(im)) + d2(im) 
    pmin  = min(p(1), pmp, lac)
    pmax  = max(p(1), pmp, lac)
    ar(1) = min(pmax, max(ar(1), pmin))
    
    do i=2, im
       pmp   = p(i) + 2.0*d1(i)
       lac   = p(i) + 0.5*(d1(i)+d2(i-1)) + d2(i-1)
       pmin  = min(p(i), pmp, lac)
       pmax  = max(p(i), pmp, lac)
       ar(i) = min(pmax, max(ar(i), pmin))
    enddo
     
    !==================================================================
    ! Constraint for AL
    !==================================================================
    do i=1, im-1
       pmp   = p(i) - 2.0*d1(i+1)
       lac   = p(i) + 0.5*(d2(i+1)-d1(i+1)) + d2(i+1)
       pmin  = min(p(i), pmp, lac)
       pmax  = max(p(i), pmp, lac)
       al(i) = min(pmax, max(al(i), pmin))
    enddo

    !==================================================================
    ! i=im
    !==================================================================
    i = im
    pmp    = p(im) - 2.0*d1(1)
    lac    = p(im) + 0.5*(d2(1)-d1(1)) + d2(1)
    pmin   = min(p(im), pmp, lac)
    pmax   = max(p(im), pmp, lac)
    al(im) = min(pmax, max(al(im), pmin))

    !==================================================================
    ! compute A6 (d2)
    !==================================================================
    do i=1, im
       d2(i) = 3.*(p(i)+p(i)  - (al(i)+ar(i)))
    enddo

  END SUBROUTINE huynh

!-----------------------------------------------------------------------------

END MODULE RegridModule
