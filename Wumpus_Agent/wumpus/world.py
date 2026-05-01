"""
world.py – Wumpus World Environment
Handles grid creation, random hazard placement, and percept generation.
"""

import random


class World:
    def __init__(self, rows: int, cols: int, num_pits: int):
        self.rows = rows
        self.cols = cols
        self.num_pits = num_pits
        self.grid: list[list[dict]] = []
        self.wumpus_pos: tuple | None = None
        self._generate()

    def _generate(self):
        # Build empty grid
        self.grid = [
            [{"r": r, "c": c, "has_pit": False, "has_wumpus": False, "has_gold": False}
             for c in range(self.cols)]
            for r in range(self.rows)
        ]

        # Candidate cells: exclude (0,0) and its immediate neighbours so start is always safe
        candidates = [
            (r, c)
            for r in range(self.rows)
            for c in range(self.cols)
            if not (r == 0 and c == 0)
            and not (r == 0 and c == 1)
            and not (r == 1 and c == 0)
        ]
        random.shuffle(candidates)

        # Place pits
        actual_pits = min(self.num_pits, max(0, len(candidates) - 1))
        for i in range(actual_pits):
            r, c = candidates[i]
            self.grid[r][c]["has_pit"] = True

        # Place wumpus (not on a pit)
        wumpus_cands = [(r, c) for r, c in candidates if not self.grid[r][c]["has_pit"]]
        if wumpus_cands:
            wr, wc = wumpus_cands[0]
            self.grid[wr][wc]["has_wumpus"] = True
            self.wumpus_pos = (wr, wc)

        # Place gold (not on pit or wumpus)
        gold_cands = [
            (r, c) for r, c in candidates
            if not self.grid[r][c]["has_pit"] and not self.grid[r][c]["has_wumpus"]
        ]
        if gold_cands:
            gr, gc = gold_cands[0]
            self.grid[gr][gc]["has_gold"] = True

    def get_percepts(self, r: int, c: int) -> dict:
        adj = self.get_adjacent(r, c)
        breeze = any(self.grid[nr][nc]["has_pit"]    for nr, nc in adj)
        stench = any(self.grid[nr][nc]["has_wumpus"] for nr, nc in adj)
        glitter = self.grid[r][c]["has_gold"]
        return {"breeze": breeze, "stench": stench, "glitter": glitter}

    def get_adjacent(self, r: int, c: int) -> list[tuple[int, int]]:
        return [
            (r + dr, c + dc)
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]
            if self.is_in_bounds(r + dr, c + dc)
        ]

    def is_in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < self.rows and 0 <= c < self.cols

    def to_dict(self) -> dict:
        return {
            "rows": self.rows,
            "cols": self.cols,
            "grid": self.grid,
            "wumpus_pos": list(self.wumpus_pos) if self.wumpus_pos else None,
        }
