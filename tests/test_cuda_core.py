"""Bounded checks of actual CUDA helpers and one-history transport fixtures.

No element sweep, material fitting or large Monte Carlo run is performed.
"""
import os
from pathlib import Path
import unittest

import numpy as np
from gsrim.scattering import backend


WRAPPERS=r'''
extern "C" __global__ void check_collision(const double* rows,double* out,int n) {
    int i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=n)return;
    const double* a=rows+i*8;
    Particle p={0.,0.,0.,a[5],a[6],a[7],a[2],0,1};
    double rx,ry,rz,rn;
    double t=elastic_collision(p,a[0],a[1],a[3],a[4],rx,ry,rz,rn);
    double* b=out+i*9;
    b[0]=p.e;b[1]=p.ux;b[2]=p.uy;b[3]=p.uz;b[4]=t;
    b[5]=rx;b[6]=ry;b[7]=rz;b[8]=rn;
}
extern "C" __global__ void check_targets(const double* f,const double* u,int* out,int n) {
    int i=blockIdx.x*blockDim.x+threadIdx.x;if(i<n)out[i]=sample_target(f,4,u[i]);
}
extern "C" __global__ void check_bad_scattering(const double* nodes,const double* bad_weights,
    const double* bad_table,const double* grid,double* out) {
    if(threadIdx.x==0){
        out[0]=theta_quadrature(100.,.2,.1,10.,nodes,bad_weights);
        out[1]=theta_table(bad_table,grid,grid,4,4,1.,1.);
    }
}
'''


@unittest.skipUnless(os.environ.get('GSRIM_TEST_GPU')=='1','GPU checks not requested')
class CudaCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cp=backend('gpu')
        root=Path(__file__).resolve().parents[1]
        source=(root/'gsrim/kernels/transport.cu').read_text(encoding='utf8')
        cls.module=cls.cp.RawModule(code=source+WRAPPERS,options=('--std=c++11',))
        cls.transport=cls.module.get_function('transport')
        nodes,weights=np.polynomial.legendre.leggauss(64)
        cls.nodes=cls.cp.asarray((nodes+1)/2);cls.weights=cls.cp.asarray(weights/2)

    def transport_once(self,*,energy=100.,thickness=1000.,density=.05,coefficient=1e20,
                       table=False,maxevents=1,bad_tau=False,bad_weights=False,ns=2):
        cp=self.cp;bins=20
        values=[[[2.,4.,1.,0.,0.],[14.,28.,25.,3.,4.7]],
                [0.,thickness],[[0.,1.]],[density],[[coefficient],[coefficient]]]
        material=[cp.asarray(x,dtype=cp.float64) for x in values]
        e=cp.asarray([3.,100.,1000.]);se=cp.full((2,1,3),7.)
        primitive=np.tile(np.array([0.,97/7,997/7]),(2,1,1))
        if bad_tau:primitive[0,0,0]=np.nan
        tau=cp.asarray(primitive)
        record=cp.zeros((1,24));hist=cp.zeros((6,bins));tracks=cp.zeros((48,384,3))
        counts=cp.zeros(48,dtype=cp.int32);lateral=cp.zeros(64);spectra=cp.zeros((3,64))
        sputter=cp.zeros(2);detail=cp.zeros((9,bins))
        unused=cp.zeros(1);logs=cp.zeros(2)
        args=(np.int32(1),np.int32(0),np.uint64(12345),np.int32(ns),np.int32(1),
              np.int32(bins),np.int32(maxevents),np.float64(energy),np.float64(0.),
              np.float64(3.),np.float64(1.),np.int32(1),np.int32(0),np.float64(500.),
              np.int32(table),*material,self.nodes,(cp.full(64,np.nan) if bad_weights else self.weights),unused,logs,logs,np.int32(1),np.int32(1),
              e,se,tau,np.int32(3),record,hist,tracks,counts,lateral,spectra,np.int32(64),
              np.int32(64),sputter,detail)
        self.transport((1,),(1,),args)
        return record.get()[0],hist.get(),tracks.get()[0],int(counts.get()[0])

    def test_actual_collision_preserves_energy_and_vector_momentum(self):
        directions=[(0.,0.,1.),(.6,.8,0.),(.3,.4,np.sqrt(.75))]
        rows=np.array([(m1,m2,10000.,theta,.73,*u)
            for m1,m2 in [(1.,1.),(1.,238.),(238.,1.)]
            for theta in [0.,.2,np.pi/2,np.pi] for u in directions])
        out=self.cp.empty((len(rows),9));kernel=self.module.get_function('check_collision')
        kernel((1,),(64,),(self.cp.asarray(rows),out,np.int32(len(rows))))
        out=out.get()
        np.testing.assert_allclose(out[:,0]+out[:,4],rows[:,2],rtol=1e-14)
        self.assertTrue(np.all(out[:,4]>=0) and np.all(out[:,4]<=rows[:,2]))
        expected=rows[:,2]*4*rows[:,0]*rows[:,1]/(rows[:,0]+rows[:,1])**2*np.sin(rows[:,3]/2)**2
        np.testing.assert_allclose(out[:,4],expected,rtol=1e-13,atol=1e-12)
        recoil=np.divide(out[:,5:8],out[:,8:9],out=np.zeros_like(out[:,5:8]),where=out[:,8:9]>0)
        before=np.sqrt(2*rows[:,0]*rows[:,2])[:,None]*rows[:,5:8]
        after=np.sqrt(2*rows[:,0]*out[:,0])[:,None]*out[:,1:4]+np.sqrt(2*rows[:,1]*out[:,4])[:,None]*recoil
        np.testing.assert_allclose(after,before,rtol=1e-11,atol=1e-9)
        np.testing.assert_allclose(np.linalg.norm(out[:,1:4],axis=1),1.,atol=1e-14)

    def test_target_roundoff_cannot_select_absent_species(self):
        cp=self.cp;u=cp.asarray([0.,.5,np.nextafter(1.,0.)]);out=cp.empty(3,dtype=cp.int32)
        f=cp.asarray([0.,.3,.6999999999999997,0.])
        self.module.get_function('check_targets')((1,),(3,),(f,u,out,np.int32(3)))
        np.testing.assert_array_equal(out.get(),[1,2,2])

    def test_invalid_target_fractions_fail_explicitly(self):
        cp=self.cp;u=cp.asarray([.5]);out=cp.empty(1,dtype=cp.int32)
        for values in ([0.,0.,0.,0.],[0.,1.,-.1,0.],[0.,np.nan,1.,0.]):
            self.module.get_function('check_targets')((1,),(1,),
                (cp.asarray(values),u,out,np.int32(1)))
            self.assertEqual(int(out.get()[0]),-1)

    def test_nan_scattering_is_not_clamped_to_a_valid_angle(self):
        cp=self.cp;out=cp.empty(2);weights=cp.full(64,np.nan)
        self.module.get_function('check_bad_scattering')((1,),(1,),
            (self.nodes,weights,cp.full((4,4),np.nan),cp.asarray(np.linspace(np.log(.1),np.log(10),4)),out))
        self.assertTrue(np.isnan(out.get()).all())

    def test_final_permitted_step_can_finish_normally(self):
        r,hist,tracks,n=self.transport_once()
        self.assertEqual(r[0],0);self.assertEqual(r[16],0);self.assertEqual(r[10],1)
        self.assertEqual(r[9],0)
        self.assertAlmostEqual(r[4],97.,places=12);self.assertAlmostEqual(r[5],3.,places=12)
        self.assertLess(r[17],1e-12)
        self.assertAlmostEqual(hist[1].sum(),r[4]);self.assertAlmostEqual(hist[2].sum(),r[5])
        self.assertEqual(n,2);np.testing.assert_array_equal(tracks[n-1],r[1:4])

    def test_true_event_limit_keeps_energy_unresolved(self):
        r,*_=self.transport_once(coefficient=0.,density=1e-30,thickness=1e30)
        self.assertEqual(r[16],1);self.assertEqual(r[0],3)
        self.assertGreater(r[9],0);self.assertLess(r[17],1e-12)

    def test_tabulated_stopping_matches_constant_loss_solution(self):
        r,_,tracks,n=self.transport_once(table=True,density=1e-30,coefficient=0.)
        self.assertEqual(r[0],0);self.assertEqual(r[16],0)
        self.assertAlmostEqual(r[3],97/7,places=12)
        self.assertAlmostEqual(r[4],97.,places=12);self.assertLess(r[17],1e-12)
        np.testing.assert_array_equal(tracks[n-1],r[1:4])

    def test_negligible_flight_does_not_lose_interpolation_energy(self):
        r,_,tracks,n=self.transport_once(energy=47.,thickness=1e-25,table=True,coefficient=0.)
        self.assertEqual(r[0],2);self.assertEqual(r[16],0)
        self.assertLess(abs(r[4]),1e-12);self.assertAlmostEqual(r[8],47.,places=12)
        self.assertEqual(n,2);np.testing.assert_array_equal(tracks[n-1],r[1:4])

    def test_invalid_stopping_data_remains_diagnostic(self):
        for kwargs in ({'coefficient':np.nan},{'table':True,'bad_tau':True},
                       {'coefficient':0.,'bad_weights':True}):
            r,*_=self.transport_once(**kwargs)
            self.assertTrue(np.isfinite(r).all())
            self.assertEqual(r[16],1);self.assertEqual(r[0],3)
            self.assertAlmostEqual(r[9],100.);self.assertEqual(r[4],0.)

    def test_fixed_size_species_buffer_is_guarded(self):
        r,*_=self.transport_once(ns=17)
        self.assertEqual(r[16],1);self.assertEqual(r[9],100.);self.assertEqual(r[0],3)

    def test_scatter_kernel_propagates_invalid_integral(self):
        from gsrim.cuda_scattering import _kernel
        cp=self.cp
        angle=cp.empty(1);transfer=cp.empty(1);root=cp.empty(1)
        _kernel(cp.cuda.runtime.getDevice())((1,),(1,),
            (cp.asarray([1000.]),cp.asarray([.2]),self.nodes,cp.full(64,np.nan),
             angle,transfer,root,np.int32(1),np.int32(64),np.float64(.1),
             np.float64(100.),np.float64(4.),np.float64(28.),np.int32(1)))
        self.assertTrue(np.isnan(angle.get()[0]) and np.isnan(transfer.get()[0]))
