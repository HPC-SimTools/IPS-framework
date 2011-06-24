
module plasma_state_mod

! Version 0.0 7/16/2006 (Batchelor)

    !---------------------------------------------------------------------------
    !
    ! This is intended to be a quick an dirty implementation of a Plasma State
    ! component that will let us get started testing the plasma_state_rf_mod
    ! module and maybe get a component ready to be exercized by the controller
    ! script - DBB 7/16/06
    !
    !   Don Batchelor
    !   ORNL
    !   Oak Ridge, TN 37831
    !   batchelordb@ornl.gov
    !
    ! Note: This version does not have provision for keeping the previous time step
    !
    !---------------------------------------------------------------------------
    
!--------------------------------------------------------------------------
!
!   Other modules used:
!       Unless there is a huge number of declarations coming in, use the "only"
!       qualifier on "use" statements so the reader can tell where the variables are
!       declared and set.
!
!--------------------------------------------------------------------------

    use swim_global_data_mod, only : &
            & rspec, ispec, &               ! int: kind specification for real and integer
            & SWIM_name, SWIM_filename, &   ! derived data types: containing one character string
            & SWIM_error                    ! subroutine: a simple error handling routine

    

    
!--------------------------------------------------------------------------
!
!   Data declarations
!
!--------------------------------------------------------------------------
    
    IMPLICIT NONE
    
!--------------------------------------------------------------------------
!
!   Internal data
!
!--------------------------------------------------------------------------
    TYPE (SWIM_filename), PARAMETER :: state_file = SWIM_filename(10, 'PLASMA_STATE.dat')
!--------------------------------------------------------------------------
!
!   PLASMA STATE DATA
!
!--------------------------------------------------------------------------
   
    !-----------------------------------
    ! Time at beginning and end of time step
    !-----------------------------------
    REAL (KIND = rspec) ::  &
        PS_t0,                  &   ! time at beginning of step [msec]
        PS_t1                       ! time at end of step [msec]
   
    !-----------------------------------
    ! Basic Geometry
    !-----------------------------------
    REAL (KIND = rspec) ::  &
        PS_r_axis,              & ! major radius of magnetic axis [m]
        PS_z_axis,              & ! Z of magnetic axis [m]
        PS_r0_mach,             & ! Z of machine center [m]
        PS_z0_mach,             & ! major radius of machine center [m]
        PS_r_min,               & ! major radius of inside of bounding box [m]
        PS_r_max,               & ! major radius of outside of bounding box [m]
        PS_z_min,               & ! Z of bottom of bounding box [m]
        PS_z_max                  ! Z of top of bounding box [m]
            
    !-----------------------------------
    ! Particle Species
    !-----------------------------------
    
    INTEGER :: PS_nspec       ! number of ion species = nspec_th + nspec_nonMax

    !-----------------------------------
    ! Main (thermal) Plasma Species
    !-----------------------------------
    
    INTEGER :: PS_nspec_th        ! number of thermal ion species
    TYPE (SWIM_name), ALLOCATABLE :: &
        PS_s_name(:)              ! names of main species, (0:nspec_th)
    REAL (KIND = rspec), ALLOCATABLE :: &
        PS_q_s(:),              & ! charge of species s [C], (0:nspec_th)
        PS_m_s(:)                 ! mass of species s [kg], (0:nspec_th)
    
    INTEGER :: PS_nrho_n          ! number of rho values in thermal species density grid
    REAL (KIND = rspec), ALLOCATABLE :: &
        PS_rho_n_grid(:),       & ! rho values in density grid, (1:nrho_n)
        PS_n_s(:, :),           & ! density profile of species s, (1:nrho_n, 0:nspec_th)
        PS_q_impurity(:),           & ! effective impurity charge profile, (1:nrho_n)
        PS_m_impurity(:)              ! effective impurity mass profile, (1:nrho_n)
 
    INTEGER :: PS_nrho_T          ! number of rho values in temperature grid
    REAL (KIND = rspec), ALLOCATABLE :: &
        PS_rho_T_grid(:),       & ! rho values in temperature grid, (1:nrho_T)
        PS_T_s(:, :)              ! Temperature profile of species s, (1:nrho_T, 0:nspec_th)
 
    INTEGER :: PS_nrho_v_par      ! number of main rho values in parallel velocity grid
    REAL (KIND = rspec), ALLOCATABLE :: &
        PS_rho_v_par_grid(:),   & ! rho values in prallel velocity grid, (1:nrho_v_par)
        PS_v_par_s(:, :)          ! v parallel profile of species s, 
                              ! (1:nrho_v_par, 0:nspec_th)
 
    !-----------------------------------
    ! Non-Maxwellian Species
    !-----------------------------------
    
    INTEGER :: PS_nspec_nonMax    ! number of non-Maxwellian species
    TYPE (SWIM_name), ALLOCATABLE :: &
        PS_nonMax_name(:)         ! names of non-Maxwellian species, (1:nspec_nonMax)
    
    REAL (KIND = rspec), ALLOCATABLE :: &
        PS_q_nonMax_s(:),       & ! charge of species s [C], (1:nspec_nonMax)
        PS_m_nonMaX_s(:)          ! mass of species s [kg], (1:nspec_nonMax)
    
    INTEGER :: PS_ntheta_n        ! number of theta values in 2D density grid

    REAL (KIND = rspec), ALLOCATABLE :: &
        PS_n_nonMax2D_s(:, :,:)  ! 2D density profile of non-Maxwellian species s,
                                 ! (1:nrho_n, 1:ntheta_n, 1:nspec_nonMax)

    REAL (KIND = rspec), ALLOCATABLE :: &
        PS_n_nonMax_s(:, :)   ! Flux surface average density profile of 
                              ! non-Maxwellian species s, (1:nrho_n, 1:nspec_nonMax)
 
    TYPE (SWIM_filename), ALLOCATABLE :: &
        PS_dist_fun_s(:)      ! distribution function of non-Maxwellian  
                              ! species s, (1:nspec_nonMax) N.B. For now a distribution
                              ! function type is a file name
 
 
    !-----------------------------------
    ! Magnetics
    !
    ! magnetics: B(x), magnetic field.  Like distribution_fn there is a
    ! user-defined type that contains a file with the data.
    ! AORSA and TORIC get all their magntics data by reading an eqdisk file.
    ! Eventually all the magnetics data will appear separately in the Plasma
    ! state.
    !-----------------------------------

    TYPE (SWIM_filename) :: PS_eqdsk_file   ! eqdisk file
        
    REAL (KIND = rspec) ::  &
        PS_B_axis               ! Field at magnetic axis [T]

    !--------------------------------------------------------------------------
    !
    ! RF Data
    !
    ! Allow multiple RF sources, ICF, ICRH. So RF_frequency, power, etc may
    ! not be a scalar in that case.
    !   Assumption 1: the RF component invocation will
    !       involve a loop over each RF source, each of which can have its own
    !       RF_frequency, etc.  (vs. adding another dimension to the arrays).
    !   Assumption 2 : each source involves invoking another executable.
    !--------------------------------------------------------------------------
   
    
    INTEGER :: PS_nrf_src         ! number of RF sources
    
    TYPE (SWIM_name), ALLOCATABLE :: &
        PS_rf_src_name(:)             ! names of rf sources, (1:nrf_src)
        
    REAL (KIND = rspec), ALLOCATABLE :: &
        PS_rf_freq_src(:),      & ! frequency of RF source s [MHz], (1:nrf_src)
        PS_rf_power_src(:)        ! power of RF sources [MW], (1:nrf_src)
    
 
    TYPE (SWIM_filename), ALLOCATABLE :: &
        PS_ant_model_src(:)   ! antenna models for RF sources, (1:nrf_src)
   

    !---------------------------------------------------------------------------
    ! Note:
    ! Antenna model is currently defined in a file. The PREPARE_CODE_INPUT program
    ! should extract from it the data needed to define the geometry and operation
    ! i.e. phasing or mode number spectrum
    !
    ! For these, see the example namelist attached to the end
    ! of the aorsa.doc file sent by Fred to Swim list.  For now the data in this
    ! file includes:
    !   nphi =toroidal mode number (find another name not conflicting toroidal angle)
    !   antlen = vertical height of antenna [m]
    !   dpsiant0 = radial thickness of antenna in rho
    !   rant = radial location of antenna in major radius [m]
    !   yant = vertical location of antenna center [m]
    !
    !  N.B. In this scheme the toroidal mode number comes in through the antenna model
    !  The antenna geometry should eventually come from one of the standard machine
    !  definition files. 
    !
    !---------------------------------------------------------------------------
  
  
    ! RF Outputs that go back into the Plasma State.  Profiles are flux surface averages.
    
    ! N.B. We will want to put in 2D power deposition profiles, but I don't think they
    ! are needed for our initial coupling
        
    INTEGER ::  &
        PS_nrho_prf,    &   ! number rho values for RF power deposition grid
        PS_ntheta_prf   ! number of theta values in 2D RF power dep grid
        
    REAL (KIND = rspec), ALLOCATABLE :: &
        PS_rho_prf_grid(:), & ! rho values in RF power deposition grid, (1:nrho__prf)
        PS_prf2D_src_s(:,:,:,:),    & ! 2D Power deposition from each source into each 
                                  ! species, (1:nrho__prf, 1:nrf_src, 0:nspec)
        PS_prf_src_s(:,:,:),    & ! Power deposition profile from each source into each 
                              ! species, (1:nrho__prf, 1:nrf_src, 0:nspec)
        PS_prf_total_s(:,:)   ! Total rf power deposition profile into each species
                              ! summed over sources, (1:nrho__prf, 0:nspec)
    
        
    INTEGER :: PS_nrho_cdrf   ! number rho values for RF current drive grid
        
    REAL (KIND = rspec), ALLOCATABLE :: &
        PS_rho_cdrf_grid(:),    & ! rho values in RF current drive grid, (1:nrho__cdrf)
        PS_cdrf_src_s(:,:,:),   & ! Driven current profile from each source, in each species
                                  ! (1:nrho__cdrf, 1:nrf_src, 1:nspec_nonMax)
        PS_cdrf_total_s(:,:)      ! Total current driven by all sources in each species
    
 
    TYPE (SWIM_filename), ALLOCATABLE :: &
        PS_ql_operator(:)       ! quasilinear operator for each non Maxwellian 
                                ! species, (1:nspec_nonMax)


!--------------------------------------------------------------------------
!
!   End of data declarations
!
!--------------------------------------------------------------------------

CONTAINS
    
!--------------------------------------------------------------------------
!
!   Routines to GET from Plasma State and WRITE to Plasma State file
!
!--------------------------------------------------------------------------
   
    
    !-------------------------------------------------------------------
    !
    ! PS_GET_PLASMA_STATE
    !
    ! This subroutine read a plasma state file and puts the data into the
    ! semi-public variables declared above
    !
    ! PS_GET_PLASMA_STATE is to be called from inside GET_PLASMA_STATE_<COMP> 
    ! routines
    !
    ! 
    !-------------------------------------------------------------------


    SUBROUTINE PS_GET_PLASMA_STATE(ierr)

        IMPLICIT none
    !----------------------------------------------------------------------
    !
    !   Declare local variables
    !
    !----------------------------------------------------------------------
    
    
        INTEGER, INTENT(out) :: ierr
        
        INTEGER :: istat    ! Error flag returned by ALLOCATE function
        
    !----------------------------------------------------------------------
    !
    !   Read Plasma State data file
    !
    !----------------------------------------------------------------------
        
        OPEN (unit=state_file%unit, file=TRIM(state_file%name), status='old', &
            action='read', iostat=istat, form='unformatted')
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('open', 'PS_GET_PLASMA_STATE' ,TRIM(state_file%name))
                ierr = istat
                RETURN
            END IF
   
    !-----------------------------------
    ! Time at beginning and end of time step
    !-----------------------------------
        READ (state_file%unit) PS_t0
        READ (state_file%unit) PS_t1
    !-----------------------------------
    ! Basic Geometry
    !-----------------------------------
        READ (state_file%unit) PS_r_axis
        READ (state_file%unit) PS_r0_mach
        READ (state_file%unit) PS_z0_mach
        READ (state_file%unit) PS_z_max
            
    !-----------------------------------
    ! Particle Species
    !-----------------------------------
        READ (state_file%unit) PS_nspec

    !-----------------------------------
    ! Main (thermal) Plasma Species
    !-----------------------------------
       READ (state_file%unit) PS_nspec_th

            ALLOCATE( PS_s_name(0:PS_nspec_th), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_s_name')
                ierr = istat
                RETURN
            END IF

        READ (state_file%unit) PS_s_name

            ALLOCATE( PS_q_s(0:PS_nspec_th), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_q_s')
                ierr = istat
                RETURN
            END IF

        READ (state_file%unit) PS_q_s

            ALLOCATE( PS_m_s(0:PS_nspec_th), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_m_s')
                ierr = istat
                RETURN
            END IF

        READ (state_file%unit) PS_m_s


        READ (state_file%unit) PS_nrho_n
        
            ALLOCATE( PS_rho_n_grid(PS_nrho_n), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_rho_n_grid')
                ierr = istat
                RETURN
            END IF

        READ (state_file%unit) PS_rho_n_grid
        
            ALLOCATE( PS_n_s(PS_nrho_n, 0:PS_nspec_th), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_n_s')
                ierr = istat
                RETURN
            END IF

        READ (state_file%unit) PS_n_s
        
            ALLOCATE( PS_q_impurity(PS_nrho_n), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_q_impurity')
                ierr = istat
                RETURN
            END IF

        READ (state_file%unit) PS_q_impurity
        
            ALLOCATE( PS_m_impurity(PS_nrho_n), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_m_impurity')
                ierr = istat
                RETURN
            END IF

        READ (state_file%unit) PS_m_impurity

        READ (state_file%unit) PS_nrho_T
        
            ALLOCATE( PS_rho_T_grid(PS_nrho_T), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_rho_T_grid')
                ierr = istat
                RETURN
            END IF

        READ (state_file%unit) PS_rho_T_grid
        
            ALLOCATE( PS_T_s(PS_nrho_T, 0:PS_nspec_th), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_T_s')
                ierr = istat
                RETURN
            END IF

        READ (state_file%unit) PS_T_s
        
        READ (state_file%unit) PS_nrho_v_par
        
            ALLOCATE( PS_rho_v_par_grid(PS_nrho_v_par), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_v_par_grid')
                ierr = istat
                RETURN
            END IF

        READ (state_file%unit) PS_rho_v_par_grid
        
            ALLOCATE( PS_v_par_s(PS_nrho_v_par, 0:PS_nspec_th), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_v_par_s')
                ierr = istat
                RETURN
            END IF

        READ (state_file%unit) PS_v_par_s
 
    !-----------------------------------
    ! Non-Maxwellian Species
    !-----------------------------------
                
        READ (state_file%unit) PS_nspec_nonMax

            ALLOCATE( PS_nonMax_name(PS_nspec_nonMax), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_nonMax_name')
                ierr = istat
                RETURN
            END IF
                
        READ (state_file%unit) PS_nonMax_name

            ALLOCATE( PS_q_nonMax_s(PS_nspec_nonMax), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_q_nonMax_s')
                ierr = istat
                RETURN
            END IF
                
        READ (state_file%unit) PS_q_nonMax_s

            ALLOCATE( PS_m_nonMax_s(PS_nspec_nonMax), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_m_nonMax_s')
                ierr = istat
                RETURN
            END IF
                        
        READ (state_file%unit) PS_m_nonMax_s
        
        READ (state_file%unit) PS_ntheta_n

            ALLOCATE( PS_n_nonMax2D_s(PS_nrho_n, PS_ntheta_n, PS_nspec_nonMax), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_n_nonMax2D_s')
                ierr = istat
                RETURN
            END IF
        
        READ (state_file%unit) PS_n_nonMax2D_s

            ALLOCATE( PS_n_nonMax_s(PS_nrho_n, PS_nspec_nonMax), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_n_nonMax_s')
                ierr = istat
                RETURN
            END IF
        
        READ (state_file%unit) PS_n_nonMax_s

            ALLOCATE( PS_dist_fun_s(PS_nspec_nonMax), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_dist_fun_s')
                ierr = istat
                RETURN
            END IF
        
        READ (state_file%unit) PS_dist_fun_s
    !-----------------------------------
    ! Magnetics
    !-----------------------------------
        
        READ (state_file%unit) PS_eqdsk_file
        
        READ (state_file%unit) PS_B_axis
        
    !--------------------------------------------------------------------------
    ! RF input data
    !--------------------------------------------------------------------------
        
        READ (state_file%unit) PS_nrf_src

            ALLOCATE( PS_rf_src_name(PS_nrf_src), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_rf_src_name')
                ierr = istat
                RETURN
            END IF
        
        READ (state_file%unit) PS_rf_src_name

            ALLOCATE( PS_rf_freq_src(PS_nrf_src), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'rf_freq_src')
                ierr = istat
                RETURN
            END IF
        
        READ (state_file%unit) PS_rf_freq_src

            ALLOCATE( PS_rf_power_src(PS_nrf_src), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_rf_power_src')
                ierr = istat
                RETURN
            END IF
        
        READ (state_file%unit) PS_rf_power_src

            ALLOCATE( PS_ant_model_src(PS_nrf_src), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_ant_model_src')
                ierr = istat
                RETURN
            END IF
        
        READ (state_file%unit) PS_ant_model_src
        
    !--------------------------------------------------------------------------
    ! RF output data
    !--------------------------------------------------------------------------
            
        READ (state_file%unit) PS_nrho_prf      
        READ (state_file%unit) PS_ntheta_prf
        READ (state_file%unit) PS_nrho_cdrf

            ALLOCATE( PS_prf2D_src_s (PS_nrho_prf, PS_ntheta_prf, PS_nrf_src, &
                PS_nspec), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'PUT_PLASMA_STATE_RF' , 'PS_prf2D_src_s')
                ierr = istat
                RETURN
            END IF

            ALLOCATE( PS_prf_src_s (PS_nrho_prf, PS_nrf_src, PS_nspec), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'PUT_PLASMA_STATE_RF' , 'PS_prf_src_s')
                ierr = istat
                RETURN
            END IF

            ALLOCATE( PS_prf_total_s (PS_nrho_prf, PS_nspec), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'PUT_PLASMA_STATE_RF' , 'PS_prf_total_s')
                ierr = istat
                RETURN
            END IF

            ALLOCATE( PS_cdrf_src_s (PS_nrho_cdrf, PS_nrf_src, PS_nspec_nonMax), &
                stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'PUT_PLASMA_STATE_RF' , 'PS_cdrf_src_s')
                ierr = istat
                RETURN
            END IF

            ALLOCATE( PS_cdrf_total_s (PS_nrho_cdrf, PS_nspec_nonMax), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'PUT_PLASMA_STATE_RF' , 'PS_CDrf_total_s')
                ierr = istat
                RETURN
            END IF


            ALLOCATE( PS_ql_operator(PS_nspec_nonMax), stat=istat )
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('allocation', 'GET_PLASMA_STATE_RF' , 'PS_ql_operator')
                ierr = istat
                RETURN
            END IF
            
        READ (state_file%unit) PS_prf2D_src_s
        READ (state_file%unit) PS_prf_src_s
        READ (state_file%unit) PS_prf_total_s
        READ (state_file%unit) PS_cdrf_src_s
        READ (state_file%unit) PS_cdrf_total_s
        READ (state_file%unit) PS_ql_operator       
        
        CLOSE (state_file%unit)
        
    RETURN

    END SUBROUTINE PS_GET_PLASMA_STATE



    SUBROUTINE PS_STORE_PLASMA_STATE(ierr)
   
    
    !-------------------------------------------------------------------
    !
    ! PS_STORE_PLASMA_STATE
    !
    ! This subroutine writes a plasma state file.
    !
    ! PS_GET_PLASMA_STATE is to be called from inside PUT_PLASMA_STATE_<COMP> 
    ! routines.  These must re-allocate the output arrays of semi-public data
    ! and load the semi-public data from the output of the component code
    !
    ! 
    !-------------------------------------------------------------------

    
    !----------------------------------------------------------------------
    !
    !   Declare local variables
    !
    !----------------------------------------------------------------------
    
    
        INTEGER, INTENT(out) :: ierr
        
        INTEGER :: istat    ! Error flag returned by OPEN function
        
    !----------------------------------------------------------------------
    !
    !   Write plasma state file
    !
    !----------------------------------------------------------------------
        OPEN (unit=state_file%unit, file=TRIM(state_file%name), status='unknown', &
            action='write', iostat=istat, form='unformatted')
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('open', 'PS_STORE_PLASMA_STATE' ,TRIM(state_file%name))
                ierr = istat
                RETURN
            END IF
 
    !-----------------------------------
    ! Time at beginning and end of time step
    !-----------------------------------
        WRITE (state_file%unit) PS_t0
        WRITE (state_file%unit) PS_t1
    !-----------------------------------
    ! Basic Geometry
    !-----------------------------------
        WRITE (state_file%unit) PS_r_axis
        WRITE (state_file%unit) PS_r0_mach
        WRITE (state_file%unit) PS_z0_mach
        WRITE (state_file%unit) PS_z_max
            
    !-----------------------------------
    ! Particle Species
    !-----------------------------------
        WRITE (state_file%unit) PS_nspec

    !-----------------------------------
    ! Main (thermal) Plasma Species
    !-----------------------------------
        WRITE (state_file%unit) PS_nspec_th

        WRITE (state_file%unit) PS_s_name
        WRITE (state_file%unit) PS_q_s
        WRITE (state_file%unit) PS_m_s
        WRITE (state_file%unit) PS_nrho_n
        WRITE (state_file%unit) PS_rho_n_grid
        WRITE (state_file%unit) PS_n_s
        WRITE (state_file%unit) PS_q_impurity
        WRITE (state_file%unit) PS_m_impurity
        WRITE (state_file%unit) PS_nrho_T
        WRITE (state_file%unit) PS_rho_T_grid
        WRITE (state_file%unit) PS_T_s
        WRITE (state_file%unit) PS_nrho_v_par
        WRITE (state_file%unit) PS_rho_v_par_grid
        WRITE (state_file%unit) PS_v_par_s
 
    !-----------------------------------
    ! Non-Maxwellian Species
    !-----------------------------------
                
        WRITE (state_file%unit) PS_nspec_nonMax
        WRITE (state_file%unit) PS_nonMax_name
        WRITE (state_file%unit) PS_q_nonMax_s
        WRITE (state_file%unit) PS_m_nonMax_s
        WRITE (state_file%unit) PS_ntheta_n
        WRITE (state_file%unit) PS_n_nonMax2D_s
        WRITE (state_file%unit) PS_n_nonMax_s
        WRITE (state_file%unit) PS_dist_fun_s
    !-----------------------------------
    ! Magnetics
    !-----------------------------------
        
        WRITE (state_file%unit) PS_eqdsk_file
        WRITE (state_file%unit) PS_B_axis
        
    !--------------------------------------------------------------------------
    ! RF Data
    !--------------------------------------------------------------------------
        
        WRITE (state_file%unit) PS_nrf_src

        WRITE (state_file%unit) PS_rf_src_name
        WRITE (state_file%unit) PS_rf_freq_src
        WRITE (state_file%unit) PS_rf_power_src
        WRITE (state_file%unit) PS_ant_model_src
            
        WRITE (state_file%unit) PS_nrho_prf     
        WRITE (state_file%unit) PS_ntheta_prf
        WRITE (state_file%unit) PS_nrho_cdrf
            
        WRITE (state_file%unit) PS_prf2D_src_s
        WRITE (state_file%unit) PS_prf_src_s
        WRITE (state_file%unit) PS_prf_total_s
        
        WRITE (state_file%unit) PS_cdrf_src_s
        WRITE (state_file%unit) PS_cdrf_total_s
        WRITE (state_file%unit) PS_ql_operator      
        
        
        CLOSE (state_file%unit)
        
    RETURN
    
    END SUBROUTINE PS_STORE_PLASMA_STATE



END MODULE plasma_state_mod
