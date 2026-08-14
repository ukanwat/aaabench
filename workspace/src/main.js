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
import { denoise } from 'three/addons/tsl/display/DenoiseNode.js';

import { Heightfield } from './world/heightfield.js';
import { Terrain } from './world/terrain.js';
import { buildRoads } from './world/roadmesh.js';
import { Sky } from './world/sky.js';

const canvas = document.getElementById('frame');

const renderer = new THREE.WebGPURenderer({ canvas, antialias: false });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.toneMapping = THREE.AgXToneMapping;
renderer.toneMappingExposure = 0.70;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
await renderer.init();

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, 1, 30000);

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

// A hemisphere light is a constant, not a fill. Environment lighting comes from
// the sky itself — see src/world/sky.js for why that distinction is the whole
// difference between shaded and empty.
const sky = new Sky(renderer, scene);
// The Preetham sky is bright in linear units and PMREM keeps that brightness,
// so the probe has to be scaled against the directional light or the ground
// blows out. These two numbers and the exposure are one system; they get tuned
// together against a frame, not separately.
scene.environmentIntensity = 0.08;

// Haze grows with distance rather than sitting on everything equally. At
// 0.00028 the whole map washed to sky colour from altitude and the frame had no
// weather in it at all — just even grey.
scene.fog = new THREE.FogExp2(0xa9bed2, 0.00006);

const _sunDir = new THREE.Vector3();
const _fogDay = new THREE.Color();
const _fogLow = new THREE.Color();
const _fogNight = new THREE.Color();
let hour = 10.5;

// Ashmouth sits at 38°N. The sun's position is computed from real solar
// geometry — declination, hour angle, latitude — rather than from a half-sine
// between 06:00 and 18:00.
//
// That earlier model had a hard on/off at both ends: at 05:30 and at 18:30 the
// sun was simply switched off, so dawn, the low warm hour, dusk and night were
// four identical dead grey frames. The golden hour did not exist and neither
// did twilight — and dusk, when the sun goes and the lamps come on, is the
// moment a city looks most alive and the hardest state to get right. It cannot
// be got right if it is not in the model at all.
const LATITUDE = 38.0;
const DECLINATION = 16.5;              // late summer

function solarPosition(h) {
  const lat = THREE.MathUtils.degToRad(LATITUDE);
  const dec = THREE.MathUtils.degToRad(DECLINATION);
  const H = THREE.MathUtils.degToRad((h - 12) * 15);
  const sinElev = Math.sin(lat) * Math.sin(dec) + Math.cos(lat) * Math.cos(dec) * Math.cos(H);
  const elev = Math.asin(THREE.MathUtils.clamp(sinElev, -1, 1));
  const cosAz = (Math.sin(dec) - Math.sin(lat) * sinElev) / (Math.cos(lat) * Math.cos(elev));
  let az = Math.acos(THREE.MathUtils.clamp(cosAz, -1, 1));
  if (H > 0) az = 2 * Math.PI - az;    // afternoon: sun is west of south
  return { elev, az };
}

function applyHour(h) {
  hour = ((h % 24) + 24) % 24;
  const { elev, az } = solarPosition(hour);

  // Direction to the sun. Azimuth is measured from north, clockwise; north is −Z.
  const ce = Math.cos(elev);
  _sunDir.set(Math.sin(az) * ce, Math.sin(elev), -Math.cos(az) * ce).normalize();
  sun.position.copy(_sunDir).multiplyScalar(1500).add(sun.target.position);

  const elevDeg = THREE.MathUtils.radToDeg(elev);

  // Direct sun fades out through the last few degrees rather than switching
  // off, and reddens hard as it does — that reddening IS the golden hour, and
  // it comes from the path length through the atmosphere, so it is a function
  // of elevation and nothing else.
  const above = THREE.MathUtils.smoothstep(elevDeg, -1.2, 7.0);
  const low = 1 - THREE.MathUtils.smoothstep(elevDeg, 0.0, 22.0);
  sun.intensity = 4.2 * above;
  sun.color.setRGB(1.0, 0.96 - low * 0.30, 0.90 - low * 0.62);

  // Twilight: the sky stays lit well after the sun has gone. Civil twilight is
  // roughly 0° to −6°, and there is usable light down to about −12°.
  const twilight = THREE.MathUtils.smoothstep(elevDeg, -12.0, 2.0);
  scene.environmentIntensity = 0.006 + 0.074 * twilight;
  renderer.toneMappingExposure = 0.70 + 0.55 * (1 - twilight);

  sky.setSun(_sunDir);

  // Haze takes its colour from the horizon so distance agrees with the sky
  // rather than being a separate grey laid over it.
  //
  // Interpolated between two explicit colours, NOT by moving the hue: rotating
  // hue from blue (0.58) toward orange (0.07) passes through green, and at low
  // sun it parked on 0.33 and turned the whole sky sage. Hue is a circle and
  // lerping it takes whichever way round the numbers happen to go.
  _fogDay.setRGB(0.55, 0.66, 0.80);
  _fogLow.setRGB(0.86, 0.52, 0.28);
  _fogNight.setRGB(0.05, 0.07, 0.12);
  scene.fog.color.copy(_fogDay).lerp(_fogLow, low * above);
  scene.fog.color.lerp(_fogNight, 1 - twilight);
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
const depthNode = scenePass.getTextureNode('depth');
const normalNode = scenePass.getTextureNode('normal');

// GTAO's raw output carries its magic-square sampling noise, which reads as a
// heavy ordered stipple across the whole frame — it is not a texture and not a
// dither, it is the AO asking to be filtered. It needs either TRAA or an
// explicit denoise; this takes the denoise.
const aoNode = ao(depthNode, normalNode, camera);
aoNode.samples.value = 16;
aoNode.scale.value = 1.0;
const aoDenoised = denoise(aoNode.getTextureNode(), depthNode, normalNode, camera);

const post = new RenderPipeline(renderer);
post.outputNode = smaa(colorNode.mul(aoDenoised.r));

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
  setEnv(i) { scene.environmentIntensity = i; return i; },
  setExposure(e) { renderer.toneMappingExposure = e; return e; },
  setSunIntensity(i) { sun.intensity = i; return i; },
  /** Mean linear luminance of the frame — a sanity number for exposure, never
   *  the verdict. A frame can score in range and read flatter than before. */
  get exposure() { return renderer.toneMappingExposure; },
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
