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
  const L = 72, R = style.yunitNote ? 64 : 28, T = 86, B = 52;
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

  // filled bars like TRIM
  trimBars(ctx, points, X, Y, T + ph, style.fill);
  // outline for paper quality
  ctx.strokeStyle = style.stroke;
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  points.forEach((p, i) => {
    const x = X(p[0]), y = Y(p[1]);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

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
