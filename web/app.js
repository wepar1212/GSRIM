'use strict';
/* GSRIM TRIM/SRIM-style GUI — vanilla JS, CSP-safe (external script only). */

const $ = id => document.getElementById(id);

/* ---------- element table (Z, mass u, name CN/EN) ---------- */
const ELEMENTS = {
  H:[1,1.008,"Hydrogen 氢"],He:[2,4.0026,"Helium 氦"],Li:[3,6.94,"Lithium 锂"],Be:[4,9.0122,"Beryllium 铍"],
  B:[5,10.81,"Boron 硼"],C:[6,12.011,"Carbon 碳"],N:[7,14.007,"Nitrogen 氮"],O:[8,15.999,"Oxygen 氧"],
  F:[9,18.998,"Fluorine 氟"],Ne:[10,20.180,"Neon 氖"],Na:[11,22.990,"Sodium 钠"],Mg:[12,24.305,"Magnesium 镁"],
  Al:[13,26.982,"Aluminum 铝"],Si:[14,28.085,"Silicon 硅"],P:[15,30.974,"Phosphorus 磷"],S:[16,32.06,"Sulfur 硫"],
  Cl:[17,35.45,"Chlorine 氯"],Ar:[18,39.95,"Argon 氩"],K:[19,39.098,"Potassium 钾"],Ca:[20,40.078,"Calcium 钙"],
  Sc:[21,44.956,"Scandium 钪"],Ti:[22,47.867,"Titanium 钛"],V:[23,50.942,"Vanadium 钒"],Cr:[24,51.996,"Chromium 铬"],
  Mn:[25,54.938,"Manganese 锰"],Fe:[26,55.845,"Iron 铁"],Co:[27,58.933,"Cobalt 钴"],Ni:[28,58.693,"Nickel 镍"],
  Cu:[29,63.546,"Copper 铜"],Zn:[30,65.38,"Zinc 锌"],Ga:[31,69.723,"Gallium 镓"],Ge:[32,72.630,"Germanium 锗"],
  As:[33,74.922,"Arsenic 砷"],Se:[34,78.971,"Selenium 硒"],Br:[35,79.904,"Bromine 溴"],Kr:[36,83.798,"Krypton 氪"],
  Rb:[37,85.468,"Rubidium 铷"],Sr:[38,87.62,"Strontium 锶"],Y:[39,88.906,"Yttrium 钇"],Zr:[40,91.224,"Zirconium 锆"],
  Nb:[41,92.906,"Niobium 铌"],Mo:[42,95.95,"Molybdenum 钼"],Tc:[43,98,"Technetium 锝"],Ru:[44,101.07,"Ruthenium 钌"],
  Rh:[45,102.91,"Rhodium 铑"],Pd:[46,106.42,"Palladium 钯"],Ag:[47,107.87,"Silver 银"],Cd:[48,112.41,"Cadmium 镉"],
  In:[49,114.82,"Indium 铟"],Sn:[50,118.71,"Tin 锡"],Sb:[51,121.76,"Antimony 锑"],Te:[52,127.60,"Tellurium 碲"],
  I:[53,126.90,"Iodine 碘"],Xe:[54,131.29,"Xenon 氙"],Cs:[55,132.91,"Cesium 铯"],Ba:[56,137.33,"Barium 钡"],
  La:[57,138.91,"Lanthanum 镧"],Ce:[58,140.12,"Cerium 铈"],Pr:[59,140.91,"Praseodymium 镨"],Nd:[60,144.24,"Neodymium 钕"],
  Pm:[61,145,"Promethium 钷"],Sm:[62,150.36,"Samarium 钐"],Eu:[63,151.96,"Europium 铕"],Gd:[64,157.25,"Gadolinium 钆"],
  Tb:[65,158.93,"Terbium 铽"],Dy:[66,162.50,"Dysprosium 镝"],Ho:[67,164.93,"Holmium 钬"],Er:[68,167.26,"Erbium 铒"],
  Tm:[69,168.93,"Thulium 铥"],Yb:[70,173.05,"Ytterbium 镱"],Lu:[71,174.97,"Lutetium 镥"],Hf:[72,178.49,"Hafnium 铪"],
  Ta:[73,180.95,"Tantalum 钽"],W:[74,183.84,"Tungsten 钨"],Re:[75,186.21,"Rhenium 铼"],Os:[76,190.23,"Osmium 锇"],
  Ir:[77,192.22,"Iridium 铱"],Pt:[78,195.08,"Platinum 铂"],Au:[79,196.97,"Gold 金"],Hg:[80,200.59,"Mercury 汞"],
  Tl:[81,204.38,"Thallium 铊"],Pb:[82,207.2,"Lead 铅"],Bi:[83,208.98,"Bismuth 铋"],Po:[84,209,"Polonium 钋"],
  At:[85,210,"Astatine 砹"],Rn:[86,222,"Radon 氡"],Fr:[87,223,"Francium 钫"],Ra:[88,226,"Radium 镭"],
  Ac:[89,227,"Actinium 锕"],Th:[90,232.04,"Thorium 钍"],Pa:[91,231.04,"Protactinium 镤"],U:[92,238.03,"Uranium 铀"],
  Np:[93,237,"Neptunium 镎"],Pu:[94,244,"Plutonium 钚"],Am:[95,243,"Americium 镅"],Cm:[96,247,"Curium 锔"],
  Bk:[97,247,"Berkelium 锫"],Cf:[98,251,"Californium 锎"],Es:[99,252,"Einsteinium 锿"],Fm:[100,257,"Fermium 镄"],
  Md:[101,258,"Mendelevium 钔"],No:[102,259,"Nobelium 锘"],Lr:[103,266,"Lawrencium 铹"],Rf:[104,267,"Rutherfordium 𬬻"],
  Db:[105,268,"Dubnium 𬭊"],Sg:[106,269,"Seaborgium 𬭳"],Bh:[107,270,"Bohrium 𬭛"],Hs:[108,269,"Hassium 𬭶"],
  Mt:[109,278,"Meitnerium 鿏"],Ds:[110,281,"Darmstadtium 𫟼"],Rg:[111,282,"Roentgenium 𬬭"],Cn:[112,285,"Copernicium 鿔"],
  Nh:[113,286,"Nihonium 鿭"],Fl:[114,289,"Flerovium 𫓧"],Mc:[115,290,"Moscovium 镆"],Lv:[116,293,"Livermorium 𫟐"],
  Ts:[117,294,"Tennessine 鿬"],Og:[118,294,"Oganesson 鿫"]
};

/* typical displacement / lattice / surface binding defaults */
const BIND_DEFAULTS = {
  H:[10,2,1],He:[10,2,1],Li:[25,3,1.7],Be:[25,3,3.4],B:[28,3,5.8],C:[28,3,7.4],N:[28,3,2],O:[28,3,2],
  F:[17,3,1.8],Ne:[15,3,1.2],Na:[25,2.5,1.1],Mg:[25,3,1.5],Al:[25,3,3.4],Si:[25,3,4.7],P:[25,3,2],
  S:[25,3,2.9],Cl:[25,3,2],Ar:[15,3,0.8],K:[25,2.5,0.9],Ca:[25,3,1.8],Sc:[25,3,3.3],Ti:[25,3,4.9],
  V:[25,3,5.3],Cr:[25,3,4.1],Mn:[25,3,2.9],Fe:[25,3,4.3],Co:[25,3,4.4],Ni:[25,3,4.4],Cu:[25,3,3.5],
  Zn:[25,3,1.4],Ga:[25,3,2.8],Ge:[25,3,3.9],As:[25,3,2.8],Se:[25,3,2.1],Br:[25,3,1.2],Kr:[15,3,0.6],
  Rb:[25,2.5,0.8],Sr:[25,3,1.7],Y:[25,3,4.3],Zr:[25,3,6.3],Nb:[25,3,7.6],Mo:[25,3,6.8],Tc:[25,3,7],
  Ru:[25,3,6.7],Rh:[25,3,5.8],Pd:[25,3,3.9],Ag:[25,3,2.9],Cd:[25,3,1.2],In:[25,3,2.5],Sn:[25,3,3.1],
  Sb:[25,3,2.8],Te:[25,3,2.2],I:[25,3,1.2],Xe:[15,3,0.6],Cs:[25,2.5,0.8],Ba:[25,3,1.9],La:[25,3,4.4],
  Ce:[25,3,4.3],Pr:[25,3,3.6],Nd:[25,3,3.4],Pm:[25,3,3.3],Sm:[25,3,2.1],Eu:[25,3,1.5],Gd:[25,3,4.1],
  Tb:[25,3,4.1],Dy:[25,3,3.1],Ho:[25,3,3.1],Er:[25,3,3.1],Tm:[25,3,2.4],Yb:[25,3,1.6],Lu:[25,3,4.4],
  Hf:[25,3,6.4],Ta:[25,3,8.1],W:[25,3,8.9],Re:[25,3,8.1],Os:[25,3,8.2],Ir:[25,3,6.9],Pt:[25,3,5.8],
  Au:[25,3,3.8],Hg:[25,3,0.7],Tl:[25,3,1.9],Pb:[25,3,2],Bi:[25,3,2.2],Th:[25,3,6.2],U:[25,3,5.4]
};

function lookupElement(sym) {
  if (!sym) return null;
  const key = String(sym).trim();
  const hit = ELEMENTS[key] || ELEMENTS[key[0].toUpperCase() + key.slice(1).toLowerCase()];
  if (!hit) return null;
  const proper = Object.keys(ELEMENTS).find(k => k.toLowerCase() === key.toLowerCase()) || key;
  return { symbol: proper, z: hit[0], mass_u: hit[1], name: hit[2] };
}

function bindDefaults(sym) {
  const el = lookupElement(sym);
  if (!el) return { displacement_ev: 25, lattice_ev: 3, surface_ev: 2 };
  const b = BIND_DEFAULTS[el.symbol] || [25, 3, 2];
  return { displacement_ev: b[0], lattice_ev: b[1], surface_ev: b[2] };
}

function makeSpecies(sym, amount) {
  const el = lookupElement(sym) || { symbol: sym || "X", z: 1, mass_u: 1 };
  const b = bindDefaults(el.symbol);
  return {
    symbol: el.symbol, z: el.z, mass_u: el.mass_u, amount: amount == null ? 1 : amount,
    displacement_ev: b.displacement_ev, lattice_ev: b.lattice_ev, surface_ev: b.surface_ev
  };
}

/* ---------- compound dictionary (fallback; optional /api/compounds) ---------- */
const COMPOUNDS = [
  { key: "Si", name: "Silicon 硅", density: 2.329, species: [["Si", 1]] },
  { key: "SiO2", name: "SiO₂ 石英", density: 2.20, species: [["Si", 1], ["O", 2]] },
  { key: "Si3N4", name: "Si₃N₄ 氮化硅", density: 3.17, species: [["Si", 3], ["N", 4]] },
  { key: "GaAs", name: "GaAs 砷化镓", density: 5.32, species: [["Ga", 1], ["As", 1]] },
  { key: "Al2O3", name: "Al₂O₃ 氧化铝", density: 3.95, species: [["Al", 2], ["O", 3]] },
  { key: "W", name: "Tungsten 钨", density: 19.25, species: [["W", 1]] },
  { key: "GaN", name: "GaN 氮化镓", density: 6.15, species: [["Ga", 1], ["N", 1]] },
  { key: "SiC", name: "SiC 碳化硅", density: 3.21, species: [["Si", 1], ["C", 1]] },
  { key: "Au", name: "Gold 金", density: 19.32, species: [["Au", 1]] },
  { key: "Cu", name: "Copper 铜", density: 8.96, species: [["Cu", 1]] },
  { key: "Al", name: "Aluminum 铝", density: 2.70, species: [["Al", 1]] },
  { key: "photoresist", name: "Photoresist CH 光刻胶", density: 1.20, species: [["C", 1], ["H", 1]] },
  { key: "polyethylene", name: "Polyethylene CH₂ 聚乙烯", density: 0.95, species: [["C", 1], ["H", 2]] }
];

const PLOT_MODES = [
  { id: "implant", label: "ION RANGE", cn: "注入分布" },
  { id: "lateral", label: "Lateral Range", cn: "横向射程" },
  { id: "ionization", label: "Ionization", cn: "电离沉积" },
  { id: "phonons", label: "Phonons", cn: "声子/晶格" },
  { id: "damage", label: "Damage Events", cn: "位移事件" },
  { id: "transfer", label: "Energy to Recoils", cn: "反冲能量" },
  { id: "backscattered", label: "Backscattered", cn: "背散射能谱" },
  { id: "transmitted", label: "Transmitted", cn: "透射能谱" },
  { id: "sputtered", label: "Sputtered", cn: "溅射能谱" },
  { id: "xy_long", label: "XY Longitudinal", cn: "轨迹散点" },
  { id: "xy_tracks", label: "XY Tracks", cn: "轨迹叠加" }
];

const STATUS_CN = {
  idle: "等待计算", ready: "准备就绪", preparing: "编译 / 准备 GPU",
  running: "GPU 计算中", paused: "已暂停 · 断点已保留",
  cancelled: "已停止 · 可续跑", completed: "计算完成 · 研究结果",
  error: "运行异常 · 部分结果不可作结论"
};

/* ---------- state ---------- */
let project = null;
let state = null;
let token = "";
let plotMode = "implant";
let selectedLayer = 0;
let polling = false;
let dirty = false;
let compoundsSource = COMPOUNDS;

/* ---------- utils ---------- */
function setView(name) {
  const setup = $("view-setup");
  const results = $("view-results");
  if (!setup || !results) return;
  const showSetup = name !== "results";
  setup.classList.toggle("hidden", !showSetup);
  results.classList.toggle("hidden", showSetup);
  document.body.dataset.view = showSetup ? "setup" : "results";
  $("tab-setup").classList.toggle("active", showSetup);
  $("tab-results").classList.toggle("active", !showSetup);
}

function message(text) {
  const el = $("message");
  el.textContent = text || "";
}

function fmt(v, digits = 3) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  if (Math.abs(n) >= 1e5 || (Math.abs(n) < 1e-3 && n !== 0)) return n.toExponential(digits);
  return n.toLocaleString("en-US", { maximumSignificantDigits: digits + 1 });
}

function pct(v) {
  if (v === null || v === undefined) return "—";
  return fmt(v, 2) + " %";
}

function ang(v) {
  return v == null || !Number.isFinite(Number(v)) ? "—" : fmt(v, 4);
}

function nm(v) {
  if (v == null || !Number.isFinite(Number(v))) return "—";
  return fmt(Number(v) / 10, 4);
}

async function api(path, data) {
  const opts = data === undefined
    ? {}
    : {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-GSRIM-Token": token },
        body: JSON.stringify(data)
      };
  const response = await fetch("/api/" + path, opts);
  const result = await response.json();
  if (!response.ok) throw Error(result.error || response.statusText);
  return result;
}

function saveFile(name, data, type) {
  const url = URL.createObjectURL(new Blob([data], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/* ---------- ion chip ---------- */
function updateIonChip() {
  const sym = $("ion-symbol").value.trim();
  const el = lookupElement(sym);
  const z = Number($("ion-z").value);
  const mass = Number($("ion-mass").value);
  $("chip-sym").textContent = el ? el.symbol : (sym || "?");
  $("chip-z").textContent = el ? el.z : (Number.isFinite(z) ? z : "?");
  $("chip-name").textContent = el ? el.name : "未知元素";
  $("chip-mass").textContent = el ? el.mass_u : (Number.isFinite(mass) ? mass : "—");
  if (el) {
    $("chip-sym").style.color = "var(--accent)";
  } else {
    $("chip-sym").style.color = "var(--amber)";
  }
}

function applyElementToIon(sym) {
  const el = lookupElement(sym);
  if (!el) return;
  $("ion-symbol").value = el.symbol;
  $("ion-z").value = el.z;
  $("ion-mass").value = el.mass_u;
  updateIonChip();
  dirty = true;
}

/* ---------- layers / species render ---------- */
function renderLayers() {
  const body = $("layers-body");
  body.replaceChildren();
  if (!project) return;
  if (selectedLayer >= project.layers.length) selectedLayer = Math.max(0, project.layers.length - 1);

  project.layers.forEach((layer, index) => {
    const tr = document.createElement("tr");
    tr.className = "layer-row" + (index === selectedLayer ? " selected" : "");
    tr.dataset.index = String(index);

    const tdSel = document.createElement("td");
    const radio = document.createElement("input");
    radio.type = "radio";
    radio.name = "layer-sel";
    radio.checked = index === selectedLayer;
    radio.addEventListener("change", () => {
      selectedLayer = index;
      renderLayers();
      renderSpecies();
    });
    tdSel.append(radio);

    const tdName = document.createElement("td");
    const inpName = document.createElement("input");
    inpName.type = "text";
    inpName.value = layer.name;
    inpName.addEventListener("change", () => {
      layer.name = inpName.value;
      dirty = true;
      renderSpecies();
      renderTargetSummary();
    });
    tdName.append(inpName);

    const tdW = document.createElement("td");
    const inpW = document.createElement("input");
    inpW.type = "number";
    inpW.step = "any";
    inpW.value = layer.thickness_a;
    inpW.addEventListener("change", () => {
      layer.thickness_a = Number(inpW.value);
      dirty = true;
      renderTargetSummary();
    });
    tdW.append(inpW);

    const tdD = document.createElement("td");
    const inpD = document.createElement("input");
    inpD.type = "number";
    inpD.step = "any";
    inpD.value = layer.density_g_cm3;
    inpD.addEventListener("change", () => {
      layer.density_g_cm3 = Number(inpD.value);
      dirty = true;
      renderTargetSummary();
    });
    tdD.append(inpD);

    const tdDel = document.createElement("td");
    const del = document.createElement("button");
    del.type = "button";
    del.className = "mini danger";
    del.textContent = "×";
    del.title = "删除层";
    del.disabled = project.layers.length <= 1;
    del.addEventListener("click", e => {
      e.stopPropagation();
      project.layers.splice(index, 1);
      selectedLayer = Math.min(selectedLayer, project.layers.length - 1);
      dirty = true;
      renderLayers();
      renderSpecies();
      renderTargetSummary();
    });
    tdDel.append(del);

    tr.append(tdSel, tdName, tdW, tdD, tdDel);
    tr.addEventListener("click", e => {
      if (e.target.tagName === "INPUT" || e.target.tagName === "BUTTON") return;
      selectedLayer = index;
      renderLayers();
      renderSpecies();
    });
    body.append(tr);
  });

  $("add-layer").disabled = project.layers.length >= 8;
  const layer = project.layers[selectedLayer];
  $("selected-layer-label").textContent = layer
    ? `Layer ${selectedLayer + 1} · ${layer.name || "未命名"}`
    : "—";
}

function renderSpecies() {
  const body = $("species-body");
  body.replaceChildren();
  if (!project || !project.layers[selectedLayer]) return;
  const layer = project.layers[selectedLayer];
  $("selected-layer-label").textContent =
    `Layer ${selectedLayer + 1} · ${layer.name || "未命名"}`;

  layer.species.forEach((s, si) => {
    const tr = document.createElement("tr");

    const mkNum = (val, key) => {
      const td = document.createElement("td");
      const inp = document.createElement("input");
      inp.type = "number";
      inp.step = "any";
      inp.value = val == null ? "" : val;
      inp.addEventListener("change", () => {
        s[key] = Number(inp.value);
        dirty = true;
        renderTargetSummary();
      });
      td.append(inp);
      return td;
    };

    // Symbol is a real element picker (TRIM-like), not free text.
    const tdSym = document.createElement("td");
    const sel = document.createElement("select");
    sel.className = "symbol-select";
    Object.keys(ELEMENTS).forEach(sym => {
      const o = document.createElement("option");
      o.value = sym;
      o.textContent = `${sym} (${ELEMENTS[sym][0]})`;
      if (sym === s.symbol) o.selected = true;
      sel.append(o);
    });
    if (!ELEMENTS[s.symbol]) {
      const o = document.createElement("option");
      o.value = s.symbol || "";
      o.textContent = s.symbol || "—";
      o.selected = true;
      sel.append(o);
    }
    sel.addEventListener("change", () => {
      const el = lookupElement(sel.value);
      if (!el) return;
      const b = bindDefaults(el.symbol);
      s.symbol = el.symbol;
      s.z = el.z;
      s.mass_u = el.mass_u;
      // Keep user-edited binding if already customized away from old element defaults;
      // when switching element, refresh binding to that element's typical values.
      s.displacement_ev = b.displacement_ev;
      s.lattice_ev = b.lattice_ev;
      s.surface_ev = b.surface_ev;
      dirty = true;
      renderSpecies();
      renderTargetSummary();
    });
    tdSym.append(sel);

    const nameEl = lookupElement(s.symbol);
    const tdName = document.createElement("td");
    tdName.className = "muted";
    tdName.textContent = nameEl ? nameEl.name : (s.symbol || "—");

    const tdZ = document.createElement("td");
    const zInp = document.createElement("input");
    zInp.type = "number";
    zInp.value = s.z;
    zInp.readOnly = true;
    zInp.title = "由元素符号自动确定";
    tdZ.append(zInp);

    const tdW = mkNum(s.mass_u, "mass_u");
    const tdA = mkNum(s.amount, "amount");
    const tdD = mkNum(s.displacement_ev, "displacement_ev");
    const tdL = mkNum(s.lattice_ev, "lattice_ev");
    const tdS = mkNum(s.surface_ev, "surface_ev");

    const tdX = document.createElement("td");
    const rm = document.createElement("button");
    rm.type = "button";
    rm.className = "mini danger";
    rm.textContent = "×";
    rm.disabled = layer.species.length <= 1;
    rm.addEventListener("click", () => {
      layer.species.splice(si, 1);
      dirty = true;
      renderSpecies();
      renderTargetSummary();
    });
    tdX.append(rm);

    tr.append(tdSym, tdName, tdZ, tdW, tdA, tdD, tdL, tdS, tdX);
    body.append(tr);
  });

  $("add-species").disabled = layer.species.length >= 8;
  renderTargetSummary();
}

function fillLayerFromCompound(key) {
  if (!project || !project.layers[selectedLayer]) return;
  if (!key) {
    message("请先在下拉框选择一种化合物");
    return;
  }
  const c = compoundsSource.find(x => x.key === key || x.name === key);
  if (!c) return;
  const layer = project.layers[selectedLayer];
  if (!layer.name || /^Layer\s*\d*$/i.test(layer.name) || /^Silicon|^未命名/i.test(layer.name)) {
    layer.name = c.key;
  }
  if (c.density) layer.density_g_cm3 = c.density;
  layer.species = c.species.map(entry => {
    if (Array.isArray(entry)) return makeSpecies(entry[0], entry[1]);
    const el = lookupElement(entry.symbol);
    if (!el) return makeSpecies(entry.symbol, entry.amount);
    const b = bindDefaults(el.symbol);
    return {
      symbol: el.symbol, z: el.z, mass_u: entry.mass_u ?? el.mass_u,
      amount: entry.amount ?? 1,
      displacement_ev: entry.displacement_ev ?? b.displacement_ev,
      lattice_ev: entry.lattice_ev ?? b.lattice_ev,
      surface_ev: entry.surface_ev ?? b.surface_ev
    };
  });
  dirty = true;
  renderLayers();
  renderSpecies();
  message(`已将 ${c.key} 填入 Layer ${selectedLayer + 1}，可继续改配比 Amount`);
  setTimeout(() => message(""), 3000);
}

/* ---------- collect / fill project ---------- */
function collect() {
  if (!project) return null;
  const p = structuredClone(project);
  p.schema = 1;
  p.name = $("name").value;
  p.ion = {
    symbol: $("ion-symbol").value.trim() || "He",
    z: Number($("ion-z").value),
    mass_u: Number($("ion-mass").value),
    energy_kev: Number($("ion-energy").value),
    angle_deg: Number($("ion-angle").value)
  };
  p.run = Object.assign({}, p.run, {
    ions: Number($("ions").value),
    seed: Number($("seed").value),
    batch_size: Number($("batch").value),
    bins: Number($("bins").value),
    cutoff_ev: Number($("cutoff").value),
    max_events: Number($("events").value),
    impact_scale: Number($("impact").value),
    mode: document.querySelector('input[name="mode"]:checked')?.value || "cascades",
    damage: $("damage").value
  });
  p.physics = Object.assign({}, p.physics, {
    stopping: ($("stopping") && $("stopping").value) || "iaea",
    scattering: document.querySelector('input[name="scattering"]:checked')?.value || "table",
    validated: false
  });
  p.layers = project.layers.map(l => ({
    name: l.name,
    thickness_a: Number(l.thickness_a),
    density_g_cm3: Number(l.density_g_cm3),
    species: l.species.map(s => ({
      symbol: s.symbol,
      z: Number(s.z),
      mass_u: Number(s.mass_u),
      amount: Number(s.amount),
      displacement_ev: Number(s.displacement_ev),
      lattice_ev: Number(s.lattice_ev),
      surface_ev: Number(s.surface_ev)
    }))
  }));
  return p;
}

function fill(p) {
  project = structuredClone(p);
  if (!project.physics) project.physics = { stopping: "iaea", scattering: "table", validated: false };
  if ($("stopping")) {
    const stop = project.physics.stopping || "iaea";
    $("stopping").value = ["iaea","biersack-varelas","lindhard-scharff"].includes(stop) ? stop : "iaea";
  }
  if (!project.run.damage) project.run.damage = "creation";
  $("name").value = project.name || "";
  $("ion-symbol").value = project.ion.symbol;
  $("ion-z").value = project.ion.z;
  $("ion-mass").value = project.ion.mass_u;
  $("ion-energy").value = project.ion.energy_kev;
  $("ion-angle").value = project.ion.angle_deg;
  $("ions").value = project.run.ions;
  $("seed").value = project.run.seed;
  $("batch").value = project.run.batch_size;
  $("bins").value = project.run.bins;
  $("cutoff").value = project.run.cutoff_ev;
  $("events").value = project.run.max_events;
  $("impact").value = project.run.impact_scale;
  $("damage").value = project.run.damage || "creation";
  const mode = project.run.mode || "cascades";
  const modeEl = document.querySelector(`input[name="mode"][value="${mode}"]`);
  if (modeEl) modeEl.checked = true;
  const scat = (project.physics && project.physics.scattering) || "table";
  const scatEl = document.querySelector(`input[name="scattering"][value="${scat}"]`);
  if (scatEl) scatEl.checked = true;
  selectedLayer = 0;
  renderLayers();
  renderSpecies();
  updateIonChip();
  dirty = false;
}

function renderTargetSummary() {
  const body = $("target-summary-body");
  body.replaceChildren();
  // A result must show the parameters that produced it, never the current draft.
  const resultProject=state?.project && state.status!=='idle' ? state.project : project;
  if (!resultProject) return;
  resultProject.layers.forEach((l, i) => {
    const tr = document.createElement("tr");
    const names = l.species.map(s => `${s.symbol}${s.amount != null && Number(s.amount) !== 1 ? fmt(s.amount, 3) : ""}`).join(" · ");
    [String(i + 1) + " " + (l.name || ""), ang(l.thickness_a), fmt(l.density_g_cm3, 4), names].forEach(t => {
      const td = document.createElement("td");
      td.textContent = t;
      tr.append(td);
    });
    body.append(tr);
  });
  if (resultProject.ion) {
    const ion = resultProject.ion;
    $("ion-summary").textContent =
      `Ion ${ion.symbol}  Z=${ion.z}  ${fmt(ion.mass_u, 5)} u  @ ${fmt(ion.energy_kev, 5)} keV  angle ${fmt(ion.angle_deg, 3)}°`;
  }
}

/* ---------- results stats ---------- */
function clearStats() {
  const ids = [
    "stat-back", "stat-trans", "stat-implant", "stat-vac",
    "range-mean", "range-str", "range-nm",
    "lat-mean", "lat-str", "lat-nm",
    "rad-mean", "rad-str", "rad-nm",
    "el-ion-ions", "el-ion-rec", "el-ion-tot",
    "el-phon-ions", "el-phon-rec", "el-phon-tot",
    "el-nuc-ions", "el-nuc-tot",
    "el-escaped", "el-ion-ev", "el-phon-ev",
    "sputter-total"
  ];
  ids.forEach(id => { const el = $(id); if (el) el.textContent = "—"; });
  $("sputter-body").replaceChildren();
  const tr = document.createElement("tr");
  const td = document.createElement("td");
  td.colSpan = 3;
  td.className = "muted";
  td.textContent = "—";
  tr.append(td);
  $("sputter-body").append(tr);
  $("summary").textContent = "";
}

function renderStats(stats) {
  if (!stats) {
    clearStats();
    return;
  }
  $("stat-back").textContent = fmt(stats.backscattered, 6);
  $("stat-trans").textContent = fmt(stats.transmitted, 6);
  $("stat-implant").textContent = fmt(stats.implanted, 6);
  $("stat-vac").textContent = fmt(stats.vacancies_per_ion, 5);

  $("range-mean").textContent = ang(stats.mean_range_a);
  $("range-str").textContent = ang(stats.range_straggle_a);
  $("range-nm").textContent = nm(stats.mean_range_a);
  $("lat-mean").textContent = ang(stats.lateral_proj_a);
  $("lat-str").textContent = ang(stats.lateral_straggle_a);
  $("lat-nm").textContent = nm(stats.lateral_proj_a);
  $("rad-mean").textContent = ang(stats.radial_a);
  $("rad-str").textContent = ang(stats.radial_straggle_a);
  $("rad-nm").textContent = nm(stats.radial_a);

  const el = stats.energy_loss_percent || {};
  const ions = el.ions || {};
  const rec = el.recoils || {};
  const ionI = ions.ionization, ionR = rec.ionization;
  const phI = ions.phonons, phR = rec.phonons;
  const nucI = ions.nuclear_to_recoils;
  $("el-ion-ions").textContent = pct(ionI);
  $("el-ion-rec").textContent = pct(ionR);
  $("el-ion-tot").textContent = pct((ionI || 0) + (ionR || 0));
  $("el-phon-ions").textContent = pct(phI);
  $("el-phon-rec").textContent = pct(phR);
  $("el-phon-tot").textContent = pct((phI || 0) + (phR || 0));
  $("el-nuc-ions").textContent = pct(nucI);
  $("el-nuc-tot").textContent = pct(nucI);
  $("el-escaped").textContent = pct(el.escaped);
  $("el-ion-ev").textContent = fmt(stats.ionization_ev_per_ion, 5);
  $("el-phon-ev").textContent = fmt(stats.phonon_ev_per_ion, 5);

  $("sputter-total").textContent = fmt(stats.sputter_yield_front, 5);
  const tbody = $("sputter-body");
  tbody.replaceChildren();
  const list = stats.sputter_by_element || [];
  if (!list.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 3;
    td.className = "muted";
    td.textContent = "无分元素溅射数据";
    tr.append(td);
    tbody.append(tr);
  } else {
    list.forEach(item => {
      const tr = document.createElement("tr");
      [item.symbol, fmt(item.atoms_per_ion, 5), fmt(item.ev_per_atom, 4)].forEach(t => {
        const td = document.createElement("td");
        td.className = "num";
        if (t === item.symbol) td.className = "";
        td.textContent = t;
        tr.append(td);
      });
      tbody.append(tr);
    });
  }

  const lines = [];
  lines.push(`Stopped ${stats.implanted} · BS ${stats.backscattered} · Trans ${stats.transmitted}`);
  lines.push(`Unresolved ${stats.unresolved_primaries ?? 0} · Failed ${stats.failed_histories ?? 0}`);
  lines.push(`Disp/ion ${fmt(stats.displacements_per_ion, 5)} · KP vac ${fmt(stats.kinchin_pease_vacancies_per_ion, 5)}`);
  lines.push(`Peak depth ${fmt(stats.peak_depth_nm, 4)} nm · peak ${stats.peak_per_cm != null ? Number(stats.peak_per_cm).toExponential(3) : "—"}/cm`);
  $("summary").textContent = lines.join("\n");
}

function renderDose() {
  if(state?.diagnostic_only){$("dose").textContent="旧版或失败结果：禁用剂量换算，请重新运行";return;}
  if (!state?.stats?.peak_per_cm) {
    $("dose").textContent = "等待有效注入分布";
    return;
  }
  const target = Number($("desired").value);
  if (!Number.isFinite(target) || target <= 0) {
    $("dose").textContent = "请输入正的目标浓度";
    return;
  }
  const dose = target / state.stats.peak_per_cm;
  $("dose").textContent =
    Number(dose).toExponential(3) + " ions/cm²" +
    (state.status === "completed" ? "" : " · 部分统计");
}

function renderWarnings(list) {
  const ul = $("warnings");
  ul.replaceChildren();
  (list && list.length ? list : ["所有统计来自独立 GPU 内核，不是调用 TRIM。"]).forEach(w => {
    const li = document.createElement("li");
    li.textContent = w;
    ul.append(li);
  });
}

/* ---------- canvas plotting: unified TRIM classic scientific style ---------- */
const COLORS = {
  red: "#cc0000",
  redFill: "rgba(204, 0, 0, 0.82)",
  redSoft: "rgba(204, 0, 0, 0.18)",
  blue: "#0000aa",
  blueFill: "rgba(0, 0, 170, 0.82)",
  green: "#006600",
  greenFill: "rgba(0, 102, 0, 0.82)",
  magenta: "#990099",
  magentaFill: "rgba(153, 0, 153, 0.82)",
  teal: "#006666",
  tealFill: "rgba(0, 102, 102, 0.82)",
  orange: "#cc6600",
  orangeFill: "rgba(204, 102, 0, 0.82)",
  grid: "#cccccc",
  frame: "#aa0000",
  axis: "#222222",
  ink: "#111111",
  bg: "#ffffff",
  muted: "#555555"
};

const TRIM_SERIES = {
  implant:   { title: "ION RANGES",     y: "(ATOMS/cm3) / (ATOMS/cm2)", fill: COLORS.redFill,     stroke: COLORS.red,     unit: "Å" },
  lateral:   { title: "LATERAL RANGE",  y: "(ATOMS/cm3) / (ATOMS/cm2)", fill: COLORS.magentaFill, stroke: COLORS.magenta, unit: "Å" },
  ionization:{ title: "IONIZATION",     y: "eV / ION / BIN",            fill: COLORS.blueFill,    stroke: COLORS.blue,    unit: "Å" },
  phonons:   { title: "PHONONS",        y: "eV / ION / BIN",            fill: COLORS.tealFill,    stroke: COLORS.teal,    unit: "Å" },
  damage:    { title: "DAMAGE EVENTS",  y: "EVENTS / ION / BIN",        fill: COLORS.orangeFill,  stroke: COLORS.orange,  unit: "Å" },
  transfer:  { title: "ENERGY TO RECOILS", y: "eV / ION / BIN",         fill: COLORS.greenFill,   stroke: COLORS.green,   unit: "Å" },
  backscattered: { title: "BACKSCATTERED IONS", y: "ATOMS / ION / BIN", fill: COLORS.orangeFill, stroke: COLORS.orange, unit: "eV" },
  transmitted:   { title: "TRANSMITTED IONS",   y: "ATOMS / ION / BIN", fill: COLORS.blueFill,   stroke: COLORS.blue,   unit: "eV" },
  sputtered:     { title: "SPUTTERED ATOMS",    y: "ATOMS / ION / BIN", fill: COLORS.greenFill,  stroke: COLORS.green,  unit: "eV" },
  xy_long:   { title: "XY LONGITUDINAL", y: "LATERAL Y", unit: "Å" },
  xy_tracks: { title: "XY TRACKS",       y: "LATERAL Y", unit: "Å" }
};

function momentsFromProfile(z, w) {
  let sw = 0, m1 = 0;
  for (let i = 0; i < z.length; i++) { sw += w[i]; m1 += z[i] * w[i]; }
  if (sw <= 0) return null;
  m1 /= sw;
  let m2 = 0, m3 = 0, m4 = 0;
  for (let i = 0; i < z.length; i++) {
    const d = z[i] - m1;
    m2 += w[i] * d * d;
    m3 += w[i] * d * d * d;
    m4 += w[i] * d * d * d * d;
  }
  m2 /= sw; m3 /= sw; m4 /= sw;
  const sd = Math.sqrt(Math.max(m2, 0));
  return {
    mean: m1, sd,
    skew: sd > 1e-30 ? m3 / (sd * sd * sd) : 0,
    kurt: m2 > 1e-30 ? m4 / (m2 * m2) : 3,
    total: sw
  };
}

function fmtTrim(v, digits = 1) {
  if (v == null || !Number.isFinite(v)) return "—";
  return Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(digits);
}

function trimCanvasFrame(ctx, W, H, title, leftLabel, rightLabel) {
  ctx.fillStyle = COLORS.bg;
  ctx.fillRect(0, 0, W, H);
  ctx.strokeStyle = "#888";
  ctx.lineWidth = 1;
  ctx.strokeRect(0.5, 0.5, W - 1, H - 1);
  ctx.fillStyle = COLORS.ink;
  ctx.font = "bold 17px 'Times New Roman', Times, serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(title, W / 2, 22);
  return { leftLabel, rightLabel };
}

function trimStatsBlock(ctx, W, linesLeft, linesRight) {
  ctx.font = "12px 'Times New Roman', Times, serif";
  ctx.fillStyle = COLORS.blue;
  ctx.textAlign = "left";
  ctx.textBaseline = "middle";
  const y0 = 48;
  linesLeft.forEach((t, i) => ctx.fillText(t, Math.round(W * 0.14), y0 + i * 17));
  linesRight.forEach((t, i) => ctx.fillText(t, Math.round(W * 0.55), y0 + i * 17));
}

function trimAxes(ctx, opts) {
  const { L, T, pw, ph, xmin, xmax, ymin, ymax, xlabel, ylabel, yunitNote } = opts;
  // red frame
  ctx.strokeStyle = COLORS.frame;
  ctx.lineWidth = 2;
  ctx.strokeRect(L, T, pw, ph);

  const nT = 6;
  ctx.font = "11px 'Times New Roman', Times, serif";
  ctx.lineWidth = 1;
  for (let i = 0; i <= nT; i++) {
    const y = T + (i * ph) / nT;
    const yv = ymax - ((ymax - ymin) * i) / nT;
    ctx.strokeStyle = COLORS.grid;
    ctx.beginPath();
    ctx.moveTo(L, y);
    ctx.lineTo(L + pw, y);
    ctx.stroke();
    ctx.fillStyle = COLORS.ink;
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    ctx.fillText(fmtTrim(yv, 2), L - 6, y);
    // right dual-style scale note
    if (yunitNote) {
      ctx.textAlign = "left";
      ctx.fillText(yunitNote(yv), L + pw + 6, y);
      ctx.textAlign = "right";
    }
  }
  for (let i = 0; i <= nT; i++) {
    const x = L + (i * pw) / nT;
    const xv = xmin + ((xmax - xmin) * i) / nT;
    ctx.strokeStyle = COLORS.grid;
    ctx.beginPath();
    ctx.moveTo(x, T);
    ctx.lineTo(x, T + ph);
    ctx.stroke();
    ctx.fillStyle = COLORS.ink;
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.fillText(fmtTrim(xv, 1), x, T + ph + 6);
  }

  ctx.fillStyle = COLORS.ink;
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  ctx.font = "12px 'Times New Roman', Times, serif";
  ctx.fillText(xlabel, L + pw / 2, T + ph + 24);

  ctx.save();
  ctx.translate(14, T + ph / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(ylabel, 0, 0);
  ctx.restore();
}

function trimBars(ctx, points, X, Y, baseY, fill) {
  if (!points.length) return;
  const n = points.length;
  const x0 = X(points[0][0]);
  const x1 = X(points[n - 1][0]);
  const bw = Math.max(1.1, Math.abs(x1 - x0) / Math.max(n - 1, 1));
  ctx.fillStyle = fill;
  for (let i = 0; i < n; i++) {
    const h = baseY - Y(points[i][1]);
    if (h <= 0.4) continue;
    ctx.fillRect(X(points[i][0]) - bw / 2, Y(points[i][1]), bw, h);
  }
}

function trimFilledLine(ctx, points, X, Y, baseY, fill, stroke) {
  if (points.length < 2) return;
  ctx.beginPath();
  ctx.moveTo(X(points[0][0]), baseY);
  points.forEach(p => ctx.lineTo(X(p[0]), Y(p[1])));
  ctx.lineTo(X(points[points.length - 1][0]), baseY);
  ctx.closePath();
  ctx.fillStyle = fill;
  ctx.fill();
  ctx.strokeStyle = stroke;
  ctx.lineWidth = 1.6;
  ctx.beginPath();
  points.forEach((p, i) => {
    const x = X(p[0]), y = Y(p[1]);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

function collectSeries(mode) {
  if (!state || !state.completed) return { points: [], tracks: [] };
  if (mode === "xy_long" || mode === "xy_tracks") {
    const tracks = (state.tracks || []).map(tr => tr.map(p => [p[2] / 10, p[0] / 10]));
    return { points: [], tracks };
  }
  if (mode === "lateral") {
    const r = state.lateral_nm || [];
    const v = state.lateral_per_ion || [];
    return { points: r.map((x, i) => [x * 10, v[i] || 0]), tracks: [] }; // Å
  }
  if (mode === "backscattered" || mode === "transmitted" || mode === "sputtered") {
    const e = state.spectra_ev || [];
    const v = (state.spectra && state.spectra[mode]) || [];
    return { points: e.map((x, i) => [x, v[i] || 0]), tracks: [] };
  }
  // depth profiles: implant or energy/damage channels
  const depthA = (state.depth_nm || []).map(z => z * 10);
  let ys;
  if (mode === "implant") ys = state.implant_per_cm || [];
  else {
    const key = { ionization: "electronic_ev", phonons: "lattice_ev", damage: "displacements", transfer: "transfer_ev" }[mode] || "electronic_ev";
    ys = (state.profiles && state.profiles[key]) || [];
  }
  return { points: depthA.map((z, i) => [z, ys[i] || 0]), tracks: [] };
}

function drawTrimPlot() {
  const canvas = $("plot");
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const cssW = canvas.clientWidth || 860;
  const cssH = Math.min(430, Math.max(340, Math.round(cssW * 0.5)));
  canvas.style.height = cssH + "px";
  canvas.width = Math.round(cssW * dpr);
  canvas.height = Math.round(cssH * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  const W = cssW, H = cssH;
  const style = TRIM_SERIES[plotMode] || TRIM_SERIES.implant;
  const isXY = plotMode === "xy_long" || plotMode === "xy_tracks";
  trimCanvasFrame(ctx, W, H, style.title);

  if (!state || !state.completed) {
    ctx.fillStyle = COLORS.muted;
    ctx.font = "13px 'Times New Roman', Times, serif";
    ctx.textAlign = "center";
    ctx.fillText("尚无结果 — Run a simulation first", W / 2, H / 2);
    $("plot-caption").textContent = style.title + " · TRIM style";
    $("legend").textContent = "统一 TRIM 科研绘图风格";
    return;
  }

  const { points, tracks } = collectSeries(plotMode);
  const L = 72, R = (plotMode === "implant" || plotMode === "lateral") ? 64 : 36, T = 86, B = 52;
  const pw = W - L - R, ph = H - T - B;

  if (isXY) {
    const all = tracks.flat();
    if (!all.length) {
      ctx.fillStyle = COLORS.muted;
      ctx.fillText("无轨迹数据", L + 10, T + 20);
      return;
    }
    let xmin = Math.min(...all.map(p => p[0]));
    let xmax = Math.max(...all.map(p => p[0]));
    let ymin = Math.min(0, ...all.map(p => p[1]));
    let ymax = Math.max(...all.map(p => p[1]));
    if (xmax - xmin < 1e-9) xmax = xmin + 1;
    if (ymax - ymin < 1e-9) ymax = ymin + 1;
    const padY = 0.08 * (ymax - ymin);
    ymin -= padY; ymax += padY;
    const X = x => L + ((x - xmin) / (xmax - xmin)) * pw;
    const Y = y => T + ph - ((y - ymin) / (ymax - ymin)) * ph;
    trimAxes(ctx, {
      L, T, pw, ph, xmin, xmax, ymin, ymax,
      xlabel: "Target Depth (Å)",
      ylabel: style.y + " (Å)"
    });
    // zero line
    ctx.strokeStyle = "#999";
    ctx.setLineDash([4, 3]);
    ctx.beginPath();
    ctx.moveTo(L, Y(0));
    ctx.lineTo(L + pw, Y(0));
    ctx.stroke();
    ctx.setLineDash([]);

    if (plotMode === "xy_long") {
      ctx.fillStyle = "rgba(0,0,170,0.35)";
      tracks.forEach(tr => tr.forEach(p => {
        ctx.fillRect(X(p[0]) - 0.6, Y(p[1]) - 0.6, 1.3, 1.3);
      }));
    } else {
      const palette = [COLORS.red, COLORS.blue, COLORS.green, COLORS.magenta, COLORS.orange, COLORS.teal, "#666", "#333"];
      tracks.forEach((tr, i) => {
        ctx.strokeStyle = palette[i % palette.length];
        ctx.lineWidth = 1.1;
        ctx.beginPath();
        tr.forEach((p, j) => {
          if (j === 0) ctx.moveTo(X(p[0]), Y(p[1]));
          else ctx.lineTo(X(p[0]), Y(p[1]));
        });
        ctx.stroke();
      });
    }
    $("plot-caption").textContent = style.title + " · Depth vs lateral (Å)";
    $("legend").textContent = "TRIM style · 蓝点/彩线 = 入射离子轨迹（抽样）";
    return;
  }

  if (!points.length) {
    ctx.fillStyle = COLORS.muted;
    ctx.fillText("无分布数据", L + 10, T + 20);
    return;
  }

  let xmin = Math.min(...points.map(p => p[0]));
  let xmax = Math.max(...points.map(p => p[0]));
  let ymax = Math.max(...points.map(p => p[1]), 0);
  if (xmax - xmin < 1e-9) xmax = xmin + 1;
  if (ymax <= 0) ymax = 1;
  ymax *= 1.05;
  const ymin = 0;
  const X = x => L + ((x - xmin) / (xmax - xmin)) * pw;
  const Y = y => T + ph - ((y - ymin) / (ymax - ymin)) * ph;

  // stats / dual axis for implant and lateral
  let leftLines = [], rightLines = [];
  let yunitNote = null;
  if (plotMode === "implant" || plotMode === "lateral") {
    const mo = momentsFromProfile(points.map(p => p[0]), points.map(p => p[1]));
    const st = state.stats || {};
    const Rp = plotMode === "implant" ? (st.mean_range_a != null ? st.mean_range_a : mo?.mean)
                                      : (mo ? mo.mean : null);
    const dRp = plotMode === "implant" ? (st.range_straggle_a != null ? st.range_straggle_a : mo?.sd)
                                        : (mo ? mo.sd : null);
    leftLines = [
      `Range     =  ${fmtTrim(Rp)} A`,
      `Straggle  =  ${fmtTrim(dRp)} A`
    ];
    rightLines = [
      `Skewness  =  ${(mo ? mo.skew : 0).toFixed(4)}`,
      `Kurtosis  =  ${(mo ? mo.kurt : 3).toFixed(4)}`
    ];
    const scale = ymax > 1e5 ? 1e5 : ymax > 1e4 ? 1e4 : ymax > 1e2 ? 1e2 : 1;
    yunitNote = (yv) => {
      const q = yv / scale;
      return q.toFixed(q >= 10 ? 1 : 2) + (scale === 1e5 ? " x10⁵" : scale === 1e4 ? " x10⁴" : scale === 1e2 ? " x10²" : "");
    };
  } else if (plotMode === "damage") {
    const st = state.stats || {};
    leftLines = [
      `Vacancies/Ion = ${fmtTrim(st.vacancies_per_ion, 2)}`,
      `Disp. events  = ${fmtTrim(st.displacements_per_ion, 2)}`
    ];
  } else if (plotMode === "ionization" || plotMode === "phonons") {
    const st = state.stats || {};
    const key = plotMode === "ionization" ? "ionization_ev_per_ion" : "phonon_ev_per_ion";
    leftLines = [`Mean eV/Ion = ${fmtTrim(st[key], 1)}`];
  }

  trimStatsBlock(ctx, W, leftLines, rightLines);
  trimAxes(ctx, {
    L, T, pw, ph, xmin, xmax, ymin, ymax,
    xlabel: (plotMode === "backscattered" || plotMode === "transmitted" || plotMode === "sputtered")
      ? `Energy (${style.unit})`
      : `Target Depth (${style.unit})`,
    ylabel: style.y,
    yunitNote
  });

  // TRIM frame + data: implant = red bars (classic), others = filled area+line (same language)
  const isDepth = !(plotMode === "backscattered" || plotMode === "transmitted" || plotMode === "sputtered");
  if (plotMode === "implant") {
    trimBars(ctx, points, X, Y, T + ph, style.fill);
    ctx.strokeStyle = style.stroke;
    ctx.lineWidth = 1.1;
    ctx.beginPath();
    points.forEach((p, i) => {
      const x = X(p[0]), y = Y(p[1]);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  } else {
    trimFilledLine(ctx, points, X, Y, T + ph, style.fill, style.stroke);
  }

  // Layer label on depth plots
  if (!isXY && plotMode !== "backscattered" && plotMode !== "transmitted" && plotMode !== "sputtered") {
    ctx.save();
    ctx.translate(L + 14, T + ph * 0.55);
    ctx.rotate(-Math.PI / 2);
    ctx.fillStyle = COLORS.ink;
    ctx.font = "12px 'Times New Roman', Times, serif";
    ctx.textAlign = "center";
    ctx.fillText("Layer 1", 0, 0);
    ctx.restore();
  }

  $("plot-caption").textContent = `${style.title} · TRIM style · ${style.y}`;
  $("legend").textContent = `统一 TRIM 科研风格 · 填充柱+红线 · ${style.title}`;
}

function drawPlot() {
  drawTrimPlot();
}

function buildPlotList() {
  const box = $("plot-list");
  box.replaceChildren();
  PLOT_MODES.forEach(m => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.dataset.plot = m.id;
    btn.title = m.cn + " — " + m.label;
    btn.textContent = m.label;
    btn.className = m.id === plotMode ? "active" : "";
    btn.addEventListener("click", () => {
      plotMode = m.id;
      box.querySelectorAll("button").forEach(b => b.classList.toggle("active", b === btn));
      drawPlot();
    });
    box.append(btn);
  });
}

/* ---------- state render ---------- */
function renderState() {
  if (!state) return;
  renderTargetSummary();
  const busy = ["preparing", "running"].includes(state.status);
  const canResume = ["paused", "cancelled"].includes(state.status) && !state.diagnostic_only;
  $("inputs").disabled = busy;
  // Ion count lives in the launch bar (outside fieldset) so it stays editable
  // before the next Start; only lock it while a run is preparing/running.
  if ($("ions")) $("ions").disabled = busy;
  $("start").disabled = busy;
  $("pause").disabled = !busy;
  $("cancel").disabled = !busy;
  $("resume").disabled = !canResume;
  $("restore").disabled = busy;
  $("load-project").disabled = busy;
  $("save-project").disabled = busy;

  const st = $("status");
  st.textContent = STATUS_CN[state.status] || state.status;
  if(state.diagnostic_only)st.textContent += " · 仅诊断/旧版只读";
  st.className = "status-pill " + (state.status || "");

  const done = state.completed || 0;
  const total = state.total || 0;
  $("progress").value = total ? done / total : 0;
  $("progress-text").textContent = total
    ? `${done.toLocaleString()} / ${total.toLocaleString()} 条入射历史`
    : "编辑参数后开始";
  $("elapsed").textContent = (state.elapsed_s || 0).toFixed(1);
  $("ions-done").textContent = done.toLocaleString();
  $("ions-total").textContent = total.toLocaleString();

  if (state.error) message(state.error);
  else if (state.status === "idle") message("");
  $("csv").disabled = !state.completed || state.diagnostic_only;
  $("json").disabled = state.status === "idle";

  renderStats(state.stats);
  renderWarnings([...(state.warnings||[]),...(state.se_sources||[]).map(source=>'Stopping source: '+source)]);
  renderDose();
  drawPlot();
}

async function poll() {
  if (polling) return;
  polling = true;
  try {
    state = await api("state");
    const conn = $("connection");
    conn.textContent = "● 本地引擎已连接";
    conn.className = "conn ok";
    // keep form in sync only when idle and not dirty
    if (state.status === "idle" && !dirty && state.project) {
      // no-op: user may be editing; only first fill
    }
    renderState();
  } catch (e) {
    const conn = $("connection");
    conn.textContent = "连接中断";
    conn.className = "conn bad";
    message(e.message);
  } finally {
    polling = false;
  }
}

async function action(name, data) {
  try {
    message("");
    const result = await api(name, data || {});
    state = result;
    if (name === "restore" && result.project) fill(result.project);
    renderState();
  } catch (e) {
    message(e.message);
  }
}

/* ---------- init UI pieces ---------- */
function initElementList() {
  const dl = $("element-list");
  Object.keys(ELEMENTS).forEach(sym => {
    const opt = document.createElement("option");
    opt.value = sym;
    opt.label = ELEMENTS[sym][2];
    dl.append(opt);
  });
}

function initCompounds() {
  const sel = $("compound-select");
  const apply = list => {
    compoundsSource = list;
    sel.replaceChildren();
    const ph = document.createElement("option");
    ph.value = "";
    ph.textContent = "— 选择化合物填入当前层 —";
    sel.append(ph);
    list.forEach(c => {
      const o = document.createElement("option");
      o.value = c.key;
      const formula = (c.species || []).map(([sym, amt]) =>
        amt === 1 ? sym : `${sym}${amt}`).join("");
      o.textContent = `${formula || c.key} — ${c.name}` + (c.density ? ` (${c.density} g/cm³)` : "");
      sel.append(o);
    });
  };
  apply(COMPOUNDS);
  api("compounds").then(res => {
    const raw = Array.isArray(res) ? res : (res.compounds || []);
    if (!Array.isArray(raw) || !raw.length) return;
    // Accept either full objects or names; never replace the embedded dict with junk.
    const mapped = raw.map(c => {
      if (typeof c === "string") {
        const hit = COMPOUNDS.find(x => x.key === c || x.name === c);
        return hit || null;
      }
      const species = (c.species || c.elements || []).map(s =>
        Array.isArray(s) ? s : [s.symbol, s.amount ?? 1]
      ).filter(p => p && p[0]);
      if (!species.length) return null;
      return {
        key: c.key || c.name,
        name: c.name || c.key || "",
        density: c.density_g_cm3 ?? c.density,
        species
      };
    }).filter(Boolean);
    if (mapped.length >= 5) apply(mapped);
  }).catch(() => { /* keep embedded dictionary */ });
}

function bindEvents() {
  $("ion-symbol").addEventListener("change", () => applyElementToIon($("ion-symbol").value));
  $("ion-symbol").addEventListener("input", updateIonChip);
  $("ion-z").addEventListener("change", () => {
    const z = Number($("ion-z").value);
    const hit = Object.keys(ELEMENTS).find(k => ELEMENTS[k][0] === z);
    if (hit) applyElementToIon(hit);
    else updateIonChip();
  });
  ["ion-mass", "ion-energy", "ion-angle", "name", "ions", "seed", "batch", "bins", "cutoff", "events", "impact"]
    .forEach(id => $(id).addEventListener("input", () => { dirty = true; }));
  $("damage").addEventListener("change", () => { dirty = true; });
  document.querySelectorAll('input[name="mode"], input[name="scattering"]').forEach(el => {
    el.addEventListener("change", () => { dirty = true; });
  });
  if ($("stopping")) $("stopping").addEventListener("change", () => { dirty = true; });

  $("add-layer").addEventListener("click", () => {
    if (!project || project.layers.length >= 8) return;
    const last = project.layers.at(-1);
    const layer = structuredClone(last);
    layer.name = "Layer" + project.layers.length;
    project.layers.push(layer);
    selectedLayer = project.layers.length - 1;
    dirty = true;
    renderLayers();
    renderSpecies();
  });

  $("add-species").addEventListener("click", () => {
    if (!project || !project.layers[selectedLayer]) return;
    const layer = project.layers[selectedLayer];
    if (layer.species.length >= 8) return;
    const used = new Set(layer.species.map(s => s.symbol));
    const pick = ["O", "N", "C", "Si", "Al", "Fe", "Cu", "Au", "W"].find(s => !used.has(s)) || "O";
    layer.species.push(makeSpecies(pick, 1));
    dirty = true;
    renderSpecies();
  });

  $("apply-compound").addEventListener("click", () => {
    fillLayerFromCompound($("compound-select").value);
  });
  $("compound-select").addEventListener("change", () => {
    if ($("compound-select").value) fillLayerFromCompound($("compound-select").value);
  });

  $("start").addEventListener("click", async () => {
    try {
      const p = collect();
      await api("validate", p);
      if (state?.completed &&
          !confirm("开始新运行将替换当前工作区结果和自动断点。请先导出需要保留的结果。继续？")) {
        return;
      }
      dirty = false;
      setView("results");
      await action("start", p);
      renderState();
    } catch (e) {
      message(e.message);
      setView("setup");
    }
  });

  $("tab-setup").addEventListener("click", () => setView("setup"));
  $("tab-results").addEventListener("click", () => setView("results"));
  $("back-setup").addEventListener("click", () => {
    if (["preparing", "running"].includes(state?.status) &&
        !confirm("计算仍在进行。返回设置页不会停止 GPU 运行，确定？")) return;
    setView("setup");
  });

  $("pause").addEventListener("click", () => action("pause"));
  $("cancel").addEventListener("click", () => action("cancel"));
  $("resume").addEventListener("click", async () => {
    if (state?.project) fill(state.project);
    await action("resume");
  });
  $("restore").addEventListener("click", async () => {
    if (state?.completed &&
        !confirm("恢复自动断点将替换当前工作区，是否继续？")) return;
    await action("restore");
    setView("results");
    renderState();
  });

  $("save-project").addEventListener("click", async () => {
    try {
      const p = collect();
      await api("validate", p);
      saveFile("gsrim-project.json", JSON.stringify(p, null, 2), "application/json");
      dirty = false;
    } catch (e) {
      message(e.message);
    }
  });
  $("load-project").addEventListener("click", () => {
    $("project-file").value = "";
    $("project-file").click();
  });
  $("project-file").addEventListener("change", async e => {
    try {
      const file = e.target.files[0];
      if (!file) return;
      if (file.size > 1024 * 1024) throw Error("项目文件不能超过 1 MB");
      const result = await api("validate", JSON.parse(await file.text()));
      fill(result.project);
      message("项目已载入；工作区仍显示上一轮结果，开始新运行后更新。");
    } catch (err) {
      message(err.message);
    }
  });

  $("desired").addEventListener("input", renderDose);
  $("csv").addEventListener("click", () => { location.href = "/api/csv"; });
  $("json").addEventListener("click", () => { location.href = "/api/result"; });
  $("save-plot").addEventListener("click", () => {
    const canvas = $("plot");
    canvas.toBlob(blob => {
      if (!blob) return;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "gsrim-plot.png";
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
  });

  $("inputs").addEventListener("input", () => { dirty = true; });
  window.addEventListener("beforeunload", e => {
    if (dirty) {
      e.preventDefault();
      e.returnValue = "";
    }
  });
  window.addEventListener("resize", () => drawPlot());
}

/* ---------- boot ---------- */
(async function boot() {
  initElementList();
  initCompounds();
  buildPlotList();
  clearStats();
  bindEvents();
  setView("setup");
  try {
    let info;
    try {info=await api('info');} catch {throw Error('当前后台是旧版引擎。请重新运行 Start-GSRIM.cmd 打开新版，不要在此页继续计算。');}
    if(info.engine_revision!==2)throw Error('前后端版本不匹配，请重新启动 GSRIM。');
    if($('checkpoint-path'))$('checkpoint-path').textContent='本服务断点：'+info.checkpoint_path+'。旧版结果只读。';
    token = (await api("token")).token;
    state = await api("state");
    if (state.project) fill(state.project);
    else fill(await api("default"));
    renderState();
    if (state && state.status && state.status !== "idle") setView("results");
    setInterval(poll, 1000);
  } catch (e) {
    message(e.message || String(e));
    $('start').disabled=true;
  }
})();
