"""GPU batch runner, energy ledger, immutable results and restart files."""
import json
import math
import os
from pathlib import Path
import threading
import time
import numpy as np
from .project import validate
from .scattering import backend
from .electronic_stopping import lindhard_scharff_coefficient
from .scatter_table import load_cached_or_build, EPS_NODES, RHO_NODES, EPS_MIN, EPS_MAX, RHO_MIN, RHO_MAX

ROOT=Path(__file__).resolve().parents[1]
ENGINE_REVISION=2
AUTOSAVE_PATH=Path(os.environ.get("GSRIM_RESULTS_DIR",str(ROOT/"results/revision-2")))/"autosave.npz"
CHANNELS=["implanted","electronic_ev","lattice_ev","displacements","stopped_recoils","transfer_ev"]
LATBINS=64
EBINS=64
NREC=24
NTRACE=48
TPTS=384
WARNINGS=[
    "Research model — not validated against SRIM or experiment; do not use as a process prescription.",
    "ZBL scattering and selected electronic stopping model; source/fallback details are reported separately.",
    "Displacements count creation events, NOT surviving defects. KP/NRT estimation is disabled pending a validated damage partition.",
    "No crystal channeling, annealing, evolving composition, replacement collisions or chemical sputtering.",
    "Finite impact cutoff and scattering-table resolution require convergence testing.",
    "Recoil transport includes planar surface escape/reflection, not a full SRIM defect/replacement model.",
]


def _stats_from_records(records, n, project, hist, lateral, spectra, lat_max_a, target, sputter_elements, species_symbols):
    den=max(1,n)
    e0=project["ion"]["energy_kev"]*1000.0
    width=target.thickness_a/project["run"]["bins"]
    implanted_mask=records[:,0]==0
    stopped=records[implanted_mask]
    # SRIM-like ranges in angstrom then nm
    if len(stopped):
        rp=float(stopped[:,3].mean())
        dRp=float(stopped[:,3].std())
        lat_proj=float(np.mean(np.sqrt(stopped[:,1]**2+stopped[:,2]**2)))
        dLat=float(np.std(np.sqrt(stopped[:,1]**2+stopped[:,2]**2)))
        radial=np.sqrt(stopped[:,1]**2+stopped[:,2]**2+stopped[:,3]**2)
        rad=float(radial.mean()); dRad=float(radial.std())
    else:
        rp=dRp=lat_proj=dLat=rad=dRad=None
    se_ion=float(records[:,4].sum()/den); sp_ion=float(records[:,5].sum()/den)
    se_rec=float(records[:,6].sum()/den); sp_rec=float(records[:,7].sum()/den)
    damage_e=float(records[:,12].sum()/den)
    creation=float(records[:,11].sum()/den)
    sputter_total=float(records[:,13].sum()/den)
    # Per-species sputter yield (device index 0 is ion; target species start at 1)
    sputter_by_element=[]
    if sputter_elements is not None and len(species_symbols)>0:
        # species_symbols[0] is projectile label; sputter_elements indexed by species id
        for idx,y in enumerate(sputter_elements):
            if idx==0: continue
            if idx-1 < len(species_symbols)-1:
                sym=species_symbols[idx]
            else:
                sym=species_symbols[idx] if idx < len(species_symbols) else f"S{idx}"
            if y>0:
                sputter_by_element.append({"symbol":sym,"atoms_per_ion":float(y/den),
                                           "ev_per_atom": None})
    lat_edges=np.linspace(0,lat_max_a,LATBINS+1)
    lat_centers=0.5*(lat_edges[:-1]+lat_edges[1:])/10.0
    lat_norm=lateral/den
    normalized=hist[0]/den/(width*1e-8)
    peak=float(normalized.max())
    # Energy loss fractions of incident energy (like SRIM % energy loss table)
    def pct(x):
        return 100.0*x/e0 if e0>0 else 0.0
    stats={
        "completed": n,
        "implanted": int(np.sum(records[:,0]==0)),
        "backscattered": int(np.sum(records[:,0]==1)),
        "transmitted": int(np.sum(records[:,0]==2)),
        "unresolved_primaries": int(np.sum(records[:,0]==3)),
        "failed_histories": int(np.sum(records[:,16]>0)),
        "vacancies_per_ion": None,
        "displacements_per_ion": creation,
        "kinchin_pease_vacancies_per_ion": None,
        "damage_energy_ev_per_ion": None,
        "cumulative_displacing_transfer_ev_per_ion": damage_e,
        "sputter_yield_front": sputter_total,
        "sputter_by_element": sputter_by_element,
        "recoil_transmitted_per_ion": float(records[:,14].sum()/den),
        "stopped_recoils_per_ion": float(records[:,15].sum()/den),
        "electronic_ev_per_ion": se_ion+se_rec,
        "ionization_ev_per_ion": se_ion+se_rec,
        "ion_ionization_ev_per_ion": se_ion,
        "recoil_ionization_ev_per_ion": se_rec,
        "phonon_ev_per_ion": sp_ion+sp_rec,
        "ion_phonon_ev_per_ion": sp_ion,
        "recoil_phonon_ev_per_ion": sp_rec,
        "lattice_ev_per_ion": sp_ion+sp_rec,
        "escaped_ev_per_ion": float(records[:,8].sum()/den),
        "unresolved_ev_per_ion": float(records[:,9].sum()/den),
        "mean_path_a": float(records[:,19].mean()) if n else None,
        "max_energy_error_ev": float(records[:,17].max()) if n else 0,
        "peak_per_cm": peak,
        "peak_depth_nm": float((np.argmax(normalized)+.5)*width/10) if peak else None,
        "lateral_rms_nm": float(np.sqrt(np.sum(lat_norm*lat_centers**2)/max(lat_norm.sum(),1e-300))) if lat_norm.sum()>0 else None,
        "mean_range_nm": float(rp/10) if rp is not None else None,
        "range_std_nm": float(dRp/10) if dRp is not None else None,
        "mean_range_a": rp,
        "range_straggle_a": dRp,
        "lateral_proj_a": lat_proj,
        "lateral_straggle_a": dLat,
        "radial_a": rad,
        "radial_straggle_a": dRad,
        "mean_range_se_nm": float(stopped[:,3].std(ddof=1)/math.sqrt(len(stopped))/10) if len(stopped)>1 else None,
        "peak_bin_count": int(hist[0].max()),
        "peak_bin_relative_poisson_se": float(1/math.sqrt(hist[0].max())) if peak else None,
        "energy_loss_percent": {
            "ions": {"ionization": pct(se_ion), "phonons": pct(sp_ion),
                     "nuclear_to_recoils": None},
            "recoils": {"ionization": pct(se_rec), "phonons": pct(sp_rec)},
            "escaped": pct(records[:,8].sum()/den),
            "note": "Exclusive energy ledger: ionization + phonons + escaped + unresolved. Cumulative transfers may exceed E0 and are not damage energy.",
            "damage_energy_percent_of_E0": None,
        },
    }
    return stats


class Simulation:
    def __init__(self, project, checkpoint=None):
        self.project,self.target=validate(project)
        self.lock=threading.RLock()
        self.command=threading.Event()
        self.pause_requested=False
        self.cancel_requested=False
        self.status="ready"
        self.error=""
        self.completed=0
        self.elapsed=0.
        self.prepare_seconds=0.
        self.batch_times=[]
        self.kernel_times=[]
        self.batch_counts=[]
        self.records=[]
        self.hist=np.zeros((6,self.project["run"]["bins"]))
        self.tracks=np.zeros((NTRACE,TPTS,3))
        self.trackcounts=np.zeros(NTRACE,dtype=np.int32)
        self.lateral=np.zeros(LATBINS)
        self.spectra=np.zeros((3,EBINS))
        self.lat_max_a=200.0
        self.sputter_elements=None
        self.species_symbols=["ion"]
        self.use_se_table=0
        self.use_table=1
        self.device_se_E=None
        self.device_se_G=None
        self.device_tau_G=None
        self.nse=1
        self.se_sources=[]
        self.thread=None
        self.engine_revision=ENGINE_REVISION
        if checkpoint is not None:
            self.engine_revision=checkpoint.get("engine_revision",1)
            self.species_symbols=checkpoint.get("species_symbols",[project["ion"]["symbol"]]+list(dict.fromkeys(s["symbol"] for l in project["layers"] for s in l["species"])))
            self.se_sources=checkpoint.get("se_sources",[])
            self.completed=checkpoint["completed"]
            self.records=[checkpoint["records"].copy()]
            self.hist=checkpoint["hist"].copy()
            # Older checkpoints may have 8x512 tracks
            tracks=checkpoint["tracks"]
            if tracks.shape[0]==8 and tracks.shape[1]==512:
                self.tracks=np.zeros((NTRACE,TPTS,3))
                for i in range(min(8,NTRACE)):
                    m=min(512,TPTS,checkpoint["trackcounts"][i])
                    self.tracks[i,:m]=tracks[i,:m]
                self.trackcounts=np.zeros(NTRACE,dtype=np.int32)
                self.trackcounts[:8]=checkpoint["trackcounts"][:8]
            else:
                self.tracks=tracks.copy()
                self.trackcounts=checkpoint["trackcounts"].copy()
            self.elapsed=checkpoint["elapsed"]
            if "lateral" in checkpoint: self.lateral=checkpoint["lateral"].copy()
            if "spectra" in checkpoint: self.spectra=checkpoint["spectra"].copy()
            if "lat_max_a" in checkpoint: self.lat_max_a=float(checkpoint["lat_max_a"])
            if "sputter_elements" in checkpoint: self.sputter_elements=checkpoint["sputter_elements"].copy()

    def prepare(self):
        cp=backend("gpu")
        ion=self.project["ion"]
        unique={}
        for layer in self.target.layers:
            for s in layer.species:
                unique[s.z]=s
        species=[[ion["z"],ion["mass_u"],1,0,0]]
        self.species_symbols=[ion.get("symbol","ion")]
        ids={}
        for z,s in unique.items():
            ids[z]=len(species)
            species.append([z,s.mass_u,s.displacement_ev,s.lattice_ev,s.surface_ev])
            self.species_symbols.append(s.symbol)
        ns,nl=len(species),len(self.target.layers)
        fractions=np.zeros((nl,ns));bounds=[0.];densities=[]
        for l,layer in enumerate(self.target.layers):
            for s,f in zip(layer.species,layer.fractions):
                fractions[l,ids[s.z]]=f
            bounds.append(bounds[-1]+layer.thickness_a)
            densities.append(layer.number_density_a3)
        ls=np.zeros((ns,nl))
        for s,(z,m,*_) in enumerate(species):
            if z<=0: continue
            for l in range(nl):
                acc=0.0
                for t,(zt,*_) in enumerate(species):
                    frac=fractions[l,t]
                    if frac<=0: continue
                    acc+=lindhard_scharff_coefficient(int(z),int(zt),m,densities[l]*frac)
                ls[s,l]=acc
        nodes,weights=np.polynomial.legendre.leggauss(32)
        use_table=int(self.project["physics"].get("scattering","table")=="table")
        stop_model=str(self.project["physics"].get("stopping","iaea")).lower()
        if stop_model in ("blend","bethe"):
            stop_model="biersack-varelas"
        if stop_model not in ("iaea","biersack-varelas","lindhard-scharff","auto"):
            stop_model="iaea"
        # Build Se(E) tables for every species-layer (ion + targets)
        from .se_tables import default_energy_grid, se_for_pair, build_tau, iaea_index
        e_se=default_energy_grid(float(self.project["run"]["cutoff_ev"]),
                                 max(1e6, ion["energy_kev"]*1000*5), 320)
        nse=len(e_se)
        se_grid=np.zeros((ns,nl,nse))
        tau_grid=np.zeros((ns,nl,nse))
        se_sources=[]
        # Map device species index -> (symbol,z,mass)
        sp_meta=[(self.species_symbols[0], int(species[0][0]), float(species[0][1]))]
        for i,sym in enumerate(self.species_symbols[1:], start=1):
            sp_meta.append((sym, int(species[i][0]), float(species[i][1])))
        for l,layer in enumerate(self.target.layers):
            target_sp=[(s.symbol, s.z, s.mass_u, f) for s,f in zip(layer.species, layer.fractions)]
            for s in range(ns):
                sym,z1,m1=sp_meta[s]
                if z1<=0:
                    se_grid[s,l]=0.0
                    tau_grid[s,l]=0.0
                    continue
                se,src=se_for_pair(
                    sym, int(z1), float(m1),
                    target_sp,
                    layer.number_density_a3,
                    layer.density_g_cm3,
                    e_se,
                    model=stop_model,
                )
                se_grid[s,l]=se
                tau_grid[s,l]=build_tau(e_se, se)
                se_sources.append(f"{sym}/L{l+1}:{src}")
        # Always keep LS matrix as kernel fallback when se table off
        tab=load_cached_or_build(eps_nodes=EPS_NODES,rho_nodes=RHO_NODES,
                                  eps_range=(EPS_MIN,EPS_MAX),rho_range=(RHO_MIN,RHO_MAX),quad_order=40)
        self.lat_max_a=float(max(50.0,0.5*self.target.thickness_a))
        self.device_arrays=[cp.asarray(v,dtype=cp.float64) for v in
            (species,bounds,fractions,densities,ls,(nodes+1)/2,weights/2)]
        self.ns,self.nl=ns,nl
        self.use_table=use_table
        self.use_se_table=0 if stop_model=="lindhard-scharff" else 1
        self.se_sources=se_sources
        self.device_se_E=cp.asarray(e_se)
        self.device_se_G=cp.asarray(se_grid)
        self.device_tau_G=cp.asarray(tau_grid)
        self.nse=nse
        self.device_tracks=cp.asarray(self.tracks)
        self.device_trackcounts=cp.asarray(self.trackcounts)
        self.device_lateral=cp.asarray(self.lateral)
        self.device_spectra=cp.asarray(self.spectra)
        if self.sputter_elements is None or len(self.sputter_elements)!=ns:
            self.sputter_elements=np.zeros(ns)
        self.device_sputter_elements=cp.asarray(self.sputter_elements)
        if use_table:
            self.device_stab=cp.asarray(tab["theta"])
            self.device_slog_eps=cp.asarray(tab["log_eps"])
            self.device_slog_rho=cp.asarray(tab["log_rho"])
            self.ne,self.nr=tab["theta"].shape
        else:
            self.device_stab=cp.zeros(1)
            self.device_slog_eps=cp.zeros(2)
            self.device_slog_rho=cp.zeros(2)
            self.ne,self.nr=1,1
        source=(Path(__file__).parent/"kernels/transport.cu").read_text(encoding="utf-8")
        self.kernel=cp.RawKernel(source,"transport",options=("--std=c++11",))
        self.kernel.compile()

    def start(self):
        with self.lock:
            if self.engine_revision != ENGINE_REVISION:
                raise ValueError("Legacy checkpoint is read-only: restart as a new project with the corrected engine")
            if self.project["run"].get("damage","creation") != "creation":
                raise ValueError("KP/NRT estimate is disabled; select displacement creation events")
            if self.thread and self.thread.is_alive():
                raise ValueError("Simulation already running")
            if self.completed>=self.project["run"]["ions"]:
                raise ValueError("Simulation is already complete")
            self.cancel_requested=False;self.pause_requested=False;self.error=""
            self.status="preparing"
            self.thread=threading.Thread(target=self._run,daemon=True)
            self.thread.start()

    def pause(self):
        with self.lock:
            if self.status not in ("running","preparing"):
                raise ValueError("No running simulation to pause")
            self.pause_requested=True

    def cancel(self):
        with self.lock:
            self.cancel_requested=True

    def _run(self):
        started=time.monotonic();base_elapsed=self.elapsed
        try:
            began=time.monotonic()
            self.prepare()
            with self.lock:
                self.prepare_seconds=time.monotonic()-began
                self.batch_times=[];self.kernel_times=[];self.batch_counts=[]
            cp=backend("gpu")
            run=self.project["run"];ion=self.project["ion"]
            with self.lock:self.status="running"
            while self.completed<run["ions"]:
                if self.cancel_requested or self.pause_requested:
                    with self.lock:self.status="cancelled" if self.cancel_requested else "paused"
                    break
                count=min(run["batch_size"],run["ions"]-self.completed)
                record=cp.zeros((count,NREC));hist=cp.zeros_like(cp.asarray(self.hist))
                args=(np.int32(count),np.int32(self.completed),np.uint64(run["seed"]),
                      np.int32(self.ns),np.int32(self.nl),np.int32(run["bins"]),np.int32(run["max_events"]),
                      np.float64(ion["energy_kev"]*1000),np.float64(math.radians(ion["angle_deg"])),
                      np.float64(run["cutoff_ev"]),np.float64(run["impact_scale"]),
                      np.int32(run["mode"]=="cascades"),np.int32(self.use_table),np.float64(self.lat_max_a),
                      np.int32(getattr(self,"use_se_table",0)),
                      *self.device_arrays,
                      self.device_stab,self.device_slog_eps,self.device_slog_rho,
                      np.int32(self.ne),np.int32(self.nr),
                      self.device_se_E,self.device_se_G,self.device_tau_G,np.int32(self.nse),
                      record,hist,self.device_tracks,self.device_trackcounts,
                      self.device_lateral,self.device_spectra,np.int32(LATBINS),np.int32(EBINS),
                      self.device_sputter_elements)
                tick=time.monotonic()
                begin=cp.cuda.Event();finish=cp.cuda.Event()
                begin.record()
                self.kernel(((count+31)//32,),(32,),args)
                finish.record()
                cpu_record=record.get();cpu_hist=hist.get()
                finish.synchronize()
                duration=time.monotonic()-tick
                kernel_seconds=cp.cuda.get_elapsed_time(begin,finish)/1e3
                with self.lock:
                    self.batch_times.append(duration);self.kernel_times.append(kernel_seconds)
                    self.batch_counts.append(count)
                    self.records.append(cpu_record);self.hist+=cpu_hist;self.completed+=count
                    self.tracks=self.device_tracks.get();self.trackcounts=self.device_trackcounts.get()
                    self.lateral=self.device_lateral.get();self.spectra=self.device_spectra.get()
                    self.sputter_elements=self.device_sputter_elements.get()
                    self.elapsed=base_elapsed+time.monotonic()-started
                if not np.all(np.isfinite(cpu_record)):
                    raise RuntimeError("Non-finite state in a history; results are not valid")
                # Event/stack overflow is recorded per history; the run continues and
                # is marked error only after all requested ions finish.
                if np.max(cpu_record[:,17])>max(1e-5,ion["energy_kev"]*1e-5):
                    raise RuntimeError("Energy accounting failed; results are not valid")
                if duration>3 and run["batch_size"]>1:
                    run["batch_size"]=max(1,run["batch_size"]//2)
                if self.completed%(max(1,run["batch_size"])*10)==0:
                    self.save_checkpoint(AUTOSAVE_PATH)
            with self.lock:
                if self.completed==run["ions"] and self.status=="running":
                    records=np.concatenate(self.records) if self.records else np.zeros((0,NREC))
                    nfail=int(np.sum(records[:,16]>0)) if len(records) else 0
                    if nfail:
                        self.status="error"
                        self.error=(f"{nfail}/{self.completed} histories hit event/stack limits. "
                                    f"Distributions include incomplete contributions and are diagnostic only — raise "
                                    f"max_events, lower energy, or use mode=ions before treating as final.")
                    else:
                        self.status="completed"
        except Exception as exc:
            with self.lock:
                self.status="error";self.error=f"{type(exc).__name__}: {exc}"
        finally:
            with self.lock:self.elapsed=base_elapsed+time.monotonic()-started
            try:self.save_checkpoint(AUTOSAVE_PATH)
            except Exception as exc:
                with self.lock:self.error += f"; checkpoint failed: {exc}"

    def snapshot(self):
        with self.lock:
            records=np.concatenate(self.records) if self.records else np.zeros((0,NREC))
            n=self.completed
            stats=_stats_from_records(records,n,self.project,self.hist,self.lateral,self.spectra,
                                      self.lat_max_a,self.target,self.sputter_elements,self.species_symbols)
            diagnostic_only=(self.engine_revision!=ENGINE_REVISION or stats["failed_histories"]>0 or self.status=="error")
            if diagnostic_only:
                for key in ("peak_per_cm","peak_depth_nm","mean_range_nm","range_std_nm","mean_range_se_nm",
                            "displacements_per_ion","vacancies_per_ion","sputter_yield_front"):
                    stats[key]=None
            width=self.target.thickness_a/self.project["run"]["bins"]
            den=max(1,n)
            normalized=self.hist[0]/den/(width*1e-8)
            lat_edges=np.linspace(0,self.lat_max_a,LATBINS+1)
            lat_centers=0.5*(lat_edges[:-1]+lat_edges[1:])/10.0
            energy_centers=(np.arange(EBINS)+0.5)/EBINS*(self.project["ion"]["energy_kev"]*1000)
            sputter_centers=(np.arange(EBINS)+0.5)/EBINS*1000.0
            warnings=WARNINGS.copy()
            if diagnostic_only:warnings.append("DIAGNOSTIC ONLY: legacy or failed histories are included. Dose inference and CSV export are disabled.")
            if self.project["physics"].get("scattering","table")!="table":
                warnings.append("Scattering uses full quadrature (slower, verification mode).")
            if self.project["run"]["mode"]=="ions":
                warnings.append("Ion-only mode deposits recoil energy locally; sputtering and cascades are not computed.")
            if self.project["run"].get("damage","creation")=="kinchin-pease":
                warnings.append("Vacancies/Ion uses Kinchin–Pease from damage energy — an upper-bound estimate, not a defect census.")
            if self.status!="completed":warnings.append("Partial run: not a final result.")
            return {"status":self.status,"error":self.error,"completed":n,"total":self.project["run"]["ions"],
                "elapsed_s":self.elapsed,"project":self.project,"stats":stats,"warnings":warnings,
                "engine_revision":self.engine_revision,"diagnostic_only":diagnostic_only,
                "se_sources":self.se_sources,
                "depth_nm":((np.arange(len(normalized))+.5)*width/10).tolist(),
                "depth_a":((np.arange(len(normalized))+.5)*width).tolist(),
                "profiles":dict(zip(CHANNELS,(self.hist/den).tolist())),
                "implant_per_cm":normalized.tolist(),
                "lateral_nm":lat_centers.tolist(),
                "lateral_per_ion":(self.lateral/den).tolist(),
                "spectra_ev":energy_centers.tolist(),
                "spectra_axes_ev":{"backscattered":energy_centers.tolist(),"transmitted":energy_centers.tolist(),"sputtered":sputter_centers.tolist()},
                "spectra":{
                    "backscattered":(self.spectra[0]/den).tolist(),
                    "transmitted":(self.spectra[1]/den).tolist(),
                    "sputtered":(self.spectra[2]/den).tolist(),
                },
                "tracks":[self.tracks[i,:self.trackcounts[i]].tolist() for i in range(NTRACE) if self.trackcounts[i]>0]}

    def timings(self):
        with self.lock:
            counts=np.asarray(self.batch_counts,dtype=float)
            wall=np.asarray(self.batch_times,dtype=float)
            kernel=np.asarray(self.kernel_times,dtype=float)
            if counts.size==0:return None
            steady=slice(1 if counts.size>2 else 0,None)
            ions=float(counts[steady].sum());wall_sum=float(wall[steady].sum());kernel_sum=float(kernel[steady].sum())
            records=np.concatenate(self.records) if self.records else np.zeros((0,NREC))
            events=float(records[:,10].sum())
            return {"prepare_s":self.prepare_seconds,"batches":int(counts.size),
                "steady_batches":int(counts[steady].size),"ions_measured":int(ions),
                "total_ions":int(counts.sum()),
                "median_batch_wall_s":float(np.median(wall[steady])),
                "median_batch_kernel_s":float(np.median(kernel[steady])),
                "total_kernel_s":float(kernel.sum()),"events":int(events),
                "ions_per_s_wall":ions/wall_sum if wall_sum>0 else None,
                "ions_per_s_kernel":ions/kernel_sum if kernel_sum>0 else None,
                "events_per_s_kernel":events/float(kernel.sum()) if kernel.sum()>0 else None}

    def save_checkpoint(self,path):
        path=Path(path)
        path.parent.mkdir(parents=True,exist_ok=True)
        with self.lock:
            records=np.concatenate(self.records) if self.records else np.zeros((0,NREC))
            se=self.sputter_elements if self.sputter_elements is not None else np.zeros(1)
            data=dict(engine_revision=np.array(self.engine_revision),
                species_symbols=np.array(json.dumps(self.species_symbols)),se_sources=np.array(json.dumps(self.se_sources)),
                project=np.array(json.dumps(self.project)),completed=np.array(self.completed),
                elapsed=np.array(self.elapsed),records=records,hist=self.hist.copy(),
                tracks=self.tracks.copy(),trackcounts=self.trackcounts.copy(),
                lateral=self.lateral.copy(),spectra=self.spectra.copy(),
                lat_max_a=np.array(self.lat_max_a),sputter_elements=se.copy())
        temporary=path.with_suffix(".tmp.npz")
        np.savez_compressed(temporary,**data)
        temporary.replace(path)

    @classmethod
    def load_checkpoint(cls,path):
        with np.load(path,allow_pickle=False) as data:
            project=json.loads(str(data["project"]))
            validate(project)
            state={key:data[key] for key in ("records","hist","tracks","trackcounts")}
            state["engine_revision"]=int(data["engine_revision"]) if "engine_revision" in data else 1
            if state["engine_revision"]>ENGINE_REVISION:raise ValueError("Checkpoint requires a newer engine")
            for key in ("species_symbols","se_sources"):
                if key in data:state[key]=json.loads(str(data[key]))
            for key in ("lateral","spectra","sputter_elements"):
                if key in data: state[key]=data[key]
            if "lat_max_a" in data: state["lat_max_a"]=float(data["lat_max_a"])
            state["completed"]=int(data["completed"]);state["elapsed"]=float(data["elapsed"])
            rec_cols=state["records"].shape[1] if state["records"].ndim==2 else 0
            if (not 0<=state["completed"]<=project["run"]["ions"]
                or state["records"].shape[0]!=state["completed"]
                or rec_cols != NREC
                or state["hist"].shape!=(6,project["run"]["bins"])):
                raise ValueError("Invalid checkpoint dimensions")
            if state["tracks"].shape!=(NTRACE,TPTS,3) or state["trackcounts"].shape!=(NTRACE,):
                raise ValueError("Unsupported trajectory dimensions in checkpoint")
            if np.any(state["trackcounts"]<0) or np.any(state["trackcounts"]>TPTS):raise ValueError("Invalid track lengths")
            for key,shape in (("lateral",(LATBINS,)),("spectra",(3,EBINS))):
                if key in state and state[key].shape!=shape:raise ValueError("Invalid checkpoint profile shape")
            for key in ("records","hist","tracks","lateral","spectra"):
                if key not in state:continue
                if not np.all(np.isfinite(state[key])):raise ValueError("Nonfinite checkpoint")
            return cls(project,state)
