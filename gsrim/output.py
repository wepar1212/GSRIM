"""Scientific plot series and TRIM-inspired text output, independent of any UI.

GSRIM outputs identify their actual quantities. Unsupported vacancy and
replacement inventories are reported as unavailable, never fabricated.
"""
from dataclasses import dataclass, field
from datetime import datetime
import csv
import io
import json
from pathlib import Path
import re

import numpy as np


@dataclass
class PlotData:
    title: str
    x: list
    series: list  # (label, values, color, fill)
    ylabel: str
    xlabel: str = "Target depth (Å)"
    notes: list = field(default_factory=list)
    xmax: float | None = None
    boundaries: list = field(default_factory=list)
    statistics: list = field(default_factory=list)  # four (label, formatted value) pairs


PLOT_NAMES = {
    "range": ("离子与反冲分布", "Ion and recoil distributions"),
    "ionization": ("电离能量损失", "Ionization"),
    "phonons": ("晶格能量沉积", "Lattice energy deposition"),
    "displacements": ("位移产生事件", "Displacement creation events"),
    "transfer": ("传给反冲的累计能量", "Cumulative energy transfer"),
    "lateral": ("横向分布", "Lateral distribution"),
    "backscattered": ("背散射离子能谱", "Backscattered ion spectrum"),
    "transmitted": ("透射离子能谱", "Transmitted ion spectrum"),
    "sputtered": ("溅射原子能谱", "Sputtered atom spectrum"),
    "tracks": ("入射离子轨迹", "Incident ion trajectories"),
}
COLORS = ["#ed0000", "#1233d8", "#128746", "#b038b0", "#c27a00", "#008c99"]


def fmt(value, precision=5):
    return "N/A" if value is None else f"{value:.{precision}E}"


def range_statistics(stats, language="zh"):
    """Population central moments; Pearson kurtosis (Gaussian=3), not excess."""
    pairs=[]
    for zh,en,key,length in [("平均射程","Ion Range","mean_range_a",True),
                              ("射程展宽","Straggle","range_straggle_a",True),
                              ("偏度","Skewness","range_skewness",False),
                              ("峰度","Kurtosis","range_kurtosis",False)]:
        value=stats.get(key)
        text="N/A" if value is None or not np.isfinite(value) else (
            f"{value:.4g} Å" if length else f"{value:.4f}")
        pairs.append((zh if language=="zh" else en,text))
    return pairs


def plot_from_snapshot(state, mode="range", language="zh"):
    zh = language == "zh"
    tr = lambda a, b: a if zh else b
    project = state["project"]
    width = sum(l["thickness_a"] for l in project["layers"]) / project["run"]["bins"]
    x = state["depth_a"]
    detail = state.get("detail_profiles", {})
    profiles = state["profiles"]
    stats = state["stats"]
    title = PLOT_NAMES.get(mode, PLOT_NAMES["range"])[0 if zh else 1]
    series, notes, statistics = [], [], []
    ymax_unit = ""
    xlabel = tr("靶材深度 (Å)", "Target depth (Å)")
    xmax = sum(l["thickness_a"] for l in project["layers"])
    boundaries = np.cumsum([l["thickness_a"] for l in project["layers"]]).tolist()[:-1]
    if mode == "range":
        series.append((tr("入射离子", "Ions"), state["implant_per_cm"], COLORS[0], True))
        targets = [k for k in detail if k.startswith("stopped_")]
        for i, key in enumerate(targets):
            series.append((key[8:], (np.asarray(detail[key]) / (width * 1e-8)).tolist(),
                           COLORS[(i+1) % len(COLORS)], False))
        if not targets:
            series.append((tr("停止反冲总计", "Stopped recoils (total)"),
                           (np.asarray(profiles["stopped_recoils"]) / (width*1e-8)).tolist(), COLORS[1], False))
        ymax_unit = "(atoms/cm³) / (ions/cm²)"
        statistics=range_statistics({} if state.get("diagnostic_only") else stats,language)
    elif mode in ("ionization", "phonons", "transfer"):
        suffix = {"ionization": "electronic_ev", "phonons": "lattice_ev", "transfer": "transfer_ev"}[mode]
        if "ion_"+suffix in detail:
            for i, key in enumerate(("ion_"+suffix, "recoil_"+suffix)):
                series.append((tr("入射离子", "Ions") if i == 0 else tr("反冲原子", "Recoils"),
                               (np.asarray(detail[key])/width).tolist(), COLORS[i], i == 0))
        else:
            key = {"ionization":"electronic_ev", "phonons":"lattice_ev", "transfer":"transfer_ev"}[mode]
            series.append((tr("总计（旧断点无分项）", "Total (split unavailable)"),
                           (np.asarray(profiles[key])/width).tolist(), COLORS[0], True))
        ymax_unit = tr("能量 / (Å·入射离子)", "Energy (eV / Å / incident ion)")
        if zh:
            ymax_unit = "能量 (eV / Å / 入射离子)"
        if mode == "transfer":
            notes.append(tr("累计转移可重复计数，不是损伤能", "Cumulative transfers; not damage energy"))
    elif mode == "displacements":
        for i, key in enumerate(k for k in detail if k.startswith("displaced_")):
            series.append((key[10:], (np.asarray(detail[key])/width).tolist(), COLORS[i % len(COLORS)], i == 0))
        if not series:
            series.append((tr("总位移事件", "Total events"),
                           (np.asarray(profiles["displacements"])/width).tolist(), COLORS[0], True))
        ymax_unit = tr("事件 / (Å·入射离子)", "Events / Å / incident ion")
        notes.append(tr("位移产生事件 ≠ 稳定空位", "Creation events are not surviving vacancies"))
    elif mode == "lateral":
        x = (np.asarray(state["lateral_nm"])*10).tolist()
        series = [(tr("停止离子", "Stopped ions"), state["lateral_per_ion"], COLORS[0], True)]
        xlabel = tr("横向半径 (Å)", "Lateral radius (Å)")
        ymax_unit = tr("离子 / 入射离子 / 分箱", "Ions / incident ion / bin")
        xmax = x[-1]+(x[-1]-x[-2])/2 if len(x)>1 else 1
        boundaries = []
        notes.append(tr("超出范围的计数归入末箱", "Overflow counts are included in the last bin"))
    elif mode in ("backscattered", "transmitted", "sputtered"):
        x = state["spectra_axes_ev"][mode]
        series = [(title, state["spectra"][mode], COLORS[0], True)]
        xlabel = tr("能量 (eV)", "Energy (eV)")
        ymax_unit = tr("粒子 / 入射离子 / 分箱", "Particles / incident ion / bin")
        xmax = 1000 if mode == "sputtered" else project["ion"]["energy_kev"]*1000
        boundaries = []
        if mode == "sputtered":
            notes.append(tr("超过 1000 eV 的计数归入末箱", "Counts above 1000 eV are in the last bin"))
    if state.get("diagnostic_only"):
        notes.insert(0, tr("仅诊断：含失败或旧版历史", "DIAGNOSTIC: failed or legacy histories"))
    elif state["status"] != "completed":
        notes.insert(0, tr("部分统计", "Partial result"))
    return PlotData(title, list(x), series, ymax_unit, xlabel, notes, xmax, boundaries,statistics)


def _header(state, title, unit=""):
    p = state["project"]
    ion = p["ion"]
    lines = ["="*78, f"GSRIM | {title}", f"Calculation: {p['name']}",
             "Independent GPU BCA research model; not official SRIM/TRIM output.",
             f"Engine revision: {state.get('engine_revision', 2)}   Status: {state['status']}",
             f"Ion = {ion['symbol']} ({ion['z']})   Mass = {ion['mass_u']:.6g} u",
             f"Energy = {ion['energy_kev']:.6g} keV   Angle from normal = {ion['angle_deg']:.6g} deg",
             f"Total incident histories calculated = {state['completed']}",
             f"Seed = {p['run']['seed']}   Mode = {p['run']['mode']}",
             f"Stopping = {p['physics']['stopping']}   Scattering = {p['physics'].get('scattering','table')}",
             f"Cutoff = {p['run']['cutoff_ev']} eV   Impact scale = {p['run']['impact_scale']}",
             "="*78, "TARGET MATERIAL"]
    for i, layer in enumerate(p["layers"]):
        total = sum(s["amount"] for s in layer["species"])
        lines.append(f"Layer {i+1}: {layer['name']} | Width = {layer['thickness_a']:.6g} Å | Density = {layer['density_g_cm3']:.6g} g/cm3")
        for s in layer["species"]:
            lines.append(f"  {s['symbol']:>3}: {100*s['amount']/total:9.4f} atomic % | Ed={s['displacement_ev']:g} El={s['lattice_ev']:g} Es={s['surface_ev']:g} eV")
    lines += ["="*78, "Stopping sources:"] + ["  "+s for s in state.get("se_sources", [])]
    if unit:
        lines += ["Units: "+unit]
    if state["status"] != "completed":
        lines += ["PARTIAL RESULT: this run is not complete."]
    return lines


def _table(state, title, unit, names, columns, notes=()):
    lines = _header(state, title, unit)+list(notes)+["="*78]
    lines += [" ".join(f"{s:>17}" for s in names), " ".join("-"*17 for _ in names)]
    for row in zip(*columns):
        lines.append(" ".join(f"{float(v):17.7E}" for v in row))
    return "\n".join(lines)+"\n"


def text_outputs(state, records=None):
    """Generate actual measured quantities with explicit units and provenance."""
    if state.get("diagnostic_only") or not state.get("completed"):
        raise ValueError("Only non-diagnostic results with completed histories can be exported")
    p = state["project"]
    width = sum(l["thickness_a"] for l in p["layers"])/p["run"]["bins"]
    d = state.get("detail_profiles", {})
    h = state["profiles"]
    x = state["depth_a"]
    stats = state["stats"]
    lines = _header(state, "Calculation details")
    for label, key in [("Average projected range (Å)", "mean_range_a"), ("Range straggling (Å)", "range_straggle_a"),
                       ("Range skewness (dimensionless)", "range_skewness"),
                       ("Range kurtosis (Pearson, Gaussian=3)", "range_kurtosis"),
                       ("Lateral range (Å)", "lateral_proj_a"), ("Radial endpoint distance (Å)", "radial_a"),
                       ("Displacement creation events / ion", "displacements_per_ion"),
                       ("Front sputter yield (atoms/ion)", "sputter_yield_front"),
                       ("Total backscattered ions", "backscattered"), ("Total transmitted ions", "transmitted"),
                       ("Electronic loss (eV/ion)", "electronic_ev_per_ion"),
                       ("Lattice deposition (eV/ion)", "lattice_ev_per_ion"),
                       ("Escape energy (eV/ion)", "escaped_ev_per_ion"),
                       ("Unresolved energy (eV/ion)", "unresolved_ev_per_ion"),
                       ("Maximum energy ledger error (eV)", "max_energy_error_ev")]:
        lines.append(f"{label:44} = {fmt(stats.get(key))}")
    lines += ["Stable vacancies / ion = N/A (not modeled)", "Replacement collisions = N/A (not modeled)",
              "KP/NRT damage estimates = N/A (disabled)",
              "Displacement creation is not a stable-defect inventory.",
              "Ranges describe stopped incident ions only; input angle is from normal.",
              "Each energy flight is assigned to its midpoint depth bin.",
              "="*78]
    outputs = {"TDATA.txt":"\n".join(lines)+"\n"}
    stopped = [key for key in d if key.startswith("stopped_")]
    rangecols = [x, state["implant_per_cm"]]+[(np.asarray(d[k])/(width*1e-8)).tolist() for k in stopped]
    names = ["DEPTH_A", p["ion"]["symbol"]+"_IONS"]+[k[8:]+"_STOPPED" for k in stopped]
    if not stopped:
        names.append("RECOILS_TOTAL")
        rangecols.append((np.asarray(h["stopped_recoils"])/(width*1e-8)).tolist())
    outputs["RANGE.txt"] = _table(state, "Ion and stopped recoil distributions", "(atoms/cm3)/(ions/cm2)", names, rangecols,
        [f"Ion Average Range = {fmt(stats.get('mean_range_a'),7)} A   Straggling = {fmt(stats.get('range_straggle_a'),7)} A",
         f"Range Skewness = {fmt(stats.get('range_skewness'),7)}",
         f"Range Kurtosis = {fmt(stats.get('range_kurtosis'),7)}",
         "Moments use stopped incident endpoints; Pearson kurtosis, Gaussian=3 (not excess)."])
    for filename, mode, suffix, aggregate in [("IONIZ.txt", "Ionization", "electronic_ev", "electronic_ev"),
                                             ("PHONON.txt", "Lattice deposition", "lattice_ev", "lattice_ev"),
                                             ("E2RECOIL.txt", "Cumulative energy transferred to recoils", "transfer_ev", "transfer_ev")]:
        if "ion_"+suffix in d:
            cols = [x, np.asarray(d["ion_"+suffix])/width, np.asarray(d["recoil_"+suffix])/width]
            heads = ["DEPTH_A", "BY_IONS", "BY_RECOILS"]
        else:
            cols, heads = [x, np.asarray(h[aggregate])/width], ["DEPTH_A", "TOTAL_NO_SPLIT"]
        notes = ["Cumulative transfers are NOT damage energy and may exceed initial energy."] if mode.startswith("Cumulative") else []
        outputs[filename] = _table(state, mode, "eV/(Å incident-ion)", heads, cols, notes)
    displaced = [k for k in d if k.startswith("displaced_")]
    heads, cols = ["DEPTH_A"], [x]
    if "primary_knockons" in d:
        heads.append("PRIMARY_KNOCKONS")
        cols.append(np.asarray(d["primary_knockons"])/width)
    heads += [k[10:]+"_EVENTS" for k in displaced]+["TOTAL_EVENTS"]
    cols += [np.asarray(d[k])/width for k in displaced]+[np.asarray(h["displacements"])/width]
    outputs["DISPLACEMENTS.txt"] = _table(state, "Displacement creation events", "events/(Å incident-ion)", heads, cols,
                                         ["Creation events, not surviving vacancies."])
    for filename, quantity in [("VACANCY.txt", "Stable vacancy inventory"), ("NOVAC.txt", "Replacement collisions")]:
        outputs[filename] = "\n".join(_header(state, quantity)+[
            "STATUS = NOT AVAILABLE", "This quantity is not modeled by the current GSRIM engine.",
            "No numeric data are provided. Do not interpret unavailable data as zero.",
            "See DISPLACEMENTS.txt for measured displacement creation events."])+"\n"
    outputs["LATERAL.txt"] = _table(state, "Lateral radial distribution", "stopped ions/(incident-ion bin)",
                                    ["RADIUS_A", "STOPPED_IONS"], [np.asarray(state["lateral_nm"])*10, state["lateral_per_ion"]],
                                    ["Overflow is included in the last bin."])
    for mode, name in [("backscattered","BACKSCAT.txt"),("transmitted","TRANSMIT.txt"),("sputtered","SPUTTER.txt")]:
        notes = ["Counts above 1000 eV are included in the last bin."] if mode == "sputtered" else []
        outputs[name] = _table(state, mode, "particles/(incident-ion energy-bin)", ["ENERGY_EV", "PARTICLES"],
                               [state["spectra_axes_ev"][mode], state["spectra"][mode]], notes)
    if records is not None:
        r = np.asarray(records)
        outputs["ION_HISTORY.txt"] = _table(state, "Incident histories", "positions Å, energies eV; status 0=stopped 1=back 2=through 3=unresolved",
            ["ID","STATUS","X_A","Y_A","Z_A","ESCAPE_EV","FAILED"],
            [r[:,18],r[:,0],r[:,1],r[:,2],r[:,3],r[:,8],r[:,16]])
    return outputs


def export_bundle(state, parent, records=None, selected=None):
    """Create a new directory; never overwrite previous calculations."""
    outputs = text_outputs(state, records)
    if selected is not None:
        outputs = {k:v for k,v in outputs.items() if k == "TDATA.txt" or k in selected}
    path = Path(parent)/("GSRIM-"+datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    path.mkdir(parents=True, exist_ok=False)
    for name, content in outputs.items():
        (path/name).write_text(content, encoding="utf-8-sig")
    (path/"result.json").write_text(json.dumps(state, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    (path/"project.json").write_text(json.dumps(state["project"], ensure_ascii=False, indent=2), encoding="utf-8")
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(["depth_A", "implant_per_cm"]+list(state["profiles"]))
    writer.writerows(zip(state["depth_a"],state["implant_per_cm"],*state["profiles"].values()))
    (path/"profiles.csv").write_text(stream.getvalue(), encoding="utf-8-sig")
    return path


_NUMERIC = re.compile(r"^[\s+-]*\d[\d.Ee+\-\s]*$")


def read_reference_table(path):
    """Read SRIM numeric tables without interpreting headers as executable input."""
    rows = []
    for line in Path(path).read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if not _NUMERIC.fullmatch(line):
            continue
        try:
            row = [float(v) for v in line.split()]
        except ValueError:
            continue
        if len(row) >= 2 and all(np.isfinite(row)):
            rows.append(row)
    if not rows or len({len(r) for r in rows}) != 1:
        raise ValueError("No consistent numeric table: "+str(path))
    return np.asarray(rows)


def reference_range_statistics(text):
    """Read reported moments, never estimate them from a reference histogram."""
    number=r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?)"
    patterns={
        "mean_range_a":r"(?:Ion\s+Average\s+Range|Average\s+Range|Average projected range\s*\([^)]*\))\s*=\s*"+number,
        "range_straggle_a":r"(?:Straggling|Straggle|Range straggling\s*\([^)]*\))\s*=\s*"+number,
        "range_skewness":r"(?:Range\s+Skew(?:ness|ne-)|Range skewness\s*\([^)]*\))\s*=\s*"+number,
        "range_kurtosis":r"(?:Range\s+Kurtosis|Range kurtosis\s*\([^)]*\))\s*=\s*"+number,
    }
    stats={}
    for key,pattern in patterns.items():
        match=re.search(pattern,text,re.IGNORECASE)
        if match:
            value=float(match.group(1))
            if np.isfinite(value):stats[key]=value
    return stats


def reference_plots(folder, language="zh"):
    """Keep original SRIM semantics separate from GSRIM's creation-event plots."""
    folder = Path(folder)
    zh = language == "zh"
    result = {}
    for mode, file, title, unit in [
        ("range","RANGE.txt",("离子与反冲分布 · 参考数据","ION RANGES · Reference"),"(atoms/cm³)/(ions/cm²)"),
        ("ionization","IONIZ.txt",("电离能量损失 · 参考数据","IONIZATION · Reference"),"eV / Å / ion"),
        ("displacements","VACANCY.txt",("空位产生 · SRIM 参考数据","VACANCY PRODUCTION · SRIM reference"),"vacancies / Å / ion"),
        ("phonons","PHONON.txt",("声子能量 · 参考数据","PHONONS · Reference"),"eV / Å / ion")]:
        path = folder/file
        if not path.is_file():
            continue
        data = read_reference_table(path)
        text=path.read_text(encoding="utf-8-sig",errors="replace")
        column_labels=[]
        for line in text.splitlines():
            match=re.match(r"^\s*DEPTH\s+(.+)$",line)
            if match:
                candidate=match.group(1).split()
                if len(candidate)==data.shape[1]-1:column_labels=candidate
        labels = ["入射离子" if zh else "Ions", "反冲原子" if zh else "Recoils"]
        if mode == "range":
            labels = column_labels or [f"Column {i}" for i in range(1,data.shape[1])]
        if mode == "displacements":
            labels = list(column_labels) or [f"Column {i}" for i in range(1,data.shape[1])]
            labels[0]="初级反冲" if zh else "Primary knock-ons"
        series = [(labels[i] if i < len(labels) else f"Column {i+1}",data[:,i+1].tolist(),COLORS[i % len(COLORS)],i==0)
                  for i in range(data.shape[1]-1)]
        result[mode] = PlotData(title[0 if zh else 1],data[:,0].tolist(),series,unit,
            "靶材深度 (Å)" if zh else "Target depth (Å)",
            ["原始参考文件 / Original reference: "+file],float(data[-1,0]))
        if mode=="range":
            tdata=folder/"TDATA.txt"
            extra=tdata.read_text(encoding="utf-8-sig",errors="replace") if tdata.is_file() else ""
            result[mode].statistics=range_statistics(reference_range_statistics(text+"\n"+extra),language)
    if not result:
        raise ValueError("No supported SRIM tables found")
    return result
