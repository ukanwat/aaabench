// Bootstrap. Smoke test for now: prove the WebGPU path, the post chain and the
// material model actually run in this browser before any city exists.
import * as THREE from 'three';
import { pass, mrt, output, normalView } from 'three/tsl';
import { RenderPipeline } from 'three/webgpu';
import { ao } from 'three/addons/tsl/display/GTAONode.js';
import { bloom } from 'three/addons/tsl/display/BloomNode.js';
import { smaa } from 'three/addons/tsl/display/SMAANode.js';

const canvas = document.getElementById('frame');

const renderer = new THREE.WebGPURenderer({ canvas, antialias: false });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.toneMapping = THREE.AgXToneMapping;
renderer.toneMappingExposure = 1.0;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

await renderer.init();

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 4000);
camera.position.set(4, 2.2, 6);
camera.lookAt(0, 1, 0);

// --- a sun and a sky, so the material test means something -------------------
const sun = new THREE.DirectionalLight(0xfff2e0, 3.2);
sun.position.set(-30, 40, 20);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.camera.left = -20; sun.shadow.camera.right = 20;
sun.shadow.camera.top = 20; sun.shadow.camera.bottom = -20;
sun.shadow.camera.far = 120;
sun.shadow.bias = -0.0006;
scene.add(sun);

const sky = new THREE.HemisphereLight(0x8fb4e8, 0x3a3630, 0.7);
scene.add(sky);
scene.background = new THREE.Color(0x9fbcd8);

// ground
const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(200, 200),
  new THREE.MeshPhysicalMaterial({ color: 0x2a2a2c, roughness: 0.92, metalness: 0.0 })
);
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);

// A row of spheres across the material model that matters for a city:
// rough concrete, wet asphalt, car paint (clearcoat), glass (transmission).
const probes = [
  { name: 'concrete', m: { color: 0xb9b4a9, roughness: 0.88, metalness: 0.0 } },
  { name: 'wet asphalt', m: { color: 0x1b1c1f, roughness: 0.18, metalness: 0.0 } },
  { name: 'car paint', m: { color: 0x8c1c22, roughness: 0.38, metalness: 0.85, clearcoat: 1.0, clearcoatRoughness: 0.06 } },
  { name: 'glass', m: { color: 0xffffff, roughness: 0.05, metalness: 0.0, transmission: 1.0, thickness: 0.4, ior: 1.5 } },
];
probes.forEach((p, i) => {
  const mesh = new THREE.Mesh(
    new THREE.SphereGeometry(0.5, 48, 32),
    new THREE.MeshPhysicalMaterial(p.m)
  );
  mesh.position.set((i - 1.5) * 1.4, 0.5, 0);
  mesh.castShadow = true;
  mesh.name = p.name;
  scene.add(mesh);
});

// --- post chain --------------------------------------------------------------
const scenePass = pass(scene, camera);
scenePass.setMRT(mrt({ output, normal: normalView }));
const colorNode = scenePass.getTextureNode('output');
const normalNode = scenePass.getTextureNode('normal');
const depthNode = scenePass.getTextureNode('depth');

// GTAONode renders into a RedFormat target, so take .r — multiplying by the whole
// RGBA zeroes green and blue and the frame comes out monochrome red.
const aoNode = ao(depthNode, normalNode, camera);
const withAO = colorNode.mul(aoNode.getTextureNode().r);
const bloomNode = bloom(withAO, 0.25, 0.4, 0.85);

const post = new RenderPipeline(renderer);
post.outputNode = smaa(withAO.add(bloomNode));

// --- loop --------------------------------------------------------------------
let frames = 0;
function tick() {
  frames++;
  const t = performance.now() * 0.0002;
  camera.position.set(Math.sin(t) * 7, 2.4, Math.cos(t) * 7);
  camera.lookAt(0, 0.6, 0);
  post.render();
  requestAnimationFrame(tick);
}
tick();

addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

window.game = {
  get frames() { return frames; },
  get backend() { return renderer.backend.isWebGPUBackend ? 'webgpu' : 'webgl2'; },
  info: () => ({
    backend: renderer.backend.isWebGPUBackend ? 'webgpu' : 'webgl2',
    calls: renderer.info.render.calls,
    tris: renderer.info.render.triangles,
    frames,
  }),
};
window.renderer = renderer;
console.log('[boot] backend =', window.game.backend);
