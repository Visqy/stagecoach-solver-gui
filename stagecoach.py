# ================================================================
# Stagecoach DP (layered shortest/longest path) + Multi-path plot
# Pure functions • tabulate + matplotlib • tanpa global I/O
# ================================================================

from __future__ import annotations
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import math
from tabulate import tabulate
import matplotlib.pyplot as plt
import itertools
import matplotlib.cm as cm


# ---------- HASIL SOLVER ----------

@dataclass(frozen=True)
class StagecoachResult:
    optimal_cost: float                 # untuk opt_mode="min" = biaya minimum; "max" = nilai maksimum
    path: List[str]                     # salah satu urutan node start → ... → goal
    tables: List[str]                   # tabel per stage (string dari tabulate)
    f_star: Dict[str, float]            # nilai optimal per node (fungsi nilai)
    policy: Dict[str, List[str]]        # backpointer: semua next node optimal


# ---------- VALIDASI ----------

def _validate_stagecoach(
    layers: List[List[str]],
    edges: Dict[str, Dict[str, float]],
    start: str,
    goal: str,
) -> Tuple[Dict[str, int], List[str]]:
    """Validasi struktur ber-stage dan kembalikan peta node→stage & flatten order."""
    if not layers or not all(isinstance(L, list) and len(L) > 0 for L in layers):
        raise ValueError("layers harus list of non-empty lists.")
    stage_of: Dict[str, int] = {}
    for k, L in enumerate(layers):
        for u in L:
            if u in stage_of:
                raise ValueError(f"Node '{u}' muncul di lebih dari satu stage.")
            stage_of[u] = k
    if start not in stage_of or goal not in stage_of:
        raise ValueError("start/goal tidak ada di layers.")
    if stage_of[start] != 0 or stage_of[goal] != len(layers) - 1:
        raise ValueError("start harus di stage 0 dan goal di stage terakhir.")

    # Edge harus selalu dari stage t ke t+1 (arah ke kanan)
    for u, nbrs in edges.items():
        if u not in stage_of:
            raise ValueError(f"Node '{u}' pada edges tidak terdapat pada layers.")
        su = stage_of[u]
        for v in nbrs:
            if v not in stage_of:
                raise ValueError(f"Node '{v}' pada edges tidak terdapat pada layers.")
            if stage_of[v] != su + 1:
                raise ValueError(f"Edge {u}->{v} harus menuju stage berikutnya (t+1).")

    return stage_of, [node for L in layers for node in L]


# ---------- SOLVER (MIN / MAX via opt_mode) ----------

def solve_stagecoach_dp(
    layers: List[List[str]],
    edges: Dict[str, Dict[str, float]],
    start: str,
    goal: str,
    opt_mode: str = "min",            # "min" untuk biaya minimum; "max" untuk nilai maksimum
    combine_op: str = "+",            # "+" untuk penjumlahan, "*" untuk perkalian
    print_tables: bool = True,
) -> StagecoachResult:
    if opt_mode not in {"min", "max"}:
        raise ValueError("opt_mode harus 'min' atau 'max'.")
    if combine_op not in {"+", "*"}:
        raise ValueError("combine_op harus '+' (jumlah) atau '*' (kali).")

    stage_of, _ = _validate_stagecoach(layers, edges, start, goal)
    K = len(layers) - 1  # banyak transisi

    # Inisialisasi terminal
    f_star: Dict[str, float] = {goal: 0.0 if combine_op == "+" else 1.0}
    policy: Dict[str, List[str]] = {goal: []}

    # Operator pembanding & identitas sesuai mode
    if opt_mode == "min":
        agg_init = math.inf
        better = lambda a, b: a < b
    else:  # "max"
        agg_init = -math.inf
        better = lambda a, b: a > b

    # Backward pass: stage K-1 .. 0
    tables: List[str] = []
    for t in range(K - 1, -1, -1):
        current = layers[t]
        next_layer = layers[t + 1]
        headers = ["node"] + next_layer + [r"f* (node)", r"next*"]
        rows = []

        for u in current:
            nbrs = edges.get(u, {})
            totals: List[Optional[float]] = []
            best_val = agg_init
            best_vs: List[str] = []

            for v in next_layer:
                if v in nbrs:
                    if combine_op == "+":
                        tot = float(nbrs[v]) + float(f_star.get(v, agg_init))
                    else:  # "*"
                        tot = float(nbrs[v]) * float(f_star.get(v, agg_init))
                    totals.append(tot)

                    if better(tot, best_val):
                        best_val = tot
                        best_vs = [v]              # reset kandidat terbaik
                    elif tot == best_val:
                        best_vs.append(v)          # tambahkan kandidat lain
                else:
                    totals.append(None)

            if not best_vs:
                raise ValueError(f"Tidak ada successor valid dari node '{u}' pada stage {t+1}.")

            f_star[u] = best_val
            policy[u] = best_vs

            pretty_totals = [("" if x is None else (int(x) if float(x).is_integer() else x)) for x in totals]
            pretty_best = int(best_val) if float(best_val).is_integer() else best_val
            rows.append([u] + pretty_totals + [pretty_best, ",".join(best_vs)])

        table_title = f"Stage {t+1} ({opt_mode}, op={combine_op})"
        table_body = tabulate(rows, headers=headers, tablefmt="grid", stralign="center", numalign="center")
        table_text = f"{table_title}\n{table_body}"
        tables.append(table_text)
        if print_tables:
            print(table_text, end="\n\n")

    # Rekonstruksi salah satu path optimal (pakai successor pertama)
    path = [start]
    u = start
    while u != goal:
        vs = policy.get(u)
        if not vs:
            raise RuntimeError(f"Path buntu di node {u}. Periksa edges.")
        v = vs[0]  # pilih kandidat pertama
        path.append(v)
        u = v

    optimal_cost = f_star[start]
    return StagecoachResult(optimal_cost=optimal_cost, path=path, tables=tables, f_star=f_star, policy=policy)



# ---------- REKONSTRUKSI SEMUA JALUR ----------

def reconstruct_all_paths(policy: Dict[str, List[str]], start: str, goal: str) -> List[List[str]]:
    """Kembalikan semua path optimal dari start ke goal berdasarkan policy."""
    paths: List[List[str]] = []

    def dfs(u: str, current: List[str]):
        if u == goal:
            paths.append(current.copy())
            return
        for v in policy.get(u, []):
            dfs(v, current + [v])

    dfs(start, [start])
    return paths


# ---------- PLOTTER MULTI-PATH ----------

def draw_stagecoach_graph(
    layers: List[List[str]],
    edges: Dict[str, Dict[str, float]],
    start: Optional[str] = None,
    goal: Optional[str] = None,
    opt_mode: str = "min",
    paths: Optional[List[List[str]]] = None,
    save_path: Optional[str] = None,
    node_radius: float = 0.16,
    x_gap: float = 2.0,
    y_gap: float = 1.2,
    linewidth: float = 1.0,
    opt_linewidth: float = 3.0,
    fontsize: int = 10,
):
    if paths is None:
        if start is None or goal is None:
            raise ValueError("Jika paths tidak diberikan, wajib isi start & goal.")
        res = solve_stagecoach_dp(layers, edges, start, goal, opt_mode=opt_mode, print_tables=False)
        paths = reconstruct_all_paths(res.policy, start, goal)

    # Posisi node
    coords: Dict[str, Tuple[float, float]] = {}
    for ix, L in enumerate(layers):
        ys = [-(len(L)-1)/2 + j for j in range(len(L))]
        for j, u in enumerate(L):
            coords[u] = (ix * x_gap, ys[j] * y_gap)

    fig, ax = plt.subplots(figsize=(10, 5))

    # Edges biasa (hitam tipis)
    for u, nbrs in edges.items():
        x0, y0 = coords[u]
        for v, c in nbrs.items():
            x1, y1 = coords[v]
            ax.plot([x0, x1], [y0, y1], color="black", linewidth=linewidth)
            lx, ly = 0.4*x0+0.6*x1, 0.4*y0+0.6*y1
            lab = int(c) if float(c).is_integer() else c
            ax.text(lx, ly, f"{lab}", fontsize=fontsize, ha="center", va="center", color="black")

    # Jalur optimal (warna berbeda, tebal)
    colors = itertools.cycle(cm.tab10.colors)
    for path in paths:
        col = next(colors)
        for u, v in zip(path[:-1], path[1:]):
            x0, y0 = coords[u]
            x1, y1 = coords[v]
            ax.plot([x0, x1], [y0, y1], color=col, linewidth=opt_linewidth)

    # Node
    for u, (x, y) in coords.items():
        circ = plt.Circle((x, y), radius=node_radius, fill=False, edgecolor="black", linewidth=linewidth)
        ax.add_patch(circ)
        ax.text(x, y, u, fontsize=fontsize, ha="center", va="center", color="black")

    # Dekorasi
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_xlim(-x_gap*0.6, x_gap*(len(layers)-1)+x_gap*0.6)
    ax.set_ylim(min(y for _, y in coords.values()) - y_gap,
                max(y for _, y in coords.values()) + y_gap)
    # ax.set_title("Stagecoach – semua jalur optimal", color="black")

    if save_path:
        plt.savefig(save_path, bbox_inches="tight", dpi=200)
    plt.show()