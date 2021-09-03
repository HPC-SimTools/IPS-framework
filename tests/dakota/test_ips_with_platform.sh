
source ../frameworkpath.py
PATH=$fsrc:$PATH

#-------------------------------------------------------------
echo; echo; echo
echo "-------------------------------------------------------"
echo "Testing with platform file specified"
echo "-------------------------------------------------------"
#-------------------------------------------------------------
${fsrc}/ips_dakota_dynamic.py --dakotaconfig=dakota_test_Rosenbrock.in --simulation=dakota_test_Rosenbrock.ips --platform=workstation.conf
