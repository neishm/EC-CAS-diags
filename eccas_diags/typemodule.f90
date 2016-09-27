! $Id: TypeModule.f90,v 1.1.1.1 2003/06/24 16:00:34 bmy Exp $
MODULE TypeModule
  
  !===========================================================================
  ! "TypeModule" contains definitions for data types. 
  ! (bmy, 10/30/98, 1/21/00)
  !
  ! Based on "Numerical Recipes in Fortran 90" by Press et al, 1996 
  !===========================================================================

  ! Symbolic names for kind types of single and double precision reals
  INTEGER,  PARAMETER :: SP  = KIND( 1.0   )    
  INTEGER,  PARAMETER :: DP  = KIND( 1.0d0 )    
  
  ! Symbolic name for kind type of default logical
  INTEGER,  PARAMETER :: LGT = KIND( .TRUE. )

END MODULE TypeModule
