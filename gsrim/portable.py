"""Frozen native application bootstrap and executable-level GPU/UI smoke test."""
import json
import os
from pathlib import Path
import sys
import traceback


def configure_storage():
    base=Path(sys.executable).resolve().parent
    candidate=base/"results"
    try:
        candidate.mkdir(parents=True,exist_ok=True)
        import tempfile
        with tempfile.TemporaryFile(dir=candidate):pass
    except OSError:
        candidate=Path(os.environ.get("LOCALAPPDATA",str(Path.home())))/"GSRIM/results"
        candidate.mkdir(parents=True,exist_ok=True)
    os.environ.setdefault("GSRIM_RESULTS_DIR",str(candidate/"revision-4"))
    os.environ.setdefault("CUPY_CACHE_DIR",str(candidate/"cuda-cache"))
    os.environ.setdefault("GSRIM_TABLE_CACHE_DIR",str(candidate/"tables"))
    return candidate


def self_test(output,ui=False):
    import copy
    import tempfile
    import numpy as np
    from .scattering import backend
    from .project import DEFAULT
    from .simulation import Simulation
    from .output import export_bundle
    cp=backend("gpu")
    props=cp.cuda.runtime.getDeviceProperties(0)
    checks={}
    with tempfile.TemporaryDirectory(prefix="gsrim-native-smoke-") as folder:
        project=copy.deepcopy(DEFAULT);project["run"].update(ions=32,batch_size=32)
        sim=Simulation(project,checkpoint_path=Path(folder)/"autosave.npz")
        sim.start();sim.thread.join(120)
        if sim.thread.is_alive():sim.cancel();raise RuntimeError("GPU smoke test exceeded 120 seconds")
        state=sim.snapshot()
        if state["status"]!="completed" or state["completed"]!=32 or state.get("diagnostic_only"):
            raise RuntimeError(str(state.get("error") or state.get("warnings")))
        restored=Simulation.load_checkpoint(Path(folder)/"autosave.npz")
        if restored.completed!=32:raise RuntimeError("Checkpoint restoration failed")
        checks["checkpoint"]=True
        bundle=export_bundle(state,folder,np.concatenate(sim.records))
        checks["text_outputs"]=len(list(bundle.glob("*.txt")))
        from .output import plot_from_snapshot
        chart=plot_from_snapshot(state,"range","en")
        if len(chart.statistics)!=4:raise RuntimeError("Range chart is missing its four moments")
        checks["range_chart_statistics"]=chart.statistics
        if ui:
            from PySide6.QtCore import QSettings
            from PySide6.QtWidgets import QApplication
            from .desktop import MainWindow
            app=QApplication.instance() or QApplication([])
            app.setStyle("Fusion")
            settings=QSettings(str(Path(folder)/"settings.ini"),QSettings.Format.IniFormat)
            window=MainWindow(settings=settings)
            window.show();app.processEvents()
            window.simulation=sim;window.state=state;window.poll()
            window.tabs.setCurrentIndex(1);app.processEvents()
            for language in ("en","zh"):
                window.language_combo.setCurrentIndex(1 if language=="en" else 0)
                app.processEvents()
                checks["native_"+language]=window.start_button.text()
            screenshot=output.with_suffix(".png")
            if not window.grab().save(str(screenshot)):raise RuntimeError("Native screenshot failed")
            window.close();app.processEvents()
            checks["native_screenshot"]=str(screenshot)
    report={"ok":True,"frozen":bool(getattr(sys,"frozen",False)),"native_gui":True,
            "gpu":props["name"].decode(),"completed":state["completed"],"status":state["status"],
            "stats":state["stats"],"stopping_sources":state.get("se_sources"),"checks":checks,
            "cupy_path":cp.__file__,"cuda_path":os.environ.get("CUDA_PATH")}
    output.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")


def main():
    storage=configure_storage();output=None
    try:
        if "--self-test" in sys.argv or "--ui-self-test" in sys.argv:
            ui="--ui-self-test" in sys.argv
            index=sys.argv.index("--ui-self-test" if ui else "--self-test")
            output=Path(sys.argv[index+1]).resolve();output.parent.mkdir(parents=True,exist_ok=True)
            self_test(output,ui=ui);return 0
        from .desktop import main as launch
        return launch() or 0
    except Exception:
        detail=traceback.format_exc();log=storage/"startup-error.txt"
        log.write_text(detail,encoding="utf-8")
        if output:output.write_text(json.dumps({"ok":False,"error":detail},indent=2),encoding="utf-8")
        elif os.name=="nt":
            import ctypes
            ctypes.windll.user32.MessageBoxW(None,f"GSRIM 启动失败 / Startup failed\n{log}\n\n{detail[-1500:]}","GSRIM",0x10)
        return 1
