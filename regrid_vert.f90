       SUBROUTINE REGRID_VERT(ni, nk_s, nk_t, plev_s, plev_t, tracer_s, tracer_t, &
                              colmass_s, colmass_t)

!*****************************************************************************
!      The purpose of this routine is to redistribute the mass of a tracer
!      (CO2 for now) from a source set of vertical levels to a target set
!      of vertical levels.  The source and target surface pressures are
!      assumed to be the same.
!      
!      Author:  Dylan Jones (U Toronto)
!      Modifications:  S Polavarapu (Sept. 18, 2014)
! 	- Add arguments, remove calc of pressure levels
!	- Add variable declarations
!	- Change variable names to those familiar to GEM code
!	- Add list of assumptions at top
!	- Add calculation of mass before and after regridding
!
!      INPUT
!      -----
!      plev_s 	Pressure of grid interfaces of source grid (Pa or hPa)
!      plev_t	Pressure of grid interfaces of target grid (Pa or hPa)
!      nk_s	Number of vertical grid boxes (thermodynamic levels) of source
!      nk_t	Number of vertical grid boxes of target grid
!      ni	Number of columns for both source and target grids
!      tracer_s Tracer on source grid at grid box centers
!
!      OUTPUT
!      ------
!      tracer_t Tracer on target grid
!      colmass_s column mass of the source field before regridding (Real*8)
!      colmass_t column mass of the target field after  regridding (Real*8)
!
!      ASSUMPTIONS and WARNING: 
!      ------------------------
!      1) Pressure arrays decrease with increasing index.  Level 1 is the
!         surface and level nk is the top, contrary to usual GEM usage.
!      2) Surface pressure of SOURCE and TARGET grids must be the same.
!      3) If the target model lid is above the source model lid, the missing
!         air mass is NOT accounted for.  Mass before will NOT equal mass after
!         regridding.
!
!*****************************************************************************

!     Declare input and output argument type and dimension
      IMPLICIT NONE
      INTEGER*4, INTENT(IN) :: ni, nk_s, nk_t
      REAL*4,    INTENT(IN) :: plev_s(ni,nk_s+1), tracer_s(ni,nk_s)
      REAL*4,    INTENT(IN) :: plev_t(ni,nk_t+1)
      REAL*4,    INTENT(OUT):: tracer_t(ni,nk_t)
      REAL*8,    INTENT(OUT):: colmass_s(ni), colmass_t(ni)

!     Local variables
      INTEGER*4	:: i,k,l
      REAL*4    :: mass_s(ni,nk_s), mass_t(ni,nk_t)
      REAL*4    :: fraction(nk_s,nk_t), dp_s(ni,nk_s), dp_t

      !======================================================================
      ! Multiply "mass"/m^2 by mixing ratio (Units are arbitrary)
      !======================================================================
      ! write(*,*) 'k, dp_s(i,k), mass_s(i,k)'
      do i=1,ni
        colmass_s(i) = 0.0
        do k=1,nk_s
           dp_s(i,k) = plev_s(i,k) - plev_s(i,k+1)
           mass_s(i,k) = dp_s(i,k)*tracer_s(i,k)
           ! write(*,*) k, dp_s(i,k), mass_s(i,k)
           colmass_s(i) = colmass_s(i) + mass_s(i,k)
        enddo
      enddo

      !======================================================================
      ! Loop over columns and redistribute mass vertically 
      !======================================================================

      do i=1,ni

        fraction(:,:) = 0.0d0
   
        !=================================================================
        ! Loop over SOURCE grid
        !=================================================================
        do l=1,nk_s

          !===============================================================
          ! Loop over TARGET grid
          !===============================================================
          do k=1,nk_t
    
            ! Ignore diagnostic levels (no physical extent)
            if (plev_s(i,l) .eq. plev_s(i,l+1)) cycle
            if (plev_t(i,k) .eq. plev_t(i,k+1)) cycle

            !==============================================================
            ! Contribution if:
            ! ----------------
            ! Entire SOURCE layer in TARGET layer
            !==============================================================

            if (  (plev_t(i,k) .ge. plev_s(i,l))  .AND.      &
                  (plev_t(i,k+1) .le. plev_s(i,l+1)) ) then
               fraction(l,k) = 1.0
               cycle
            endif

            !==============================================================
            ! Contribution if:
            ! ----------------
            ! Top of TARGET layer in SOURCE layer
            !==============================================================
            if (  (plev_t(i,k+1) .le. plev_s(i,l))  .AND.    &
                  (plev_t(i,k) .ge. plev_s(i,l)) ) then
               fraction(l,k) = (plev_s(i,l) - plev_t(i,k+1))/dp_s(i,l)
               cycle
            endif

            !==============================================================
            ! Contribution if:
            ! ----------------
            ! Entire TARGET layer in SOURCE layer
            !==============================================================
            if (  (plev_t(i,k) .le. plev_s(i,l))  .AND.    &
                  (plev_t(i,k+1) .ge. plev_s(i,l+1)) ) then
               fraction(l,k) = (plev_t(i,k) - plev_t(i,k+1))/dp_s(i,l)
               cycle
            endif

            !==============================================================
            ! Contribution if:
            ! ----------------
            ! Bottom of TARGET layer in SOURCE layer
            !==============================================================
            if (  (plev_t(i,k) .ge. plev_s(i,l+1))  .AND.    &
                  (plev_t(i,k+1) .le. plev_s(i,l+1)) ) then
               fraction(l,k) = (plev_t(i,k) - plev_s(i,l+1))/dp_s(i,l)
               cycle
            endif

            enddo  ! loop over TARGET grid (k)
          enddo   ! loop over SOURCE grid (l)

          !=================================================================
          ! NOTE: GEOS-Chem top level is at 0.01 hPa whereas for GEM it is
          ! at lower altitudes. We will neglect extrapolation in top layer.
          !=================================================================

          do l=1,nk_s
             if ( abs(1.0 - sum(fraction(l,1:nk_t))) .gt. 1.0e-04) then
                 write(*,*) 'Fraction does not add to 1'
                 write(*,*) i,l,sum(fraction(l,1:nk_t))
             endif
          enddo

          !================================================================
          ! get new "mass" distribution on new grid
          !================================================================
          mass_t=0.0
          do k=1,nk_t
            do l=1,nk_s
              mass_t(i,k) = mass_t(i,k) + mass_s(i,l)*fraction(l,k)
            enddo
          enddo

          do k=1,nk_t
             tracer_t(i,k) = mass_t(i,k)/(plev_t(i,k) - plev_t(i,k+1))
          enddo

          ! Fill in diagnostic level(s) with nearest available data
          do k=2,nk_t
             if (plev_t(i,k) .eq. plev_t(i,k+1)) then
               tracer_t(i,k) = tracer_t(i,k-1)
             endif
          enddo
          do k=nk_t-1,1,-1
             if (plev_t(i,k) .eq. plev_t(i,k+1)) then
               tracer_t(i,k) = tracer_t(i,k+1)
             endif
          enddo

      enddo    ! loop over columns

      !================================================================
      ! Compute column mass after regridding
      !================================================================

       do i=1,ni
         colmass_t(i) = 0.0
         do k=1,nk_t
            dp_t = plev_t(i,k) - plev_t(i,k+1)
            mass_t(i,k) = dp_t*tracer_t(i,k)
            ! write(*,*) k, dp_t, mass_t(i,k)
            colmass_t(i) = colmass_t(i) + mass_t(i,k)
         enddo
       enddo

      END SUBROUTINE REGRID_VERT
