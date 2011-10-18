##########################################################################
# DESCRIPTION OF PROBLEMS (tokH_HRamp1):
# This input file sets the parameters for serial H-mode buildup case.
# Based on DIII-D discharge 0118897 1555 msec.  Using 30x30 mesh with
# hydrogen only.  This case only evolves electron and ion temperature with
# no convective heat flow. Spatially-dependent transport coefficients are
# obtained from an interpretive analysis of the pedestal region, and initial
# profiles are a spatial mix beginning with the tanh and spline fits to
# the data.
###########################################################################
#

# mesh construction --
bbb.mhdgeo=1
flx.aeqdskfname = 'a118897.01555'
flx.geqdskfname = 'g118897.01555'
com.geometry="snull"
flx.psi0min1=.85
flx.psi0min2=.98
flx.psi0sep=1.00005
flx.psi0max=1.08
flx.alfcy=3.0  
grd.slpxt=1.2
bbb.ngrid=1
com.nxleg[0,0] = 7
com.nxleg[0,1] = 7
com.nxcore[0,0] = 8
com.nxcore[0,1] = 8
com.nycore[0] = 18
com.nysol[0] = 12
##nxxpt=0;nxmod=3;alfxptu=0.5
##kxmesh=1

# core plasma boundary conditions --
bbb.iflcore=1  # flag for fixed core power condition
bbb.pcoree=2.2e6
bbb.pcorei=1.44e6     	#Uses xu50 executable
bbb.isnicore[0] = 3	#=3 ni=const; icore=curcore
bbb.ncore[0] = 3.0e19
bbb.curcore[0] = -200.	#NB cur used for interp analysis only
bbb.isupcore = 1
bbb.isngcore = 2

# radial energy convection coeff
bbb.cfloyi = 1.5
bbb.cfloye = 1.5

# outer wall plasma boundary conditions  --
bbb.isnwcono[0] = 3
bbb.lyni = 0.1	# fixed scale length, lyni
bbb.nwomin[0] = 1.e14
bbb.isextrtw=0	# extrapolation b.c.'s for temperature are OFF
bbb.istewc=3
bbb.lyte=0.1	# fixed scale length, lyte
bbb.istiwc=3
bbb.lyti=0.1	# fixed scale length, lyti

# private-flux wall plasma boundary conditions  --
bbb.isnwconi[0] = 3	# fixed scale length
bbb.nwimin[0] = 1.e14
bbb.istepfc=3	# fixed scale length, lyte
bbb.istipfc=3	# fixed scale length, lyti

# Finite-difference algorithms (upwind, central diff, etc.)
bbb.methn = 33                  #ion continuty eqn
bbb.methu = 33                  #ion parallel momentum eqn
bbb.methe = 33                  #electron energy eqn
bbb.methi = 33                  #ion energy eqn
bbb.methg = 33                  #neutral gas continuity eqn

# Numerical solver
bbb.svrpkg = "nksol"
bbb.premeth = "ilut"
delpy = 1.e-8

# Transport coefficients (dif_use, kye_use, kyi_use in restore file)
bbb.difni[0] = 0.               #D for radial hydrogen diffusion
bbb.kye = 0.                    #chi_e for radial elec energy diffusion
bbb.kyi = 0.                    #chi_i for radial ion energy diffusion
bbb.travis[0] = 0.5             #eta_a for radial ion momentum diffusion

# Flux limits
bbb.flalfe = 0.21               #electron parallel thermal conduct. coeff
bbb.flalfi = 0.21               #ion parallel thermal conduct. coef
bbb.isplflxl=0                  # turn off thermal flux limits at plate
bbb.flalfv = 0.5                #ion parallel viscosity coeff
bbb.flalfgx = 1.                #neut. gas in poloidal direction
bbb.flalfgy = 1.                #neut. gas in radial direction
bbb.flalftgx = 1.1              #neut. gas in poloidal direction
bbb.flalftgy = 1.1              #neut. gas in radial direction
bbb.lgmax = 0.05
bbb.lgtmax = 0.1
bbb.lgvmax = 0.1

# miscellaneous switches and options:
bbb.isupss=1

# Neutral parallel momentum eqn
bbb.isupgon[0] = 1
bbb.isngon[0] = 0
com.ngsp = 1
com.nhsp = 2
bbb.ziin[1] = 0
bbb.ineudif = 2                 #=2 uses pg=ng*tg as perp mom. variable
bbb.cfnidh = 0.                 #coeff. heating from charge-exchange (upi-upn)
bbb.ngbackg[0] = 1.e12          #floor for hydrogen neutral dens
bbb.ingb = 2                    #exponent for source of ng floor function
bbb.cngflox = 0.
bbb.cngfloy = 0.

# ion recycling at the plates:
bbb.recycp[0] = 1.0		# recycling as CX neutrals at the plates

# boundary conditions for neutrals:
bbb.nwsor=1			# number of source regions on each wall
bbb.issorlb[0] = 1		# measure source positions from left plate

# at outer wall --
bbb.igaso[0] = 250.			# no puff at outer boundary
bbb.xgaso = 0.
bbb.wgaso = 1000.
bbb.albdso[0] = 1.0
bbb.matwso[0] = 1			# material wall b.c. is ON

# at inner wall --
bbb.xgasi = 0.0
bbb.wgasi = 1000.
bbb.igasi[0] = 0.			# no puff at inner boundary
bbb.albdsi[0] = 1.0			# neutral pumping on inner boundary
bbb.matwsi[0] = 1			# material wall b.c. is ON

# ion recycling at the walls:
bbb.recycw[0] = 1.00		# recycling as CX neutrals at the walls

# atomic physics rates:
com.istabon = 10		# use DEGAS rates
bbb.isrecmon = 1		# recombination is ON
aph.aphdir = '../share'         #location of rate tables

# set tolerance for intial timestep and subsequent timesteps for rundt
bbb.ftol = 1.e-8
bbb.ftol_dt = 1.e-5
bbb.t_stop = 0.035
bbb.dt_max = 0.005
bbb.tstor_s = 0.5e-3
bbb.tstor_e = 2.e-2
bbb.n_stor = 30

# Switch for v*grad_P terms in engy eqns
bbb.cvgp = 0.

# This says to dump the diffusivities.  
# Definitely needed for the pdb2h5 conversion.
bbb.read_diffs=1

bbb.kye_io=1
bbb.kyi_io=1
bbb.dif_io=1
bbb.tra_io=0
bbb.dutm_io=0
bbb.vy_io=0
bbb.vyup_io=0
bbb.vyte_io=0
bbb.vyti_io=0
bbb.fniyos_io=0
bbb.feeyosn_io=0
bbb.feiyosn_io=0

