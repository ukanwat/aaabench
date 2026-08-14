// INSTRUMENT — how many point lights can this renderer actually afford?
//
// This is the question that decides whether a night city is possible with stock
// three.js lighting or whether it needs a clustered/tiled light system written by
// hand. Answering it late turns the night pass into a rewrite, so it gets answered
// before the city exists.
//
//   probe.html?lights=128&shadows=0
//
// Read the p50/p99 from `shot.py --frames 300`, not the average.
import * as THREE from 'three';

const q = new URLSearchParams(location.search);
const N = parseInt(q.get('lights') ?? '64', 10);
const SHADOWS = q.get('shadows') === '1';

const canvas = document.getElementById('frame');
const renderer = new THREE.WebGPURenderer({ canvas, antialias: false });
renderer.setPixelRatio(1);
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.toneMapping = THREE.AgXToneMapping;
renderer.shadowMap.enabled = SHADOWS;
await renderer.init();

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x04060a);
const camera = new THREE.PerspectiveCamera(60, innerWidth / innerHeight, 0.1, 500);
camera.position.set(0, 6, 40);

// A street canyon: two facades and a road. Roughly the geometry a night frame has
// to survive — big flat surfaces that every light in range touches.
const roadMat = new THREE.MeshPhysicalMaterial({ color: 0x17181b, roughness: 0.45 });
const wallMat = new THREE.MeshPhysicalMaterial({ color: 0x6e6a63, roughness: 0.85 });
const road = new THREE.Mesh(new THREE.BoxGeometry(16, 0.2, 400), roadMat);
road.receiveShadow = SHADOWS;
scene.add(road);
for (const side of [-1, 1]) {
  const wall = new THREE.Mesh(new THREE.BoxGeometry(2, 24, 400), wallMat);
  wall.position.set(side * 9, 12, 0);
  wall.castShadow = SHADOWS; wall.receiveShadow = SHADOWS;
  scene.add(wall);
}

// Street lamps down both sides, warm sodium on one, cold LED on the other —
// the real mix on a street that got half-upgraded.
const lights = [];
const bulbGeo = new THREE.SphereGeometry(0.12, 8, 6);
for (let i = 0; i < N; i++) {
  const side = i % 2 === 0 ? -1 : 1;
  const z = -190 + (i / N) * 380;
  const warm = side < 0;
  const colour = warm ? 0xffb35c : 0xd8e4ff;
  const l = new THREE.PointLight(colour, 22, 26, 2);
  l.position.set(side * 7, 5.2, z);
  if (SHADOWS) { l.castShadow = true; l.shadow.mapSize.set(256, 256); }
  scene.add(l);
  lights.push(l);
  const bulb = new THREE.Mesh(bulbGeo, new THREE.MeshBasicMaterial({ color: colour }));
  bulb.position.copy(l.position);
  scene.add(bulb);
}

let frames = 0, drawSum = 0;
function tick() {
  frames++;
  renderer.info.reset();
  camera.position.z = 60 - ((performance.now() * 0.004) % 240);
  camera.lookAt(0, 4, camera.position.z - 30);
  renderer.render(scene, camera);
  drawSum += renderer.info.render.calls;
  requestAnimationFrame(tick);
}
tick();

window.probe = {
  lights: N,
  shadows: SHADOWS,
  info: () => ({
    lights: N, shadows: SHADOWS, frames,
    avgDraws: Math.round(drawSum / Math.max(1, frames)),
    tris: renderer.info.render.triangles,
    backend: renderer.backend.isWebGPUBackend ? 'webgpu' : 'webgl2',
  }),
};
console.log(`[probe] ${N} point lights, shadows=${SHADOWS}`);
