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
!      Modifications:  M Neish (Oct. 17, 2014)
!       - Remove the mass_s and mass_t arrays (to save space)
!       - Make dp_s a scalar (to save more space)
!       - Remove the fraction arrray, and refactor the code to avoid looping
!         over all combinations of source / target levels.
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
      INTEGER*4 :: i,k,k_start,l
      REAL*4    :: dp_s, dp_t

      !======================================================================
      ! Multiply "mass"/m^2 by mixing ratio (Units are arbitrary)
      !======================================================================
      ! write(*,*) 'k, dp_s(i,k), mass_s(i,k)'
      do i=1,ni
        colmass_s(i) = 0.0
        do k=1,nk_s
           dp_s = plev_s(i,k) - plev_s(i,k+1)
           colmass_s(i) = colmass_s(i) + dp_s*tracer_s(i,k)
        enddo
      enddo

      !======================================================================
      ! Loop over columns and redistribute mass vertically 
      !======================================================================

      do i=1,ni

        tracer_t(i,:) = 0.  ! Initialize target column

        k_start = 1   ! First target level to look at

        !=================================================================
        ! Loop over SOURCE grid
        !=================================================================
        do l=1,nk_s

          !===============================================================
          ! Loop over TARGET grid
          !===============================================================
          do k=k_start,nk_t

            dp_t = plev_t(i,k) - plev_t(i,k+1)
    
            ! Ignore target diagnostic level
            if (dp_t .eq. 0) cycle

            ! If we're completely below the source grid, then need to move
            ! to the next higher target level.
            if (plev_t(i,k+1) .ge. plev_s(i,l)) cycle

            ! If we're completely above the source grid, then need to move
            ! to the next higher source level.
            if (plev_t(i,k) .le. plev_s(i,l+1)) exit

            ! Compute how much overlap there is with the source layer.
            dp_s = min(plev_s(i,l), plev_t(i,k))  &
                 - max(plev_s(i,l+1), plev_t(i,k+1))

            ! Attribute this portion of source mass to the target mass
            tracer_t(i,k) = tracer_t(i,k) + (dp_s/dp_t)*tracer_s(i,l)

            enddo  ! loop over TARGET grid (k)

            k_start = max(1,k-1)

          enddo   ! loop over SOURCE grid (l)


      enddo    ! loop over columns

      !================================================================
      ! Compute column mass after regridding
      !================================================================

       do i=1,ni
         colmass_t(i) = 0.0
         do k=1,nk_t
            dp_t = plev_t(i,k) - plev_t(i,k+1)
            colmass_t(i) = colmass_t(i) + dp_t*tracer_t(i,k)
         enddo
       enddo

      END SUBROUTINE REGRID_VERT
