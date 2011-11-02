######################################################################
#
# CMakeLists.txt for tests
#
# $Id:$
#
######################################################################

#add_subdirectory(bin)
add_subdirectory(components)
add_subdirectory(comprehensive)
add_subdirectory(unittest)
add_subdirectory(refactor)
configure_file(frameworkpath.py.in ${CMAKE_CURRENT_BINARY_DIR}/frameworkpath.py)
