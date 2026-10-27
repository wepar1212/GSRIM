// Independent research BCA transport. Amorphous, static planar layers.
// Scattering: universal ZBL table in reduced (eps, rho) with Catmull-Rom bicubic,
// or full quadrature. Outputs never imply SRIM equivalence.
struct Particle { double x,y,z,ux,uy,uz,e; int s,primary; };

__device__ double uniform(unsigned long long &state) {
    state ^= state >> 12; state ^= state << 25; state ^= state >> 27;
    return fmin(0.9999999999999999,((state*2685821657736338717ULL >> 11)+0.5)*1.1102230246251565e-16);
}
__device__ unsigned long long init_seed(unsigned long long x) {
    x+=0x9e3779b97f4a7c15ULL;
    x=(x^(x>>30))*0xbf58476d1ce4e5b9ULL;
    x=(x^(x>>27))*0x94d049bb133111ebULL;
    return (x^(x>>31)) | 1ULL;
}
__device__ double phi_zbl(double x) {
    return .1818*exp(-3.2*x)+.5099*exp(-.9423*x)+.2802*exp(-.4029*x)+.02817*exp(-.2016*x);
}
__device__ double theta_quadrature(double ec,double b,double a,double k,const double* nodes,const double* weights) {
    if(!isfinite(ec)||!isfinite(b)||!isfinite(a)||!isfinite(k)||ec<=0.||b<0.||a<=0.||k<=0.) return nan("");
    if(b==0.)return 3.141592653589793;
    double c=k/ec*phi_zbl(0.),lo=0.,hi=.5*(c+sqrt(c*c+4*b*b));
    for(int q=0;q<64;q++) {
        double r=.5*(lo+hi);
        if(1.-b*b/(r*r)-k*phi_zbl(r/a)/(r*ec)>0.) hi=r; else lo=r;
    }
    double r0=.5*(lo+hi),integral=0.;
    if(!isfinite(r0)||r0<=0.)return nan("");
    for(int q=0;q<64;q++) {
        double t=nodes[q],u=1.-t*t;
        double f=1.-b*b*u*u/(r0*r0)-k*u*phi_zbl(r0/(u*a))/(r0*ec);
        if(!isfinite(f)||f < -1e-12) return nan("");
        integral+=weights[q]*2*t/sqrt(fmax(f,1e-28));
    }
    double angle=3.141592653589793-2*b/r0*integral;
    // Tolerate roundoff near zero, but do not turn a failed solve into
    // apparently physical zero/pi scattering through fmin/fmax's NaN rules.
    if(!isfinite(angle)||angle < -1e-7||angle > 3.141592653589793+1e-7) return nan("");
    return fmin(3.141592653589793,fmax(0.,angle));
}
__device__ void catmull_weights(double t,double* w) {
    double t2=t*t,t3=t2*t;
    w[0]=-0.5*t+t2-0.5*t3;
    w[1]=1.0-2.5*t2+1.5*t3;
    w[2]=0.5*t+2.0*t2-1.5*t3;
    w[3]=-0.5*t2+0.5*t3;
}
__device__ int clampi(int v,int lo,int hi){return v<lo?lo:(v>hi?hi:v);}
__device__ double theta_table(const double* table,const double* log_eps,const double* log_rho,
                              int ne,int nr,double eps,double rho) {
    if(!isfinite(eps)||!isfinite(rho)||eps<=0.||rho<0.||ne<2||nr<2) return nan("");
    if(rho==0.0) return 3.141592653589793;
    eps=eps<1e-300?1e-300:eps;
    double le=log(eps), lr=log(rho);
    double dle=log_eps[1]-log_eps[0], dlr=log_rho[1]-log_rho[0];
    double fi=(le-log_eps[0])/dle, fj=(lr-log_rho[0])/dlr;
    fi=fmin(fmax(fi,0.0),(double)(ne-1)-1e-12);
    fj=fmin(fmax(fj,0.0),(double)(nr-1)-1e-12);
    int i=(int)floor(fi), j=(int)floor(fj);
    double ti=fi-i, tj=fj-j;
    double wi[4],wj[4];
    catmull_weights(ti,wi); catmull_weights(tj,wj);
    double acc=0.0;
    for(int di=-1;di<=2;di++) {
        int ii=clampi(i+di,0,ne-1);
        double wa=wi[di+1];
        if(wa==0.0) continue;
        for(int dj=-1;dj<=2;dj++) {
            int jj=clampi(j+dj,0,nr-1);
            double wb=wj[dj+1];
            if(wb==0.0) continue;
            acc+=wa*wb*table[(size_t)ii*nr+jj];
        }
    }
    if(!isfinite(acc))return nan("");
    return fmin(3.141592653589793,fmax(0.0,acc));
}
__device__ int sample_target(const double* fractions,int ns,double u) {
    double total=0.,cum=0.;int last=-1;
    for(int s=1;s<ns;s++) {
        double f=fractions[s];
        if(!isfinite(f)||f<0.)return -1;
        if(f>0.){total+=f;last=s;}
    }
    if(!isfinite(total)||total<=0.||!isfinite(u)||u<0.||u>=1.)return -1;
    double choose=u*total;
    for(int s=1;s<ns;s++) {
        if(fractions[s]<=0.)continue;
        cum+=fractions[s];if(choose<cum)return s;
    }
    return last;  // Only an actually present species may absorb rounding residue.
}
__device__ double elastic_collision(Particle& p,double m1,double m2,double theta,double az,
                                     double& rx,double& ry,double& rz,double& rnorm) {
    double ex,ey,ez;
    if(fabs(p.uz)<.9) {double norm=sqrt(p.ux*p.ux+p.uy*p.uy);ex=-p.uy/norm;ey=p.ux/norm;ez=0.;}
    else {double norm=sqrt(p.uy*p.uy+p.uz*p.uz);ex=0.;ey=-p.uz/norm;ez=p.uy/norm;}
    double fx=p.uy*ez-p.uz*ey,fy=p.uz*ex-p.ux*ez,fz=p.ux*ey-p.uy*ex;
    double vx=cos(theta)*p.ux+sin(theta)*(cos(az)*ex+sin(az)*fx);
    double vy=cos(theta)*p.uy+sin(theta)*(cos(az)*ey+sin(az)*fy);
    double vz=cos(theta)*p.uz+sin(theta)*(cos(az)*ez+sin(az)*fz);
    double transfer=p.e*4.*m1*m2/((m1+m2)*(m1+m2))*pow(sin(theta/2),2);
    transfer=fmin(transfer,p.e);
    rx=p.ux-vx;ry=p.uy-vy;rz=p.uz-vz;rnorm=sqrt(rx*rx+ry*ry+rz*rz);
    double nx=m1*p.ux+m2*vx,ny=m1*p.uy+m2*vy,nz=m1*p.uz+m2*vz,nn=sqrt(nx*nx+ny*ny+nz*nz);
    p.e=fmax(0.,p.e-transfer);
    if(nn>1e-20) {p.ux=nx/nn;p.uy=ny/nn;p.uz=nz/nn;}
    return transfer;
}
__device__ int layer_at(double z,const double* bounds,int nl) {
    if(z<0.) return -1;
    for(int l=0;l<nl;l++) if(z<bounds[l+1]) return l;
    return nl;
}
__device__ void tally(double* hist,int channel,double z,double value,double total,int bins) {
    int b=(int)(z/total*bins); b=max(0,min(bins-1,b));
    atomicAdd(hist+channel*bins+b,value);
}
__device__ void tally_energy(double* spectra,int band,int ebound,double e,double emax) {
    if(e<=0.0 || emax<=0.0) return;
    int ei=(int)(e/emax*ebound);
    ei=clampi(ei,0,ebound-1);
    atomicAdd(spectra+(size_t)band*ebound+ei,1.0);
}

// records layout (24):
// 0 status, 1-3 stop xyz, 4 Se_ion, 5 Sp_ion, 6 Se_recoil, 7 Sp_recoil,
// 8 escape, 9 unresolved, 10 transport steps, 11 displacements,
// 12 cumulative displacing transfer (not damage energy),
// 13 sputtered, 14 transmitted recoils, 15 recoil_stops, 16 failed, 17 energy_err, 18 id,
// 19 path_length
#define NREC 24
#define NTRACE 48
#define TPTS 384

extern "C" __global__ void transport(
    int count,int offset,unsigned long long seed,int ns,int nl,int bins,int maxevents,
    double energy,double angle,double cutoff,double impactscale,int cascade,int use_table,
    double lat_max,int use_se_table,
    const double* species,const double* bounds,const double* fractions,const double* densities,
    const double* ls,const double* nodes,const double* weights,
    const double* stab,const double* slog_eps,const double* slog_rho,int ne,int nr,
    const double* se_E,const double* se_G,const double* tau_G,int nse,
    double* records,double* hist,double* tracks,int* trackcounts,
    double* lateral,double* spectra,int latbins,int ebound,double* sputter_elements,double* detail) {
    int id=blockIdx.x*blockDim.x+threadIdx.x; if(id>=count) return;
    unsigned long long rng=init_seed(seed^((unsigned long long)(id+offset)*0xd2b74407b1ce6e93ULL));
    Particle stack[128]; int top=0,events=0,failed=0;
    Particle p={0.,0.,0.,sin(angle),0.,cos(angle),energy,0,1};
    double se_ion=0.,sp_ion=0.,se_rec=0.,sp_rec=0.,escape=0.,unresolved=0.;
    double damage_e=0., path=0.;
    double primary_x=0.,primary_y=0.,primary_z=0.;
    int status=3,displacements=0,sputtered=0,recoil_back=0,recoil_stops=0;
    int traceid=id+offset, nt=0;
    const double PI=3.141592653589793;
    if(ns<2||ns>16||nl<1||nl>8||bins<1||maxevents<1
       ||(use_se_table && (se_E==0||nse<2))) {
        double* r=records+id*NREC;for(int j=0;j<NREC;j++)r[j]=0.;
        r[0]=3.;r[9]=energy;r[16]=1.;r[18]=traceid;return;
    }
    // Precompute tau at cutoff per species-layer if table mode
    double tau_cutoff_static[16*8];
    int nsl=ns*nl;
    if(use_se_table && se_E!=0 && nsl<=128) {
        for(int i=0;i<nsl;i++) {
            const double* EG=tau_G+(size_t)i*nse;
            // binary search cutoff in se_E
            int lo=0,hi=nse-1;
            while(lo<hi){int mid=(lo+hi)/2; if(se_E[mid]<cutoff) lo=mid+1; else hi=mid;}
            double t0=EG[lo];
            if(lo>0 && se_E[lo]>cutoff) {
                double f=(cutoff-se_E[lo-1])/fmax(se_E[lo]-se_E[lo-1],1e-30);
                t0=EG[lo-1]+f*(EG[lo]-EG[lo-1]);
            }
            tau_cutoff_static[i]=t0;
        }
    }
    while(true) {
        int l=layer_at(p.z,bounds,nl);
        if(!isfinite(p.e)||p.e<0.||!isfinite(p.x)||!isfinite(p.y)||!isfinite(p.z)||p.z<0.||p.z>bounds[nl]
           ||!isfinite(p.ux)||!isfinite(p.uy)||!isfinite(p.uz)) {
            unresolved+=p.e; for(int j=0;j<top;j++) unresolved+=stack[j].e;
            failed=1; break;
        }
        if(p.e<=cutoff) {
            if(p.primary) {
                if(traceid<NTRACE && nt<TPTS) {
                    int t=(traceid*TPTS+nt)*3;tracks[t]=p.x;tracks[t+1]=p.y;tracks[t+2]=p.z;nt++;
                }
                sp_ion+=p.e; status=0; primary_x=p.x;primary_y=p.y;primary_z=p.z;
                tally(hist,0,p.z,1.,bounds[nl],bins);
            } else {
                sp_rec+=p.e; recoil_stops++; tally(hist,4,p.z,1.,bounds[nl],bins);
            }
            tally(hist,2,p.z,p.e,bounds[nl],bins);
            tally(detail,p.primary?2:3,p.z,p.e,bounds[nl],bins);
            if(!p.primary) tally(detail,7+p.s-1,p.z,1.,bounds[nl],bins);
            if(top==0) break; p=stack[--top]; continue;
        }
        if(l<0 || l>=nl) {
            failed=1;unresolved+=p.e;
            for(int j=0;j<top;j++)unresolved+=stack[j].e;
            break;
        }
        // A particle that stopped on the last permitted step is already done.
        // Apply the budget only when another transport step is required.
        if(events>=maxevents) {
            unresolved+=p.e;for(int j=0;j<top;j++)unresolved+=stack[j].e;
            failed=1;break;
        }
        events++;
        if(p.primary && traceid<NTRACE && nt<TPTS) {
            int t=(traceid*TPTS+nt)*3; tracks[t]=p.x;tracks[t+1]=p.y;tracks[t+2]=p.z;nt++;
        }
        double coeff=ls[p.s*nl+l];
        if(!isfinite(densities[l])||densities[l]<=0.||!isfinite(coeff)||coeff<0.) {
            unresolved+=p.e;for(int j=0;j<top;j++)unresolved+=stack[j].e;
            failed=1;break;
        }
        double radius=cbrt(3./(4.*PI*densities[l]))*impactscale;
        double flight=-log(uniform(rng))/(PI*radius*radius*densities[l]);
        double edge=p.uz>0. ? (bounds[l+1]-p.z)/p.uz : (p.uz<0. ? (bounds[l]-p.z)/p.uz : 1e100);
        double olde=p.e, ds=0., stop_path=1e100;
        if(use_se_table && se_E!=0) {
            // Optical-depth path integral on Se(E) table for this species-layer
            int base=(p.s*nl+l)*nse;
            const double* EG=se_E;
            double ee=p.e;
            if(!isfinite(EG[0])||!isfinite(EG[nse-1])||ee<EG[0]||ee>EG[nse-1]
               ||cutoff<EG[0]||cutoff>EG[nse-1]) {
                unresolved+=p.e;for(int j=0;j<top;j++)unresolved+=stack[j].e;
                failed=1;break;
            }
            int lo=0,hi=nse-1;
            while(lo<hi){int mid=(lo+hi)/2; if(EG[mid]<ee) lo=mid+1; else hi=mid;}
            int i1=lo; if(i1<1)i1=1; if(i1>nse-1)i1=nse-1; int i0=i1-1;
            double f=(ee-EG[i0])/fmax(EG[i1]-EG[i0],1e-30);
            double tau=tau_G[base+i0]+f*(tau_G[base+i1]-tau_G[base+i0]);
            double tau_c=tau_cutoff_static[p.s*nl+l];
            if(!isfinite(tau)||!isfinite(tau_c)||tau<tau_c
               ||!(tau_G[base+i1]>tau_G[base+i0])) {
                unresolved+=p.e;for(int j=0;j<top;j++)unresolved+=stack[j].e;
                failed=1;break;
            }
            stop_path=fmax(0.,tau-tau_c);
            ds=fmax(0.,fmin(flight,fmin(edge,stop_path)));
            // Invert tau: tau_after = tau - ds
            double ta=fmax(tau_c,tau-ds);
            int lo2=0,hi2=nse-1;
            while(lo2<hi2){int mid=(lo2+hi2)/2; if(tau_G[base+mid]<ta) lo2=mid+1; else hi2=mid;}
            int k1=lo2; if(k1<1)k1=1; if(k1>nse-1)k1=nse-1; int k0=k1-1;
            if(!isfinite(tau_G[base+k0])||!isfinite(tau_G[base+k1])
               ||!(tau_G[base+k1]>tau_G[base+k0])) {
                unresolved+=p.e;for(int j=0;j<top;j++)unresolved+=stack[j].e;
                failed=1;break;
            }
            double g=(ta-tau_G[base+k0])/fmax(tau_G[base+k1]-tau_G[base+k0],1e-30);
            // Exact inverse of the piecewise LINEAR E -> tau mapping above.
            // Mixing geometric and arithmetic interpolation loses energy at ds=0.
            p.e=fmin(olde,EG[k0]+g*(EG[k1]-EG[k0]));
            if(p.e>cutoff && stop_path<=flight && stop_path<=edge) p.e=fmin(p.e,cutoff);
        } else {
            stop_path=coeff>0. ? 2.*(sqrt(p.e)-sqrt(cutoff))/coeff : 1e100;
            ds=fmax(0.,fmin(flight,fmin(edge,stop_path)));
            double root=fmax(0.,sqrt(p.e)-.5*coeff*ds);
            p.e=root*root;
        }
        bool stopped_first=stop_path<=flight && stop_path<=edge;
        if(stopped_first)p.e=fmin(p.e,cutoff);
        double midz=p.z+.5*ds*p.uz;
        double dEe=olde-p.e;
        if(p.primary) se_ion+=dEe; else se_rec+=dEe;
        path+=ds;
        tally(hist,1,midz,dEe,bounds[nl],bins);
        tally(detail,p.primary?0:1,midz,dEe,bounds[nl],bins);
        p.x+=ds*p.ux;p.y+=ds*p.uy;p.z+=ds*p.uz;
        if(stopped_first)continue;
        if(edge<=flight) {
            double boundary=p.uz>0. ? bounds[l+1] : bounds[l];
            p.z=boundary;
            bool outer=(l==0 && p.uz<0.)||(l==nl-1 && p.uz>0.);
            if(outer) {
                double binding=p.primary ? 0. : species[p.s*5+4];
                double normal=p.e*p.uz*p.uz;
                if(normal<=binding) {
                    p.uz=-p.uz;
                    p.z=nextafter(boundary,p.uz>0. ? 1.7976931348623157e308 : -1.7976931348623157e308);
                    continue;
                }
                if(p.primary) sp_ion+=binding; else sp_rec+=binding;
                tally(hist,2,p.z,binding,bounds[nl],bins);
                tally(detail,p.primary?2:3,p.z,binding,bounds[nl],bins);
                p.e-=binding;escape+=p.e;
                if(p.primary) {
                    if(traceid<NTRACE && nt<TPTS) {
                        int t=(traceid*TPTS+nt)*3;tracks[t]=p.x;tracks[t+1]=p.y;tracks[t+2]=p.z;nt++;
                    }
                    status=p.uz<0. ? 1:2;
                    primary_x=p.x;primary_y=p.y;primary_z=p.z;
                    tally_energy(spectra,p.uz<0.?0:1,ebound,p.e,energy);
                } else if(p.uz<0.) {
                    sputtered++;
                    atomicAdd(sputter_elements+p.s,1.0);
                    tally_energy(spectra,2,ebound,p.e,1000.0);
                } else recoil_back++;
                if(top==0) break;p=stack[--top];continue;
            }
            p.z=nextafter(boundary,p.uz>0. ? 1.7976931348623157e308 : -1.7976931348623157e308);continue;
        }
        int target=sample_target(fractions+l*ns,ns,uniform(rng));
        if(target<1) {
            unresolved+=p.e;for(int j=0;j<top;j++)unresolved+=stack[j].e;
            failed=1;break;
        }
        double z1=species[p.s*5],z2=species[target*5],m1=species[p.s*5+1],m2=species[target*5+1];
        double a=.88534*.529177210903/(pow(z1,.23)+pow(z2,.23));
        double k=14.3996454784255*z1*z2;
        double ecm=p.e*m2/(m1+m2);
        double b=radius*sqrt(uniform(rng));
        double theta;
        double reduced_energy=ecm*a/k,reduced_impact=b/a;
        if(use_table && stab!=0
           && reduced_energy>=exp(slog_eps[0]) && reduced_energy<=exp(slog_eps[ne-1])
           && reduced_impact>=exp(slog_rho[0]) && reduced_impact<=exp(slog_rho[nr-1])) {
            theta=theta_table(stab,slog_eps,slog_rho,ne,nr,reduced_energy,reduced_impact);
        } else {
            theta=theta_quadrature(ecm,b,a,k,nodes,weights);
        }
        if(!isfinite(theta)) {
            unresolved+=p.e;for(int j=0;j<top;j++)unresolved+=stack[j].e;
            failed=1;break;
        }
        double az=2.*PI*uniform(rng);
        double rx,ry,rz,rnorm;
        double transfer=elastic_collision(p,m1,m2,theta,az,rx,ry,rz,rnorm);
        tally(hist,5,p.z,transfer,bounds[nl],bins);
        tally(detail,p.primary?4:5,p.z,transfer,bounds[nl],bins);
        if(transfer>=species[target*5+2]) {
            displacements++;
            damage_e+=transfer;
            tally(hist,3,p.z,1.,bounds[nl],bins);
            if(p.primary) tally(detail,6,p.z,1.,bounds[nl],bins);
            tally(detail,7+(ns-1)+target-1,p.z,1.,bounds[nl],bins);
            double binding=species[target*5+3],re=transfer-binding;
            if(cascade && re>cutoff && rnorm>1e-20) {
                if(p.primary) sp_ion+=binding; else sp_rec+=binding;
                tally(hist,2,p.z,binding,bounds[nl],bins);
                tally(detail,p.primary?2:3,p.z,binding,bounds[nl],bins);
                if(top<128) {Particle recoil={p.x,p.y,p.z,rx/rnorm,ry/rnorm,rz/rnorm,re,target,0};stack[top++]=recoil;}
                else {unresolved+=re;failed=1;}
            } else {
                if(p.primary) sp_ion+=transfer; else sp_rec+=transfer;
                tally(hist,2,p.z,transfer,bounds[nl],bins);
                tally(detail,p.primary?2:3,p.z,transfer,bounds[nl],bins);
            }
        } else {
            if(p.primary) sp_ion+=transfer; else sp_rec+=transfer;
            tally(hist,2,p.z,transfer,bounds[nl],bins);
            tally(detail,p.primary?2:3,p.z,transfer,bounds[nl],bins);
        }
    }
    if(traceid<NTRACE) trackcounts[traceid]=nt;
    if(status==0 && latbins>0 && lat_max>0.) {
        double rad=sqrt(primary_x*primary_x+primary_y*primary_y);
        int rb=clampi((int)(rad/lat_max*latbins),0,latbins-1);
        atomicAdd(lateral+rb,1.0);
    }
    double* r=records+id*NREC;
    r[0]=status;r[1]=primary_x;r[2]=primary_y;r[3]=primary_z;
    r[4]=se_ion;r[5]=sp_ion;r[6]=se_rec;r[7]=sp_rec;
    r[8]=escape;r[9]=unresolved;r[10]=events;r[11]=displacements;r[12]=damage_e;
    r[13]=sputtered;r[14]=recoil_back;r[15]=recoil_stops;r[16]=failed;
    r[17]=fabs(energy-se_ion-sp_ion-se_rec-sp_rec-escape-unresolved);
    r[18]=id+offset;r[19]=path;
}
