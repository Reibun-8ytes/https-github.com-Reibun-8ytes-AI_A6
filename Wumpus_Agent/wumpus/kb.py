"""
kb.py – Knowledge Base & Resolution Refutation Engine (Python)

Literals:  "P_r_c"   = Pit at (r,c)
           "~P_r_c"  = No Pit at (r,c)
           "W_r_c"   = Wumpus at (r,c)
           "~W_r_c"  = No Wumpus at (r,c)

Clause     = frozenset of literal strings
KB         = list of clauses (CNF)
"""

from __future__ import annotations


def _neg(lit: str) -> str:
    return lit[1:] if lit.startswith("~") else "~" + lit


class KnowledgeBase:
    def __init__(self):
        self.clauses: list[frozenset[str]] = []
        self.inference_steps: int = 0
        self.known_safe: set[str] = set()   # "r_c"
        self.known_pit: set[str] = set()
        self.known_wumpus: set[str] = set()

    # ── Internals ────────────────────────────────────────────────────────────

    def _add_clause(self, lits: list[str] | frozenset[str]):
        clause = frozenset(lits)

        # Tautology: contains L and ~L → skip
        for lit in clause:
            if _neg(lit) in clause:
                return

        # Don't add if subsumed by existing clause
        for existing in self.clauses:
            if existing <= clause:
                return  # existing subsumes new

        # Remove clauses subsumed by new
        self.clauses = [c for c in self.clauses if not (clause <= c)]
        self.clauses.append(clause)

    def _update_known(self):
        for clause in self.clauses:
            if len(clause) == 1:
                (lit,) = clause
                neg = lit.startswith("~")
                base = lit[1:] if neg else lit
                parts = base.split("_")
                t, r, c = parts[0], parts[1], parts[2]
                key = f"{r}_{c}"
                if t == "P" and not neg:
                    self.known_pit.add(key)
                if t == "W" and not neg:
                    self.known_wumpus.add(key)

    # ── TELL ─────────────────────────────────────────────────────────────────

    def tell(self, r: int, c: int, percepts: dict, adjacent: list[tuple[int, int]]):
        breeze = percepts["breeze"]
        stench = percepts["stench"]

        # Visited cell is always safe
        self._add_clause([f"~P_{r}_{c}"])
        self._add_clause([f"~W_{r}_{c}"])
        self.known_safe.add(f"{r}_{c}")

        if not breeze:
            for nr, nc in adjacent:
                self._add_clause([f"~P_{nr}_{nc}"])
                self.known_safe.add(f"{nr}_{nc}")
        else:
            # Breeze ↔ ∨ P_adj  (B known true → forward: ∨ P_adj)
            pit_lits = [f"P_{nr}_{nc}" for nr, nc in adjacent]
            if pit_lits:
                self._add_clause(pit_lits)
            # Backward: for each k, if all others ¬pit → k is pit
            for k, (kr, kc) in enumerate(adjacent):
                clause = [f"~P_{nr}_{nc}" for i, (nr, nc) in enumerate(adjacent) if i != k]
                clause.append(f"P_{kr}_{kc}")
                self._add_clause(clause)

        if not stench:
            for nr, nc in adjacent:
                self._add_clause([f"~W_{nr}_{nc}"])
        else:
            w_lits = [f"W_{nr}_{nc}" for nr, nc in adjacent]
            if w_lits:
                self._add_clause(w_lits)
            for k, (kr, kc) in enumerate(adjacent):
                clause = [f"~W_{nr}_{nc}" for i, (nr, nc) in enumerate(adjacent) if i != k]
                clause.append(f"W_{kr}_{kc}")
                self._add_clause(clause)

        self._update_known()

    # ── ASK ──────────────────────────────────────────────────────────────────

    def ask(self, r: int, c: int) -> dict:
        safe_pit    = self._prove_negation(f"P_{r}_{c}")
        safe_wumpus = self._prove_negation(f"W_{r}_{c}")
        return {
            "safe_pit":    safe_pit,
            "safe_wumpus": safe_wumpus,
            "safe":        safe_pit and safe_wumpus,
        }

    def _prove_negation(self, pos_lit: str) -> bool:
        """Prove ¬pos_lit by assuming pos_lit and deriving contradiction."""
        working = list(self.clauses) + [frozenset([pos_lit])]
        result = self._resolution(working)
        self.inference_steps += result["steps_used"]
        return result["contradiction"]

    # ── Resolution ───────────────────────────────────────────────────────────

    def _resolution(self, initial_clauses: list[frozenset[str]]) -> dict:
        def clause_key(c: frozenset[str]) -> str:
            return "|".join(sorted(c))

        seen: set[str] = {clause_key(c) for c in initial_clauses}
        clauses = list(initial_clauses)
        steps = 0
        MAX_STEPS = 2000

        while steps < MAX_STEPS:
            new_clauses: list[frozenset[str]] = []

            for i in range(len(clauses)):
                for j in range(i + 1, len(clauses)):
                    resolvents = self._resolve(clauses[i], clauses[j])
                    steps += 1
                    for resolvent in resolvents:
                        if len(resolvent) == 0:
                            return {"contradiction": True, "steps_used": steps}
                        key = clause_key(resolvent)
                        if key not in seen:
                            seen.add(key)
                            new_clauses.append(resolvent)

            if not new_clauses:
                return {"contradiction": False, "steps_used": steps}

            clauses.extend(new_clauses)

        return {"contradiction": False, "steps_used": steps}

    def _resolve(self, c1: frozenset[str], c2: frozenset[str]) -> list[frozenset[str]]:
        resolvents = []
        for lit in c1:
            neg_lit = _neg(lit)
            if neg_lit in c2:
                candidate = (c1 - {lit}) | (c2 - {neg_lit})
                # Skip tautologies
                tautology = any(_neg(l) in candidate for l in candidate)
                if not tautology:
                    resolvents.append(frozenset(candidate))
        return resolvents

    # ── Serialization ────────────────────────────────────────────────────────

    def get_clause_strings(self, limit: int = 20) -> list[str]:
        result = []
        for clause in self.clauses[:limit]:
            lits = sorted(
                lit.replace("_", ",").replace("~", "¬")
                for lit in clause
            )
            result.append(lits[0] if len(lits) == 1 else f"({'  ∨  '.join(lits)})")
        return result

    def reset(self):
        self.clauses.clear()
        self.inference_steps = 0
        self.known_safe.clear()
        self.known_pit.clear()
        self.known_wumpus.clear()
