// OPERATOR-ADDED — not the agent's work.
//
// Written by hand after session 1 so a human could actually look at the world. The session had
// built `window.game` (goto / stand / aerial / info) for its own screenshots, which is enough to
// drive a camera from a script and useless for exploring: there was no way to press a key and
// move. This file is the stopgap.
//
// If you are a later session reading this: **this was not written by you.** Delete it and build
// your own — the demand now requires an inspection layer, and doing it properly means integrating
// it with your own systems rather than inheriting this. It is recorded in the harness's
// CONTAMINATION.md.
//
// Free-fly camera + readout. Nothing here touches the world; it only moves the camera the page
// already exposes, and `applyCamera()` in main.js is called on demand rather than per frame, so
// there is nothing to fight over.

import * as THREE from 'three';

export function attachOperatorCamera(game, canvas) {
  const cam = game.camera;
  const keys = new Set();
  let yaw = 0, pitch = 0, locked = false, enabled = true, groundClamp = false;

  // seed orientation from wherever the camera is now
  const e = new THREE.Euler().setFromQuaternion(cam.quaternion, 'YXZ');
  yaw = e.y; pitch = e.x;

  canvas.addEventListener('click', () => { if (enabled) canvas.requestPointerLock(); });
  document.addEventListener('pointerlockchange', () => { locked = document.pointerLockElement === canvas; });
  document.addEventListener('mousemove', (ev) => {
    if (!locked) return;
    yaw -= ev.movementX * 0.0022;
    pitch = Math.max(-1.55, Math.min(1.55, pitch - ev.movementY * 0.0022));
  });
  addEventListener('keydown', (ev) => {
    keys.add(ev.code);
    if (ev.code === 'KeyT') hud.style.display = hud.style.display === 'none' ? 'block' : 'none';
    if (ev.code === 'KeyG') groundClamp = !groundClamp;
    if (ev.code === 'KeyF') enabled = !enabled;            // hand the camera back to game.*
    if (ev.code === 'BracketLeft')  game.setHour((game.hour - 0.5 + 24) % 24);
    if (ev.code === 'BracketRight') game.setHour((game.hour + 0.5) % 24);
    if (['KeyW','KeyA','KeyS','KeyD','KeyQ','KeyE','Space'].includes(ev.code)) ev.preventDefault();
  });
  addEventListener('keyup', (ev) => keys.delete(ev.code));

  const hud = document.createElement('div');
  hud.style.cssText = `position:fixed;left:12px;top:12px;z-index:9999;font:12px/1.45 ui-monospace,
    SFMono-Regular,Menlo,monospace;color:#e6e8ef;background:rgba(12,14,20,.82);padding:10px 12px;
    border:1px solid rgba(255,255,255,.14);border-radius:6px;white-space:pre;pointer-events:none;
    backdrop-filter:blur(6px)`;
  document.body.appendChild(hud);

  const fwd = new THREE.Vector3(), right = new THREE.Vector3(), up = new THREE.Vector3(0, 1, 0);
  const q = new THREE.Quaternion();
  // If game.goto/stand/aerial moves the camera, adopt that orientation instead of fighting it.
  const mine = new THREE.Quaternion().copy(cam.quaternion);
  let last = performance.now(), fps = 0, acc = 0, n = 0;

  function frame(now) {
    const dt = Math.min((now - last) / 1000, 0.1); last = now;
    acc += dt; n++;
    if (acc > 0.4) { fps = n / acc; acc = 0; n = 0; }

    if (enabled) {
      if (!cam.quaternion.equals(mine)) {          // something else moved it — take its word
        const e2 = new THREE.Euler().setFromQuaternion(cam.quaternion, 'YXZ');
        yaw = e2.y; pitch = e2.x;
      }
      q.setFromEuler(new THREE.Euler(pitch, yaw, 0, 'YXZ'));
      cam.quaternion.copy(q);
      mine.copy(q);

      let speed = keys.has('ShiftLeft') || keys.has('ShiftRight') ? 320
                : keys.has('ControlLeft') ? 6 : 55;
      fwd.set(0, 0, -1).applyQuaternion(q);
      right.set(1, 0, 0).applyQuaternion(q);
      const move = new THREE.Vector3();
      if (keys.has('KeyW')) move.add(fwd);
      if (keys.has('KeyS')) move.sub(fwd);
      if (keys.has('KeyD')) move.add(right);
      if (keys.has('KeyA')) move.sub(right);
      if (keys.has('KeyE') || keys.has('Space')) move.add(up);
      if (keys.has('KeyQ')) move.sub(up);
      if (move.lengthSq()) cam.position.addScaledVector(move.normalize(), speed * dt);

      if (groundClamp && game.hf) {
        const g = game.hf.heightAt(cam.position.x, cam.position.z);
        if (Number.isFinite(g)) cam.position.y = g + 1.7;
      }
    }

    const i = game.info();
    hud.textContent =
      `${locked ? 'MOUSE LOCKED' : 'click canvas to look around'}${enabled ? '' : '   [camera released]'}\n` +
      `pos    ${i.camera[0].toFixed(0)}, ${i.camera[1].toFixed(0)}, ${i.camera[2].toFixed(0)}\n` +
      `ground ${game.hf ? game.hf.heightAt(cam.position.x, cam.position.z).toFixed(1) : '?'} m` +
      `${groundClamp ? '   [walking]' : ''}\n` +
      `hour   ${i.hour.toFixed(1)}\n` +
      `fps    ${fps.toFixed(0)}   calls ${i.calls}   tris ${(i.tris / 1000).toFixed(0)}k\n` +
      `chunks ${i.chunks}   tex ${i.textures}   geo ${i.geometries}\n` +
      `\nWASD move · Q/E down/up · Shift fast · Ctrl slow\nG walk on ground · [ ] time · T hide · F release`;

    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  return { disable() { enabled = false; }, enable() { enabled = true; } };
}
