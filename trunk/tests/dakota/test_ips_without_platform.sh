
source ../frameworkpath.py

#-------------------------------------------------------------
echo; echo; echo
echo "-------------------------------------------------------"
echo "Testing without platform file specified"
echo "-------------------------------------------------------"
#-------------------------------------------------------------
${fsrc}/ips_dakota_dynamic.py --dakotaconfig=dakota_test_Rosenbrock.in --simulation=dakota_test_Rosenbrock.ips
exit
