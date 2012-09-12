#------------------------------------------------------------------
#  Set location and hostname info that's more useful
#  Variables:
#   	hostnm
#   	location
#------------------------------------------------------------------
function host_info
{	
	hostnm=`hostname`
	if [ -f /usr/ucb/hostname ]; then hostnm=`/usr/ucb/hostname`; fi
	machinetype=`uname`

	case $hostnm in
	  # hopper
	  hopper*)  
		hostnm="hopper"; location="nersc"
            MPIRUN=aprun
            PHYS_BIN_ROOT=/project/projectdirs/m876/phys-bin/phys-hopper/
            DATA_TREE_ROOT=/project/projectdirs/m876/data
            PORTAL_URL=http://swim.gat.com:8080/monitor		# URL for the portal
            RUNID_URL=http://swim.gat.com:4040/runid.esp
            DATA_ROOT=/project/projectdirs/m876/data/
            NODE_DETECTION=checkjob
            CORES_PER_NODE=24
            SOCKETS_PER_NODE=4
            NODE_ALLOCATION_MODE=EXCLUSIVE 
            USE_ACCURATE_NODES=OFF 
		;;
	  # carver
	  carver*)  
		hostnm="carver"; location="nersc"
            DATA_ROOT=/project/projectdirs/m876/data/
            NODE_DETECTION=pbs_env
            TOTAL_PROCS=32
            NODES=4
            PROCS_PER_NODE=8
            CORES_PER_NODE=8
            SOCKETS_PER_NODE=2
            NODE_ALLOCATION_MODE=SHARED
		;;
	  # frost
	  frost*)  
		hostnm="frost"; location="?"
            MPIRUN=mpirun
            MPIRUN_VERSION=SGI
            NODE_DETECTION=qstat2
            CORES_PER_NODE=4
            SOCKETS_PER_NODE=2
            NODE_ALLOCATION_MODE=SHARED
		;;
	  # odin
	  odin*)  
		hostnm="odin"; location="?"
            MPIRUN=mpirun
            PHYS_BIN_ROOT=/nfs/rinfs/san/homedirs/ssfoley
            DATA_TREE_ROOT=/nfs/rinfs/san/homedirs/ssfoley
            DATA_ROOT=/nfs/rinfs/san/homedirs/ssfoley
            NODE_DETECTION=slurm_env
            CORES_PER_NODE=4
            SOCKETS_PER_NODE=2
            NODE_ALLOCATION_MODE=SHARED 
		;;
	  pacman*)  
		hostnm="pacman"; location="?"
            MPIRUN=mpirun
            PHYS_BIN_ROOT=/home
            PORTAL_URL=http://swim.gat.com:8080/monitor		
            RUNID_URL=http://swim.gat.com:4040/runid.esp
            NODE_DETECTION=pbs_env 
            TOTAL_PROCS=64
            NODES=4
            PROCS_PER_NODE=16
            CORES_PER_NODE=16
            SOCKETS_PER_NODE=4
            NODE_ALLOCATION_MODE=SHARED 
		;;
	  stix*)  
		hostnm="stix"; location="pppl"
            MPIRUN=mpiexec
            PHYS_BIN_ROOT=/p/swim1/phys
            PORTAL_URL=http://swim.gat.com:8080/monitor		
            RUNID_URL=http://swim.gat.com:4040/runid.esp
            DATA_TREE_ROOT=/p/swim1/data 
            NODE_DETECTION=pbs_env 
            TOTAL_PROCS=16
            NODES=1
            PROCS_PER_NODE=${TOTAL_PROCS}
            CORES_PER_NODE=${TOTAL_PROCS}
            SOCKETS_PER_NODE=${TOTAL_PROCS}
            NODE_ALLOCATION_MODE=SHARED
		;;
	  sif*)  
		hostnm="sif"; location="?"
            MPIRUN=mpirun
            PHYS_BIN_ROOT=/nfs/rinfs/san/homedirs/ssfoley
            DATA_TREE_ROOT=/nfs/rinfs/san/homedirs/ssfoley
            DATA_ROOT=/nfs/rinfs/san/homedirs/ssfoley
            NODE_DETECTION=slurm_env 
            CORES_PER_NODE=8
            SOCKETS_PER_NODE=2
            NODE_ALLOCATION_MODE=SHARED
		;;
      esac
}

