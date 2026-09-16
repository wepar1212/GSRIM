// Independently implemented classical ZBL scattering. One collision per thread.
__device__ double screening(double x) {
    return .1818*exp(-3.2*x)+.5099*exp(-.9423*x)
         + .2802*exp(-.4029*x)+.02817*exp(-.2016*x);
}
extern "C" __global__ void binary_scatter(
    const double* energy, const double* impact, const double* nodes,
    const double* weights, double* angles, double* recoils, double* roots,
    int count, int order, double a, double k, double m1, double m2,
    int screened) {
    int i = blockDim.x*blockIdx.x + threadIdx.x;
    if (i >= count) return;
    double e = energy[i], b = impact[i], ec = e*m2/(m1+m2);
    double c = k/ec, low = 0., high = .5*(c+sqrt(c*c+4*b*b));
    for (int j=0; j<64; ++j) {
        double r = .5*(low+high);
        double v = k/r*(screened ? screening(r/a) : 1.);
        if (1.-(b/r)*(b/r)-v/ec > 0.) high=r; else low=r;
    }
    double r0 = .5*(low+high), integral=0.;
    for (int j=0; j<order; ++j) {
        double t=nodes[j], u=1.-t*t, r=r0/u;
        double v=k/r*(screened ? screening(r/a) : 1.);
        double f=1.-(b*u/r0)*(b*u/r0)-v/ec;
        integral += weights[j]*2*t/sqrt(fmax(f,1e-30));
    }
    double angle = b == 0. ? 3.14159265358979323846
                          : 3.14159265358979323846-2*b/r0*integral;
    angles[i]=angle;
    recoils[i]=e*(4*m1*m2/((m1+m2)*(m1+m2)))*sin(angle/2)*sin(angle/2);
    roots[i]=r0;
}
