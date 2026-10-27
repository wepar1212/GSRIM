"""Generate audited element setup suggestions from local tables and a paper.

Run with the project interpreter after obtaining the cited PDF and extracting
its text with pdftotext -layout. Runtime never accesses the original SRIM tree.
"""
import ast
import argparse
import csv
import hashlib
import json
from pathlib import Path
import pprint
import re

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ("displacement_ev", "lattice_ev", "surface_ev")


def literal_assignment(file, name):
    for node in ast.parse(file.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            try:
                return ast.literal_eval(node.value)
            except ValueError:
                pass
    return {}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tables',type=Path,required=True,help='Folder containing the original ATOMDATA.csv')
    parser.add_argument('--paper-dir',type=Path,required=True,help='Folder containing Konobeyev-2017.pdf and Konobeyev-2017.txt (pdftotext -layout)')
    parser.add_argument('--report-dir',type=Path,default=ROOT/'results/element-defaults-generation',help='Output folder for the local provenance report')
    args=parser.parse_args()
    source = args.tables / "ATOMDATA.csv"
    review=args.paper_dir
    rows = list(csv.DictReader(source.open(encoding="utf-8-sig", newline="")))
    text = (review / "Konobeyev-2017.txt").read_text(encoding="utf-8")
    page4 = text.split("\f")[3]
    left = "\n".join(line[:78] for line in page4.splitlines())
    table4 = left[left.index("Table 4"):left.index("Table 5")]
    literature = {}
    for z, symbol, value, uncertainty, adopted in re.findall(
        r"(\d+)\s*([A-Z][a-z]?)\s+(\d+)\s*±\s*(\d+)(\s+A)?", table4
    ):
        assert symbol not in literature
        literature[symbol] = {"z": int(z), "value": float(value),
                              "uncertainty_ev": float(uncertainty), "adopted": bool(adopted)}
    assert len(literature) == 81, len(literature)
    assert literature["W"]["value"] == 90
    assert literature["Si"]["value"] == 37
    old_elements = literal_assignment(ROOT / "gsrim/compounds.py", "ELEMENTS")
    previous = literal_assignment(ROOT / "gsrim/element_defaults.py", "ELEMENT_RECORDS") if (ROOT / "gsrim/element_defaults.py").exists() else {}
    sources = {
        "atomdata": {
            "label_zh": "SRIM-RE ATOMDATA 升华热（表面能初始估计）",
            "label_en": "SRIM-RE ATOMDATA heat of sublimation (surface estimate)",
            "file": source.name, "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "note": "Positive heat_subl values are used as editable SBE estimates. Zero is treated as unavailable, not as a zero barrier.",
        },
        "konobeyev2017": {
            "label_zh": "Konobeyev 等，2017，表 4，取向平均位移阈能",
            "label_en": "Konobeyev et al. (2017), Table 4, direction-averaged threshold",
            "url": "https://doi.org/10.1016/j.nucet.2017.08.007",
            "repository": "https://publikationen.bibliothek.kit.edu/1000076502",
            "pdf_sha256": hashlib.sha256((review / "Konobeyev-2017.pdf").read_bytes()).hexdigest(),
            "note": "Use Table 4 Ed, not Table 2 Edmin or Table 6 Edeff. These are elemental-solid evaluations, not recovered SRIM defaults or compound-specific constants.",
        },
        "srim-si": {
            "label_zh": "SRIM 官方损伤教程中的 Si 示例",
            "label_en": "Si example in the official SRIM target-damage tutorial",
            "url": "https://www.srim.org/SRIM/Tutorials/SRIM%20Tutorial%204%20-%20Target%20Damage.pdf",
            "note": "Si Ed=15, El=2, Es=4.7 eV. This published tutorial baseline takes priority over the alternative Table 4 mean Ed=37 eV.",
        },
        "local-sample": {
            "label_zh": "本机已保存 TRIM 样例（依赖材料环境）",
            "label_en": "Locally saved TRIM sample (material dependent)",
            "examples": ["Ga2O3 target input", "O/H target input"],
            "note": "O/Ga values are from Ga2O3 examples; H values from the saved O/H example. These do not establish universal pure-element or TIN defaults.",
        },
        "lattice-assumption": {
            "label_zh": "晶格能模型假设 3 eV（非逐元素实测值）",
            "label_en": "Assumed lattice energy 3 eV (not element-specific measurement)",
            "url": "https://www.srim.org/SRIM/SRIM%2008.pdf",
            "note": "The manual quotes typical El=1-3 eV and notes missing compound data. 3 eV is a disclosed editable model assumption, not an evaluated elemental table.",
        },
        "unknown": {
            "label_zh": "已核对的表与文献未提供；需按材料填写",
            "label_en": "Unavailable in the checked sources; enter a material-specific value",
        },
    }
    records = {}
    for row in rows:
        symbol = row["symbol"]
        prior = old_elements.get(symbol) or previous.get(symbol) or {}
        z = int(row["Z"])
        displacement = literature.get(symbol)
        heat = float(row["heat_subl"])
        records[symbol] = {
            "z": z, "mass_u": float(prior.get("mass_u", row["weight"])),
            "displacement_ev": displacement["value"] if displacement else None,
            "lattice_ev": 3.0,
            "surface_ev": heat if heat > 0 else None,
            "sources": {
                "displacement_ev": "konobeyev2017" if displacement else "unknown",
                "lattice_ev": "lattice-assumption",
                "surface_ev": "atomdata" if heat > 0 else "unknown",
            },
        }
        if displacement:
            assert displacement["z"] == z
            records[symbol]["displacement_uncertainty_ev"] = displacement["uncertainty_ev"]
    # Preserve observed TRIM comparison baselines where available.
    # Their material-dependent origin remains explicit in the source metadata.
    for symbol, values in {"H": (10, 3, 2), "O": (28, 3, 2), "Ga": (25, 3, 2.82)}.items():
        records[symbol].update(dict(zip(FIELDS, map(float, values))))
        records[symbol]["sources"] = dict.fromkeys(FIELDS, "local-sample")
        records[symbol].pop("displacement_uncertainty_ev", None)
    records["Si"].update(dict(zip(FIELDS, (15.0, 2.0, 4.7))))
    records["Si"]["sources"] = dict.fromkeys(FIELDS, "srim-si")
    records["Si"].pop("displacement_uncertainty_ev", None)
    assert len(records) == 92
    header = '"""Audited editable setup suggestions; missing values remain None.\n\nGenerated by build/generate_element_defaults.py. No original SRIM executable\nor stopping coefficient table is needed at runtime. See docs/ELEMENT_DEFAULTS.md.\n"""\nfrom copy import deepcopy\n\n'
    output = header + "BINDING_FIELDS = " + repr(FIELDS) + "\n\n"
    output += "SOURCES = " + pprint.pformat(sources, width=110, sort_dicts=False) + "\n\n"
    output += "ELEMENT_RECORDS = " + pprint.pformat(records, width=110, sort_dicts=False) + "\n\n"
    output += '''
def binding_defaults(symbol):
    """Return an independent copy of the three suggestions (possibly None)."""
    record = ELEMENT_RECORDS.get(symbol, {})
    return {key: record.get(key) for key in BINDING_FIELDS}


def binding_hint(symbol, key, language="zh"):
    """Describe the suggested default, never the provenance of a user override."""
    record = ELEMENT_RECORDS.get(symbol, {})
    value = record.get(key)
    source = SOURCES[record.get("sources", {}).get(key, "unknown")]
    zh = language == "zh"
    if value is None:
        return ("待填写：已核对的来源没有通用数值，请按具体靶材输入。" if zh else
                "Value required: checked sources provide no general value; use the actual target material.")
    label = source["label_zh" if zh else "label_en"]
    lead = "建议默认" if zh else "Suggested default"
    tail = ("仅作初始建议；可手动修改。已有项目的数值保持原样。" if zh else
            "Editable setup suggestion. Values in existing projects are preserved.")
    return f"{lead}: {value:g} eV\\n{label}\\n{tail}"
'''
    (ROOT / "gsrim/element_defaults.py").write_text(output, encoding="utf-8")
    with (ROOT / "docs/element-defaults.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["symbol","Z","displacement_eV","lattice_eV","surface_eV","Ed_source","El_source","Es_source"])
        for symbol, row in records.items():
            writer.writerow([symbol, row["z"], *[row[k] for k in FIELDS], *[row["sources"][k] for k in FIELDS]])
    args.report_dir.mkdir(parents=True,exist_ok=True)
    (args.report_dir / "source-audit.json").write_text(json.dumps({
        "sources": sources, "elements": len(records), "literature_table4_rows": len(literature),
        "missing": {k:[s for s,r in records.items() if r[k] is None] for k in FIELDS},
        "raw_literature_table4": literature,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"elements":len(records),"literature_rows":len(literature),
                      "missing":{k:[s for s,r in records.items() if r[k] is None] for k in FIELDS}},ensure_ascii=False))


if __name__ == "__main__":
    main()
