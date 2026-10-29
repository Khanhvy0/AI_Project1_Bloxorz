import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";

const $ = (id) => document.getElementById(id);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const ROLL_MS = 220,
  REPLAY_ROLL_MS = 160,
  REPLAY_GAP_MS = 100;

// Bảng màu Monument Valley / Pastel Zen
const COLORS = {
  floor: 0xf4eee4, // Đá cẩm thạch kem ấm
  pillar: 0xdfd3c3, // Cột đá sa thạch bên dưới
  fragile: 0xf2b880, // Cam đào pastel (Ô yếu)
  bridge: 0x84b59f, // Xanh ngọc lá xô thơm (Cầu)
  block: 0xe07a5f, // Cam đất nung Terracotta (Khối chính)
  blockActive: 0xf4a261, // Vàng cam nắng ấm khi chọn khối phân tách
  soft: 0x5c9ead, // Xanh lam gốm (Công tắc tròn)
  heavy: 0xd66853, // Đỏ san hô trầm (Công tắc chữ X)
  split: 0x9b8bb4, // Tím oải hương trầm (Công tắc phân tách)
};
let boardZoom = 1;

// Tạo bề mặt đá/gốm mịn có viền vát nhẹ kiểu Monument Valley
function createStoneTileTexture(baseHex, insetHex, accentHex) {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 128;
  const ctx = canvas.getContext("2d");

  ctx.fillStyle = baseHex;
  ctx.fillRect(0, 0, 128, 128);

  // Viền ngoài dịu nhẹ
  ctx.strokeStyle = insetHex;
  ctx.lineWidth = 6;
  ctx.strokeRect(3, 3, 122, 122);

  // Họa tiết hình học tối giản bên trong ô
  ctx.strokeStyle = accentHex;
  ctx.lineWidth = 2;
  ctx.strokeRect(18, 18, 92, 92);

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

const stoneTexture = createStoneTileTexture(
  "#f6f0e6",
  "#e5dccb",
  "rgba(180, 165, 145, 0.35)",
);
const fragileTexture = createStoneTileTexture(
  "#f7c59f",
  "#e8a574",
  "rgba(210, 120, 70, 0.35)",
);
const bridgeTexture = createStoneTileTexture(
  "#9ec5b2",
  "#7da893",
  "rgba(255, 255, 255, 0.45)",
);

const tileGeometry = new RoundedBoxGeometry(0.96, 0.22, 0.96, 4, 0.05);
const pillarGeometry = new RoundedBoxGeometry(0.84, 0.68, 0.84, 3, 0.04);
const persistentGeometries = new Set([tileGeometry, pillarGeometry]);
const persistentMaterials = new Set();

async function api(path, body, options = {}) {
  const res = await fetch(
    path,
    body
      ? {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
          ...options,
        }
      : options,
  );
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

/* ---------- scene ---------- */
const stage = $("stage");
const scene = new THREE.Scene();
// Để canvas trong suốt nhằm hiển thị nền Gradient hoàng hôn Pastel từ CSS
const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 200);
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
stage.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.06;
controls.maxPolarAngle = Math.PI / 2.05;

// Hệ thống ánh sáng ấm áp kiểu Pastel Zen
const hemiLight = new THREE.HemisphereLight(0xfffcf5, 0xd8c3a5, 1.25);
hemiLight.position.set(0, 20, 0);
scene.add(hemiLight);

const sun = new THREE.DirectionalLight(0xfff3e0, 1.35);
sun.position.set(10, 18, 12);
sun.castShadow = true;
sun.shadow.mapSize.width = 2048;
sun.shadow.mapSize.height = 2048;
sun.shadow.camera.near = 1;
sun.shadow.camera.far = 60;
const d = 16;
sun.shadow.camera.left = -d;
sun.shadow.camera.right = d;
sun.shadow.camera.top = d;
sun.shadow.camera.bottom = -d;
sun.shadow.bias = -0.0005;
scene.add(sun);

const fillLight = new THREE.DirectionalLight(0xcde4e8, 0.55);
fillLight.position.set(-10, 6, -10);
scene.add(fillLight);

// Hạt bụi nắng lơ lửng (Floating Sun Motes)
const motesCount = 45;
const motesPositions = new Float32Array(motesCount * 3);
for (let i = 0; i < motesCount; i++) {
  motesPositions[i * 3] = (Math.random() - 0.5) * 24;
  motesPositions[i * 3 + 1] = (Math.random() - 0.3) * 10;
  motesPositions[i * 3 + 2] = (Math.random() - 0.5) * 24;
}
const motesGeo = new THREE.BufferGeometry();
motesGeo.setAttribute("position", new THREE.BufferAttribute(motesPositions, 3));
const motesMat = new THREE.PointsMaterial({
  color: 0xffffff,
  size: 0.12,
  transparent: true,
  opacity: 0.55,
});
const sunMotes = new THREE.Points(motesGeo, motesMat);
scene.add(sunMotes);
persistentGeometries.add(motesGeo);
persistentMaterials.add(motesMat);

const boardGroup = new THREE.Group();
const blockGroup = new THREE.Group();
scene.add(boardGroup, blockGroup);
let goalGlowMats = [];

function resize() {
  const w = stage.clientWidth,
    h = stage.clientHeight;
  renderer.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
window.addEventListener("resize", resize);

(function loop(now = 0) {
  sunMotes.rotation.y = now * 0.00005;
  sunMotes.position.y = Math.sin(now * 0.0008) * 0.25;
  const glint =
    0.35 + 0.2 * Math.sin(now * 0.003) + 0.05 * Math.sin(now * 0.011);
  for (const m of goalGlowMats) m.emissiveIntensity = glint;
  controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(loop);
})();

/* ---------- board ---------- */
let bridgeTiles = {};

function addSwitch(sw) {
  const [r, c] = sw.pos;
  const g = new THREE.Group();
  g.userData.isSwitch = true;
  g.position.set(c, 0.025, r);
  const mat = (color) =>
    new THREE.MeshStandardMaterial({
      color,
      roughness: 0.4,
      metalness: 0.05,
    });
  if (sw.type === "soft") {
    // 1 đĩa tròn
    const mesh = new THREE.Mesh(
      new THREE.CylinderGeometry(0.28, 0.3, 0.06, 28),
      mat(COLORS.soft),
    );
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    g.add(mesh);
  } else if (sw.type === "heavy") {
    // chữ X
    for (const a of [Math.PI / 4, -Math.PI / 4]) {
      const bar = new THREE.Mesh(
        new THREE.BoxGeometry(0.72, 0.06, 0.15),
        mat(COLORS.heavy),
      );
      bar.rotation.y = a;
      bar.castShadow = true;
      bar.receiveShadow = true;
      g.add(bar);
    }
  } else {
    // split: 2 đĩa nhỏ "( )"
    for (const dx of [-0.21, 0.21]) {
      const d = new THREE.Mesh(
        new THREE.CylinderGeometry(0.12, 0.13, 0.06, 20),
        mat(COLORS.split),
      );
      d.position.x = dx;
      d.castShadow = true;
      d.receiveShadow = true;
      g.add(d);
    }
  }
  boardGroup.add(g);
}

function addGoalHole(r, c) {
  // Kích thước lấy theo ô thường để đồng bộ:
  //   ô: tileGeometry 0.96 x 0.22 x 0.96 (tâm y = -0.11), chân cột: pillarGeometry 0.84 x 0.68 x 0.84 (tâm y = -0.55)
  const TILE = 0.96,
    TILE_H = 0.22,
    TILE_Y = -0.11;
  const PILLAR = 0.84,
    PILLAR_H = 0.68,
    PILLAR_Y = -0.55;
  const HOLE = 0.87; // cạnh miệng hố
  const RIM = (TILE - HOLE) / 2; // bề rộng khung đá quanh miệng hố (0.15)
  const EDGE = HOLE / 2 + RIM / 2; // khoảng cách từ tâm ô tới tâm thanh khung
  const WALL = (PILLAR - HOLE) / 2; // độ dày thành chân cột rỗng (0.09)
  const WEDGE = HOLE / 2 + WALL / 2;
  const DEPTH = 0.88; // độ sâu hố = tới đáy chân cột
  const OVERLAP = 0.03; // thanh bên chồng nhẹ vào thanh trên/dưới để không lộ khe ở góc

  const goalGroup = new THREE.Group();
  goalGroup.position.set(c, 0, r);

  const stoneMat = new THREE.MeshStandardMaterial({
    color: 0xf6f0e6, // cùng màu nền với stoneTexture của ô thường
    roughness: 0.65,
    metalness: 0.02,
  });
  const pillarMat = new THREE.MeshStandardMaterial({
    color: COLORS.pillar,
    roughness: 0.85,
    metalness: 0.02,
  });
  const goldMat = new THREE.MeshStandardMaterial({
    color: 0xe09f3e,
    emissive: 0xe09f3e,
    emissiveIntensity: 0.35, // hơi phát sáng để nổi bật
    roughness: 0.3,
    metalness: 0.3,
  });
  goalGlowMats.push(goldMat);

  const rbox = (w, h, d, radius = 0.04) =>
    new RoundedBoxGeometry(w, h, d, 4, radius);
  const place = (geo, mat, x, y, z, shadow = true) => {
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.set(x, y, z);
    mesh.castShadow = shadow;
    mesh.receiveShadow = true;
    goalGroup.add(mesh);
    return mesh;
  };

  // 1. Khung đá: ngoài cùng 0.96 x 0.96 x 0.22, đúng kích thước ô thường
  const barNS = rbox(TILE, TILE_H, RIM, 0.05);
  const barEW = rbox(RIM, TILE_H, HOLE + 2 * OVERLAP, 0.03);
  place(barNS, stoneMat, 0, TILE_Y, -EDGE);
  place(barNS, stoneMat, 0, TILE_Y, EDGE);
  place(barEW, stoneMat, -EDGE, TILE_Y, 0);
  place(barEW, stoneMat, EDGE, TILE_Y, 0);

  // 2. Chân cột rỗng: ngoài 0.84 x 0.68 x 0.84 như chân cột ô thường, bên trong chừa giếng
  const wallNS = rbox(PILLAR, PILLAR_H, WALL, 0.02);
  const wallEW = rbox(WALL, PILLAR_H, HOLE, 0.02);
  place(wallNS, pillarMat, 0, PILLAR_Y, -WEDGE);
  place(wallNS, pillarMat, 0, PILLAR_Y, WEDGE);
  place(wallEW, pillarMat, -WEDGE, PILLAR_Y, 0);
  place(wallEW, pillarMat, WEDGE, PILLAR_Y, 0);

  // 3. Lòng hố: hộp nhìn từ bên trong, tô gradient từ nâu xám (miệng) xuống gần đen (đáy) tạo cảm giác sâu
  const shaftGeo = new THREE.BoxGeometry(HOLE - 0.005, DEPTH, HOLE - 0.005);
  const pos = shaftGeo.attributes.position;
  const topColor = new THREE.Color(0x7d6c5a),
    bottomColor = new THREE.Color(0x1d1612),
    tmp = new THREE.Color();
  const colors = new Float32Array(pos.count * 3);
  for (let i = 0; i < pos.count; i++) {
    const t = (DEPTH / 2 - pos.getY(i)) / DEPTH; // 0 ở miệng, 1 ở đáy
    tmp.copy(topColor).lerp(bottomColor, t);
    colors.set([tmp.r, tmp.g, tmp.b], i * 3);
  }
  shaftGeo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  const shaft = new THREE.Mesh(
    shaftGeo,
    new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide }),
  );
  shaft.position.y = -DEPTH / 2;
  goalGroup.add(shaft);

  // 4. Viền vàng đồng nằm sát miệng hố (đặc điểm nhận biết chính của ô đích)
  const RIM_GOLD = 0.045,
    RIM_Y = -0.026, // dày 0.06: nhô lên 0.004 trên mặt ô, chìm xuống phủ kín phần mép khung bo tròn
    RIM_H = 0.06,
    RIM_EDGE = HOLE / 2 + RIM_GOLD / 2;
  const goldNS = new THREE.BoxGeometry(HOLE + 2 * RIM_GOLD, RIM_H, RIM_GOLD);
  const goldEW = new THREE.BoxGeometry(RIM_GOLD, RIM_H, HOLE);
  place(goldNS, goldMat, 0, RIM_Y, -RIM_EDGE, false);
  place(goldNS, goldMat, 0, RIM_Y, RIM_EDGE, false);
  place(goldEW, goldMat, -RIM_EDGE, RIM_Y, 0, false);
  place(goldEW, goldMat, RIM_EDGE, RIM_Y, 0, false);

  // 5. Ốp vàng liền một dải từ miệng hố xuống LINER_H, lấp kín vùng giữa hai viền
  const LINER_H = 0.12, // độ sâu lớp ốp vàng, tăng lên nếu muốn vàng sâu hơn
    LINER_Y = -LINER_H / 2,
    LINER_OFF = HOLE / 2 - 0.008;
  const linerNS = new THREE.BoxGeometry(HOLE - 0.02, LINER_H, 0.01);
  const linerEW = new THREE.BoxGeometry(0.01, LINER_H, HOLE - 0.01);
  place(linerNS, goldMat, 0, LINER_Y, -LINER_OFF, false);
  place(linerNS, goldMat, 0, LINER_Y, LINER_OFF, false);
  place(linerEW, goldMat, -LINER_OFF, LINER_Y, 0, false);
  place(linerEW, goldMat, LINER_OFF, LINER_Y, 0, false);

  boardGroup.add(goalGroup);
}

function clearGroup(group) {
  const geometries = new Set();
  const materials = new Set();
  group.traverse((object) => {
    if (object.geometry) geometries.add(object.geometry);
    if (object.material) {
      for (const material of Array.isArray(object.material)
        ? object.material
        : [object.material])
        materials.add(material);
    }
  });
  geometries.forEach((geometry) => {
    if (!persistentGeometries.has(geometry)) geometry.dispose();
  });
  materials.forEach((material) => {
    if (!persistentMaterials.has(material)) material.dispose();
  });
  group.clear();
}

function buildBoard(level) {
  clearGroup(boardGroup);
  goalGlowMats = [];
  bridgeTiles = {};
  const rows = level.grid.length,
    cols = level.grid[0].length;
  const bridgeOf = {};
  for (const [id, b] of Object.entries(level.bridges || {}))
    for (const [r, c] of b.cells) bridgeOf[`${r},${c}`] = id;

  const floorMaterial = new THREE.MeshStandardMaterial({
    color: 0xffffff,
    map: stoneTexture,
    roughness: 0.65,
    metalness: 0.02,
  });

  const fragileMaterial = new THREE.MeshStandardMaterial({
    color: 0xffffff,
    map: fragileTexture,
    roughness: 0.55,
    metalness: 0.04,
  });

  const pillarMaterial = new THREE.MeshStandardMaterial({
    color: COLORS.pillar,
    roughness: 0.85,
    metalness: 0.02,
  });

  level.grid.forEach((line, r) =>
    [...line].forEach((ch, c) => {
      if (ch === "." || ch === " ") return;
      if (ch === "g") {
        addGoalHole(r, c);
        return;
      }

      let mat;
      if (ch === "o") {
        mat = floorMaterial;
      } else if (ch === "f") {
        mat = fragileMaterial;
      } else if (ch === "b") {
        mat = new THREE.MeshStandardMaterial({
          color: 0xffffff,
          map: bridgeTexture,
          transparent: true,
          roughness: 0.5,
        });
      } else {
        mat = floorMaterial;
      }

      const tile = new THREE.Mesh(tileGeometry, mat);
      tile.position.set(c, -0.11, r);
      tile.receiveShadow = true;
      tile.castShadow = true;
      boardGroup.add(tile);

      // Chân cột kiến trúc bên dưới các ô đá cố định tạo vẻ đẹp Monument Valley
      if (ch === "o") {
        const pillar = new THREE.Mesh(pillarGeometry, pillarMaterial);
        pillar.position.set(c, -0.55, r);
        pillar.receiveShadow = true;
        boardGroup.add(pillar);
      }

      if (ch === "b") (bridgeTiles[bridgeOf[`${r},${c}`]] ||= []).push(tile);
    }),
  );

  (level.switches || []).forEach(addSwitch);

  const cx = (cols - 1) / 2,
    cz = (rows - 1) / 2;
  controls.target.set(cx, 0, cz);
  sunMotes.position.set(cx, 0, cz);

  const verticalHalfFov = THREE.MathUtils.degToRad(camera.fov) / 2;
  const horizontalHalfFov = Math.atan(
    Math.tan(verticalHalfFov) * camera.aspect,
  );
  const halfFov = Math.min(verticalHalfFov, horizontalHalfFov);
  const boardRadius = Math.hypot(cols / 2, rows / 2, 1);
  const distance = (boardRadius / Math.sin(halfFov)) * 0.9;
  const target = controls.target;
  camera.position.set(
    target.x + (distance * 0.37) / boardZoom,
    target.y + (distance * 0.65) / boardZoom,
    target.z + (distance * 0.65) / boardZoom,
  );
  controls.update();
}

function adjustBoardZoom(change) {
  const previousZoom = boardZoom;
  boardZoom = Math.min(
    2,
    Math.max(0.5, Math.round((boardZoom + change) * 10) / 10),
  );
  if (boardZoom === previousZoom) return;
  const offset = camera.position.clone().sub(controls.target);
  camera.position
    .copy(controls.target)
    .addScaledVector(offset, previousZoom / boardZoom);
  controls.update();
}

function setBridges(bridges) {
  for (const [id, tiles] of Object.entries(bridgeTiles))
    tiles.forEach((t) => {
      t.material.opacity = bridges[id] ? 1 : 0.18;
    });
}

/* ---------- block ---------- */
let blockMeshes = [];

function blockBox(cells, multi) {
  const rs = cells.map((c) => c[0]),
    cs = cells.map((c) => c[1]);
  const r0 = Math.min(...rs),
    r1 = Math.max(...rs),
    c0 = Math.min(...cs),
    c1 = Math.max(...cs);
  const h = cells.length === 1 && !multi ? 2 : 1; // đứng cao 2; nằm hoặc khối lập phương cao 1
  return { r0, r1, c0, c1, h, w: c1 - c0 + 1, d: r1 - r0 + 1 };
}

function renderState() {
  clearGroup(blockGroup);
  blockMeshes = [];
  const multi = state.blocks.length > 1;
  state.blocks.forEach((cells, i) => {
    const b = blockBox(cells, multi);
    const isActive = multi && i === state.active;
    const mat = new THREE.MeshPhysicalMaterial({
      color: isActive ? COLORS.blockActive : COLORS.block,
      roughness: 0.38,
      metalness: 0.04,
      clearcoat: 0.25,
      clearcoatRoughness: 0.4,
    });
    if (isActive) {
      mat.emissive = new THREE.Color(0xf4a261);
      mat.emissiveIntensity = 0.22;
    }

    const geom = new RoundedBoxGeometry(
      b.w * 0.95,
      b.h * 0.98,
      b.d * 0.95,
      5,
      0.07,
    );
    const mesh = new THREE.Mesh(geom, mat);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
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
  const xc = (b.c0 + b.c1) / 2,
    zc = (b.r0 + b.r1) / 2;
  const cfg = {
    right: { p: [b.c1 + 0.5, 0, zc], axis: "z", a: -Math.PI / 2 },
    left: { p: [b.c0 - 0.5, 0, zc], axis: "z", a: Math.PI / 2 },
    down: { p: [xc, 0, b.r1 + 0.5], axis: "x", a: Math.PI / 2 },
    up: { p: [xc, 0, b.r0 - 0.5], axis: "x", a: -Math.PI / 2 },
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
      materials.push({
        material,
        transparent: material.transparent,
        opacity: material.opacity,
      });
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
        initialRotation.z + tilt[2] * k,
      );
      const scale = 1 - fall * 0.88;
      mesh.scale.set(
        initialScale.x * scale,
        initialScale.y * scale,
        initialScale.z * scale,
      );
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
      const list = Array.isArray(part.material)
        ? part.material
        : [part.material];
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
          piece.position.z + Math.sin(piece.angle) * fall * 1.1,
        );
        piece.object.rotation.set(
          piece.rotation.x + Math.sin(piece.angle) * fall * 0.8,
          piece.rotation.y + fall * 0.35,
          piece.rotation.z + Math.cos(piece.angle) * fall * 0.8,
        );
        const scale = 1 - fall * 0.45;
        piece.object.scale.set(
          piece.scale.x * scale,
          piece.scale.y * scale,
          piece.scale.z * scale,
        );
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
let level = null,
  state = null,
  levels = [],
  busy = false,
  replaying = false,
  moves = 0;
let metricsVisible = false;
let solveAbortController = null,
  activeSolveId = null,
  stopRequested = false;

function updateHud() {
  const el = $("hud-status");
  el.className = state.status;
  el.textContent =
    state.status === "playing" ? "Playing" : state.status.toUpperCase();
  $("hud-moves").textContent = `Moves: ${moves}`;
}
const setMsg = (t) => {
  $("msg").textContent =
    t || "Select a solver or use keyboard to guide the block.";
};
const setDisabled = (v) =>
  document
    .querySelectorAll("button:not(.solve-prompt-action):not(#btn-solve-stop)")
    .forEach((b) => {
      b.disabled = v;
    });

function askAfterSolve() {
  const prompt = $("solve-prompt");
  prompt.hidden = false;
  return new Promise((resolve) => {
    const finish = (choice) => {
      prompt.hidden = true;
      $("btn-solve-next").removeEventListener("click", continueClick);
      $("btn-solve-replay").removeEventListener("click", replayClick);
      resolve(choice);
    };
    const continueClick = () => finish("next");
    const replayClick = () => finish("replay");
    $("btn-solve-next").addEventListener("click", continueClick);
    $("btn-solve-replay").addEventListener("click", replayClick);
    $("btn-solve-next").focus();
  });
}

async function announceResult(status) {
  const announcement = $("game-announcement");
  announcement.className = `game-announcement ${status}`;
  announcement.textContent =
    status === "won" ? "You Win!" : "You Fell!";
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
  syncCustomDropdown(id);
}

async function advanceLevel() {
  const index = levels.findIndex((item) => item.id === level.id);
  if (index < 0 || index + 1 >= levels.length) {
    setMsg("All chapters completed!");
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
    const { state: next } = await api("/api/move", {
      level_id: level.id,
      state,
      action,
    });
    if (action !== "swap" && action !== "switch") await rollBlock(state.active, action, ms);
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
  } finally {
    busy = false;
  }
}

function showStats(s) {
  if (s) metricsVisible = true;
  $("metrics-panel").hidden = !metricsVisible;
  $("st-time").textContent = s ? `${Number(s.search_time_ms).toFixed(4)} ms` : "-";
  $("st-nodes").textContent = s ? s.expanded_nodes.toLocaleString() : "-";
  $("st-mem").textContent = s ? `${s.peak_memory_kb} KB` : "-";
  $("st-len").textContent =
    s && s.solution_length != null ? `${s.solution_length} moves` : "-";
}

async function solve(algo, label) {
  if (busy || replaying) return;
  replaying = true;
  stopRequested = false;
  activeSolveId = crypto.randomUUID();
  solveAbortController = new AbortController();
  $("btn-solve-stop").hidden = false;
  $("level-select").disabled = true;
  if ($("dropdown-trigger")) $("dropdown-trigger").disabled = true;
  setDisabled(true);
  try {
    await loadLevel(level.id, { showMetrics: true });
    setMsg(`Contemplating path with ${label}...`);
    const res = await api(
      "/api/solve",
      {
        level_id: level.id,
        algo,
        solve_id: activeSolveId,
      },
      { signal: solveAbortController.signal },
    );
    activeSolveId = null;
    showStats(res.stats);
    if (!res.path) {
      setMsg("No solution found for this monument.");
      return;
    }
    setMsg(`Solved in ${res.path.length} moves. Guiding block...`);
    for (const a of res.path) {
      if (stopRequested) break;
      await act(a, REPLAY_ROLL_MS);
      if (!stopRequested) await sleep(REPLAY_GAP_MS);
    }
    if (stopRequested) {
      setMsg("Solver stopped. Choose another level or solver.");
      return;
    }
    if (state.status === "won") {
      setMsg("Replay finished!");
      $("btn-solve-stop").hidden = true;
      const choice = await askAfterSolve();
      if (choice === "next") await advanceLevel();
      else await loadLevel(level.id);
    } else if (state.status === "playing") {
      setMsg("Replay ended on an unexpected state - check engine/solver.");
    }
  } catch (error) {
    if (stopRequested) {
      setMsg("Solver stopped. Choose another level or solver.");
    } else {
      throw error;
    }
  } finally {
    activeSolveId = null;
    solveAbortController = null;
    $("btn-solve-stop").hidden = true;
    $("level-select").disabled = false;
    if ($("dropdown-trigger")) $("dropdown-trigger").disabled = false;
    replaying = false;
    setDisabled(false);
  }
}

async function stopSolver() {
  if (!replaying || stopRequested) return;
  stopRequested = true;
  const solveId = activeSolveId;
  if (solveId) {
    try {
      await api("/api/solve/cancel", { solve_id: solveId });
    } catch (error) {
      solveAbortController.abort();
      setMsg(`Could not stop solver cleanly: ${error.message}`);
      return;
    }
    solveAbortController.abort();
  }
  setMsg("Stopping solver...");
}

/* ---------- UI wiring ---------- */
const KEYS = {
  ArrowUp: "up",
  ArrowDown: "down",
  ArrowLeft: "left",
  ArrowRight: "right",
  w: "up",
  s: "down",
  a: "left",
  d: "right",
  W: "up",
  S: "down",
  A: "left",
  D: "right",
  " ": "swap",
};
window.addEventListener("keydown", (e) => {
  const action = KEYS[e.key];
  if (!action || replaying || e.target.tagName === "SELECT") return;
  e.preventDefault();
  act(action);
});

document.querySelectorAll(".solvers button").forEach((b) =>
  b.addEventListener("click", () => {
    const title = b.querySelector(".algo-title")?.textContent || b.textContent;
    solve(b.dataset.algo, title);
  }),
);
$("btn-restart").addEventListener(
  "click",
  () => !replaying && loadLevel(level.id),
);
$("btn-solve-stop").addEventListener("click", stopSolver);
$("btn-board-smaller").addEventListener("click", () => adjustBoardZoom(-0.1));
$("btn-board-larger").addEventListener("click", () => adjustBoardZoom(0.1));
$("btn-new").addEventListener("click", () => {
  if (replaying) return;
  const sel = $("level-select");
  sel.selectedIndex = (sel.selectedIndex + 1) % sel.options.length;
  loadLevel(sel.value);
});
$("level-select").addEventListener(
  "change",
  (e) => !replaying && loadLevel(e.target.value),
);

/* ---------- Custom Level Dropdown (10 levels visible, scroll to see all) ---------- */
function closeDropdown() {
  const menu = $("dropdown-menu");
  const trigger = $("dropdown-trigger");
  if (menu) menu.hidden = true;
  if (trigger) trigger.setAttribute("aria-expanded", "false");
}

function openDropdown() {
  if (replaying) return;
  const menu = $("dropdown-menu");
  const trigger = $("dropdown-trigger");
  if (menu) menu.hidden = false;
  if (trigger) trigger.setAttribute("aria-expanded", "true");

  if (level) {
    const listContainer = $("dropdown-level-list");
    const activeEl = listContainer?.querySelector(`.dropdown-item[data-id="${level.id}"]`);
    if (activeEl) {
      activeEl.scrollIntoView({ block: "nearest" });
    }
  }
}

function toggleDropdown() {
  const menu = $("dropdown-menu");
  if (!menu || menu.hidden) {
    openDropdown();
  } else {
    closeDropdown();
  }
}

function renderCustomDropdown() {
  if (!levels || levels.length === 0) return;
  const listContainer = $("dropdown-level-list");
  if (!listContainer) return;

  listContainer.innerHTML = levels
    .map((l) => {
      const isActive = level && l.id === level.id;
      return `<div class="dropdown-item ${isActive ? "active" : ""}" data-id="${l.id}">${l.name}</div>`;
    })
    .join("");

  listContainer.querySelectorAll(".dropdown-item").forEach((item) => {
    item.addEventListener("click", async (e) => {
      e.stopPropagation();
      if (replaying) return;
      const id = item.dataset.id;
      closeDropdown();
      $("level-select").value = id;
      await loadLevel(id);
    });
  });
}

function syncCustomDropdown(levelId) {
  if (!levels || levels.length === 0) return;
  const idx = levels.findIndex((l) => l.id === levelId);
  if (idx >= 0) {
    const triggerLabel = $("dropdown-current-level");
    if (triggerLabel) {
      triggerLabel.textContent = levels[idx].name;
    }
    const listContainer = $("dropdown-level-list");
    if (listContainer) {
      listContainer.querySelectorAll(".dropdown-item").forEach((item) => {
        const isActive = item.dataset.id === levelId;
        item.classList.toggle("active", isActive);
        if (isActive) {
          item.scrollIntoView({ block: "nearest" });
        }
      });
    }
  }
}

function initCustomDropdown() {
  renderCustomDropdown();

  const trigger = $("dropdown-trigger");
  if (trigger) {
    trigger.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleDropdown();
    });
  }

  document.addEventListener("click", (e) => {
    const wrap = $("custom-level-dropdown");
    if (wrap && !wrap.contains(e.target)) {
      closeDropdown();
    }
  });

  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeDropdown();
    }
  });
}

(async function init() {
  resize();
  levels = await api("/api/levels");
  $("level-select").innerHTML = levels
    .map((l) => `<option value="${l.id}">${l.name}</option>`)
    .join("");
  initCustomDropdown();
  await loadLevel(levels[0].id);
})();
