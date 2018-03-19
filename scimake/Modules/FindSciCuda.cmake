######################################################################
# - FindSciCuda: Find include directories and libraries for Cuda.
#
# Module usage:
#   find_package(SciCuda ...)
#
# This module will define the following variables:
#  HAVE_CUDA, CUDA_FOUND = Whether libraries and includes are found
#  CUDA_INCLUDE_DIRS       = Location of Cuda includes
#  CUDA_LIBRARY_DIRS       = Location of Cuda libraries
#  CUDA_LIBRARIES          = Required libraries
#
# Copyright 2013-2015, Tech-X Corporation, Boulder, CO.
# See LICENSE file (EclipseLicense.txt) for conditions of use.
#
######################################################################

message("")
message("--------- Looking for CUDA -----------")
message(STATUS "SciCuda_FIND_VERSION = ${SciCuda_FIND_VERSION}.")
if (NOT WIN32 AND EXISTS /usr/local/cuda-${SciCuda_FIND_VERSION})
    set(CUDA_BIN_PATH /usr/local/cuda-${SciCuda_FIND_VERSION})
endif ()

find_package(CUDA ${SciCuda_FIND_VERSION})

if (CMAKE_BUILD_TYPE MATCHES Debug)
  list(APPEND CUDA_NVCC_FLAGS
      -g -G --use_fast_math --generate-code arch=compute_20,code=sm_20)
else ()
  list(APPEND CUDA_NVCC_FLAGS
      -O3
      --use_fast_math
      --ptxas-options=-v
      --generate-code arch=compute_20,code=sm_20
      --generate-code arch=compute_20,code=sm_21
      --generate-code arch=compute_30,code=sm_30
      --generate-code arch=compute_35,code=sm_35
      --generate-code arch=compute_50,code=sm_50
      --generate-code arch=compute_52,code=sm_52
   )
endif ()

string(FIND ${CMAKE_CXX_FLAGS} "-std=c++11" POS)
if (NOT ${POS} EQUAL -1)
  list(APPEND CUDA_NVCC_FLAGS "-std=c++11")
endif ()

# find_cuda_helper_libs(cusparse)
if (CUDA_CUDART_LIBRARY AND NOT CUDA_LIBRARY_DIRS)
  get_filename_component(CUDA_LIBRARY_DIRS ${CUDA_CUDART_LIBRARY}
    DIRECTORY CACHE
  )
endif ()

# if (ENABLE_PARALLEL AND SCI_SERIAL_C_COMPILER)
if (ENABLE_PARALLEL)
# This is needed to get around nvcc finding what mpicc is linked to
# and using that, which then prevents the openmpi compilers from knowing
# what configuration file to use.
  set(CUDA_HOST_COMPILER ${CMAKE_C_COMPILER})
  # list(APPEND CUDA_NVCC_FLAGS -ccbin ${SCI_SERIAL_C_COMPILER})
endif ()

# If CMake version >= 2.8.11, need to add the CUDA library manually
if (${CMAKE_VERSION} VERSION_GREATER 2.8.10)
  if (CUDA_CUDA_LIBRARY)
    get_filename_component(CUDA_CUDA_DIR ${CUDA_CUDA_LIBRARY}/.. REALPATH)
    set(CUDA_LIBRARIES ${CUDA_LIBRARIES} ${CUDA_CUDA_LIBRARY})
    if (LINUX)
      set(CUDA_LIBRARIES ${CUDA_LIBRARIES} "-Wl,-rpath -Wl,${CUDA_CUDA_DIR}")
    endif ()
  else ()
    message(WARNING "CUDA_CUDA_LIBRARY not found, so link may fail.")
  endif ()
endif ()

# The cuda library may not be in the frameworks area
find_library(CUDA_cuda_SHLIB cuda
  PATHS /usr/local/cuda-${CUDA_VERSION}
  PATH_SUFFIXES lib64 lib
  NO_DEFAULT_PATH
)
if (CUDA_cuda_SHLIB)
  get_filename_component(CUDA_cuda_SHLIB_DIR ${CUDA_cuda_SHLIB}
    DIRECTORY CACHE
  )
  set(CUDA_LIBRARY_DIRS ${CUDA_LIBRARY_DIRS} ${CUDA_cuda_SHLIB_DIR})
else ()
  set(CUDA_cuda_SHLIB ${CUDA_CUDA_LIBRARY})
endif ()

if (CUDA_TOOLKIT_ROOT_DIR)
  set(HAVE_CUDA_TOOLKIT TRUE)
  set(CUDA_BASE_LIBRARIES ${CUDA_cusparse_LIBRARY} ${CUDA_CUDART_LIBRARY})
# cublas is linked to cuda as opposed to dlopening it.  So it cannot
# be linked but must be dlopened.
  if (APPLE)
# Could we instead use "-undefined dynamic_lookup"?
    set(CUDA_BASE_LIBRARIES ${CUDA_BASE_LIBRARIES} ${CUDA_cuda_SHLIB})
  endif ()
else ()
  set(HAVE_CUDA_TOOLKIT FALSE)
endif ()

# Print results
SciPrintCMakeResults(CUDA)
foreach (sfx VERSION CUDA_LIBRARY cuda_SHLIB NVCC_EXECUTABLE
    NVCC_FLAGS TOOLKIT_ROOT_DIR TOOLKIT_INCLUDE INCLUDE_DIRS
    LIBRARY_DIRS LIBRARIES CUDART_LIBRARY
    curand_LIBRARY cublas_LIBRARY
    cusparse_LIBRARY cufft_LIBRARY npp_LIBRARY cupti_LIBRARY
    BASE_LIBRARIES
)
  SciPrintVar(CUDA_${sfx})
endforeach ()
SciPrintVar(HAVE_CUDA_TOOLKIT)
message("")

# Macros covering presence or absence of cuda
macro(scicuda_add_library)
  if (HAVE_CUDA_TOOLKIT)
    cuda_add_library(${ARGV})
  else ()
    add_library(${ARGV})
  endif ()
endmacro()

macro(scicuda_add_executable)
  if (HAVE_CUDA_TOOLKIT)
    cuda_add_executable(${ARGV})
  else ()
    add_executable(${ARGV})
  endif ()
endmacro()

