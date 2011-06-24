!--------------------------------------------------------------------------
!
!   Skeleton of a code to generate the input files for AORSA.  Gets the plasma
!   state data by using plasma_state_rf_mod.
!   
!
!       Don Batchelor
!       ORNL
!       Oak Ridge, TN 37831
!       batchelordb@ornl.gov
!
!--------------------------------------------------------------------------

! Version 0.0 7/19/2006 (Batchelor)

PROGRAM PREPARE_AORSA_INPUT

    USE plasma_state_rf_mod ! This declares the RF relevant PS variables

        IMPLICIT none
    !----------------------------------------------------------------------
    !
    !   Declare local variables
    !
    !----------------------------------------------------------------------
    
        INTEGER :: ierr
        
    !--------------------------------------------------------------------------
    !
    !   Declare AORSA-specific input variable names if different from Plasma 
    !   State form.
    !
    !--------------------------------------------------------------------------
    
        REAL (KIND = rspec) ::  r0
        ! N.B. Not necessary to declare B_axis becasue it is declared in 
        ! plasma_state_rf_mod and AORSA name is the same.
                
    !--------------------------------------------------------------------------
    !
    !   Insert code:
    !   Declare variable names for non-PS input variables (none in this example).
    !
    !--------------------------------------------------------------------------
            
    !--------------------------------------------------------------------------
    !
    !   Load Plasma State Data relevant to RF into plasma_state_rf_mod module.
    !
    !-------------------------------------------------------------------------- 
    
        CALL GET_PLASMA_STATE_RF(ierr)
            
    !--------------------------------------------------------------------------
    !
    !   Assign AORSA variables (if different from Plasma State form) from
    !   plasma_state_rf_mod module.
    !
    !--------------------------------------------------------------------------
    
        r0 = r_axis             ! Change to AORSA name
        B_axis = 10000.*B_axis  ! Change units to Gauss
        
    !--------------------------------------------------------------------------
    !
    !   Insert code:
    !   Read files to get non-PS AORSA input variables (None in this example).
    !
    !--------------------------------------------------------------------------

    !--------------------------------------------------------------------------
    !
    !   Insert code:
    !   Write standard AORSA input file.
    !
    !--------------------------------------------------------------------------

        WRITE (*,*) "r0 = ", r0
        WRITE (*,*) "B_axis = ", B_axis
        
        
END PROGRAM PREPARE_AORSA_INPUT
