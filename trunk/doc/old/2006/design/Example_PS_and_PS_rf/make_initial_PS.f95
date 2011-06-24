!--------------------------------------------------------------------------
!
!   Simple code to write a Plasma State data file so we can get started testing
!   
!   I have just made up some null data to test the modules.  We will need to write
!   a more elaborate code to read real data from some input files and generate
!   an initial PS data file.
!
!       Don Batchelor
!       ORNL
!       Oak Ridge, TN 37831
!       batchelordb@ornl.gov
!
!--------------------------------------------------------------------------

! Version 0.0 7/19/2006 (Batchelor)

PROGRAM make_initial_PS
  

    USE plasma_state_mod
    

    use swim_global_data_mod, only : &
            & rspec, ispec, &               ! int: kind specification for real and integer
            & SWIM_name, SWIM_filename, &   ! derived data types: containing one character string
            & SWIM_error                    ! subroutine: a simple error handling routine
    
    IMPLICIT none
    
    INTEGER :: ierr, istat

        OPEN (unit=state_file%unit, file=TRIM(state_file%name), status='unknown', &
            action='write', iostat=istat, form='unformatted')
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('open', 'PS_STORE_PLASMA_STATE' ,TRIM(state_file%name))
                ierr = istat
            END IF
        
   
    !-----------------------------------
    ! Time at beginning and end of time step
    !-----------------------------------
        PS_t0 = 0.
        PS_t1 = 0.
    !-----------------------------------
    ! Basic Geometry
    !-----------------------------------
         PS_r_axis = 0.
         PS_r0_mach = 0.
         PS_z0_mach = 0.
         PS_z_max = 0.
            
    !-----------------------------------
    ! Particle Species
    !-----------------------------------
         PS_nspec = 3

    !-----------------------------------
    ! Main (thermal) Plasma Species
    !-----------------------------------
        PS_nspec_th = 2
  
            ALLOCATE( PS_s_name(0:PS_nspec_th), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_s_name')
                ierr = istat
            END IF
        PS_s_name = (/SWIM_name('e'), SWIM_name('D')/)
    
            ALLOCATE( PS_q_s(0:PS_nspec_th), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_q_s')
                ierr = istat
            END IF
        PS_q_s = (/0., 0./)

            ALLOCATE( PS_m_s(0:PS_nspec_th), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_m_s')
                ierr = istat
            END IF
        PS_m_s = (/0., 0./)


        PS_nrho_n = 3
        
            ALLOCATE( PS_rho_n_grid(PS_nrho_n), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_rho_n_grid')
                ierr = istat
            END IF
        PS_rho_n_grid = 0.
        
            ALLOCATE( PS_n_s(PS_nrho_n, 0:PS_nspec_th), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_n_s')
                ierr = istat
            END IF
        PS_n_s = 0.
        
            ALLOCATE( PS_q_impurity(PS_nrho_n), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_q_impurity')
                ierr = istat
            END IF
        PS_q_impurity = 0.
        
            ALLOCATE( PS_m_impurity(PS_nrho_n), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_m_impurity')
                ierr = istat
            END IF
        PS_m_impurity = 0.

        PS_nrho_T = 3
        
            ALLOCATE( PS_rho_T_grid(PS_nrho_T), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_rho_T_grid')
                ierr = istat
            END IF
        PS_rho_T_grid = 0.
        
            ALLOCATE( PS_T_s(PS_nrho_T, 0:PS_nspec_th), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_T_s')
                ierr = istat
            END IF
        PS_T_s = 0.
        
        PS_nrho_v_par = 3
        
            ALLOCATE( PS_rho_v_par_grid(PS_nrho_v_par), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_v_par_grid')
                ierr = istat
            END IF
        PS_rho_v_par_grid = 0.
        
            ALLOCATE( PS_v_par_s(PS_nrho_v_par, 0:PS_nspec_th), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_v_par_s')
                ierr = istat
            END IF
        PS_v_par_s = 0.
 
    !-----------------------------------
    ! Non-Maxwellian Species
    !-----------------------------------
                
        PS_nspec_nonMax = 1

            ALLOCATE( PS_nonMax_name(PS_nspec_nonMax), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_nonMax_name')
                ierr = istat
            END IF
        PS_nonMax_name = SWIM_name('H minority')

            ALLOCATE( PS_q_nonMax_s(PS_nspec_nonMax), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_q_nonMax_s')
                ierr = istat
            END IF
        PS_q_nonMax_s = 0.

            ALLOCATE( PS_m_nonMax_s(PS_nspec_nonMax), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_m_nonMax_s')
                ierr = istat
            END IF
        PS_m_nonMax_s = 0.
        
        PS_ntheta_n = 3

            ALLOCATE( PS_n_nonMax2D_s(PS_nrho_n, PS_ntheta_n, PS_nspec_nonMax), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_n_nonMax2D_s')
                ierr = istat
            END IF
        
        PS_n_nonMax2D_s = 0.

            ALLOCATE( PS_n_nonMax_s(PS_nrho_n, PS_nspec_nonMax), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_n_nonMax_s')
                ierr = istat
            END IF
        PS_n_nonMax_s = 0.

            ALLOCATE( PS_dist_fun_s(PS_nspec_nonMax), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_dist_fun_s')
                ierr = istat
            END IF
        PS_dist_fun_s = SWIM_filename(11, 'H_min_dist')
        
    !-----------------------------------
    ! Magnetics
    !-----------------------------------
        
         PS_eqdsk_file = SWIM_filename(12,'My_eqdsk.dat')
         PS_B_axis = 0.
        
    !--------------------------------------------------------------------------
    ! RF input data
    !--------------------------------------------------------------------------
        
        PS_nrf_src = 1

            ALLOCATE( PS_rf_src_name(PS_nrf_src), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_rf_src_name')
                ierr = istat
            END IF
        PS_rf_src_name = SWIM_name('ICRH')

            ALLOCATE( PS_rf_freq_src(PS_nrf_src), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'rf_freq_src')
                ierr = istat
            END IF
        PS_rf_freq_src = 6.0e7

            ALLOCATE( PS_rf_power_src(PS_nrf_src), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_rf_power_src')
                ierr = istat
            END IF
        PS_rf_power_src = 11.0e6

            ALLOCATE( PS_ant_model_src(PS_nrf_src), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_ant_model_src')
                ierr = istat
            END IF
        PS_ant_model_src = SWIM_filename(13, 'ICRH_ant.dat')

    !--------------------------------------------------------------------------    !
    ! RF output data
    !--------------------------------------------------------------------------
            
        PS_nrho_prf = 3     
        PS_ntheta_prf = 3
        PS_nrho_cdrf = 3
    
            ALLOCATE( PS_prf2D_src_s (PS_nrho_prf, PS_ntheta_prf, PS_nrf_src, PS_nspec), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'PUT_PLASMA_STATE_RF' , 'PS_prf2D_src_s')
                ierr = istat
            END IF
        PS_prf2D_src_s = 0.
        
            ALLOCATE( PS_prf_src_s (PS_nrho_prf, PS_nrf_src, PS_nspec), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'PUT_PLASMA_STATE_RF' , 'PS_prf_src_s')
                ierr = istat
            END IF
        PS_prf_src_s = 0.
        
            ALLOCATE( PS_prf_total_s (PS_nrho_prf, PS_nspec), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'PUT_PLASMA_STATE_RF' , 'PS_prf_total_s')
                ierr = istat
            END IF
        PS_prf_total_s = 0.
        
        PS_nrho_cdrf = 3

            ALLOCATE( PS_cdrf_src_s (PS_nrho_cdrf, PS_nrf_src, PS_nspec_nonMax), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'PUT_PLASMA_STATE_RF' , 'PS_cdrf_src_s')
                ierr = istat
            END IF
        PS_cdrf_src_s = 0.
        
            ALLOCATE( PS_cdrf_total_s (PS_nrho_cdrf, PS_nspec_nonMax), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'PUT_PLASMA_STATE_RF' , 'PS_CDrf_total_s')
                ierr = istat
            END IF
        PS_cdrf_total_s = 0.

            ALLOCATE( PS_ql_operator(PS_nspec_nonMax), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_ql_operator')
                ierr = istat
            END IF
        PS_ql_operator = SWIM_filename(14, "My_QL_operator.dat")
        
    
        CALL PS_STORE_PLASMA_STATE(ierr)
        
        WRITE (*,*) "Stored Plasma State"       


END PROGRAM make_initial_PS