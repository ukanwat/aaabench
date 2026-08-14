// Chunked, level-of-detailed terrain, displaced on the GPU from one height texture.
//
// The chunks carry no height data of their own — every one of them samples the
// same texture, so neighbouring chunks at different detail levels cannot
// disagree about where the ground is and there are no seams to stitch. Dropping
// a level of detail costs nothing but a coarser grid, and there is no per-chunk
// geometry to stream at all.
//
// Normals are taken per-fragment from the height texture rather than from the
// mesh, so a coarse distant chunk is still lit by the real shape of the ground
// instead of by its own faceting.
import * as THREE from 'three';
import {
  Fn, texture, uv, vec2, vec3, vec4, float, positionLocal, positionWorld,
  modelWorldMatrix, normalize, cross, mix, smoothstep, dot, max, abs, clamp,
} from 'three/tsl';

export const CHUNK = 256;               // metres
const LOD_SEGMENTS = [64, 32, 16, 8];   // vertices per side, by detail level
const LOD_RANGES = [420, 900, 1800];    // metres at which each level gives way

export class Terrain {
  constructor(hf, { maxDistance = 3400 } = {}) {
    this.hf = hf;
    this.maxDistance = maxDistance;
    this.group = new THREE.Group();
    this.group.name = 'terrain';
    this.chunks = new Map();            // key -> { mesh, lod }
    this.cols = Math.ceil(hf.worldW / CHUNK);
    this.rows = Math.ceil(hf.worldH / CHUNK);

    this.geometries = LOD_SEGMENTS.map((s) => {
      const g = new THREE.PlaneGeometry(CHUNK, CHUNK, s, s);
      g.rotateX(-Math.PI / 2);
      return g;
    });

    this.material = this._buildMaterial();
    this._tmp = new THREE.Vector3();
  }

  _buildMaterial() {
    const hf = this.hf;
    const B = hf.bounds;
    const texel = vec2(1 / hf.width, 1 / hf.depth);
    const invSize = vec2(1 / hf.worldW, 1 / hf.worldH);
    const origin = vec2(B.minX, B.minZ);

    const worldToUV = Fn(([wxz]) => wxz.sub(origin).mul(invSize));

    const sampleH = Fn(([uvv]) => texture(hf.texture, uvv).r);

    const mat = new THREE.MeshStandardNodeMaterial();

    // --- displacement ---------------------------------------------------
    // The chunk transform is a pure XZ translation, so world XZ comes straight
    // from the model matrix and the local grid.
    const worldXZ = modelWorldMatrix.mul(vec4(positionLocal, 1.0)).xz;
    const h = sampleH(worldToUV(worldXZ));
    mat.positionNode = vec3(positionLocal.x, h, positionLocal.z);

    // --- per-fragment normal from the heightfield ------------------------
    const uvw = worldToUV(positionWorld.xz);
    const e = texel;
    const hL = sampleH(uvw.sub(vec2(e.x, 0)));
    const hR = sampleH(uvw.add(vec2(e.x, 0)));
    const hD = sampleH(uvw.sub(vec2(0, e.y)));
    const hU = sampleH(uvw.add(vec2(0, e.y)));
    const step = float(hf.cell * 2.0);
    const n = normalize(vec3(hL.sub(hR), step, hD.sub(hU)));
    mat.normalNode = n;

    // --- provisional ground colour ---------------------------------------
    // Blockout colouring, not art: enough to read landform, slope and the
    // waterline while the layout is being judged. Real materials come with the
    // mesh pass; this exists so the shape can be inspected honestly first.
    const height = positionWorld.y;
    const slope = float(1.0).sub(clamp(dot(n, vec3(0, 1, 0)), 0, 1));

    const sand = vec3(0.62, 0.57, 0.44);
    const grass = vec3(0.28, 0.32, 0.18);
    const dry = vec3(0.42, 0.41, 0.27);
    const rock = vec3(0.34, 0.33, 0.31);
    const seabed = vec3(0.20, 0.22, 0.20);

    let c = mix(seabed, sand, smoothstep(float(-2.2), float(0.15), height));
    c = mix(c, grass, smoothstep(float(0.6), float(4.0), height));
    c = mix(c, dry, smoothstep(float(26.0), float(74.0), height));
    c = mix(c, rock, smoothstep(float(0.22), float(0.55), slope));
    mat.colorNode = c;
    mat.roughnessNode = float(0.95);
    mat.metalnessNode = float(0.0);

    return mat;
  }

  _lodFor(dist) {
    for (let i = 0; i < LOD_RANGES.length; i++) if (dist < LOD_RANGES[i]) return i;
    return LOD_SEGMENTS.length - 1;
  }

  /** Create, retire and re-detail chunks around a position. Call every frame;
   *  it allocates only when a chunk actually changes. */
  update(camPos) {
    const hf = this.hf;
    const half = CHUNK * 0.5;
    const wanted = new Set();

    const c0 = Math.max(0, Math.floor((camPos.x - this.maxDistance - hf.bounds.minX) / CHUNK));
    const c1 = Math.min(this.cols - 1, Math.ceil((camPos.x + this.maxDistance - hf.bounds.minX) / CHUNK));
    const r0 = Math.max(0, Math.floor((camPos.z - this.maxDistance - hf.bounds.minZ) / CHUNK));
    const r1 = Math.min(this.rows - 1, Math.ceil((camPos.z + this.maxDistance - hf.bounds.minZ) / CHUNK));

    for (let r = r0; r <= r1; r++) {
      for (let c = c0; c <= c1; c++) {
        const cx = hf.bounds.minX + c * CHUNK + half;
        const cz = hf.bounds.minZ + r * CHUNK + half;
        const dx = cx - camPos.x, dz = cz - camPos.z;
        const dist = Math.hypot(dx, dz) - half * 1.414;
        if (dist > this.maxDistance) continue;

        const key = r * this.cols + c;
        wanted.add(key);
        const lod = this._lodFor(dist);
        const have = this.chunks.get(key);
        if (have && have.lod === lod) continue;
        if (have) this.group.remove(have.mesh);

        const mesh = new THREE.Mesh(this.geometries[lod], this.material);
        mesh.position.set(cx, 0, cz);
        // The bounding sphere has to cover the displaced height range or the
        // frustum cull throws away chunks whose ground is far above or below
        // the flat grid it was built from.
        mesh.geometry.boundingSphere = new THREE.Sphere(
          new THREE.Vector3(0, 0, 0), CHUNK * 0.75 + 140);
        mesh.receiveShadow = true;
        mesh.castShadow = false;
        mesh.matrixAutoUpdate = false;
        mesh.updateMatrix();
        this.group.add(mesh);
        this.chunks.set(key, { mesh, lod });
      }
    }

    for (const [key, entry] of this.chunks) {
      if (!wanted.has(key)) {
        this.group.remove(entry.mesh);
        this.chunks.delete(key);
      }
    }
  }

  get chunkCount() { return this.chunks.size; }
}
