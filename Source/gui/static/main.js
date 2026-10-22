import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const $ = (id) => document.getElementById(id);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const ROLL_MS = 220, REPLAY_ROLL_MS = 160, REPLAY_GAP_MS = 100;
const COLORS = { floor: 0x5b6b8c, fragile: 0xd9a441, goal: 0x07090d, bridge: 0x3fb5a8,
  block: 0xc8553d, soft: 0xf2f2f2, heavy: 0xff6b81, split: 0x6ec1ff };

function createBrickTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 128;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#fff";
  ctx.fillRect(0, 0, 128, 128);
  ctx.strokeStyle = "rgba(12, 12, 16, 0.34)";
  ctx.lineWidth = 3;

  for (const y of [0, 32, 64, 96, 127]) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(128, y);
    ctx.stroke();
  }
  for (const [x, y1, y2] of [[0, 0, 32], [64, 0, 32], [32, 32, 64], [96, 32, 64],
    [0, 64, 96], [64, 64, 96], [32, 96, 127], [96, 96, 127], [127, 0, 32], [127, 64, 96]]) {
    ctx.beginPath();
    ctx.moveTo(x, y1);
    ctx.lineTo(x, y2);
    ctx.stroke();
  }
  ctx.strokeStyle = "rgba(8, 8, 10, 0.2)";
  ctx.lineWidth = 1.5;
  for (const [x, y] of [[13, 13], [84, 49], [48, 82], [111, 112]]) {
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + 4, y + 5);
    ctx.lineTo(x + 2, y + 10);
    ctx.lineTo(x + 7, y + 14);
    ctx.stroke();
  }

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

const brickTexture = createBrickTexture();

async function api(path, body) {
  const res = await fetch(path, body
    ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }
    : undefined);
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

/* ---------- scene ---------- */
const stage = $("stage");
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x14181f);
const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 200);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
stage.appendChild(renderer.domElement);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.maxPolarAngle = Math.PI / 2.05;
scene.add(new THREE.AmbientLight(0xffffff, 0.75));
const sun = new THREE.DirectionalLight(0xffffff, 1.1);
sun.position.set(6, 12, 8);
scene.add(sun);
const boardGroup = new THREE.Group();
const blockGroup = new THREE.Group();
scene.add(boardGroup, blockGroup);

function resize() {
  const w = stage.clientWidth, h = stage.clientHeight;
  renderer.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
window.addEventListener("resize", resize);
(function loop() { controls.update(); renderer.render(scene, camera); requestAnimationFrame(loop); })();

/* ---------- board ---------- */
let bridgeTiles = {};

function addSwitch(sw) {
  const [r, c] = sw.pos;
  const g = new THREE.Group();
  g.userData.isSwitch = true;
  g.position.set(c, 0.03, r);
  const mat = (color) => new THREE.MeshStandardMaterial({ color });
  if (sw.type === "soft") {                       // 1 đĩa tròn
    g.add(new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.3, 0.06, 24), mat(COLORS.soft)));
  } else if (sw.type === "heavy") {               // chữ X
    for (const a of [Math.PI / 4, -Math.PI / 4]) {
      const bar = new THREE.Mesh(new THREE.BoxGeometry(0.75, 0.06, 0.14), mat(COLORS.heavy));
      bar.rotation.y = a;
      g.add(bar);
    }
  } else {                                        // split: 2 đĩa nhỏ "( )"
    for (const dx of [-0.22, 0.22]) {
      const d = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 0.06, 20), mat(COLORS.split));
      d.position.x = dx;
      g.add(d);
    }
  }
  boardGroup.add(g);
}

function addGoalHole(r, c) {
  const well = new THREE.Mesh(
    new THREE.CylinderGeometry(0.34, 0.4, 0.34, 32),
    new THREE.MeshStandardMaterial({ color: 0x030407, roughness: 1 })
  );
  well.position.set(c, -0.34, r);
  boardGroup.add(well);
}

function clearGroup(group) {
  const geometries = new Set();
  const materials = new Set();
  group.traverse((object) => {
    if (object.geometry) geometries.add(object.geometry);
    if (object.material) {
      for (const material of Array.isArray(object.material) ? object.material : [object.material])
        materials.add(material);
    }
  });
  geometries.forEach((geometry) => geometry.dispose());
  materials.forEach((material) => material.dispose());
  group.clear();
}

function buildBoard(level) {
  clearGroup(boardGroup);
  bridgeTiles = {};
  const rows = level.grid.length, cols = level.grid[0].length;
  const bridgeOf = {};
  for (const [id, b] of Object.entries(level.bridges || {}))
    for (const [r, c] of b.cells) bridgeOf[`${r},${c}`] = id;

  level.grid.forEach((line, r) => [...line].forEach((ch, c) => {
    if (ch === "." || ch === " ") return;
    if (ch === "g") {
      addGoalHole(r, c);
      return;
    }
    const color = { o: COLORS.floor, f: COLORS.fragile, g: COLORS.goal, b: COLORS.bridge }[ch] ?? COLORS.floor;
    const mat = new THREE.MeshStandardMaterial({
      color,
      map: brickTexture,
      transparent: ch === "b",
      roughness: 0.9,
    });
    const tile = new THREE.Mesh(new THREE.BoxGeometry(0.96, 0.2, 0.96), mat);
    tile.position.set(c, -0.1, r);
    boardGroup.add(tile);
    if (ch === "b") (bridgeTiles[bridgeOf[`${r},${c}`]] ||= []).push(tile);
  }));
  (level.switches || []).forEach(addSwitch);

  const cx = (cols - 1) / 2, cz = (rows - 1) / 2, span = Math.max(cols, rows);
  controls.target.set(cx, 0, cz);
  camera.position.set(cx + span * 0.55, span * 0.95, cz + span * 0.95);
  controls.update();
}

function setBridges(bridges) {
  for (const [id, tiles] of Object.entries(bridgeTiles))
    tiles.forEach((t) => { t.material.opacity = bridges[id] ? 1 : 0.12; });
}

/* ---------- block ---------- */
let blockMeshes = [];

function blockBox(cells, multi) {
  const rs = cells.map((c) => c[0]), cs = cells.map((c) => c[1]);
  const r0 = Math.min(...rs), r1 = Math.max(...rs), c0 = Math.min(...cs), c1 = Math.max(...cs);
  const h = cells.length === 1 && !multi ? 2 : 1;   // đứng cao 2; nằm hoặc khối lập phương cao 1
  return { r0, r1, c0, c1, h, w: c1 - c0 + 1, d: r1 - r0 + 1 };
}

function renderState() {
  clearGroup(blockGroup);
  blockMeshes = [];
  const multi = state.blocks.length > 1;
  state.blocks.forEach((cells, i) => {
    const b = blockBox(cells, multi);
    const mat = new THREE.MeshStandardMaterial({ color: COLORS.block, map: brickTexture, roughness: 0.88 });
    if (multi && i === state.active) { mat.emissive = new THREE.Color(0xffd166); mat.emissiveIntensity = 0.35; }
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(b.w * 0.96, b.h * 0.98, b.d * 0.96), mat);
    mesh.add(new THREE.LineSegments(new THREE.EdgesGeometry(mesh.geometry),
      new THREE.LineBasicMaterial({ color: 0x1a1210 })));
    mesh.position.set((b.c0 + b.c1) / 2, b.h / 2, (b.r0 + b.r1) / 2);
    blockGroup.add(mesh);
    blockMeshes.push(mesh);
  });
  setBridges(state.bridges);
  updateHud();
}

// Lăn quanh cạnh đáy phía hướng di chuyển: đúng cho cả 3 hướng của khối.
function rollBlock(idx, dir, ms) {
  const mesh = blockMeshes[idx];
  const b = blockBox(state.blocks[idx], state.blocks.length > 1);
  const xc = (b.c0 + b.c1) / 2, zc = (b.r0 + b.r1) / 2;
  const cfg = {
    right: { p: [b.c1 + 0.5, 0, zc], axis: "z", a: -Math.PI / 2 },
    left:  { p: [b.c0 - 0.5, 0, zc], axis: "z", a:  Math.PI / 2 },
    down:  { p: [xc, 0, b.r1 + 0.5], axis: "x", a:  Math.PI / 2 },
    up:    { p: [xc, 0, b.r0 - 0.5], axis: "x", a: -Math.PI / 2 },
  }[dir];
  const pivot = new THREE.Group();
  pivot.position.set(...cfg.p);
  scene.add(pivot);
  pivot.attach(mesh);
  return new Promise((resolve) => {
    const t0 = performance.now();
    (function step(now) {
      const k = Math.min((now - t0) / ms, 1);
      const e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
      pivot.rotation[cfg.axis] = cfg.a * e;
      if (k < 1) requestAnimationFrame(step);
      else {
        blockGroup.attach(mesh);
        scene.remove(pivot);
        resolve();
      }
    })(t0);
  });
}

function dropBlock(idx, dir, ms = 620) {
  const mesh = blockMeshes[idx];
  if (!mesh) return Promise.resolve();

  const initialY = mesh.position.y;
  const initialScale = mesh.scale.clone();
  const initialRotation = mesh.rotation.clone();
  const tilt = {
    right: [0, 0, -0.24],
    left: [0, 0, 0.24],
    down: [0.24, 0, 0],
    up: [-0.24, 0, 0],
  }[dir] || [0.18, 0, 0.18];
  const materials = [];
  mesh.traverse((part) => {
    if (!part.isMesh) return;
    const list = Array.isArray(part.material) ? part.material : [part.material];
    for (const material of list) {
      materials.push({ material, transparent: material.transparent, opacity: material.opacity });
      material.transparent = true;
    }
  });

  return new Promise((resolve) => {
    const t0 = performance.now();
    (function step(now) {
      const k = Math.min((now - t0) / ms, 1);
      const fall = k * k;
      mesh.position.y = initialY - fall * 2.8;
      mesh.rotation.set(
        initialRotation.x + tilt[0] * k,
        initialRotation.y + tilt[1] * k,
        initialRotation.z + tilt[2] * k
      );
      const scale = 1 - fall * 0.88;
      mesh.scale.set(initialScale.x * scale, initialScale.y * scale, initialScale.z * scale);
      for (const { material } of materials) material.opacity = 1 - fall;
      if (k < 1) requestAnimationFrame(step);
      else resolve();
    })(t0);
  });
}

function crumbleBoard(ms = 850) {
  for (const object of [...boardGroup.children]) {
    if (!object.userData.isSwitch) continue;
    clearGroup(object);
    boardGroup.remove(object);
  }
  const pieces = [...boardGroup.children].map((object, index) => {
    const materials = [];
    object.traverse((part) => {
      if (!part.isMesh) return;
      const list = Array.isArray(part.material) ? part.material : [part.material];
      for (const material of list) {
        materials.push({ material, opacity: material.opacity });
        material.transparent = true;
      }
    });
    return {
      object,
      index,
      position: object.position.clone(),
      rotation: object.rotation.clone(),
      scale: object.scale.clone(),
      materials,
      angle: index * 2.399,
    };
  });

  return new Promise((resolve) => {
    const t0 = performance.now();
    (function step(now) {
      let complete = true;
      for (const piece of pieces) {
        const k = Math.max(0, Math.min((now - t0) / ms, 1));
        const fall = k * k;
        piece.object.position.set(
          piece.position.x + Math.cos(piece.angle) * fall * 1.1,
          piece.position.y - fall * 2.4,
          piece.position.z + Math.sin(piece.angle) * fall * 1.1
        );
        piece.object.rotation.set(
          piece.rotation.x + Math.sin(piece.angle) * fall * 0.8,
          piece.rotation.y + fall * 0.35,
          piece.rotation.z + Math.cos(piece.angle) * fall * 0.8
        );
        const scale = 1 - fall * 0.45;
        piece.object.scale.set(piece.scale.x * scale, piece.scale.y * scale, piece.scale.z * scale);
        for (const { material, opacity } of piece.materials)
          material.opacity = opacity * (1 - fall);
        if (k < 1) complete = false;
      }
      if (complete) resolve();
      else requestAnimationFrame(step);
    })(t0);
  });
}

/* ---------- game flow ---------- */
let level = null, state = null, levels = [], busy = false, replaying = false, moves = 0;
let metricsVisible = false;

function updateHud() {
  const el = $("hud-status");
  el.className = state.status;
  el.textContent = state.status === "playing" ? "Playing" : "";
  $("hud-moves").textContent = `Moves: ${moves}`;
}
const setMsg = (t) => { $("msg").textContent = t; };
const setDisabled = (v) => document.querySelectorAll("button").forEach((b) => { b.disabled = v; });

async function announceResult(status) {
  const announcement = $("game-announcement");
  announcement.className = `game-announcement ${status}`;
  announcement.textContent = status === "won" ? "YOU WIN!" : "YOU FELL!";
  announcement.hidden = false;
  await sleep(2000);
  announcement.hidden = true;
}

async function loadLevel(id, { showMetrics = false } = {}) {
  const data = await api(`/api/level/${id}`);
  level = data.level;
  state = data.state;
  moves = 0;
  metricsVisible = showMetrics;
  buildBoard(level);
  renderState();
  setMsg("");
  showStats(null);
}

async function advanceLevel() {
  const index = levels.findIndex((item) => item.id === level.id);
  if (index < 0 || index + 1 >= levels.length) {
    setMsg("All levels completed!");
    return;
  }
  const nextLevel = levels[index + 1];
  $("level-select").value = nextLevel.id;
  await loadLevel(nextLevel.id);
}

async function act(action, ms = ROLL_MS) {
  if (busy || state.status !== "playing") return;
  busy = true;
  try {
    const { state: next } = await api("/api/move", { level_id: level.id, state, action });
    if (action !== "swap") await rollBlock(state.active, action, ms);
    state = next;
    moves += 1;
    renderState();
    if (next.status === "lost") {
      await Promise.all([
        dropBlock(state.active, action, 850),
        crumbleBoard(850),
        announceResult("lost"),
      ]);
    } else if (next.status === "won") {
      await Promise.all([
        dropBlock(state.active, action, 850),
        announceResult("won"),
      ]);
    }
    if (state.status === "lost") {
      await loadLevel(level.id);
    } else if (state.status === "won" && !replaying) {
      await advanceLevel();
    }
  } finally { busy = false; }
}

function showStats(s) {
  if (s) metricsVisible = true;
  $("metrics-panel").hidden = !metricsVisible;
  $("st-time").textContent = s ? `${s.search_time_ms} ms` : "-";
  $("st-nodes").textContent = s ? s.expanded_nodes : "-";
  $("st-mem").textContent = s ? `${s.peak_memory_kb} KB` : "-";
  $("st-len").textContent = s && s.solution_length != null ? s.solution_length : "-";
}

async function solve(algo, label) {
  if (busy || replaying) return;
  replaying = true;
  setDisabled(true);
  try {
    await loadLevel(level.id, { showMetrics: true });
    setMsg(`Solving with ${label}...`);
    const res = await api("/api/solve", { level_id: level.id, algo });
    showStats(res.stats);
    if (!res.path) { setMsg("No solution found."); return; }
    setMsg(`Solved in ${res.path.length} moves. Replaying...`);
    for (const a of res.path) { await act(a, REPLAY_ROLL_MS); await sleep(REPLAY_GAP_MS); }
    if (state.status === "won") {
      setMsg("Replay finished!");
      await advanceLevel();
    } else if (state.status === "playing") {
      setMsg("Replay ended on an unexpected state - check engine/solver.");
    }
  } finally { replaying = false; setDisabled(false); }
}

/* ---------- UI wiring ---------- */
const KEYS = { ArrowUp: "up", ArrowDown: "down", ArrowLeft: "left", ArrowRight: "right",
  w: "up", s: "down", a: "left", d: "right", W: "up", S: "down", A: "left", D: "right", " ": "swap" };
window.addEventListener("keydown", (e) => {
  const action = KEYS[e.key];
  if (!action || replaying || e.target.tagName === "SELECT") return;
  e.preventDefault();
  act(action);
});

document.querySelectorAll(".solvers button").forEach((b) =>
  b.addEventListener("click", () => solve(b.dataset.algo, b.textContent)));
$("btn-restart").addEventListener("click", () => !replaying && loadLevel(level.id));
$("btn-new").addEventListener("click", () => {
  if (replaying) return;
  const sel = $("level-select");
  sel.selectedIndex = (sel.selectedIndex + 1) % sel.options.length;
  loadLevel(sel.value);
});
$("level-select").addEventListener("change", (e) => !replaying && loadLevel(e.target.value));

(async function init() {
  resize();
  levels = await api("/api/levels");
  $("level-select").innerHTML = levels.map((l) => `<option value="${l.id}">${l.name}</option>`).join("");
  await loadLevel(levels[0].id);
})();
