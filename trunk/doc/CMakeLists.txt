######################################################################
#
# CMakeLists.txt for docs
#
# $Id: CMakeLists.txt 1138 2011-01-28 00:25:57Z swsides $
#
######################################################################

#
# Install files in build directory
# 
if(${ENABLE_WEBDOCS})
	message(STATUS "enable webdocs is on")
	install(DIRECTORY ${CMAKE_BINARY_DIR}/doc/
			  DESTINATION ${CMAKE_INSTALL_PREFIX}
		          PATTERN  "Makefile" EXCLUDE
		          PATTERN  "cmake_install.cmake" EXCLUDE
		          PATTERN  "CMakeFiles" EXCLUDE
		          PATTERN  "Makefile.sphinx" EXCLUDE
		          PATTERN  "conf.py" EXCLUDE
		          PATTERN  ".svn" EXCLUDE)
else()
	install(DIRECTORY ${CMAKE_BINARY_DIR}/doc/
			  DESTINATION ${CMAKE_INSTALL_PREFIX}/doc
		          PATTERN  "Makefile" EXCLUDE
		          PATTERN  "cmake_install.cmake" EXCLUDE
		          PATTERN  "CMakeFiles" EXCLUDE
		          PATTERN  "Makefile.sphinx" EXCLUDE
		          PATTERN  "conf.py" EXCLUDE
			    PATTERN  ".svn" EXCLUDE)
endif()

# Substitute paths in conf.py.in file (this installs in build directory)
configure_file(conf.py.in  conf.py)
configure_file(Makefile.sphinx.in  Makefile.sphinx)

#
# Generic stuff for userdocs.  See subdirectories for targets
#
add_custom_target(docs)
add_custom_target(docs-html      COMMAND make html           -f Makefile.sphinx)
add_custom_target(docs-dirhtml   COMMAND make singlehtml  -f Makefile.sphinx)
add_custom_target(docs-latexpdf  COMMAND make latexpdf     -f Makefile.sphinx)
add_dependencies(docs docs-html docs-latexpdf)


add_custom_target(install-docs
                   COMMAND $(CMAKE_COMMAND)  -P $(CMAKE_BINARY_DIR)/doc/cmake_install.cmake)
add_dependencies(install-docs docs)
