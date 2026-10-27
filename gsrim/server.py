"""Loopback-only graphical application backend. No external service required."""
import argparse
import csv
import io
import json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import secrets
import threading
import webbrowser
from .project import DEFAULT,validate
from .simulation import Simulation,ROOT,CHANNELS,AUTOSAVE_PATH,ENGINE_REVISION


class App:
    def __init__(self):
        self.token=secrets.token_urlsafe(32)
        self.lock=threading.RLock()
        self.simulation=None

    def snapshot(self):
        with self.lock:
            return self.simulation.snapshot() if self.simulation else {"status":"idle","project":DEFAULT}


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass

        def send(self,code,data,kind="application/json; charset=utf-8",filename=None):
            if not isinstance(data,bytes):data=json.dumps(data,ensure_ascii=False,allow_nan=False).encode()
            self.send_response(code)
            self.send_header("Content-Type",kind)
            self.send_header("Content-Length",str(len(data)))
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("Content-Security-Policy","default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
            if filename:self.send_header("Content-Disposition",f'attachment; filename="{filename}"')
            self.end_headers();self.wfile.write(data)

        def allowed_host(self):
            port=self.server.server_port
            return self.headers.get("Host") in (f"127.0.0.1:{port}",f"localhost:{port}")

        def do_GET(self):
            if not self.allowed_host():return self.send(403,{"error":"Host rejected"})
            path=self.path.split("?",1)[0]
            try:
                if path=="/api/info":return self.send(200,{"app":"GSRIM","engine_revision":ENGINE_REVISION,"project_root":str(ROOT),"checkpoint_path":str(AUTOSAVE_PATH)})
                if path=="/api/state":return self.send(200,app.snapshot())
                if path=="/api/default":return self.send(200,DEFAULT)
                if path=="/api/compounds":
                    try:
                        from .compounds import list_elements, COMPOUNDS
                        from .element_defaults import ELEMENT_RECORDS, binding_defaults
                        payload=[]
                        for name,c in COMPOUNDS.items():
                            payload.append({
                                "key": name,
                                "name": name,
                                "density_g_cm3": c["density_g_cm3"],
                                "species": c["species"],
                            })
                        return self.send(200,{"compounds":payload,"elements":list_elements(),
                            "element_defaults":{symbol:binding_defaults(symbol) for symbol in ELEMENT_RECORDS}})
                    except ImportError:
                        return self.send(200,{"compounds":[],"elements":[]})
                if path=="/api/token":return self.send(200,{"token":app.token})
                if path=="/api/result":
                    state=app.snapshot()
                    if state["status"]=="idle":raise ValueError("No results available")
                    return self.send(200,state,filename="gsrim-result.json")
                if path=="/api/csv":
                    state=app.snapshot()
                    if not state.get("completed"):raise ValueError("No completed histories")
                    if state.get("diagnostic_only"):raise ValueError("Legacy/failed results are diagnostic only; export JSON for inspection")
                    output=io.StringIO();writer=csv.writer(output)
                    writer.writerow(["# GSRIM research model; not SRIM-equivalent; status="+state["status"]])
                    writer.writerow(["depth_nm","implant_per_cm"]+[s+"_per_incident_ion_per_bin" for s in CHANNELS])
                    for i,z in enumerate(state["depth_nm"]):
                        writer.writerow([z,state["implant_per_cm"][i]]+[state["profiles"][s][i] for s in CHANNELS])
                    writer.writerow([])
                    writer.writerow(["# lateral radial distribution"])
                    writer.writerow(["radius_nm","stopped_per_ion_per_bin"])
                    for r,v in zip(state.get("lateral_nm") or [], state.get("lateral_per_ion") or []):
                        writer.writerow([r,v])
                    writer.writerow([])
                    writer.writerow(["# escape spectra (counts per ion per energy bin)"])
                    writer.writerow(["ion_energy_ev","backscattered","transmitted","sputter_energy_ev","sputtered_0_1kev"])
                    for i,e in enumerate(state.get("spectra_ev") or []):
                        writer.writerow([e,
                            state["spectra"]["backscattered"][i],
                            state["spectra"]["transmitted"][i],state["spectra_axes_ev"]["sputtered"][i],
                            state["spectra"]["sputtered"][i]])
                    return self.send(200,output.getvalue().encode("utf-8-sig"),"text/csv; charset=utf-8","gsrim-profiles.csv")
                files={"/":("index.html","text/html; charset=utf-8"),"/app.js":("app.js","text/javascript; charset=utf-8"),"/style.css":("style.css","text/css; charset=utf-8")}
                if path in files:
                    name,kind=files[path]
                    return self.send(200,(ROOT/"web"/name).read_bytes(),kind)
                return self.send(404,{"error":"Not found"})
            except Exception as exc:self.send(400,{"error":str(exc)})

        def do_POST(self):
            if not self.allowed_host() or self.headers.get("X-GSRIM-Token")!=app.token:
                return self.send(403,{"error":"Local application token required"})
            origin=self.headers.get("Origin")
            if origin and origin!=f'http://{self.headers.get("Host")}':
                return self.send(403,{"error":"Origin rejected"})
            try:
                size=int(self.headers.get("Content-Length",0))
                if not 0<=size<=1024*1024:raise ValueError("Request too large")
                data=json.loads(self.rfile.read(size) or b"{}")
                with app.lock:
                    sim=app.simulation
                    busy=sim is not None and sim.thread is not None and sim.thread.is_alive()
                    if self.path=="/api/validate":
                        project,_=validate(data);return self.send(200,{"project":project})
                    if self.path=="/api/start":
                        if busy:raise ValueError("Current run is active; pause or cancel before replacing it")
                        sim=Simulation(data);app.simulation=sim;sim.start()
                    elif self.path=="/api/pause":
                        if sim is None:raise ValueError("No active run")
                        sim.pause()
                    elif self.path=="/api/cancel":
                        if sim is None:raise ValueError("No active run")
                        sim.cancel()
                    elif self.path=="/api/resume":
                        if sim is None:raise ValueError("No run to resume")
                        if sim.status=="error":raise ValueError("Failed runs cannot be resumed; correct parameters and start a new run")
                        sim.start()
                    elif self.path=="/api/restore":
                        if busy:raise ValueError("Pause the active run first")
                        path=AUTOSAVE_PATH if AUTOSAVE_PATH.exists() else ROOT/"results/autosave.npz"
                        sim=Simulation.load_checkpoint(path)
                        sim.status="completed" if sim.completed==sim.project["run"]["ions"] else "paused"
                        if sim.records and any((r[:,16]>0).any() for r in sim.records):
                            sim.status="error";sim.error="Checkpoint contains failed histories; start a corrected run"
                        app.simulation=sim
                    else:return self.send(404,{"error":"Not found"})
                return self.send(200,app.snapshot())
            except Exception as exc:self.send(400,{"error":str(exc)})
    return Handler


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--port",type=int,default=8765)
    parser.add_argument("--no-browser",action="store_true")
    args=parser.parse_args()
    app=App();server=ThreadingHTTPServer(("127.0.0.1",args.port),make_handler(app))
    if not args.no_browser:threading.Timer(.5,lambda:webbrowser.open(f"http://127.0.0.1:{args.port}")).start()
    print(f"GSRIM GUI: http://127.0.0.1:{args.port}",flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:
        if app.simulation:
            app.simulation.cancel()
            if app.simulation.thread:app.simulation.thread.join(10)
        server.server_close()


if __name__=="__main__":main()
