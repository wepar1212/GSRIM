"""Exercise the actual native Run button, language switching, GPU and exports."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import time

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
parser=argparse.ArgumentParser()
parser.add_argument("--output",type=Path,required=True)
parser.add_argument("--reference",type=Path)
parser.add_argument("--ions",type=int,default=256,help="Number of histories for the native workflow check")
parser.add_argument("--project",choices=("default","ga2o3"),default="default")
args=parser.parse_args()
out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
os.environ["GSRIM_RESULTS_DIR"]=str(out/"runs")

from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from gsrim.desktop import MainWindow, reference_project
from gsrim.output import export_bundle, reference_plots
from gsrim.simulation import Simulation
from gsrim.project import DEFAULT
import copy
import numpy as np

app=QApplication([]);app.setStyle("Fusion")
with tempfile.TemporaryDirectory() as folder:
    settings=QSettings(str(Path(folder)/"settings.ini"),QSettings.Format.IniFormat)
    settings.setValue("language","zh")
    w=MainWindow(settings=settings);w.resize(1460,970)
    w.fill_project(reference_project() if args.project=="ga2o3" else copy.deepcopy(DEFAULT))
    w.run_fields["ions"].setText(str(args.ions));w.run_fields["batch_size"].setText(str(min(args.ions,64)))
    w.show();app.processEvents();w.grab().save(str(out/"setup-zh.png"))
    w.language_combo.setCurrentIndex(1);app.processEvents();w.grab().save(str(out/"setup-en.png"))
    w.language_combo.setCurrentIndex(0)
    QTest.mouseClick(w.start_button,Qt.MouseButton.LeftButton)
    if w.simulation is None:raise RuntimeError("Native start button did not create a simulation")
    # Changing locale while preparing/running must preserve the task object.
    original=w.simulation
    w.language_combo.setCurrentIndex(1);w.language_combo.setCurrentIndex(0)
    assert original is w.simulation
    began=time.monotonic()
    while w.busy():
        app.processEvents();time.sleep(.02)
        if time.monotonic()-began>120:
            w.simulation.cancel();raise RuntimeError("Native GPU integration timed out")
    w.poll();app.processEvents()
    state=w.simulation.snapshot()
    if state["status"]!="completed":raise RuntimeError(state.get("error"))
    assert state["completed"]==args.ions
    bundle=export_bundle(state,out,np.concatenate(w.simulation.records))
    w.grab().save(str(out/"results-zh.png"))
    for row,name in [(0,"ion-distribution"),(1,"ionization"),(2,"lattice"),(3,"displacements")]:
        w.plot_list.setCurrentRow(row);app.processEvents();w.chart.image().save(str(out/(name+"-zh.png")))
    w.language_combo.setCurrentIndex(1);w.plot_list.setCurrentRow(1);app.processEvents()
    w.grab().save(str(out/"results-en.png"));w.chart.image().save(str(out/"ionization-en.png"))
    if args.reference:
        w.reference_folder=str(args.reference);w.references=reference_plots(args.reference,"en")
        w.source.setCurrentIndex(1);app.processEvents()
        w.chart.image().save(str(out/"reference-ionization-en.png"))
        assert not w.export_button.isEnabled()
    restored=Simulation.load_checkpoint(w.simulation.autosave_path)
    np.testing.assert_array_equal(restored.detail_hist,w.simulation.detail_hist)
    w.language_combo.setCurrentIndex(0);w.source.setCurrentIndex(0);w.tabs.setCurrentIndex(0)
    w.grab().save(str(out/"setup-zh-final.png"))
    report={"ok":True,"native_run_button":True,"language_switch_while_running":True,
            "completed":state["completed"],"status":state["status"],"stats":state["stats"],
            "bundle":str(bundle),"checkpoint":str(w.simulation.autosave_path),
            "reference_parsed":bool(args.reference)}
    (out/"verification.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    w.close();app.processEvents()
print(json.dumps({"ok":True,"output":str(out),"bundle":str(bundle)}))
