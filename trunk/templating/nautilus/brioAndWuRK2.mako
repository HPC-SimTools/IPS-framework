##available to all input files
<%
tStart = 0.0
tEnd = 0.1
numFrames = 1
initDt = 0.1
verbosity = 'info'
usePeriodicBoundaries = True
%>

##Just some scalars
<%
MU0 = 1.26e-6
GAMMA = 5.0/3.0
integrationScheme = 'rk1'
numericalFlux = 'hlldMhdFlux'
preservePositivity = 'true'
limiter = 'characteristicMinMod'
%>

##Random variables! you can define as many as you want or none at all!
<%
variableList = []
variableList.append("pr = 1.0")
variableList.append("pl = 0.1")
variableList.append("rhor = 1.0")
variableList.append("rhol = 0.125")
variableList.append("mu0 = "+`MU0`)
variableList.append("gas_gamma = "+`GAMMA`)
%>

##Pre expressions. There can be as many as you want.  These help you define your initial conditions
<% 
thisList = []
thisList.append("rho = if (x > 0.0, rhol, rhor)")
thisList.append("v = 0.0")
thisList.append("u = 0.0")
thisList.append("w = 0.0")
thisList.append("P = if(x > 0.0, pl, pr)")
thisList.append("bx = 0.75*sqrt(mu0)")
thisList.append("by = if(x>0.0, -1.0*sqrt(mu0), 1.0*sqrt(mu0))")
thisList.append("bz = 0.0")
thisList.append("phi = 0.0")
%>

##Variables that go into the pre expression -- there will only be 8 for this system.  These
##are your actual initial conditions
<% 
densityExpr = "rho"
xMomentumExpr = "rho*u"
yMomentumExpr = "rho*v"
zMomentumExpr = "0.0"
energyExpr = "P/(gas_gamma-1) + 0.5*rho*(u*u+v*v)+(0.5/mu0)*(bx*bx+by*by)"
bxExpr = "bx"
byExpr = "by"
bzExpr = "bz"
%>


<%doc>
Everything below here should not be touched.  Everthing above this point
can be modified by the GUI
</%doc>


tStart = ${tStart}
tEnd = ${tEnd}
numFrames = ${numFrames}
initDt = ${initDt}
verbosity = ${verbosity}


<Component fluids>
  kind = updaterComponent

  <Grid domain>
    kind = cart1d
    lower = [-0.5]
    upper = [0.5]
    cells = [200]

    %if usePeriodicBoundaries==True:	
    periodicDirs = [0 1] # X direction is periodic
    %endif
  </Grid>

  <DataStruct q>
    kind = distArray1d
    onGrid = domain
    guard = [2 2]
    numComponents = 9
  </DataStruct>

    <DataStruct dummy1>
    kind = distArray1d
    onGrid = domain
    guard = [2 2]
    numComponents = 9
  </DataStruct>
  
  <DataStruct dummy2>
    kind = distArray1d
    onGrid = domain
    guard = [2 2]
    numComponents = 9
  </DataStruct>
  
  <DataStruct dummy3>
    kind = distArray1d
    onGrid = domain
    guard = [2 2]
    numComponents = 9
  </DataStruct>

  <DataStruct qAux>
    kind = distArray1d
    onGrid = domain
    guard = [2 2]
    numComponents = 9
    writeOut = 0
  </DataStruct>

  <DataStruct qnew>
    kind = distArray1d
    onGrid = domain
    guard = [2 2]
    numComponents = 9
    writeOut = 0
  </DataStruct>

# updater for initial conditions
  <Updater init>
    kind = initArrayUpdater
    onGrid = domain
    out = [q qnew]

    <Function func>
      kind = exprFunc
		
	  %for thisVar in variableList: 	
      ${thisVar}
      %endfor
      
      
      preExprs = [ \
      %for thisVar in thisList:
      "${thisVar}" \
      %endfor
      ]
	  

      exprs = ["${densityExpr}" "${xMomentumExpr}" "${yMomentumExpr}" "${zMomentumExpr}" "${energyExpr}" "${bxExpr}" "${byExpr}" "${bzExpr}" "0.0"]

    </Function>

  </Updater>

  <Updater bcLeft>
    kind = copyGridBndryUpdater1d
    onGrid = domain
    out = [q]
    dir = 0
    edge = lower
  </Updater>
  
  <Updater bcRight>
    kind = copyGridBndryUpdater1d
    onGrid = domain
    out = [q]
    dir = 0
    edge = upper
  </Updater>

  <Updater hyper>
    kind = musclUpdater1d
    timeIntegrationScheme = none
    numericalFlux = ${numericalFlux}
    preservePositivity = ${preservePositivity}
    onGrid = domain

    limiter = ${limiter}
    in = [q qAux]

    out = [qnew]

    cfl = 0.5

    equations = [mhd]

     <Equation mhd>
      kind = mhdMunzEqn
      mu0 = ${MU0}
      gasGamma = ${GAMMA}
      correctionSpeed = 0.0
    </Equation>

  </Updater>

  <Updater rkUpdater>
    kind = multiUpdater1d
    onGrid = domain
    timeIntegrationScheme = ${integrationScheme}

    %if usePeriodicBoundaries :
	updaters = [hyper]
    %else:
    updaters = [bcLeft bcRight hyper]
    %endif
    
    syncVars_bcRight=[q]
    syncVars_hyper = [qnew]
    
    integrationVariablesIn = [q]
    integrationVariablesOut = [qnew]
    dummyVariables_q = [dummy1 dummy2 dummy3]

    syncAfterSubStep = [qnew]
  </Updater>

  <Updater copier>
    kind = linCombinerUpdater
    onGrid = domain

    in = [qnew]
    out = [q]
    coeffs = [1.0]

  </Updater>

  <UpdateStep initStep>
     updaters = [init]
     syncVars = [q qnew]
  </UpdateStep>

  <UpdateStep hyperStep>
     updaters = [rkUpdater]
  </UpdateStep>
  
  <UpdateStep correctionStep>
    updaters = [correct]
  </UpdateStep>

  <UpdateStep copyStep>
     updaters = [copier]
     syncVars = [q qnew]
  </UpdateStep>

  <UpdateSequence sequence>
    startOnly = [initStep]
    loop = [hyperStep copyStep]
  </UpdateSequence>

</Component>
