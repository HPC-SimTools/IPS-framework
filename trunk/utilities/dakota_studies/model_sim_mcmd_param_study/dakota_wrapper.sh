#!/bin/bash -f
#
#

# Check for correct number of arguments (2 or 3)
if [ ! $# -eq 1 ]; then
    if [ ! $# -eq 2 ]; then
	echo ********************************************************
	echo *    INCORRECT NUMBER OF ARGUMENTS: $#
	echo ********************************************************
	echo * Script to run a Dakota parameter study on ips
	echo * Usage:
	echo *      ./dakota_wrapper.sh IPS_CONFIG_FILE DAKOTA_INPUT_FILE {optional parameters}
	echo * Example:
	echo *      ./dakota_wrapper.sh model_sim.config dakota_ips.config
	echo * Optional parameters:
	echo *      -dryrun
	echo *        script completes all configuration,
	echo *        creates all working files,
	echo *        but does not execute dakota
	echo ********************************************************
	exit 1
    fi
fi

DAKOTA_ROOT=/usr/common/usg/Dakota

# Where to put the working directory?
PARAMETER_STUDY_DIR="${PWD}/parameter_study"

# Grab the arguments
IPS_CONFIG_FILE=$1
echo "Using IPS config file: ${IPS_CONFIG_FILE}"

DAKOTA_CONFIG_FILE=$2
echo "Using Dakota config file: ${DAKOTA_CONFIG_FILE}"

# Check for the existence of the Dakota_root directory, and for the dakota executable
if [ ! -d $DAKOTA_ROOT ]; then
    echo Unable to find root directory for Dakota - $DAKOTA_ROOT does not exist.
    exit 1
fi
if [ ! -d $DAKOTA_ROOT/bin ]; then
    echo Unable to find bin directory for Dakota - $DAKOTA_ROOT/bin does not exist.
    exit 1
fi
if [ ! -x $DAKOTA_ROOT/bin/dakota ]; then
    echo Unable to find executable for Dakota - $DAKOTA_ROOT/bin/dakota does not exist or is not executable.
    exit 1
fi

# Check the arguments
if [ ! -e $DAKOTA_CONFIG_FILE ]; then
    echo File not found: $DAKOTA_CONFIG_FILE
    exit 6
fi

if [ ! -e $IPS_CONFIG_FILE ]; then
    echo File not found: $IPS_CONFIG_FILE
    exit 7
fi

# Grab the definition of IPS_ROOT from the IPS config file
IPS_ROOT=`../dakota_utils/extractVariableDefinition.py ${IPS_CONFIG_FILE} IPS_ROOT`
echo "Extracted IPS_ROOT value from ips config file: ${IPS_ROOT}"

# Check for the existence of the IPS_root directory, and for the ips executable
if [ ! -d $IPS_ROOT ]; then
    echo Unable to find root directory for IPS - $IPS_ROOT does not exist.
    exit 2
fi
if [ ! -d $IPS_ROOT/bin ]; then
    echo Unable to find bin directory for IPS - $IPS_ROOT/bin does not exist.
    exit 2
fi
if [ ! -x $IPS_ROOT/bin/ips ]; then
    echo Unable to find executable for IPS - $IPS_ROOT/bin/ips does not exist or is not executable.
    exit 2
fi

# Check for an existing work directory
if [ -d $PARAMETER_STUDY_DIR ]; then
    echo Working directory $PARAMETER_STUDY_DIR already exists, please rename or remove it and run again.
    exit 3
fi

# Check if user requested a dry run
DRY_RUN="False"
for arg in "$@"; do
    if [ $arg == "dryrun" ]; then
        DRY_RUN="True"
    fi
    if [ $arg == "-dryrun" ]; then
        DRY_RUN="True"
    fi
done

# Display settings and begin working
echo **************************************
echo * Dakota script running with these values:
echo *   Ips Root Directory = $IPS_ROOT
echo *   Ips Config File = $IPS_CONFIG_FILE
echo *   Dakota Root Directory = $DAKOTA_ROOT
echo *   Dakota Config File = $DAKOTA_CONFIG_FILE
echo *   Working Directory = $PARAMETER_STUDY_DIR
echo *   Dry Run? $DRY_RUN
echo **************************************

# If we got this far, all of the arguments were ok, so export them for other scripts
export IPS_ROOT
export DAKOTA_ROOT
export PARAMETER_STUDY_DIR
export IPS_CONFIG_FILE

# Create a working directory
mkdir $PARAMETER_STUDY_DIR
echo $PARAMETER_STUDY_DIR

echo DAKOTA_CONFIG_FILE = $DAKOTA_CONFIG_FILE
# Copy config files to working directory
cp $DAKOTA_CONFIG_FILE $PARAMETER_STUDY_DIR  #dakota settings file
cp $IPS_ROOT/components/epa/model_epa/model_epa_input_eqdsk_init.nml $PARAMETER_STUDY_DIR
cp ../dakota_utils/createInputNamelist.py $PARAMETER_STUDY_DIR
cp ../dakota_utils/parseIpsConfig.py $PARAMETER_STUDY_DIR
cp ips_wrapper.sh $PARAMETER_STUDY_DIR
cp $IPS_CONFIG_FILE $PARAMETER_STUDY_DIR

if [ $DRY_RUN = "False" ]; then
    # Go to work directory
    cd $PARAMETER_STUDY_DIR

    #invoke dakota - all of the rest of the information is in dakota_ips.in
    $DAKOTA_ROOT/bin/dakota -input $DAKOTA_CONFIG_FILE -output dakota_output.txt -error dakota_error.txt
    #clean up
    rm -rf ips_wrapper.sh
    rm -rf dakota.rst
    rm -rf createInputNamelist.py
    rm -rf parseIpsConfig.py

    #go back to starting directory
    cd ..
    
    echo Full run complete
else
    echo Dry run complete
fi
