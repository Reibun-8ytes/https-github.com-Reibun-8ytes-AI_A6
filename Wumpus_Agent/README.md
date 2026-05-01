# 🧠 Dynamic Wumpus Logic Agent

![Wumpus World Cover](static/img/wumpus.png)

A fully functional, zero-dependency **Knowledge-Based Agent** built for the classic AI Wumpus World environment. The agent autonomously navigates a dynamic grid by processing percepts and using **Propositional Logic** and **Resolution Refutation** to deduce safe paths to the gold while avoiding deadly pits and the Wumpus.

---

## 🌟 Key Features

* **Dynamic Grids:** Support for custom grid sizes (up to 10×10) and varying numbers of pits.
* **Pure Python Backend:** A robust, from-scratch implementation of an Inference Engine, bypassing heavy libraries.
* **Resolution Refutation:** Applies strict logical deduction (CNF clauses) to prove cell safety before moving.
* **Zero Dependencies:** Powered exclusively by Python's standard library (`http.server`), requiring absolutely no `pip` installations.
* **Premium Web UI:** A beautiful, responsive frontend built with Vanilla JS, Flexbox multi-sprite layering, Glassmorphism CSS, and custom pixel-art sprites.

---

## 🛠️ Tech Stack

* **Backend Engine:** Pure Python 3 (`wumpus/kb.py`, `wumpus/agent.py`)
* **API / Server:** Python `http.server` module (`app.py`)
* **Frontend:** HTML5, Vanilla JavaScript, CSS3
* **Visuals:** Custom transparent pixel art

---

## 🧠 How It Works: The Inference Mechanism

The agent operates strictly on logical certainty. 

1. **Percept Gathering:** As the agent moves, it receives percepts indicating adjacent hazards.
    * *Breeze* suggests an adjacent Pit.
    * *Stench* suggests an adjacent Wumpus.
2. **TELL (Knowledge Base):** Percepts are converted into **Conjunctive Normal Form (CNF)** clauses and updated in the Knowledge Base (KB). For example, if there is no breeze at `(0,0)`, the KB records `¬P_0_1` and `¬P_1_0`.
3. **ASK (Resolution):** Before generating a move, the agent queries the KB. To prove a cell `(r, c)` is safe from a pit, it temporarily asserts `P_r_c` into the KB and attempts to derive a contradiction via **Robinson's Resolution Algorithm**.
4. **Action:** If a contradiction is found, `¬P_r_c` is logically entailed, marking the cell as strictly safe to navigate.

---

## 🚀 Installation & Usage

Because the application is designed to be highly portable with zero external dependencies, running it is incredibly straightforward.

**Prerequisites:** 
* Python 3.8+ installed on your machine.

**Steps:**
1. Clone this repository or download the source code.
2. Open a terminal and navigate to the project directory:
   ```bash
   cd AI_Q6
   ```
3. Start the built-in HTTP server:
   ```bash
   python3 app.py
   ```
4. Open your web browser and navigate to:
   ```
   http://localhost:5050
   ```

---

## 🎮 Playing the Simulation

* **New Game:** Generates a new random environment based on your chosen dimensions.
* **Step:** Advances the agent's logic engine by one move.
* **Auto-Run:** Unleashes the agent to continuously resolve and move until it secures the Gold, hits a hazard, or gets stuck without any safe paths.
* **Reveal Truth:** A "cheat mode" toggle allowing you to see the hidden hazards beneath the fog of war.

---

*Developed for the AI Dynamic Pathfinding Assignment.*
