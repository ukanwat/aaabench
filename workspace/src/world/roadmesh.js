// Road centrelines → ribbons laid on the ground.
//
// Blockout geometry, deliberately: enough to see whether the network went where
// roads would go, and to walk and drive it. The real carriageway — camber,
// crossfall, superelevation into bends, kerbs, a graded verge meeting the
// terrain — is a mesh-pass job, and building it now against a layout that is
// still moving would be building it twice.
import * as THREE from 'three';

const WIDTH = { motorway: 22.0, primary: 14.0, secondary: 10.0, residential: 7.0 };
const LIFT = 0.18;   // clear of the ground so it does not z-fight the terrain

export function buildRoads(roads, hf) {
  const group = new THREE.Group();
  group.name = 'roads';

  const mats = {
    motorway: new THREE.MeshStandardMaterial({ color: 0x2a2a2d, roughness: 0.88 }),
    primary: new THREE.MeshStandardMaterial({ color: 0x303033, roughness: 0.9 }),
    secondary: new THREE.MeshStandardMaterial({ color: 0x343436, roughness: 0.92 }),
    residential: new THREE.MeshStandardMaterial({ color: 0x393937, roughness: 0.94 }),
  };

  for (const road of roads) {
    const pts = road.points;
    if (pts.length < 2) continue;
    const w = (WIDTH[road.cls] ?? 10) * 0.5;

    const positions = [];
    const normals = [];
    const uvs = [];
    const indices = [];

    for (let i = 0; i < pts.length; i++) {
      const [x, z] = pts[i];
      const p = pts[Math.max(0, i - 1)];
      const n = pts[Math.min(pts.length - 1, i + 1)];
      let tx = n[0] - p[0], tz = n[1] - p[1];
      const len = Math.hypot(tx, tz) || 1;
      tx /= len; tz /= len;
      // Left normal in the ground plane.
      const nx = -tz, nz = tx;
      const y = hf.heightAt(x, z) + LIFT;
      positions.push(x + nx * w, y, z + nz * w);
      positions.push(x - nx * w, y, z - nz * w);
      normals.push(0, 1, 0, 0, 1, 0);
      const v = i / (pts.length - 1);
      uvs.push(0, v * len, 1, v * len);
      if (i < pts.length - 1) {
        const a = i * 2;
        indices.push(a, a + 2, a + 1, a + 1, a + 2, a + 3);
      }
    }

    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    g.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3));
    g.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
    g.setIndex(indices);
    g.computeBoundingSphere();

    const mesh = new THREE.Mesh(g, mats[road.cls] ?? mats.secondary);
    mesh.name = road.name;
    mesh.receiveShadow = true;
    group.add(mesh);
  }

  return group;
}
