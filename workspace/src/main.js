// Ashmouth — bootstrap.
//
// Blockout viewer at this stage: the whole map, its terrain, water and road
// network, drivable from outside through `window.game` so every capture is
// repeatable and comparable across sessions.
import * as THREE from 'three';
import { pass, mrt, output, normalView } from 'three/tsl';
import { RenderPipeline } from 'three/webgpu';
import { ao } from 'three/addons/tsl/display/GTAONode.js';
import { smaa } from 'three/addons/tsl/display/SMAANode.js';

import { Heightfield } from './world/heightfield.js';
import { Terrain } from './world/terrain.js';
import { buildRoads } from './world/roadmesh.js';

const canvas = document.getElementById('frame');

const renderer = new THREE.WebGPURenderer({ canvas, antialias: false });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.toneMapping = THREE.AgXToneMapping;
renderer.toneMappingExposure = 1.0;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
await renderer.init();

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, 1, 12000);

// ---------------------------------------------------------------------------
// Sun and sky. One sun, one direction, and an exposure that behaves like a
// camera — the placeholder gradient stands in until real captured environment
// lighting lands, which is the next lighting job and the biggest one.
// ---------------------------------------------------------------------------
const sun = new THREE.DirectionalLight(0xfff0dc, 3.4);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.camera.near = 1;
sun.shadow.camera.far = 3000;
const S = 700;
sun.shadow.camera.left = -S; sun.shadow.camera.right = S;
sun.shadow.camera.top = S; sun.shadow.camera.bottom = -S;
sun.shadow.bias = -0.0004;
scene.add(sun, sun.target);

const sky = new THREE.HemisphereLight(0x9dc0e8, 0x3d3a30, 0.55);
scene.add(sky);
// Haze grows with distance rather than sitting on everything equally. At
// 0.00028 the whole map washed to sky colour from altitude and the frame had no
// weather in it at all — just even grey.
scene.fog = new THREE.FogExp2(0xa9bed2, 0.00006);
scene.background = new THREE.Color(0xa9bed2);

let hour = 10.5;
function applyHour(h) {
  hour = ((h % 24) + 24) % 24;
  // 38°N, summer: the sun tracks from the north-east through south to
  // north-west, and its elevation drives both the colour and the sky.
  const t = (hour - 6) / 12;                 // 0 at sunrise, 1 at sunset
  const elev = Math.sin(Math.PI * t) * 62;   // degrees
  const azim = -120 + t * 240;
  const e = THREE.MathUtils.degToRad(Math.max(elev, -8));
  const a = THREE.MathUtils.degToRad(azim);
  const d = 1400;
  sun.position.set(Math.sin(a) * Math.cos(e) * d, Math.sin(e) * d, Math.cos(a) * Math.cos(e) * d);
  sun.position.add(sun.target.position);

  const day = THREE.MathUtils.clamp(Math.sin(Math.PI * t), 0, 1);
  const warm = Math.pow(1 - day, 2);
  sun.intensity = 3.6 * day;
  sun.color.setRGB(1.0, 0.94 - warm * 0.22, 0.86 - warm * 0.45);
  sky.intensity = 0.12 + 0.5 * day;
  const skyCol = new THREE.Color().setHSL(0.58, 0.35 + 0.1 * day, 0.06 + 0.62 * day);
  scene.background = skyCol;
  scene.fog.color.copy(skyCol);
}

// ---------------------------------------------------------------------------
const hf = await Heightfield.load('./world/');
const terrain = new Terrain(hf);
scene.add(terrain.group);

const roads = buildRoads(hf.manifest.roads, hf);
scene.add(roads);

// Water: a single plane at sea level for now. Real water — swell one way, wind
// chop another, neither repeating — is its own job.
const water = new THREE.Mesh(
  new THREE.PlaneGeometry(hf.worldW * 3, hf.worldH * 3, 1, 1),
  new THREE.MeshPhysicalMaterial({
    color: 0x16303f, roughness: 0.07, metalness: 0.0,
    transmission: 0.0, reflectivity: 0.6,
  })
);
water.rotation.x = -Math.PI / 2;
water.position.y = hf.seaLevel;
water.receiveShadow = false;
scene.add(water);

// ---------------------------------------------------------------------------
// Camera rig. A free-flying observer for now: the player controller is next
// session's work, and a blockout has to be flown and driven before it is judged.
// ---------------------------------------------------------------------------
const rig = {
  target: new THREE.Vector3(140, 20, 300),
  dist: 900, yaw: 0.7, pitch: -0.55,
};
function applyCamera() {
  const cp = Math.cos(rig.pitch), sp = Math.sin(rig.pitch);
  camera.position.set(
    rig.target.x + Math.sin(rig.yaw) * cp * rig.dist,
    rig.target.y - sp * rig.dist,
    rig.target.z + Math.cos(rig.yaw) * cp * rig.dist,
  );
  camera.lookAt(rig.target);
  sun.target.position.copy(rig.target);
  sun.target.updateMatrixWorld();
  applyHour(hour);
}

// ---------------------------------------------------------------------------
const scenePass = pass(scene, camera);
scenePass.setMRT(mrt({ output, normal: normalView }));
const colorNode = scenePass.getTextureNode('output');
const aoNode = ao(scenePass.getTextureNode('depth'), scenePass.getTextureNode('normal'), camera);
const post = new RenderPipeline(renderer);
post.outputNode = smaa(colorNode.mul(aoNode.getTextureNode().r));

let frames = 0;
function tick() {
  frames++;
  renderer.info.reset();       // does not auto-reset on this path
  terrain.update(camera.position);
  post.render();
  requestAnimationFrame(tick);
}

applyHour(hour);
applyCamera();
tick();

addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

// ---------------------------------------------------------------------------
// The outside interface. Everything the harness needs to put the camera somewhere
// specific and read back what it found, so captures are repeatable.
// ---------------------------------------------------------------------------
const districts = Object.fromEntries(hf.manifest.districts.map((d) => [d.key, d]));

window.game = {
  hf, terrain, scene, camera, renderer,
  get hour() { return hour; },
  get frames() { return frames; },
  setHour(h) { applyHour(h); applyCamera(); },
  /** Look at a district from a given distance and bearing. */
  goto(key, { dist = 700, yaw = 0.7, pitch = -0.5, height = null } = {}) {
    const d = districts[key];
    if (!d) return `no district '${key}' — have: ${Object.keys(districts).join(', ')}`;
    rig.target.set(d.x, height ?? (hf.heightAt(d.x, d.z) + 10), d.z);
    rig.dist = dist; rig.yaw = yaw; rig.pitch = pitch;
    applyCamera();
    return { key, x: d.x, z: d.z, ground: hf.heightAt(d.x, d.z) };
  },
  /** Put the camera at a world position at eye height, looking along a bearing. */
  stand(x, z, bearingDeg = 0, eye = 1.6) {
    rig.target.set(x, hf.heightAt(x, z) + eye, z);
    rig.dist = 0.01;
    rig.yaw = THREE.MathUtils.degToRad(bearingDeg);
    rig.pitch = 0;
    applyCamera();
    camera.position.set(x, hf.heightAt(x, z) + eye, z);
    const b = THREE.MathUtils.degToRad(bearingDeg);
    camera.lookAt(x + Math.sin(b) * 100, hf.heightAt(x, z) + eye, z + Math.cos(b) * 100);
    return { x, z, ground: hf.heightAt(x, z), slope: hf.slopeAt(x, z), land: hf.isLand(x, z) };
  },
  /** Whole map from above. */
  aerial(y = 4200) {
    rig.target.set(0, 0, -100); rig.dist = y; rig.pitch = -1.3; rig.yaw = 0;
    applyCamera();
    return { y };
  },
  info: () => ({
    backend: renderer.backend.isWebGPUBackend ? 'webgpu' : 'webgl2',
    hour: +hour.toFixed(2),
    chunks: terrain.chunkCount,
    calls: renderer.info.render.calls,
    tris: renderer.info.render.triangles,
    textures: renderer.info.memory.textures,
    geometries: renderer.info.memory.geometries,
    camera: [camera.position.x, camera.position.y, camera.position.z].map((v) => +v.toFixed(1)),
  }),
};
window.renderer = renderer;

console.log(`[boot] ${hf.manifest.name} — ${hf.manifest.stats.landAreaKm2} km² land, `
  + `${hf.manifest.roads.length} roads, backend ${window.game.info().backend}`);
