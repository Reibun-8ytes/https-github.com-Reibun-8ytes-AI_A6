/**
 * ui.js – Frontend for Flask-powered Wumpus World
 * All game logic runs on the Python backend; this file just calls the API
 * and renders the response.
 */

// ── Pixel-art image map ────────────────────────────────────────────────────
const SPRITES = {
  agent:   '/static/img/agent.png',
  pit:     '/static/img/pit.png',
  wumpus:  '/static/img/wumpus.png',
  gold:    '/static/img/gold.png',
  breeze:  '/static/img/breeze.png',
  stench:  '/static/img/stench.png',
};

// ── State ─────────────────────────────────────────────────────────────────
let snapshot     = null;   // last snapshot from server
let autoTimer    = null;
let autoSpeed    = 400;    // ms
let revealMode   = false;

// ── Init ──────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('btn-new').addEventListener('click', newGame);
  document.getElementById('btn-step').addEventListener('click', stepOnce);
  document.getElementById('btn-auto').addEventListener('click', toggleAuto);
  document.getElementById('btn-reveal').addEventListener('click', toggleReveal);

  document.getElementById('speed-slider').addEventListener('input', e => {
    autoSpeed = 1050 - Number(e.target.value);
    document.getElementById('speed-label').textContent =
      e.target.value < 350 ? 'Slow' : e.target.value < 700 ? 'Medium' : 'Fast';
  });
});

// ── API Helpers ───────────────────────────────────────────────────────────
async function api(path, body = null) {
  const opts = body
    ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
    : { method: 'GET' };
  const res = await fetch(path, opts);
  return res.json();
}

// ── Controls ──────────────────────────────────────────────────────────────
async function newGame() {
  stopAuto();
  revealMode = false;
  hidePopup();

  const rows = Math.max(2, Math.min(10, parseInt(document.getElementById('inp-rows').value) || 4));
  const cols = Math.max(2, Math.min(10, parseInt(document.getElementById('inp-cols').value) || 4));
  const pits = Math.max(1, Math.min(rows * cols - 4, parseInt(document.getElementById('inp-pits').value) || 2));

  document.getElementById('inp-rows').value = rows;
  document.getElementById('inp-cols').value = cols;
  document.getElementById('inp-pits').value = pits;

  const data = await api('/api/new_game', { rows, cols, pits });
  snapshot = data.snapshot;
  render(snapshot);
  setStatus('🟢 New game started. Press Step or Auto-Run.');

  showPopup({
    type: 'start',
    title: '🧠 Logic Agent Deployed',
    body: `Grid: <strong>${rows} × ${cols}</strong> &nbsp;|&nbsp; Pits: <strong>${pits}</strong> &nbsp;|&nbsp; Wumpus: <strong>1</strong><br><br>
           <div style="font-size: 0.85em; text-align: left; background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px;">
             <strong>Legend:</strong><br>
             🤖 Agent &nbsp;&nbsp; 🕳️ Pit &nbsp;&nbsp; 👹 Wumpus &nbsp;&nbsp; 🏆 Gold<br>
             💨 Breeze (Adjacent to Pit) &nbsp;&nbsp; 🦨 Stench (Adjacent to Wumpus)
           </div>`,
    sub:  'Python backend uses Propositional Resolution to infer safe cells before moving.',
    btnText: '▶ Start',
  });
}

async function stepOnce() {
  if (!snapshot) return;
  const agent = snapshot.agent;
  if (agent.status !== 'idle' && agent.status !== 'running') return;

  const data = await api('/api/step', {});
  snapshot = data.snapshot;
  render(snapshot);

  if (!data.can_continue) {
    stopAuto();
    handleGameEnd(snapshot);
  }
}

function toggleAuto() {
  if (autoTimer) {
    stopAuto();
  } else {
    document.getElementById('btn-auto').textContent = '⏸ Pause';
    document.getElementById('btn-auto').classList.add('active');
    autoTimer = setInterval(async () => {
      if (!snapshot) return;
      const agent = snapshot.agent;
      if (agent.status !== 'idle' && agent.status !== 'running') {
        stopAuto(); return;
      }
      const data = await api('/api/step', {});
      snapshot = data.snapshot;
      render(snapshot);
      if (!data.can_continue) {
        stopAuto();
        handleGameEnd(snapshot);
      }
    }, autoSpeed);
  }
}

function stopAuto() {
  if (autoTimer) { clearInterval(autoTimer); autoTimer = null; }
  document.getElementById('btn-auto').textContent = '▶ Auto-Run';
  document.getElementById('btn-auto').classList.remove('active');
}

function toggleReveal() {
  revealMode = !revealMode;
  if (snapshot) render(snapshot);
  setStatus(revealMode ? '👁 Truth revealed! (Cheat mode)' : '🟢 Cheat mode off.');
}

// ── Rendering ─────────────────────────────────────────────────────────────
function render(snap) {
  if (!snap || snap.error) return;

  const { world, agent, kb } = snap;
  const container = document.getElementById('grid');
  container.innerHTML = '';
  container.style.setProperty('--cols', world.cols);
  container.style.setProperty('--rows', world.rows);

  for (let r = 0; r < world.rows; r++) {
    for (let c = 0; c < world.cols; c++) {
      const key     = `${r}_${c}`;
      const cell    = world.grid[r][c];
      const isAgent = (r === agent.r && c === agent.c);
      const state   = isAgent ? 'agent' : (agent.cell_state[key] || 'unvisited');

      const el = document.createElement('div');
      el.className = 'cell';
      el.id = `cell-${r}-${c}`;
      el.dataset.state = state;

      // Gather sprites to display
      const spritesToRender = [];

      // Determine environment sprites
      if (revealMode && cell.has_pit) {
        spritesToRender.push(SPRITES.pit);
        el.dataset.state = 'pit';
      } else if (revealMode && cell.has_wumpus) {
        spritesToRender.push(SPRITES.wumpus);
        el.dataset.state = 'wumpus';
      } else if (revealMode && cell.has_gold) {
        spritesToRender.push(SPRITES.gold);
      } else if (state === 'pit') {
        spritesToRender.push(SPRITES.pit);
      } else if (state === 'wumpus') {
        spritesToRender.push(SPRITES.wumpus);
      } else if (state === 'visited') {
        const p = getPercepts(world, r, c);
        if (p.breeze) spritesToRender.push(SPRITES.breeze);
        if (p.stench) spritesToRender.push(SPRITES.stench);
      }

      // Add agent
      if (isAgent) {
        spritesToRender.push(SPRITES.agent);
      }

      if (spritesToRender.length > 1) el.classList.add('multi-sprite');

      spritesToRender.forEach(src => {
        const img = document.createElement('img');
        img.className = 'cell-sprite';
        img.src = src;
        img.alt = '';
        el.appendChild(img);
      });

      // Fallback text for states without sprites
      const label = document.createElement('div');
      label.className = 'cell-label';
      if (!isAgent && state === 'safe' && !revealMode) label.textContent = '✓';
      if (!isAgent && state === 'unvisited') label.textContent = '?';

      const coord = document.createElement('div');
      coord.className = 'cell-coord';
      coord.textContent = `${r},${c}`;

      el.appendChild(label);
      el.appendChild(coord);
      container.appendChild(el);
    }
  }

  // Metrics
  document.getElementById('metric-infer').textContent = (kb.inference_steps || 0).toLocaleString();
  document.getElementById('metric-score').textContent = agent.score;
  document.getElementById('metric-cells').textContent = agent.visited.length;

  const p = agent.last_percepts || {};
  const tags = [];
  if (p.breeze)  tags.push('<span class="tag breeze">💨 Breeze</span>');
  if (p.stench)  tags.push('<span class="tag stench">🦨 Stench</span>');
  if (p.glitter) tags.push('<span class="tag glitter">✨ Glitter</span>');
  document.getElementById('percepts').innerHTML = tags.length
    ? tags.join('') : '<span class="tag none">— None</span>';

  // Log
  document.getElementById('agent-log').innerHTML = (agent.log || [])
    .map(l => `<div class="log-entry">${l}</div>`).join('');

  // KB clauses
  document.getElementById('kb-clauses').innerHTML = (kb.clauses || [])
    .map(s => `<div class="kb-clause">${s}</div>`).join('');
}

function getPercepts(world, r, c) {
  // Recompute percepts client-side for visualization
  const adj = [[r-1,c],[r+1,c],[r,c-1],[r,c+1]]
    .filter(([nr,nc]) => nr>=0 && nr<world.rows && nc>=0 && nc<world.cols);
  let breeze = false, stench = false;
  for (const [nr,nc] of adj) {
    if (world.grid[nr][nc].has_pit)    breeze = true;
    if (world.grid[nr][nc].has_wumpus) stench = true;
  }
  return { breeze, stench };
}

// ── Game End ──────────────────────────────────────────────────────────────
function handleGameEnd(snap) {
  const agent = snap.agent;
  const kb    = snap.kb;
  const score = agent.score;
  const steps = (kb.inference_steps || 0).toLocaleString();
  const visited = agent.visited.length;

  const cfgs = {
    won: {
      type: 'win', title: '🏆 VICTORY!',
      body:    'The agent found the <strong>gold</strong> using only logic!',
      sub:     `Score: <strong>${score}</strong> &nbsp;|&nbsp; Cells: <strong>${visited}</strong> &nbsp;|&nbsp; Inference steps: <strong>${steps}</strong>`,
      btnText: '🔄 Play Again',
    },
    dead_pit: {
      type: 'lose', title: '💀 GAME OVER',
      body:    `Fell into a <strong>pit</strong> at (${agent.r}, ${agent.c}).`,
      sub:     `Score: <strong>${score}</strong> &nbsp;|&nbsp; Inference steps: <strong>${steps}</strong>`,
      btnText: '🔄 Try Again',
    },
    dead_wumpus: {
      type: 'lose', title: '💀 GAME OVER',
      body:    `Eaten by the <strong>Wumpus</strong> at (${agent.r}, ${agent.c}).`,
      sub:     `Score: <strong>${score}</strong> &nbsp;|&nbsp; Inference steps: <strong>${steps}</strong>`,
      btnText: '🔄 Try Again',
    },
    stuck: {
      type: 'stuck', title: '🤔 STUCK',
      body:    'No safe reachable cells remain.',
      sub:     `Cells: <strong>${visited}</strong> &nbsp;|&nbsp; Inference steps: <strong>${steps}</strong>`,
      btnText: '🔄 New Game',
    },
  };
  const cfg = cfgs[agent.status] || cfgs.stuck;
  setStatus(cfg.title);
  showPopup(cfg);
}

// ── Popup ─────────────────────────────────────────────────────────────────
function showPopup({ type, title, body, sub, btnText }) {
  const overlay = document.getElementById('popup-overlay');
  const box     = document.getElementById('popup-box');
  const btn     = document.getElementById('popup-btn');
  
  overlay.dataset.type = type;
  document.getElementById('popup-title').innerHTML = title;
  document.getElementById('popup-body').innerHTML  = body;
  document.getElementById('popup-sub').innerHTML   = sub;
  btn.textContent = btnText;
  
  // Set specific click behavior based on context to prevent infinite loops
  if (type === 'start') {
    btn.onclick = () => hidePopup();
  } else {
    btn.onclick = () => newGame();
  }

  overlay.classList.remove('hidden');
  box.style.animation = 'none';
  box.offsetHeight;
  box.style.animation = '';
}

function hidePopup() {
  document.getElementById('popup-overlay').classList.add('hidden');
}

function setStatus(msg) {
  document.getElementById('status-banner').textContent = msg;
}
