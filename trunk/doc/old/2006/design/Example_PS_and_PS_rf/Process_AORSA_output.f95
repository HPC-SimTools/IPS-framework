PROGRAM PROCESS_AORSA_OUTPUT
!--------------------------------------------------------------------------
!
!   Skeleton of a code write the output from AORSA back into the plasma state
!   
!
!       Don Batchelor
!       ORNL
!       Oak Ridge, TN 37831
!       batchelordb@ornl.gov
!
!--------------------------------------------------------------------------

! Version 0.0 7/19/2006 (Batchelor)


    USE plasma_state_rf_mod ! This declares the RF relevant PS variables

    use swim_global_data_mod, only : &
            & rspec, ispec              ! int: kind specification for real and integer


        IMPLICIT none
    !----------------------------------------------------------------------
    !
    !   Declare local variables
    !
    !----------------------------------------------------------------------
    
        INTEGER :: ierr, istat
        
    !--------------------------------------------------------------------------
    !
    !   Declare AORSA-specific output variable names for PS data if different
    !   from Plasma State form
    !
    !--------------------------------------------------------------------------
    
        REAL (KIND = rspec) ::  AORSA_Prf(4,2)
            
    !--------------------------------------------------------------------------
    !
    !   Insert code:
    !   Declare variable names for non-PS output variables (none in this 
    !   example).
    !
    !--------------------------------------------------------------------------
                            
    !--------------------------------------------------------------------------
    !
    !   Insert code:
    !   Read stadard AORSA output files
    !
    !   For this example only one code output variable is different from Plasma
    !   State form: AORSA_Prf --> prf_total_s
    !
    !--------------------------------------------------------------------------

        nrho_prf = 4                    ! Change number of grid points 
                                        ! Invent AORSA data
        AORSA_Prf= RESHAPE( (/ 1., 2., 3., 4., 5., 6., 7., 8. /), (/ 4, 2 /) )

        nspec =2        ! pretend we read this from AORSA output file
        nspec_nonMax =1 ! pretend we read this from AORSA output file
        nrf_src = 1     ! pretend we read this from AORSA output file
        ntheta_prf = 3  ! pretend we read this from AORSA output file
        nrho_cdrf = 3   ! pretend we read this from AORSA output file
    
            ALLOCATE( prf2D_src_s (nrho_prf, ntheta_prf, nrf_src, nspec), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'PUT_PLASMA_STATE_RF' , 'prf2D_src_s')
                ierr = istat
            END IF
        prf2D_src_s = 0.    ! pretend we read this from AORSA output file
        
            ALLOCATE( prf_src_s (nrho_prf, nrf_src, nspec), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'PUT_PLASMA_STATE_RF' , 'prf_src_s')
                ierr = istat
            END IF
        prf_src_s = 0.  ! pretend we read this from AORSA output file
        
        
        nrho_cdrf = 3   ! pretend we read this from AORSA output file

            ALLOCATE( cdrf_src_s (nrho_cdrf, nrf_src, nspec_nonMax), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'PUT_PLASMA_STATE_RF' , 'cdrf_src_s')
                ierr = istat
            END IF
        cdrf_src_s = 0.     ! pretend we read this from AORSA output file
        
            ALLOCATE( cdrf_total_s (nrho_cdrf, nspec_nonMax), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'PUT_PLASMA_STATE_RF' , 'CDrf_total_s')
                ierr = istat
            END IF
        cdrf_total_s = 0.   ! pretend we read this from AORSA output file

            ALLOCATE( ql_operator(nspec_nonMax), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'ql_operator')
                ierr = istat
            END IF
        ql_operator = SWIM_filename(14, "My_QL_operator.dat")   ! pretend we read 
                                                    ! this from AORSA output file
        
        
        
        
        
    !--------------------------------------------------------------------------
    !
    !   Convert AORSA output variables to plasma_state form. (N.B. Have to allocate
    !   arrays if PS names are different from AORSA form)
    !
    !--------------------------------------------------------------------------

            ALLOCATE( prf_total_s (nrho_prf, nspec), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'PUT_PLASMA_STATE_RF' , 'prf_total_s')
                ierr = istat
            END IF
    
        prf_total_s  = AORSA_Prf                ! Change from AORSA name to PS name
                    
    !--------------------------------------------------------------------------
    !
    !   Update Plasma State Data relevant to RF
    !
    !-------------------------------------------------------------------------- 
    
        CALL PUT_PLASMA_STATE_RF(ierr)
        
    WRITE (*,*) 'Wrote into plasma state prf_total_s  = ', prf_total_s
            

END PROGRAM PROCESS_AORSA_OUTPUT

