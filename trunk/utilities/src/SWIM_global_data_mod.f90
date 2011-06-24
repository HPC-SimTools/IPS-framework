MODULE swim_global_data_mod

  SAVE
    
!--------------------------------------------------------------------------
!  original author: Don Batchelor (ORNL) 7/9/06
!                   batchelordb@ornl.gov (865) 574-1288
!
! Modifications:
!   
!   dbb 9/21/06 --  Use of derived types is deprecated when something simpler
!                   will work. Types SWIM_name, and SWIM_filename may dissappear.
!                   Added SWIM_name_length and SWIM_filename_length so as to
!                   avoid conflicting character string lengths.
!                   
!
!    dmc 21 Sep 2006 -- added SAVE stmt for global data
!                    -- changed default message in SWIM_ERROR to show
!                       "error_kind" argument.
!
!   F90 kind specifications
!
! For REAL variables
!   Use p = 6, r = 35       for single precision on 32 bit machines
!   Use p = 12, r = 100     for double precision on 64 bit machines
!
! For compatibility with SIDL doubles and ints
!   Use p = 15, r = 307     for doubles
!   Use p = 9               for ints
!
! Parameters for SELECTED_REAL_KIND:
!   p = number of digits
!   r = exponent range from -r to r
!
!--------------------------------------------------------------------------

    INTEGER, PARAMETER :: &
        rspec = SELECTED_REAL_KIND(p=15,r=307), &
        ispec = SELECTED_int_KIND(r=9)
        

!--------------------------------------------------------------------------
!
!   SWIM F90 derived data type declarations
!   Note: use of these derived types is deprecated and they may dissappear.
!   Use SWIM_name_length and SWIM_filename_length below in character declarations.
!
!--------------------------------------------------------------------------

    TYPE SWIM_name
        CHARACTER (len = 31) :: name    ! standard form for character names like species
    END TYPE SWIM_name

    TYPE SWIM_filename
        INTEGER :: unit                 ! Fortran unit number
        CHARACTER (len = 256) :: name   ! standard from for file names, should hold whole path
    END TYPE SWIM_filename
    

!--------------------------------------------------------------------------
!
!   Globally accessible data
!
!--------------------------------------------------------------------------



    INTEGER :: SWIM_ierr    ! Set in routine SWIM_error, below.  A simple way
                            ! to store some information about an error
    
    INTEGER, PARAMETER :: SWIM_err_out_file = 6 ! File to write error outputs.
                                                ! (Initially just standard out)

    INTEGER, PARAMETER :: SWIM_name_length = 31 ! Character string length to be
                                                ! used for names

    INTEGER, PARAMETER :: SWIM_filename_length = 256 ! Character string length to be
                                                ! used for file names

!--------------------------------------------------------------------------
!
!   Generally useful functions
!
!--------------------------------------------------------------------------

CONTAINS

!--------------------------------------------------------------------------
!
! SWIM_error
!   A simple way to handle errors. Writes to standard out the kind of error,
!   the routine from which SWIM_error was called, and optionally a variable
!   name associated with the error.  For example the name of an array for which
!   an allocation error occured.
!
!   It also sets an integer flag in the globally accessible data above: SWIM_ierr
!   This could be accessed by the caller or controller script to help figure out
!   What to do about the error.
!   
!   We can certainly be more elaborate later.
!
!--------------------------------------------------------------------------

SUBROUTINE SWIM_error (error_kind, calling_routine, variable_name)

    CHARACTER (len=*), INTENT(in) :: error_kind, calling_routine

    CHARACTER (len=*), OPTIONAL, INTENT(in) :: variable_name
    
    SWIM_ierr = 0
    
    SELECT CASE (TRIM( error_kind ))
    
        CASE ('allocation')
            IF (PRESENT( variable_name ))  THEN 
                WRITE(SWIM_err_out_file,*) 'Could not allocate ', &
                TRIM(variable_name), ' in routine ', TRIM(calling_routine)
            ELSE 
                WRITE(SWIM_err_out_file,*) 'Allocation error in routine ', TRIM(calling_routine)
            END IF
            
            SWIM_ierr = 1
    
        CASE ('open')
            IF (PRESENT( variable_name ))  THEN 
                WRITE(SWIM_err_out_file,*) 'Could not open file ', &
                TRIM(variable_name), ' in routine ', TRIM(calling_routine)
            ELSE 
                WRITE(SWIM_err_out_file,*) 'File open error in routine ', TRIM(calling_routine)
            END IF
            
            SWIM_ierr = 2
            
        CASE DEFAULT
            WRITE(*,*) '(Default Message) error "',TRIM(error_kind), &
                             '" in routine ', TRIM(calling_routine)
            
            SWIM_ierr = 999
            
    END SELECT
    
END SUBROUTINE SWIM_error
END MODULE swim_global_data_mod         


