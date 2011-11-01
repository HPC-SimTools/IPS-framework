######################################################################
#
# CMakeLists.txt for simple examples
#
# $Id: CMakeLists.txt 17128 2011-06-23 16:10:39Z kruger $
#
######################################################################

# Project information
project(simyan)
set(VERSION_MAJOR "1")
set(VERSION_MINOR "0")
set(VERSION_PATCH "0")
set(IPS_VERSION ${VERSION_MAJOR}.${VERSION_MINOR}.${VERSION_PATCH})

# Required version
cmake_minimum_required(VERSION 2.8.3)
enable_testing()

######################################################################
#
# Usual initialization stuff
#
######################################################################

include(${CMAKE_SOURCE_DIR}/CMake/TxInit.cmake)
set(SIMYAN_VERSION "${PROJECT_VERSION}")
set(SIMYAN_REV "${PROJECT_REV}")

######################################################################
#
# Packages.
#
######################################################################
include(CMake/TxDocLogic.cmake)
# Documentation sudirectories
if (ENABLE_USERDOCS)
  add_subdirectory(doc)
endif ()
######################################################################
#
#  Do subdirectories after you find packages.
#
######################################################################
add_subdirectory(framework)
add_subdirectory(share)
add_subdirectory(components)
add_subdirectory(tests)

######################################################################
#
# Set the variables needed for platform.conf and configure.
#
######################################################################
set(PHYS_BIN_ROOT   "${CMAKE_BINARY_DIR}"
    CACHE PATH "Location of physics binaries")
set(DATA_TREE_ROOT  "${CMAKE_INSTALL_DIR}/share"
    CACHE PATH "Location of physics data files")
set(PORTAL_URL      "http://swim.gat.com:8080/monitor"
    CACHE STRING "URL of portal")
set(RUNID_URL       "http://swim.gat.com:4040/runid.esp"
    CACHE STRING "URL of runId")
set(MPIRUN          "mpiexec"
    CACHE STRING "Executable of mpi to submit jobs")
set(NODE_DETECTION  "checkjob"
    CACHE STRING "Resource detection method")
set(CORES_PER_NODE  "1"
    CACHE STRING "Cores per node")
set(SOCKETS_PER_NODE  "1"
    CACHE STRING "Sockets per node")
set(NODE_ALLOCATION_MODE "checkjob"
    CACHE STRING "node allocation")

TxPrintString("PHYS_BIN_ROOT  = ${PHYS_BIN_ROOT}")
TxPrintString("DATA_TREE_ROOT  = ${DATA_TREE_ROOT}")
TxPrintString("PORTAL_URL      = ${PORTAL_URL}")
TxPrintString("RUNID_URL       = ${RUNID_URL}")
TxPrintString("MPIRUN          = ${MPIRUN}")
TxPrintString("NODE_DETECTION  = ${NODE_DETECTION}")
TxPrintString("CORES_PER_NODE  = ${CORES_PER_NODE}")
TxPrintString("SOCKETS_PER_NODE  = ${SOCKETS_PER_NODE}")
TxPrintString("NODE_ALLOCATION_MODE  = ${NODE_ALLOCATION_MODE}")

#Other variables in platform.conf.in (HOSTNAME already set
set(IPS_ROOT "${CMAKE_BINARY_DIR}")  # Install needs to fix this

######################################################################
#
# Finalize (installation, packaging)
#
######################################################################
# Set before final installation and packaging
set(COMMON_INSTALL TRUE)
set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "IPS Framework")
set(CONFIG_FILES)  # Clear out
include(${CMAKE_SOURCE_DIR}/CMake/TxFinalize.cmake)
