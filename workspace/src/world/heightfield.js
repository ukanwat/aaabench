// The heightfield, on both sides of the fence.
//
// One 16-bit raw image is the single source of truth for the shape of the world.
// The GPU gets it as a texture and displaces terrain grids from it; the CPU gets
// the same numbers for anything that has to know where the ground is — placing a
// building, dropping a prop, spawning the player, keeping a car on the road.
// Two copies of the terrain that disagree is a class of bug worth designing out.
import * as THREE from 'three';

export class Heightfield {
  constructor(manifest, int16, landPixels) {
    const H = manifest.height;
    this.width = H.width;
    this.depth = H.height;
    this.cell = H.cell;
    this.scale = H.scale;
    this.bounds = manifest.bounds;
    this.worldW = this.bounds.maxX - this.bounds.minX;
    this.worldH = this.bounds.maxZ - this.bounds.minZ;
    this.seaLevel = manifest.seaLevel ?? 0;

    this.data = new Float32Array(this.width * this.depth);
    for (let i = 0; i < this.data.length; i++) this.data[i] = int16[i] * this.scale;
    this.land = landPixels; // Uint8Array, 0..255

    this.texture = new THREE.DataTexture(
      this.data, this.width, this.depth, THREE.RedFormat, THREE.FloatType);
    this.texture.magFilter = THREE.LinearFilter;
    this.texture.minFilter = THREE.LinearFilter;
    this.texture.wrapS = THREE.ClampToEdgeWrapping;
    this.texture.wrapT = THREE.ClampToEdgeWrapping;
    this.texture.needsUpdate = true;
  }

  static async load(base = './world/') {
    const manifest = await (await fetch(base + 'manifest.json')).json();
    const buf = await (await fetch(base + manifest.height.file)).arrayBuffer();
    const int16 = new Int16Array(buf);

    // The land mask arrives as a PNG; read it back through a canvas.
    const img = new Image();
    img.src = base + manifest.landMask.file;
    await img.decode();
    const cv = document.createElement('canvas');
    cv.width = img.width; cv.height = img.height;
    const ctx = cv.getContext('2d', { willReadFrequently: true });
    ctx.drawImage(img, 0, 0);
    const rgba = ctx.getImageData(0, 0, img.width, img.height).data;
    const land = new Uint8Array(img.width * img.height);
    for (let i = 0; i < land.length; i++) land[i] = rgba[i * 4];

    const hf = new Heightfield(manifest, int16, land);
    hf.manifest = manifest;
    return hf;
  }

  /** Bilinear height in metres at a world position. */
  heightAt(x, z) {
    const fx = (x - this.bounds.minX) / this.cell;
    const fz = (z - this.bounds.minZ) / this.cell;
    const x0 = Math.floor(fx), z0 = Math.floor(fz);
    const tx = fx - x0, tz = fz - z0;
    const cx0 = Math.min(Math.max(x0, 0), this.width - 1);
    const cz0 = Math.min(Math.max(z0, 0), this.depth - 1);
    const cx1 = Math.min(cx0 + 1, this.width - 1);
    const cz1 = Math.min(cz0 + 1, this.depth - 1);
    const d = this.data;
    const h00 = d[cz0 * this.width + cx0], h10 = d[cz0 * this.width + cx1];
    const h01 = d[cz1 * this.width + cx0], h11 = d[cz1 * this.width + cx1];
    return (h00 * (1 - tx) + h10 * tx) * (1 - tz) + (h01 * (1 - tx) + h11 * tx) * tz;
  }

  isLand(x, z) {
    const ix = Math.round((x - this.bounds.minX) / this.cell);
    const iz = Math.round((z - this.bounds.minZ) / this.cell);
    if (ix < 0 || iz < 0 || ix >= this.width || iz >= this.depth) return false;
    return this.land[iz * this.width + ix] > 127;
  }

  /** Surface normal from central differences, in world space. */
  normalAt(x, z, out = new THREE.Vector3()) {
    const e = this.cell;
    const hl = this.heightAt(x - e, z), hr = this.heightAt(x + e, z);
    const hd = this.heightAt(x, z - e), hu = this.heightAt(x, z + e);
    return out.set(hl - hr, 2 * e, hd - hu).normalize();
  }

  /** Percent gradient at a world position — what a road or a car cares about. */
  slopeAt(x, z) {
    const e = this.cell;
    const gx = (this.heightAt(x + e, z) - this.heightAt(x - e, z)) / (2 * e);
    const gz = (this.heightAt(x, z + e) - this.heightAt(x, z - e)) / (2 * e);
    return Math.hypot(gx, gz) * 100;
  }
}
