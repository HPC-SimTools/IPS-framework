
Building IPS with CMake
=======================

This assumes that you have already checked out the simyan, and have the
dependencies installed in something like /contrib or /usr/local.

From the top level directory::
  
  mkdir build
  cd build
  cmake ..

After configuring, to build IPS, the documentation, and run the tests
respectively::
  
  make
  make docs
  make test

You can see

The documentation may be found at docs/html/index.html.  The
tests are located in the tests subdirectory.


A more complicated configuration example::

  cmake \
    -DCMAKE_INSTALL_PREFIX:PATH=/usr/local/ips \
    -DCMAKE_BUILD_TYPE:STRING=RELEASE \
    -DCMAKE_VERBOSE_MAKEFILE:BOOL=TRUE \
    -DCMAKE_INSTALL_ALWAYS:BOOL=TRUE \
    -DSUPRA_SEARCH_PATH='/usr/local;/contrb' \
    -DENABLE_WEBDOCS:BOOL=ON \
    $PWD/..

SUPRA_SEARCH_PATH is a list of directories to search for where to find
things like sphinx which is used to build the documentation.

