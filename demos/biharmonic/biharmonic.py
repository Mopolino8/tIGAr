"""
The simplest example of a weak form that cannot be approached with traditional
FEA:  The biharmonic problem.

This example uses the simplest IGA discretization, namely, explicit B-splines
in which parametric and physical space are the same.
"""

from tIGAr import *
from tIGAr.BSplines import *
import math

####### Preprocessing #######

# Parameters determining the polynomial degree and number of elements in
# each parametric direction.  By changing these and recording the error,
# it is easy to see that the discrete solutions converge at optimal rates under
# refinement.
p = 3
q = 3
NELu = 40
NELv = 40

if(mpirank==0):
    print("Generating extraction...")

# Create a control mesh for which $\Omega = \widehat{\Omega}$.
splineMesh = ExplicitBSplineControlMesh([p,q],\
                                        [uniformKnots(p,-1.0,1.0,NELu),\
                                         uniformKnots(q,-1.0,1.0,NELv)])

# Create a spline generator for a spline with a single scalar field on the
# given control mesh, where the scalar field is the same as the one used
# to determine the mapping $\mathbf{F}:\widehat{\Omega}\to\Omega$.
splineGenerator = EqualOrderSpline(1,splineMesh)

# Set Dirichlet boundary conditions on the 0-th (and only) field, on both
# ends of the domain, in both directions, for two layers of control points.
# This strongly enforces BOTH $u=0$ and $\nabla u\cdot\mathbf{n}=0$. 
field = 0
scalarSpline = splineGenerator.getScalarSpline(field)
for parametricDirection in [0,1]:
    for side in [0,1]:
        sideDofs = scalarSpline.getSideDofs(parametricDirection,side,
                                            ##############################
                                            nLayers=2) # two layers of CPs
                                            ##############################
        splineGenerator.addZeroDofs(field,sideDofs)

# Write extraction data to the filesystem.
DIR = "./extraction"
splineGenerator.writeExtraction(DIR)

####### Analysis #######

if(mpirank==0):
    print("Setting up extracted spline...")

# Choose the quadrature degree to be used throughout the analysis.
QUAD_DEG = 2*max(p,q)

# Create the extracted spline directly from the generator.
# As of version 2017.2, this is required for using quad/hex elements in
# parallel.
spline = ExtractedSpline(splineGenerator,QUAD_DEG)

# Alternative: Can read the extracted spline back in from the filesystem.
# For quad/hex elements, in version 2017.2, this only works in serial.

#spline = ExtractedSpline(DIR,QUAD_DEG)


if(mpirank==0):
    print("Solving...")

# Homogeneous coordinate representation of the trial function u.  Because all
# weights are 1 in the B-spline case, this can be used directly in the PDE,
# without dividing through by weight.
u = TrialFunction(spline.V)

# Corresponding test function.
v = TestFunction(spline.V)

# Laplace operator, using spline's div and grad operations
def lap(x):
    return spline.div(spline.grad(x))

# Create a force, f, to manufacture the solution, soln
x = spline.spatialCoordinates()
soln = (cos(pi*x[0])+1.0)*(cos(pi*x[1])+1.0)
f = lap(lap(soln))

# Set up and solve the Poisson problem
res = inner(lap(u),lap(v))*spline.dx - inner(f,v)*spline.dx
u = Function(spline.V)
spline.solveLinearVariationalProblem(res,u)


####### Postprocessing #######

# The solution, u, is in the homogeneous representation, but, again, for
# B-splines with weight=1, this is the same as the physical representation.
File("results/u.pvd") << u

# Compute and print the $L^2$ error in the discrete solution.
L2_error = math.sqrt(assemble(((u-soln)**2)*spline.dx))
if(mpirank==0):
    print("L2 Error = "+str(L2_error))
