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
set(VORPAL_VERSION ${VERSION_MAJOR}.${VERSION_MINOR}.${VERSION_PATCH})

# Required version
cmake_minimum_required(VERSION 2.8.3)
# Set group write installation perm
# May need to be different on different machines
if (NOT DEFINED TX_GROUP_WRITE)
  set(TX_GROUP_WRITE ""
      CACHE STRING "Value of group write permissions")
endif ()
if (NOT DEFINED TX_WORLD_PERMS)
  set(TX_WORLD_PERMS ""
      CACHE STRING "Value of group write permissions")
endif ()

######################################################################
#
# Usual initialization stuff
#
######################################################################

include(${CMAKE_SOURCE_DIR}/CMake/TxInit.cmake)

# Subdirectories
add_subdirectory(framework)
add_subdirectory(doc)

######################################################################
#
# Packages.
#
######################################################################

# Find/Setup Sphinx and MathJax
find_package(Sphinx)
if(SPHINX_FOUND)
   MESSAGE("SPHINX_EXECUTABLE found.")
   MESSAGE("SPHINX_EXECUTABLE  = ${SPHINX_EXECUTABLE}")
endif()


# Install files
install(FILES ${CMAKE_SOURCE_DIR}/svninfo.txt DESTINATION share
  PERMISSIONS OWNER_READ OWNER_WRITE GROUP_READ ${TX_GROUP_WRITE}
)
set(CONFIG_FILES ${CMAKE_BINARY_DIR}/CMakeCache.txt)

# CPack version numbers for release tarball name.
set(CPACK_PACKAGE_VERSION_MAJOR ${VERSION_MAJOR})
set(CPACK_PACKAGE_VERSION_MINOR ${VERSION_MINOR})
set(CPACK_PACKAGE_VERSION_PATCH ${VERSION_PATCH}-r${PROJECT_REV})

set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "Tech-X Vorpal")
set(CPACK_PACKAGE_VENDOR "Tech-X Corporation")
set(CPACK_SOURCE_PACKAGE_FILE_NAME "vorpal-${VORPAL_VERSION}r${PROJECT_REV}"
  CACHE INTERNAL "tarball basename"
)
set(CPACK_SOURCE_GENERATOR TGZ)
set(CPACK_SOURCE_IGNORE_FILES
  "/CVS/;/.svn/;.swp$;.#;/#;/build;/serial;/parallel;~;/autom4te.cache/;/.config")
set(CPACK_GENERATOR TGZ)
include(CPack)
