
Building IPS with CMake
=======================

This assumes that you have already checked out the simyan, and have the
dependencies installed in something like /contrib or /usr/local.

From the top level directory::
  
  mkdir build
  cd build
  cmake \
    -DCMAKE_INSTALL_PREFIX:PATH=/scr_gabrielle/kruger/volatile-gnu/webdocs/simyan \
    -DCMAKE_BUILD_TYPE:STRING=RELEASE \
    -DCMAKE_VERBOSE_MAKEFILE:BOOL=TRUE \
    -DCMAKE_INSTALL_ALWAYS:BOOL=TRUE \
    -DSUPRA_SEARCH_PATH='/usr/local;/contrb' \
    -DENABLE_WEBDOCS:BOOL=ON \
    $PWD/..

After configuring, to build IPS, the documentation, and run the tests
respectively::
  
  make
  make docs
  make test

The documentation may be found at docs/html/index.html.  The
tests are located in the tests subdirectory.


