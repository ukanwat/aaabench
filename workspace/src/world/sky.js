// Sky and environment lighting.
//
// The problem this solves is the one that kills generated cities: **shadow is
// not the absence of light**. In a real street the shaded side is lit by the
// sunlit wall opposite and by the strip of sky overhead, which is why the deep
// part of an urban canyon reads blue and the shade under a cornice reads warm.
// A directional light plus a hemisphere light cannot do that — a hemisphere
// light is a constant, not a fill, and deep shadows under it are holes.
//
// So the environment is a real, physically-derived sky: the Preetham analytic
// daylight model, rendered to a cube map and PMREM-filtered into an irradiance
// probe. Critically it is REGENERATED WHEN THE SUN MOVES, so the ambient at
// dusk is actually the dusk sky rather than noon dimmed — which is the whole
// difference between night as a world and night as a colour grade.
//
// A captured HDRI would be more photoreal for one instant and wrong for every
// other, because it bakes the sun position it was shot at. This is a world with
// a moving sun, so the sky has to be a function of it.
import * as THREE from 'three';
import { SkyMesh } from 'three/addons/objects/SkyMesh.js';

export class Sky {
  constructor(renderer, scene, { size = 256 } = {}) {
    this.renderer = renderer;
    this.scene = scene;

    this.mesh = new SkyMesh();
    this.mesh.scale.setScalar(20000);
    this.mesh.frustumCulled = false;
    // The sky dome must not be fogged. It sits at 20 km, so exponential fog
    // reaches ~70% there and drags the entire sky toward the haze colour —
    // which turned dawn and dusk into a flat sage-green wall. Fog is what the
    // atmosphere does to things seen THROUGH it; the sky is the atmosphere.
    this.mesh.material.fog = false;
    scene.add(this.mesh);

    // Turbidity is haze: a coastal city at 38°N sits low, and salt air keeps it
    // from ever being alpine-clear.
    this.mesh.turbidity.value = 3.4;
    this.mesh.rayleigh.value = 2.1;
    this.mesh.mieCoefficient.value = 0.006;
    this.mesh.mieDirectionalG.value = 0.82;

    // The environment is generated from a scene containing only the sky.
    this.envScene = new THREE.Scene();
    this.envSky = new SkyMesh();
    this.envSky.scale.setScalar(20000);
    this.envScene.add(this.envSky);

    this.pmrem = new THREE.PMREMGenerator(renderer);
    this.pmrem.compileEquirectangularShader?.();
    this._rt = null;
    this._lastSun = new THREE.Vector3(1e9, 0, 0);
    this._sunDir = new THREE.Vector3();
    this.size = size;
  }

  /** Point the sky at a sun direction (unit vector). Rebuilds the environment
   *  probe only when the sun has actually moved enough to matter — the PMREM
   *  pass is not free and the sun does not move every frame. */
  setSun(dir, { force = false } = {}) {
    this._sunDir.copy(dir).normalize();
    this.mesh.sunPosition.value.copy(this._sunDir);
    this.envSky.sunPosition.value.copy(this._sunDir);

    if (!force && this._sunDir.angleTo(this._lastSun) < 0.012) return false;
    this._lastSun.copy(this._sunDir);
    this._rebuild();
    return true;
  }

  _rebuild() {
    for (const s of [this.mesh, this.envSky]) {
      s.turbidity.value = this.mesh.turbidity.value;
      s.rayleigh.value = this.mesh.rayleigh.value;
      s.mieCoefficient.value = this.mesh.mieCoefficient.value;
      s.mieDirectionalG.value = this.mesh.mieDirectionalG.value;
    }
    // The sun disc itself must not go into the probe: a few thousand-nit pixels
    // in a 256px cube face become a blotchy hotspot in the irradiance, and the
    // sun is already represented by the directional light.
    this.envSky.showSunDisc.value = false;

    const old = this._rt;
    this._rt = this.pmrem.fromScene(this.envScene, 0.0, 1, 40000);
    this.scene.environment = this._rt.texture;
    this.scene.background = this._rt.texture;
    this.scene.backgroundBlurriness = 0;
    if (old) old.dispose();
  }

  /** Ambient light level implied by the sky, for driving exposure and for
   *  deciding when the street lights come on. */
  get skyLuminance() {
    return Math.max(0, this._sunDir.y);
  }

  dispose() {
    this._rt?.dispose();
    this.pmrem.dispose();
  }
}
