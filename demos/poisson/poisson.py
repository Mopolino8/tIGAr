"""
The "hello, world" of computational PDEs:  Solve the Poisson equation, 
verifying accuracy via the method of manufactured solutions.  

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
NELu = 20
NELv = 20

# Parameters determining the position and size of the domain.
x0 = 0.0
y0 = 0.0
Lx = 1.0
Ly = 1.0

if(mpirank==0):
    print("Generating extraction...")

# Create a control mesh for which $\Omega = \widehat{\Omega}$.
splineMesh = ExplicitBSplineControlMesh([p,q],\
                                        [uniformKnots(p,x0,x0+Lx,NELu),\
                                         uniformKnots(q,y0,y0+Ly,NELv)])

# Create a spline generator for a spline with a single scalar field on the
# given control mesh, where the scalar field is the same as the one used
# to determine the mapping $\mathbf{F}:\widehat{\Omega}\to\Omega$.
splineGenerator = EqualOrderSpline(1,splineMesh)

# Set Dirichlet boundary conditions on the 0-th (and only) field, on both
# ends of the domain, in both directions.
field = 0
scalarSpline = splineGenerator.getScalarSpline(field)
for parametricDirection in [0,1]:
    for side in [0,1]:
        sideDofs = scalarSpline.getSideDofs(parametricDirection,side)
        splineGenerator.addZeroDofs(field,sideDofs)

# Alternative: set BCs based on location of corresponding control points.
# (Note that this only makes sense for splineGenerator of type
# EqualOrderSpline; for non-equal-order splines, there is not
# a one-to-one correspondence between degrees of freedom and geometry
# control points.)

#field = 0
#class BdryDomain(SubDomain):
#    def inside(self,x,on_boundary):
#        return (near(x[0],x0) or near(x[0],x0+Lx)
#                or near(x[1],y0) or near(x[1],y0+Ly))
#splineGenerator.addZeroDofsByLocation(BdryDomain(),field)


# Write extraction data to the filesystem.
DIR = "./extraction"
splineGenerator.writeExtraction(DIR)


####### Analysis #######

if(mpirank==0):
    print("Setting up extracted spline...")

# Choose the quadrature degree to be used throughout the analysis.
# In IGA, especially with rational spline spaces, under-integration is a
# fact of life, but this does not impair optimal convergence.
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

# Create a force, f, to manufacture the solution, soln
x = spline.spatialCoordinates()
soln = sin(pi*(x[0]-x0)/Lx)*sin(pi*(x[1]-y0)/Ly)
f = -spline.div(spline.grad(soln))

# Set up and solve the Poisson problem
res = inner(spline.grad(u),spline.grad(v))*spline.dx - inner(f,v)*spline.dx
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
