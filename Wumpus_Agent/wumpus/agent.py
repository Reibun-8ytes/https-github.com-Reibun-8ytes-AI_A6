"""
agent.py – Knowledge-Based Agent (Python)
Decides moves using the KB inference engine.
"""

from __future__ import annotations
from .world import World
from .kb import KnowledgeBase


class Agent:
    STATUS_IDLE    = "idle"
    STATUS_RUNNING = "running"
    STATUS_WON     = "won"
    STATUS_PIT     = "dead_pit"
    STATUS_WUMPUS  = "dead_wumpus"
    STATUS_STUCK   = "stuck"

    def __init__(self, world: World, kb: KnowledgeBase):
        self.world = world
        self.kb = kb
        self.r = 0
        self.c = 0
        self.status = self.STATUS_IDLE
        self.visited: set[str] = set()
        self.safe_queue: list[dict] = []    # [{r, c}]
        self.cell_state: dict[str, str] = {}
        self.last_percepts: dict = {}
        self.log: list[str] = []
        self.score = 0
        self.wumpus_alive = True

    # ── Main Step ─────────────────────────────────────────────────────────────

    def step(self) -> bool:
        """Execute one agent step. Returns True if the agent can still move."""
        if self.status == self.STATUS_IDLE:
            self.status = self.STATUS_RUNNING
        if self.status != self.STATUS_RUNNING:
            return False

        self._arrive(self.r, self.c)

        # Check gold
        if self.world.grid[self.r][self.c]["has_gold"]:
            self.score += 1000
            self.world.grid[self.r][self.c]["has_gold"] = False
            self._log(f"🏆 Gold grabbed at ({self.r},{self.c})! Score: {self.score}")
            self.status = self.STATUS_WON
            return False

        # Death checks
        if self.world.grid[self.r][self.c]["has_pit"]:
            self._log(f"💀 Fell into pit at ({self.r},{self.c})")
            self.status = self.STATUS_PIT
            return False
        if self.world.grid[self.r][self.c]["has_wumpus"] and self.wumpus_alive:
            self._log(f"💀 Eaten by Wumpus at ({self.r},{self.c})")
            self.status = self.STATUS_WUMPUS
            return False

        # Choose next cell
        nxt = self._choose_next()
        if nxt is None:
            self._log("🤔 No safe moves found — stuck.")
            self.status = self.STATUS_STUCK
            return False

        self._log(f"➡ Moving to ({nxt['r']},{nxt['c']})")
        self.score -= 1
        self.r = nxt["r"]
        self.c = nxt["c"]
        return True

    # ── Arrive ───────────────────────────────────────────────────────────────

    def _arrive(self, r: int, c: int):
        key = f"{r}_{c}"
        if key in self.visited:
            return

        self.visited.add(key)
        self.cell_state[key] = "visited"
        self.score -= 1

        adjacent = self.world.get_adjacent(r, c)
        percepts = self.world.get_percepts(r, c)
        self.last_percepts = percepts

        self._log(f"📍 At ({r},{c}) — {self._percept_str(percepts)}")

        # TELL the KB
        self.kb.tell(r, c, percepts, adjacent)

        # ASK about every unvisited adjacent cell
        for nr, nc in adjacent:
            nkey = f"{nr}_{nc}"
            if nkey in self.visited:
                continue
            result = self.kb.ask(nr, nc)
            if result["safe"]:
                if self.cell_state.get(nkey) != "safe":
                    self.cell_state[nkey] = "safe"
                    if not any(d["r"] == nr and d["c"] == nc for d in self.safe_queue):
                        self.safe_queue.append({"r": nr, "c": nc})
            elif result["safe_pit"] and not result["safe_wumpus"]:
                if nkey not in self.cell_state or self.cell_state[nkey] == "unknown":
                    self.cell_state[nkey] = "unknown-stench"
            elif result["safe_wumpus"] and not result["safe_pit"]:
                if nkey not in self.cell_state or self.cell_state[nkey] == "unknown":
                    self.cell_state[nkey] = "unknown-breeze"
            else:
                if nkey not in self.cell_state:
                    self.cell_state[nkey] = "unknown"

        # Mark confirmed hazards
        for pit_key in self.kb.known_pit:
            self.cell_state[pit_key] = "pit"
        for w_key in self.kb.known_wumpus:
            self.cell_state[w_key] = "wumpus"

    # ── Choose Next ──────────────────────────────────────────────────────────

    def _choose_next(self) -> dict | None:
        # 1. Safe queue
        while self.safe_queue:
            cand = self.safe_queue.pop(0)
            if f"{cand['r']}_{cand['c']}" not in self.visited:
                return cand

        # 2. Any cell marked safe but not visited
        for key, state in self.cell_state.items():
            if state == "safe" and key not in self.visited:
                r, c = map(int, key.split("_"))
                return {"r": r, "c": c}

        # 3. Risk an unknown adjacent cell
        for nr, nc in self.world.get_adjacent(self.r, self.c):
            nkey = f"{nr}_{nc}"
            if nkey not in self.visited and self.cell_state.get(nkey) not in ("pit", "wumpus"):
                self._log(f"⚠ Risking unknown at ({nr},{nc})")
                return {"r": nr, "c": nc}

        return None

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _percept_str(self, p: dict) -> str:
        parts = []
        if p.get("breeze"):  parts.append("Breeze")
        if p.get("stench"):  parts.append("Stench")
        if p.get("glitter"): parts.append("Glitter")
        return ", ".join(parts) if parts else "None"

    def _log(self, msg: str):
        self.log.insert(0, msg)
        if len(self.log) > 50:
            self.log.pop()

    # ── Serialization ────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "r": self.r,
            "c": self.c,
            "status": self.status,
            "visited": list(self.visited),
            "cell_state": self.cell_state,
            "last_percepts": self.last_percepts,
            "log": self.log[:30],
            "score": self.score,
        }
