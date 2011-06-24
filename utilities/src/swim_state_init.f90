program swim_state_init

  !--------------------------------------------------------------------
  ! Demo program for use of plasma state component
  ! D. McCune 9 Oct 2006
  !
  !--------------------------------------------------------------------
  !
  ! This routine demonstrates use of the IPS state interface.
  !
  !-----------------------------------
  ! The state contents are specified in "swim_state_spec.dat".  This is
  ! input to a code generator which produces the state file i/o routines;
  ! an "internal" plasma state component interface is also defined; an
  ! implementation is provided using xplasma2.  The internal interface 
  ! is not currently documented.
  !
  !   Procedure for modifying the contents of state:
  !     1.  edit "swim_state_spec.dat"
  !     2.  run the code generator script.
  !
  ! After the state definition is modified, old state files can still
  ! be examined (e.g. with a plotting tool) but will not be usable for
  ! simulation restarts.
  !-----------------------------------
  !
  ! State elements are traditional f77 integer, floating point, and character
  ! string scalars and arrays all contained within a large container data 
  ! type "plasma_state".  Two instances of this container data type are
  ! declared in the module "plasma_state_mod":
  !
  !   ps -- the current state (timestep now being computed).
  !   psp -- the prior or "committed" state (completed, prior timestep)
  !
  ! Elements of the state can be referenced directly using the standard
  ! f95 syntax-- e.g. ps%nrho is the size of one of the radial flux 
  ! coordinate "rho" grids in the state.
  !
  ! State elements can be directly modified by codes that use the plasma
  ! state-- although this should be done carefully.  Generally, items in 
  ! the state are meant to be shared between multiple components of the 
  ! IPS; conventions for use of the state data will need to evolve.
  !
  ! States will be mapped to NetCDF files.  The module "plasma_state_mod"
  ! defines two variables for these filenames:
  !
  !   CHARACTER*256 :: state_file = 'plasma_state.cdf'
  !   CHARACTER*256 :: prior_file = 'prior_state.cdf'
  !
  ! The assigned default values can of course be modified.
  !-----------------------------------
  ! In addition to direct access to state data elements, the following
  ! subroutines are available (defined in the f95 module plasma_state_mod)
  ! (this is the module's public interface):
  !
  !    integer :: ierr -- status code returned by many routines (0=OK).
  !
  !    SUBROUTINE label_plasma_state(global_label,ierr)
  !       Apply a global label to the plasma state data-- e.g. name of a
  !       program or ID of a run
  ! 
  !    SUBROUTINE ps_alloc_plasma_state(ierr)
  !       ALLOCATE all arrays for which non-zero dimensions have been defined.
  !       This is done at the start of simulations.  Arrays are allocated only
  !       once; their sizes are not permitted to change in time-- NB relaxing
  !       this rule would entail many complications and should be avoided at
  !       least in early versions of the software.
  !
  !    SUBROUTINE ps_label_species(iZatom,iZcharge,iAMU,suffix, &
  !         label, qatom, qcharge, mass)
  !
  !       Based on atomic number and integer-approximate AMU, get label
  !       and charge and mass (in C, kg) of plasma species (detailed 
  !       argument descriptions in plasma_state_mod)
  !
  !    SUBROUTINE ps_clear_profs(ierr)
  !       Set all profile data to zero-- this might be desirable when starting
  !       to build a state at a new time.  It will be easier to tell what has
  !       been added, and what not, if quantities not added are zero, rather
  !       than from the prior timestep.  All the prior timestep data is still
  !       accessible in the prior state object psp-- i.e. psp%rho_eq(...), etc.
  !       Scalar data and grids are not affected by this call-- just profiles.
  !
  !    SUBROUTINE ps_update_equilibrium(<g-filename>,ierr)
  !       Update state MHD equilibrium from G-eqdsk file <g-filename>
  !          (could also be an MDSplus G-eqdsk timeslice from an experiment).
  !       Compute state quantities derived from the equilibrium
  !       Arrays such as enclosed volumes (m^3) ps%vol(1:ps%nrho_eq) are 
  !       filled in.
  !
  !    SUBROUTINE ps_store_plasma_state(ierr)
  !       Update interpolation information and store the state (ps) in
  !       the file (state_file).
  !
  !    SUBROUTINE ps_update_plasma_state(ierr)
  !       Update interpolation information but do not write a file.
  !
  !    SUBROUTINE ps_commit_plasma_state(ierr)
  !       Copy current state (ps) to prior state (psp).  Save prior state
  !       in file (prior_state).  The file (state_file) is not modified--
  !       use ps_store_plasma_state for this.
  !
  !    SUBROUTINE ps_get_plasma_state(ierr)
  !       Read the current state (ps) with all interpolation information
  !       from (state_file) --AND-- read the prior state (psp) with all
  !       its interpolation information from the file (prior_state).
  !
  ! Profile IDs:  each state array that is defined over one or more coordinate
  !   grids is assigned an ID variable or array with name ID_<name>.  These IDs
  !   are needed to refer to specific profiles for interpolation or rezoning.
  !
  !   Examples mapping from swim_state_spec.dat to plasma state object "ps":
  !
  !      R|pclin  chi_e(nrho)          ! electron thermal conductivity
  !
  !      -> ps%chi_e(...)  (1d allocated REAL(KIND=rspec) array (1:ps%nrho)) &
  !      -> ps%id_chi_e    INTEGER scalar
  !
  !      R|units=m^-3|step  ns(~nrho,0:nspec_th)       ! thermal specie density
  !
  !      -> ps%ns(...)     (2d allocated REAL(KIND=rspec) array
  !      -> ps%id_ns(...)  (1d allocated INTEGER array)
  !
  !              ps%ns(1:ps%nrho-1,0:ps%nspec_th)
  !              ps%id_ns(0:ps%nspec_th)
  !
  ! Direct interpolation:
  !
  !    SUBROUTINE PS_INTRP_1D(...)  for 1D profiles
  !
  !       CALL PS_INTRP_1D( &
  !            x,  &      ! target of interpolation: scalar or 1d vector
  !            id, &      ! profile(s) interpolated: scalar 1d or 2d INT array
  !            ans,&      ! result, dimensioned to match x(...) and id(...)
  !            ierr,   &  ! completion code 0=OK
  !            icur,   &  ! OPTIONAL: "ps_previous" or "ps_current" (default)
  !            ideriv, &  ! OPTIONAL: derivative control for all IDs
  !            ideriv1s,& ! OPTIONAL: derivative control for each ID separately
  !            iccw_th)   ! OPTIONAL: .FALSE. for clockwise poloidal angle
  !                         (theta) coordinate
  !
  !       If x is a vector, the 1st dimension size of ans matches size(x);
  !       subsequent dimensions match sizes of dimensions of id(...).
  !
  !       icur can be used to select the current or prior state; current state
  !       is the default.
  !
  !       ideriv1s is only available if id(...) is an array.  If so, ideriv1s
  !       takes precedence over ideriv, if both are present.  The dimensioning
  !       of INT array ideriv1s must match dimensioning of ID exactly.
  !
  !       If neither ideriv nor ideriv1s are specified, the interpolating 
  !       function value is evaluated with no derivatives.
  !
  !       iccw_th would only be needed if a profile f(theta) is ever defined.
  !
  !    SUBROUTINE PS_INTRP_2D(...)  for 2D profiles
  !
  !       (interface is like PS_INTRP_1D, except that:
  !
  !          x -> x1,x2 -- two interpolation target scalars or vectors must
  !                        be supplied; the coordinate to which they belong
  !                        will match the declaration
  !
  !          similarly, optional derivative control is available separately
  !          for each coordinate:
  !            ideriv -> ideriv1,ideriv2
  !            ideriv1s -> ideriv1s,ideriv2s
  !
  ! Profile rezoning integration:
  !
  !    SUBROUTINE PS_RHO_REZONE(...) for "conservative" rezoning
  !      of profiles f(rho) 
  !      (rezoning to 1d of profiles f(rho,theta) will be done but is
  !      not yet implemented -- DMC 16 Oct 2006).
  !
  !    SUBROUTINE PS_RHOTH_REZONE(...) for "conservative" rezoning
  !      of profiels f(rho,theta) -- not yet implemented DMC 16 Oct 2006
  ! 
  !-----------------------------------
  ! Implementation of interpolation and rezoning-- the "visible" state
  ! elements ps%* and psp%* are not the entire state.  When interpolation
  ! and rezoning operations are carried out, additional hidden information
  ! is accessed which defines the profile interpolation methods.
  !
  ! Interpolation methods for profiles are part of the state specification
  ! "swim_state_spec.dat" and are handled by generated code.
  !-----------------------------------

  ! define state object and interface...

  USE plasma_state_mod
!--------------------------------------------------------------------------

    use swim_global_data_mod, only : &
            & rspec, ispec, &               ! int: kind specification for real and integer
!            & swim_string_length, &         ! length of strings for names, files, etc.
	    & swim_error		    ! error routine
    

    
!--------------------------------------------------------------------------
!
!   Data declarations
!
!--------------------------------------------------------------------------
    
    IMPLICIT NONE
    
    integer, parameter :: swim_string_length = 256
    integer :: istat
    
!--------------------------------------------------------------------------
!
!   Internal data
!
!--------------------------------------------------------------------------
    character(len = swim_string_length) :: state_initial  !initial state file
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
      & PS_t1                       ! time at end of step [msec]
   
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
    !-----------------------------------m
    
    integer, parameter :: nrho_max = 120
    integer, parameter :: n_spec_th_max = 5
    integer, parameter :: n_spec_max = 7
    integer, parameter :: n_spec_nm_max = 2

    
    
    INTEGER :: PS_nspec_th                    ! number of thermal ion species
    character(len = swim_string_length) ::  &
        PS_s_name(0:n_spec_max)              ! names of main species, (0:nspec_th)
    REAL (KIND = rspec) :: &
        PS_q_s(0:n_spec_th_max),              & ! charge of species s [C], (0:nspec_th)
     &  PS_m_s(0:n_spec_th_max)                 ! mass of species s [kg], (0:nspec_th)
    
    INTEGER :: PS_nrho_n          ! number of rho values in thermal species density grid
    REAL (KIND = rspec) :: &
        PS_rho_n_grid(nrho_max),       & ! rho values in density grid, (1:nrho_n)
     &  PS_n_s(nrho_max, 0:n_spec_th_max),           & ! density profile of species s, (1:nrho_n, 0:nspec_th)
     &  PS_q_impurity(nrho_max),           & ! effective impurity charge profile, (1:nrho_n)
     &  PS_m_impurity(nrho_max)              ! effective impurity mass profile, (1:nrho_n)
 
    INTEGER :: PS_nrho_T          ! number of rho values in temperature grid
    REAL (KIND = rspec) :: &
        PS_rho_T_grid(nrho_max),       & ! rho values in temperature grid, (1:nrho_T)
      & PS_T_s(nrho_max, 0:n_spec_th_max)              ! Temperature profile of species s, (1:nrho_T, 0:nspec_th)
 
    INTEGER :: PS_nrho_v_par      ! number of main rho values in parallel velocity grid
!    REAL (KIND = rspec), ALLOCATABLE :: &
!        PS_rho_v_par_grid(:),   & ! rho values in parallel velocity grid, (1:nrho_v_par)
!      & PS_v_par_s(:, :)        & ! v parallel profile of species s, 
                                  ! (1:nrho_v_par, 0:nspec_th)
 
    !-----------------------------------
    ! Non-Maxwellian Species
    !-----------------------------------
    
    INTEGER :: PS_nspec_nonMax    ! number of non-Maxwellian species
    character(len=swim_string_length), dimension(n_spec_nm_max ) :: &
        PS_nonMax_name         ! names of non-Maxwellian species, (1:nspec_nonMax)
    
    REAL (KIND = rspec), dimension(n_spec_nm_max ) :: &
        PS_q_nonMax_s,       & ! charge of species s [C], (1:nspec_nonMax)
        PS_m_nonMaX_s          ! mass of species s [kg], (1:nspec_nonMax)
    
    INTEGER :: PS_ntheta_n        ! number of theta values in 2D density grid

    REAL (KIND = rspec), ALLOCATABLE :: &
        PS_n_nonMax2D_s(:, :,:)  ! 2D density profile of non-Maxwellian species s,
                                 ! (1:nrho_n, 1:ntheta_n, 1:nspec_nonMax)

    REAL (KIND = rspec), ALLOCATABLE :: &
        PS_n_nonMax_s(:, :)   ! Flux surface average density profile of 
                              ! non-Maxwellian species s, (1:nrho_n, 1:nspec_nonMax)
 
    character(len = swim_string_length) :: &
        PS_dist_fun_s         ! distribution function of non-Maxwellian  
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

    character(len = swim_string_length) :: PS_eqdsk_file   ! eqdisk file
        
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
       ! names of rf sources, (1:nrf_src)
        

    
 
    character(len = swim_string_length) :: PS_ant_model_src !file name for antenna model 
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
        PS_prf2D_src_s(:,:,:,:),   & ! 2D Power deposition from each source into each 
                                  	         	! species, (1:nrho__prf, 1:nrf_src, 0:nspec)
        PS_prf_src_s(:,:,:)  ! Power deposition profile from each source into each 
                              ! species, (1:nrho__prf, 1:nrf_src, 0:nspec)
    real(kind = rspec) ::   PS_prf_total_s(nrho_max,0:n_spec_max)   ! Total rf power deposition profile into each species
                              ! summed over sources, (1:nrho__prf, 0:nspec)
    
    integer :: PS_nrho_cdrf(n_spec_max) ! # of rho values for RF current drive grid for each species
        
    REAL (KIND = rspec), ALLOCATABLE :: &
        PS_rho_cdrf_grid(:),    & ! rho values in RF current drive grid, (1:nrho__cdrf)
        PS_cdrf_src_s(:,:,:),   & ! Driven current profile from each source, in each species
                                  ! (1:nrho__cdrf, 1:nrf_src, 1:nspec_nonMax)
        PS_cdrf_total_s(:,:)      ! Total current driven by all sources in each species
    
 
    character(len = swim_string_length), dimension(n_spec_nm_max)  :: &
        PS_ql_operator          ! quasilinear operator for each non Maxwellian--file name 
                                ! species, (1:nspec_nonMax)
    character(len = swim_string_length), dimension(n_spec_nm_max) :: &
        PS_distribution_fun	! distribution function for each non Maxwellian species


!--------------------------------------------------------------------------
!
!   End of data declarations
!
!--------------------------------------------------------------------------  
    namelist /state/ PS_t0, PS_t1, PS_r_axis, PS_z_axis, PS_r0_mach, &
       PS_z0_mach, PS_r_min, PS_r_max, PS_z_min, PS_z_max, &
       PS_nspec,PS_nspec_th,PS_s_name, PS_q_s, PS_m_s,  &
       PS_nrho_n, PS_rho_n_grid, PS_n_s, PS_q_impurity, PS_m_impurity, &
       PS_nrho_T, PS_rho_T_grid, PS_T_S, PS_ant_model_src, PS_ql_operator, &
       PS_distribution_fun




  !------------------------------------
  !  local
  INTEGER :: ierr
  INTEGER :: iout = 6

  !  for this simple demo, all profiles will vary as:
  !    (<core_value>-<edge_value>)*(1-rho**2)**2 + <edge_value> -- cf profgen

  REAL(KIND=rspec) :: time0 = 0.1_rspec      ! s -- time of start of "run".
  REAL(KIND=rspec) :: delta_t = 0.01_rspec   ! s -- initial time step size

  REAL(KIND=rspec) :: T0 = 5.0_rspec   ! KeV at core
  REAL(KIND=rspec) :: Ta = 0.1_rspec   ! KeV at edge

  REAL(KIND=rspec) :: den0 = 1.0e20_rspec  ! #/m^3 electrons at core
  REAL(KIND=rspec) :: dena = 0.2e20_rspec  ! #/m^3 electrons at edge

  REAL(KIND=rspec) :: Zeff0 = 1.2_rspec    ! Z_eff at core
  REAL(KIND=rspec) :: Zeffa = 2.0_rspec    ! Z_eff at edge

  REAL(KIND=rspec) :: Aimp_atom = 12.011_rspec ! Carbon A

  REAL(KIND=rspec) :: Zimp0 = 6.0_rspec    ! <Z_imp> at core (Carbon +6)
  REAL(KIND=rspec) :: Zimpa = 5.0_rspec    ! <Z_imp> at edge (Carbon +5)

  REAL(KIND=rspec) :: frac_mino = 0.02_rspec  ! n_minority/n_e  for this benchmark
  integer :: iZ_mino = 1   ! Z of minority (H)
  integer :: iA_mino = 1   ! A of minority (H)

  REAL(KIND=rspec), dimension(:), allocatable :: Zeff,Zimp,rho_zc

  integer :: i,ii,ith,ict,inum,nrho,nrho_zc
  integer :: id,ids(2)
  REAL(KIND=rspec) :: zne_adj,zzne_adj,zrho,zdvol
  REAL(KIND=rspec) :: ZERO= 0.0_rspec
  REAL(KIND=rspec) :: ONE = 1.0_rspec
  REAL(KIND=rspec) :: vpp0,ppp0,zansR0,zansZ0
  REAL(KIND=rspec) :: test_Rmin,test_Rmax
  REAL(KIND=rspec) :: test_Zmin,test_Zmax

  REAL(KIND=rspec), dimension(:), allocatable :: rho_intrp,th_intrp
  REAL(KIND=rspec), dimension(:), allocatable :: dvdrho,dpsidrho
  REAL(KIND=rspec), dimension(:,:), allocatable :: buf2
  REAL(KIND=rspec), dimension(:), allocatable :: buf1
  REAL(KIND=rspec), dimension(:), allocatable :: rho_bdys,dvols
  REAL(KIND=rspec), dimension(:,:), allocatable :: my_ns,my_ts
  REAL(KIND=rspec), dimension(:), allocatable :: zvols
  REAL(KIND=rspec), dimension(:), allocatable :: volref_ns,volref_nt
  REAL(KIND=rspec), dimension(:), allocatable :: volint_ns,volint_nt
  REAL(KIND=rspec), dimension(:), allocatable :: maxdiff_ns,maxdiff_nt

  !------------------------------------
  ! When starting a simulation, there is no prior state.
  ! To create a state from scratch:
  !   a) specify state array dimensions (could be e.g. by a namelist read)
  !   b) apply a global label to the plasma state data (e.g. name of a program)
  !      set the initial time.
  !   c) allocate state arrays
  !   d) fill in names and values where appropriate for all non-coordinate
  !      array dimensions:  species lists, RF antenna lists, NB injector
  !      lists, ...
  !   e) acquire initial MHD equilibrium
  !   f) acquire initial conditions-- e.g. temperatures and densities for
  !      each species.
  !   g) store and commit the initial state-- now both a current and prior
  !      state exist, and time dependent simulation can commence.
  !
  ! Elements of the current state are in ps%<element-names>(indices,...)
  ! Elements of the prior state are in  psp%<element-names>(indices,...)
  !------------------------------------

  !==========================================================================
  !  Contents of "ps" are defined in "swim_state_spec.dat"

  !==========================================================================
  ! (a) array dimensions -- set ONLY ONCE at start of simulation...
  !     (the values here are chosen somewhat arbitrarily).

!-----------BERRY--read the namelist that has the regression state in it
        state_initial = 'state.in'
        OPEN (unit=21, file=TRIM(state_initial), status='old', &
            action='read', iostat=istat, form='formatted')
            IF (istat /= 0 ) THEN
                CALL SWIM_error ('open', 'PS_GET_PLASMA_STATE',TRIM(state_initial))
                ierr = istat
		stop 'cannot open namelist state for loading into xplasma state'
		
            END IF
	ierr = 0
	read(21, nml=state)
        CLOSE (21)
  ps%nspec_th = ps_nspec_th !fill state
  ps%nspec_nonMax = 0 !fill state
  ps%nspec = ps%nspec_th

  !  ps%nspec will be computed when the state is allocated
  !    see state specification "swim_state_spec.dat".

  ps%nrho = 51   ! set to 51 LAB
  ps_debug = 3

  ! PLASMA...

  call ps_init_tag

  ! RF...

  ps%nicrf_src = 1

  ps%nrho_icrf = 50  ! set to 50 LAB  50 volumes to edge


  ! Equilibrium -- R and Z grid sizes will be reset when first G-eqdsk is read.
  !   (The G-eqdsk R and Z grids are used).

  ps%nrho_eq = 51
  ps%nth_eq = 101
  ps%nR = 0
  ps%nZ = 0
  

  !-------------------------
  ! (b) Global label for state data (as will appear in state files)
  !     Here the program name "swim_state_test" is used, but it is likely
  !     better to use a runid -- ID string to uniquely identify a specific
  !     run or simulation

  CALL ps_label_plasma_state('swim_DIIID_AORSA',ierr)

  !  the initial times.  The first state does not really represent a timestep
  !  so both the start time ps%t0 and the final time ps%t1 are set:

  ps%t0 = time0
  ps%t1 = time0

  if(ierr.ne.0) then
     write(iout,*) ' ?swim_DIIID_AORSA: ps_label_plasma_state: ierr=',ierr
     stop
  endif

  !-------------------------
  ! (c) Initial allocation of state arrays.  All integers and floats are
  ! initialized to ZERO; all character strings to blank

  ! Note, it is possible to call this several times, providing additional
  ! non-zero array dimensions on each call, BUT: once a non-zero dimension
  ! has been supplied, the rule for now is that it cannot be changed!  This
  ! routine enforces the rule by checking all arrays prior to allocation,
  ! and checking the sizes of arrays already allocated against their
  ! corresponding array dimension variables in the state.  Generated 
  ! code is used to do this.

  CALL ps_alloc_plasma_state(ierr)

  if(ierr.ne.0) then
     write(iout,*) ' ?swim_DIIID_AORSA: ps_alloc_plasma_state: ierr=',ierr
     stop
  endif
  


  !==========================================================================
  ! (d) Define names of list elements.
  !
  ! Explanation:
  ! Array dimensions come in two flavor:
  !    1.  Grid dimensions -- e.g. along rho, theta, R, Z
  !    2.  List dimensions -- e.g. species index, RF antenna index, ...
  ! Each element of each list dimension must have a tag name associated
  ! with it, so that distinct names can be provided for every profile
  ! over the grid dimensions.  For example, the state array:
  !
  !  R|units=MW/m^3|step prf_srcs(~nrho_prf,nrf_src,0:nspec)
  !                    ! RF power deposition
  !
  ! defines (ps%nrf_srf * (ps%nspec + 1)) profiles vs. rho.  In the state
  ! output files these will be gathered as a list "PRF_SRCS" containing
  ! elements with such names as:
  !    "PRF_SRCS_ANT1_E" (heating from Antenna#1 to electrons)
  !    "PRF_SRCS_ANT1_D" (heating from Antenna#1 to deuterons)
  !    "PRF_SRCS_ANT1_TOK" (heating from Antenna#1 to TOKamakium impurity)
  !    "PRF_SRCS_ANT3_HMINO" (heating from Antenna#3 to H-minority)
  !       ...
  !       ...
  !    "PRF_SRCS_ANT3_HMINO" (heating from Antenna#3 to H-minority)
  ! I.e. if there are 3 antennas and 4 species {e,D,TOK,Hmino}, there would
  ! be 4 profiles, each separately named and available (e.g. for plotting).
  !
  ! But, these names can only be generated if the tag names for all elements
  ! of the list dimensions are defined first.
  !
  ! (The plasma state cannot be saved to a file until all tag names are 
  ! defined; duplicate tags within a list dimension are not allowed).
  !-------------------------
  ! 1. Define species lists tag names...
  !
  !    The subroutine ps_label_species(...) is provided for this purpose.
  !
  !  input(charge-fully-stripped, charge, AMU-nearest-integer, suffix-string)
  !  output(label, C-fully-stripped, C, m(kg)) (charges converted to C)
  !
  !  The AMU-nearest-integer argument is only used for H and He isotopes;
  !  it is ignored for all other elements...
  !
  !  various combinations of the first three arguments and their meaning:
  !
  !  (-1,-1,0) -- electrons -- 2nd and 3rd arguments ignored.
  !  (0,0,0) -- TOKAMAKIUM impurity  -- 2nd and 3rd arguments ignored.
  !
  !  (1,1,1) -- H ion  --> "H"
  !  (1,1,2) -- D ion  --> "D"
  !  (1,1,3) -- T ion  --> "T"
  !  (2,2,3) -- He3 (fully stripped) --> "He3"
  !  (2,2,4) -- He4 (fully stripped) --> "He4"
  !  (2,1,4) -- He4 charge +1 --> "He4_1"
  !  (6,6,0) -- C (Carbon) (fully stripped) -- AMU (3rd) arg ignored. --> "C"
  !  (6,4,0) -- C (Carbon) charge +4 -- AMU (3rd) arg ignored. --> "C_4"
  !
  !  *** thermal species ***
  !  ALL (0:nspec_th) MUST BE LABELED!
  !    suffix argument blank -- thermal species
  
  ps%s_type(0) = -1  !labels a species as thermal
  ps%s_type(1) = 1
  ps%s_type(2) = 5
  ps%s_type(3) = 4
  
  print*, ps%s_type
  
  CALL ps_label_spectype(-1, -1, 0, ps%s_type(0), &
       ps%s_name(0), ps%qatom_s(0), ps%q_s(0), ps%m_s(0))  ! electron

  CALL ps_label_spectype(1, 1, 2, ps%s_type(1), &
       ps%s_name(1), ps%qatom_s(1), ps%q_s(1), ps%m_s(1))  ! Deuterium
       
  CALL ps_label_spectype(1, 1, 1, ps%s_type(2), &
       ps%s_name(2), ps%qatom_s(2), ps%q_s(2), ps%m_s(2))  ! Hydrogen minorty
       
  CALL ps_label_spectype(1, 1, 2, ps%s_type(3), &
       ps%s_name(3), ps%qatom_s(3), ps%q_s(3), ps%m_s(3))  ! Deuterium beam

  CALL ps_merge_species_lists(ierr)
  if(ierr.ne.0) then
     write(iout,*) ' ?swim_state_test: ps_merge_species_lists: ierr=',ierr
     stop
  endif
  !  The state includes a special index for TOKAMAKIUM, the only plasma
  !  specie defined to have a RADIALLY VARYING <Z> and <A>:

  !ps%imp_index = 2  problems??

  !  *** fast species ***
  !  ALL (1:nspec_nonMax) MUST BE LABELED!
  !    suffix argument set -- fast species
  !
  !  (I have used suffixes "mino", "beam", and "fusn" for RF minority, beam,
  !  and fusion product ions respectively -- dmc).
  !
  !  Hydrogen minority -- "mino" suffix suggested...

  If(ps%nspec_nonMax .gt. 0) then
     CALL ps_label_species(iZ_mino, iZ_mino, iA_mino, 'mino', &
       ps%nonMax_name(1), ps%qatom_nonMax(1), ps%q_nonMax(1), ps%m_nonMax(1))
  end if
  !----------------------------------
  !  form combined species list -- some arrays e.g. RF power coupling will
  !    want to be defined over the combined list.
   write(iout,'(1x,a,1x,i3)') ' TOKAMAKIUM impurity specie index: ',ps%imp_index

  !  print out the species...
  !  Sanity checks...

  if((ps%imp_index.le.0).or.(ps%imp_index.gt.ps%nspec)) then
     write(iout,*) ' ?TOKAMAKIUM index (ps%imp_index) out of range.'
     stop
  endif

  if(ps%all_type(ps%imp_index).ne.ps_tokamakium) then
     write(iout,*) ' ?TOKAMAKIUM impurity type code error detected!'
     stop
  endif

  !  Print out combined species list...

  ii = -1
  do i=0,ps%nspec_th
     ii = ii + 1
     ps%all_name(ii) = ps%s_name(i)
     ps%qatom_all(ii) = ps%qatom_s(i)
     ps%q_all(ii) = ps%q_s(i)
     ps%m_all(ii) = ps%m_s(i)
     write(iout,1001) ii,trim(ps%all_name(ii)),ps%q_all(ii),ps%m_all(ii)
  enddo

  do i=1,ps%nspec_nonMax
     ii = ii + 1
     ps%all_name(ii) = ps%nonMax_name(i)
     ps%qatom_all(ii) = ps%qatom_nonMax(i)
     ps%q_all(ii) = ps%q_nonMax(i)
     ps%m_all(ii) = ps%m_nonMax(i)
     write(iout,1001) ii,trim(ps%all_name(ii)),ps%q_all(ii),ps%m_all(ii)
  enddo

1001 format(' Specie index: ',i2,1x,'"',a,'" charge & mass: ',2(1pe12.5,1x))
  ps%ant_model(1) = 'DIIID' ! no path yet--still in aorsa namelist
  !------------------------------------
  ! (d) continued: lists other than species lists...
  ! Define antenna list
  ! ALL (1:nrf_src) MUST BE LABELED!

  ps%icrf_src_name(1) = 'Ant_1'

  ! additional lists -- e.g. of neutral beams -- could be added to the state
  ! and defined...

  !==========================================================================
  ! (e) Initialize (rho,theta) grids -- use local CONTAIN'ed routine below...

!  CALL rho_grid(ps%nrho_n2d, ps%rho_n2d)  no rho_fi
  CALL rho_grid(ps%nrho_icrf, ps%rho_icrf)
  CALL rho_grid(ps%nrho,     ps%rho)

!  CALL th_grid(ps%ntheta_n2d,ps%theta_n2d)
  CALL th_grid(ps%ntheta_icrf,ps%theta_icrf)
  

  !==========================================================================
  ! (f) initial equilibrium
  !    Here I simply take an existing (old NSTX) equilibrium G-eqdsk file
  !    The R and Z grids will be allocated (allong with associated profile
  !    arrays on the first call to "ps_update_equilibrium".  It is assumed,
  !    at least for now, that the range and resolution of the R and Z grids,
  !    once established, will not change in time.

  !    A number of profiles corresponding to metric quantities and flux
  !    surface averages are also computed in this call

  !  this routine also initializes the ps%rho_eq and ps%th_eq grids
  !  on its first call
  print*, 'just before update equib'
  CALL ps_update_equilibrium(ierr, 'g096028.02650')
  if(ierr.ne.0) then
     write(iout,*) ' ?swim_state_test: ps_update_equilibrium: ierr=',ierr
     stop
  endif
  print*, 'just after updating the equilibrium'
  !==========================================================================
  ! (g) initial profiles

  !------------------------------------------------
  !  densities -- ps%ns(1:ps%nrho-1,0:ps%nspec_th)
  !     step function zone oriented data

  !  zone centered grid (construct local copy)

  nrho_zc = ps%nrho - 1
  allocate(rho_zc(nrho_zc))
  rho_zc = (ps%rho(1:nrho_zc) + ps%rho(2:ps%nrho))/2

  !   electron density

 ps_n_s(51,0) = 2.0*ps_n_s(50,0) - ps_n_s(49,0)  !need to add last boundary point = same slope
 
  ! only beam density is in MMs original files
  
 ps_n_s(51,2) = 2.0*ps_n_s(50,2) - ps_n_s(49,2)  !need to add last boundary point = same slope
 
 print*, '#0 electrons', ps_n_s(1:50,0)
 print*, '#2 beam', ps_n_s(1:50,2)
 
  ps%ns(1:nrho_zc,0) = (ps_n_s(1:nrho_zc, 0) + ps_n_s(2:nrho_zc+1,0))/2.
  
  ps%ns(:,2) = frac_mino * ps%ns(:,0)  !the minority density
   
  !beam density 
  ps%ns(1:nrho_zc,3) = (ps_n_s(1:nrho_zc, 2) + ps_n_s(2:nrho_zc+1,2))/2. 
 
  ps%ns(:,1) = (one - frac_mino) * ps%ns(:,0) - ps%ns(:,3) !bulk ions
  ! the above gives charge neutrality

  ! now the tempuratures
  ps_t_s(51,0) = 2.0*ps_t_s(50,0) - ps_t_s(49,0)
  ps_t_s(51,1) = 2.0*ps_t_s(50,1) - ps_t_s(49,1)
  ps_t_s(51,2) = 2.0*ps_t_s(50,2) - ps_t_s(49,2)
  !electrons
  ps%ts(1:nrho_zc,0) = (ps_t_s(1:nrho_zc, 0) + ps_t_s(2:nrho_zc+1,0))/2.
  !majority ions
  ps%ts(1:nrho_zc,1) = (ps_t_s(1:nrho_zc, 1) + ps_t_s(2:nrho_zc+1,1))/2.
  !beam ions
  print*, ps_t_s(1:nrho_zc,2), 'beam t'
  ps%ts(1:nrho_zc,3) = (ps_t_s(1:nrho_zc, 2) + ps_t_s(2:nrho_zc+1,2))/2.
  !minority ions
  ps%ts(:,2) = ps%ts(:,1)
  ps%power_ic(1) = 1.1e6
  ps%freq_ic(1) = 60.0
  

  !  Check conversions back
  allocate(buf1(ps%nrho))
  
  do i = 0, ps%nspec_th
    call zone_check(ps%nrho, buf1, ps%ts(:,i))
    print*, 'temp check -- ', trim(ps%s_name(i))
    print*, buf1
    call zone_check(ps%nrho, buf1, ps%ns(:,i))
    print*, 'density check -- ', trim(ps%s_name(i))
    print*, buf1
  end do
  
  deallocate(buf1)

  print*, 'just before storing the state'


  write(iout,*) ' -- storing plasma state -- '
  CALL ps_store_plasma_state(ierr)
  if(ierr.ne.0) then
     write(iout,*) ' ?swim_DIIID_aorsa: ps_store_plasma_state: ierr=',ierr
     stop
  endif

  write(iout,*) ' -- committing plasma state -- '
  CALL ps_commit_plasma_state(ierr)
  if(ierr.ne.0) then
     write(iout,*) ' ?swim_DIIID_aorsa: ps_commit_plasma_state: ierr=',ierr
     stop
  endif

  write(iout,*) ' -- clearing plasma state profiles to ZERO -- '
  CALL ps_clear_profs(ierr)
  if(ierr.ne.0) then
     write(iout,*) ' ?swim_DIIID_aorsa: ps_clear_profs: ierr=',ierr
     stop
  endif

  write(iout,*) ' -- get (restore) plasma state from file -- '
  CALL ps_get_plasma_state(ierr)
  if(ierr.ne.0) then
     write(iout,*) ' ?swim_DIIID_aorsa: ps_get_plasma_state: ierr=',ierr
     stop
  endif
  
  write(iout,*) ' -- storing plasma state -- '
  CALL ps_store_plasma_state(ierr)
  if(ierr.ne.0) then
     write(iout,*) ' ?swim_DIIID_aorsa: ps_store_plasma_state: ierr=',ierr
     stop
  endif

  write(iout,*) ' -- current and prior state files should be identical except for name.'



  !------------------------------------


  CONTAINS
    !------------------------------------
    subroutine zone_check(nrho, x_out, x_in)
    
      ! unravel zone points to boundary points
      integer, intent(in) :: nrho    ! # of pts covering [0:1]
      REAL(KIND=rspec), intent(in) :: x_in(nrho-1)  ! zone values
      REAL(KIND=rspec), intent(out) :: x_out(nrho)  ! boundary values
      
      integer :: irho
      
      x_out(nrho) = 0.5 * (3.0 * x_in(nrho -1) - x_in(nrho-2))
      do irho = nrho - 1, 1, -1
         x_out(irho) = 2.0 * x_in(irho) - x_out(irho + 1)
      end do
      
    end subroutine zone_check
      
    !------------------------------------
     SUBROUTINE rho_grid(nrho,rho)

      ! generate evenly spaced rho grid

      integer, intent(in) :: nrho    ! # of pts covering [0:1]
      REAL(KIND=rspec) :: rho(nrho)  ! the rho grid being generated

      REAL(KIND=rspec), parameter :: ONE = 1.0_rspec

      integer :: irho

      do irho = 1,nrho
         rho(irho) = (irho-1)*ONE/(nrho-1)
      enddo

    END SUBROUTINE rho_grid

    !------------------------------------
    SUBROUTINE th_grid(nth,th)

      ! generate evenly spaced theta grid [-pi:pi]

      integer, intent(in) :: nth    ! # of pts covering the range
      REAL(KIND=rspec) :: th(nth)   ! the theta grid being generated

      REAL(KIND=rspec), parameter :: PI = 3.1415926535897931_rspec

      integer :: ith

      do ith = 1,nth
         th(ith) = -PI + (ith-1)*2*PI/(nth-1)
      enddo

    END SUBROUTINE th_grid

    !------------------------------------
    SUBROUTINE profgen(f0,fa,rho,fans)

      !  quick & dirty profile generator

      REAL(KIND=rspec), intent(in) :: f0,fa  ! core and edge values
      REAL(KIND=rspec), dimension(:), intent(in) :: rho  ! normalized sqrt tor. flux
      REAL(KIND=rspec), dimension(:), intent(out) :: fans  ! formula output

      fans = (f0-fa)*(1.0_rspec-rho**2)**2 + fa

    END SUBROUTINE profgen

end program swim_state_init
