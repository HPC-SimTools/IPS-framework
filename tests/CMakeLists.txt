######################################################################
#
# CMakeLists.txt for tests
#
# $Id:$
#
######################################################################

add_subdirectory(bin)
add_subdirectory(helloworld)
add_subdirectory(components)
add_subdirectory(dakota)
add_subdirectory(unittest)
add_subdirectory(permutations)
add_subdirectory(multirun)
configure_file(frameworkpath.py.in ${CMAKE_CURRENT_BINARY_DIR}/frameworkpath.py)
