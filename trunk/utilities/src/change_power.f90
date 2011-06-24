program change_power

  
 
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
  !    SUBROUTINE PS_INTRP_1D(...)  for 1D profiles  LAB based on steps
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
!---------------------------------------------------------------------

!--------------------------------------------------------------------------
!
!   AORSA data that will be given to the state via the swim_out file
!   the aorsa output data is in a file called swim_out
!
!--------------------------------------------------------------------------
   


 
  IMPLICIT NONE

  !------------------------------------
  !  local
  INTEGER :: ierr, n
  INTEGER :: iout = 6

   
  write(iout,*) ' -- get (restore) plasma state from file -- '
  ! this call retrives the plasma state at the present ps%, and
  ! prvious time steps psp%
  
  CALL ps_get_plasma_state(ierr)

  if(ierr.ne.0) then
     write(iout,*) ' process aorsa: ps_get_plasma_state: ierr=',ierr
     stop
  endif
  
  ps%power_ic(1) = ps%power_ic(1) + 1.0E5

  call ps_store_plasma_state(ierr)
  if(ierr .ne. 0) then
     write(iout,*) '  cannot open state in change state'
  end if
  
  print*, 'new ic power'
  print*, ps%power_ic(1)

end program change_power
