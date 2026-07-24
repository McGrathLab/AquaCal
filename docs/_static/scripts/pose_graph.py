"""Pose graph diagram for AquaCal documentation.

Generates the bipartite camera/frame graph used during Stage 2 (extrinsic
initialization) and highlights the directed discovery edges the priority-heap
traversal actually produced.

Node types:
    - Camera nodes (circles, CAMERA_COLOR): cam0, cam1, cam2, cam3
    - Frame/board nodes (rounded boxes, BOARD_COLOR): F1, F2, F3

Edges connect a camera to each frame it observes. This script does not
hardcode which edges the traversal used: it builds a small four-camera /
three-frame
:class:`~aquacal.config.schema.DetectionResult` fixture, calls
:func:`aquacal.calibration.extrinsics.build_pose_graph` to get the library's
own adjacency, and then replays the same priority-heap loop
``estimate_extrinsics`` runs (seed the reference camera, pop the highest
corner-count entry, resolve every unvisited neighbour, push new entries)
to classify each edge as a directed discovery edge or an undirected
redundant observation edge.

Known limitation: the adjacency comes from the library, but the heap loop
below is a *replay* of ``estimate_extrinsics``'s policy, not a call into it --
``estimate_extrinsics`` needs full intrinsics and detections and returns poses
rather than the traversal order this figure needs. Nothing currently ties the
two together, so a change to the real prioritisation (the ``(-num_corners,
node)`` key, or the finalise-on-first-discovery rule) must be mirrored here or
the figure will quietly misrepresent the algorithm.
"""

import heapq
import sys
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

from aquacal.calibration.extrinsics import build_pose_graph
from aquacal.config.schema import Detection, DetectionResult, FrameDetections

# Ensure palette.py is importable regardless of working directory
sys.path.insert(0, str(Path(__file__).parent))
from palette import (  # noqa: E402
    BOARD_COLOR,
    CAMERA_COLOR,
    GRID_COLOR,
    LABEL_COLOR,
    RAY_AIR,
    WATER_SURFACE,
)

# ---------------------------------------------------------------------------
# Fixture: 4 cameras, 3 frames, corner counts taken from the paper supplement's
# own worked example (main.tex Figure 2 reference topology). Corner counts
# only drive traversal priority; the discovery/redundant classification below
# is computed by replaying the real heap logic, not by hand.
# ---------------------------------------------------------------------------

_FRAME_OBSERVATIONS: dict[int, dict[str, int]] = {
    1: {"cam0": 31, "cam2": 22},  # F1
    2: {"cam0": 48, "cam1": 42},  # F2
    3: {"cam1": 39, "cam2": 35, "cam3": 27},  # F3
}
_FRAME_LABELS = {1: "F1", 2: "F2", 3: "F3"}


def _build_detection_result() -> DetectionResult:
    """Construct the toy 4-camera / 3-frame fixture as a real DetectionResult."""
    frames: dict[int, FrameDetections] = {}
    all_cameras: set[str] = set()
    for frame_idx, cam_corners in _FRAME_OBSERVATIONS.items():
        detections = {}
        for cam_name, n_corners in cam_corners.items():
            all_cameras.add(cam_name)
            detections[cam_name] = Detection(
                corner_ids=np.arange(n_corners, dtype=np.int32),
                corners_2d=np.zeros((n_corners, 2), dtype=np.float64),
            )
        frames[frame_idx] = FrameDetections(frame_idx=frame_idx, detections=detections)
    return DetectionResult(
        frames=frames,
        camera_names=sorted(all_cameras),
        total_frames=len(frames),
    )


def _replay_traversal(pose_graph, reference_camera: str) -> list[tuple[str, str]]:
    """Replay the priority-heap traversal and return discovery edges in order.

    Mirrors ``estimate_extrinsics``'s loop (``extrinsics.py`` heap section):
    seed the heap with the reference camera, pop the highest-corner-count
    entry, resolve every unvisited neighbour in that single pop, and push
    each newly-resolved node back onto the heap keyed by its corner count.
    Neighbour order within a pop does not affect which edges are discovered
    (every unvisited neighbour is resolved regardless of iteration order),
    so both node types are iterated in sorted order here purely for a
    deterministic rendering — this is not a behavioral difference from the
    library's own unsorted camera-branch iteration.

    Returns:
        List of (from_node, to_node) discovery edges, in traversal order.
        Node names are camera names or ``"F{idx}"`` display labels.
    """
    heap: list[tuple[int, str]] = [(0, reference_camera)]
    visited: set[str] = {reference_camera}
    discovery_edges: list[tuple[str, str]] = []

    while heap:
        _priority, node = heapq.heappop(heap)
        neighbors = sorted(pose_graph.adjacency.get(node, []))
        for neighbor in neighbors:
            if neighbor in visited:
                continue
            visited.add(neighbor)
            corners = _corner_count(node, neighbor)
            discovery_edges.append((node, neighbor))
            heapq.heappush(heap, (-corners, neighbor))

    return discovery_edges


def _corner_count(node_a: str, node_b: str) -> int:
    """Corner count for the observation edge between a camera and a frame node."""
    if node_a.startswith("f"):
        frame_idx, cam_name = int(node_a[1:]), node_b
    else:
        frame_idx, cam_name = int(node_b[1:]), node_a
    return _FRAME_OBSERVATIONS[frame_idx][cam_name]


def _display(node: str) -> str:
    """Map a pose-graph node name to its display label ("f2" -> "F2")."""
    return _FRAME_LABELS[int(node[1:])] if node.startswith("f") else node


def _draw_camera_node(ax, pos, label, is_reference=False, node_size=0.06):
    """Draw a camera node as a circle with label."""
    x, y = pos
    edge_color = RAY_AIR if is_reference else CAMERA_COLOR
    lw = 3.5 if is_reference else 1.5
    circle = plt.Circle(
        (x, y), node_size, color=CAMERA_COLOR, ec=edge_color, linewidth=lw, zorder=3
    )
    ax.add_patch(circle)
    ax.text(
        x,
        y,
        label,
        ha="center",
        va="center",
        fontsize=9,
        fontweight="bold" if is_reference else "normal",
        color="white",
        zorder=4,
    )


def _draw_frame_node(ax, pos, label, node_size=0.06):
    """Draw a frame/board node as a rounded rectangle."""
    x, y = pos
    rect = mpatches.FancyBboxPatch(
        (x - node_size, y - node_size * 0.7),
        node_size * 2,
        node_size * 1.4,
        boxstyle="round,pad=0.01",
        facecolor=BOARD_COLOR,
        edgecolor="#CC8800",
        linewidth=1.5,
        zorder=3,
    )
    ax.add_patch(rect)
    ax.text(
        x,
        y,
        label,
        ha="center",
        va="center",
        fontsize=9,
        fontweight="bold",
        color=LABEL_COLOR,
        zorder=4,
    )


def _draw_edge(ax, src_pos, dst_pos, *, directed, badge=None, node_size=0.06):
    """Draw an edge between two node positions, clipped to node boundaries.

    Directed discovery edges are thick and arrowed in WATER_SURFACE, pointing
    from the already-known node to the node it determined. Redundant
    observation edges are thin, grey, and undirected (no arrowhead).
    """
    x0, y0 = src_pos
    x1, y1 = dst_pos
    dx, dy = x1 - x0, y1 - y0
    dist = float(np.hypot(dx, dy))
    ux, uy = dx / dist, dy / dist

    x_start, y_start = x0 + ux * node_size, y0 + uy * node_size
    x_end, y_end = x1 - ux * node_size, y1 - uy * node_size

    color = WATER_SURFACE if directed else GRID_COLOR
    lw = 2.4 if directed else 1.0
    alpha = 1.0 if directed else 0.55
    zorder = 2 if directed else 1

    ax.annotate(
        "",
        xy=(x_end, y_end),
        xytext=(x_start, y_start),
        arrowprops=dict(arrowstyle="-|>" if directed else "-", color=color, lw=lw),
        alpha=alpha,
        zorder=zorder,
    )

    if badge is not None:
        mid_x, mid_y = (x_start + x_end) / 2, (y_start + y_end) / 2
        ax.add_patch(
            plt.Circle(
                (mid_x, mid_y),
                0.028,
                facecolor="white",
                edgecolor=WATER_SURFACE,
                linewidth=1.0,
                zorder=5,
            )
        )
        ax.text(
            mid_x,
            mid_y,
            badge,
            ha="center",
            va="center",
            fontsize=6.5,
            fontweight="bold",
            color=WATER_SURFACE,
            zorder=6,
        )


def generate(output_dir: Path) -> None:
    """Generate and save the pose graph diagram.

    Args:
        output_dir: Directory where the PNG will be saved.
    """
    detections = _build_detection_result()
    pose_graph = build_pose_graph(detections, min_cameras=2)
    reference_camera = pose_graph.camera_names[0]

    discovery_edges = _replay_traversal(pose_graph, reference_camera)
    # Keep the ordered (from_node, to_node) pair alongside the unordered lookup key —
    # the frozenset is needed for membership testing against `all_edges` (which is
    # always stored as (cam, frame)), but only the ordered tuple preserves which
    # endpoint the traversal actually discovered *from*.
    discovery_direction = {
        frozenset((_display(a), _display(b))): (_display(a), _display(b))
        for a, b in discovery_edges
    }
    badge_lookup = {
        frozenset((_display(a), _display(b))): str(i + 1)
        for i, (a, b) in enumerate(discovery_edges)
    }

    all_edges = [
        (cam, _FRAME_LABELS[frame_idx])
        for frame_idx, cam_corners in _FRAME_OBSERVATIONS.items()
        for cam in cam_corners
    ]

    camera_nodes = sorted(pose_graph.camera_names)
    frame_nodes = [_FRAME_LABELS[idx] for idx in sorted(pose_graph.frame_indices)]

    cam_x, frame_x = 0.18, 0.82
    cam_spacing = 1.0 / (len(camera_nodes) + 1)
    frame_spacing = 1.0 / (len(frame_nodes) + 1)
    node_pos = {}
    for i, cam in enumerate(camera_nodes):
        node_pos[cam] = (cam_x, 1.0 - (i + 1) * cam_spacing)
    for i, frame in enumerate(frame_nodes):
        node_pos[frame] = (frame_x, 1.0 - (i + 1) * frame_spacing)

    fig, ax = plt.subplots(figsize=(8, 5.5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal")
    ax.axis("off")

    node_size = 0.06

    for cam, frame in all_edges:
        key = frozenset((cam, frame))
        directed = key in discovery_direction
        if directed:
            src, dst = discovery_direction[key]
            src_pos, dst_pos = node_pos[src], node_pos[dst]
        else:
            src_pos, dst_pos = node_pos[cam], node_pos[frame]
        badge = badge_lookup.get(key) if directed else None
        _draw_edge(
            ax,
            src_pos,
            dst_pos,
            directed=directed,
            badge=badge,
            node_size=node_size,
        )

    for cam in camera_nodes:
        _draw_camera_node(
            ax,
            node_pos[cam],
            cam,
            is_reference=(cam == reference_camera),
            node_size=node_size,
        )
    for frame in frame_nodes:
        _draw_frame_node(ax, node_pos[frame], frame, node_size=node_size)

    ax.text(
        cam_x,
        0.97,
        "Cameras",
        ha="center",
        va="top",
        fontsize=10,
        fontweight="bold",
        color=LABEL_COLOR,
    )
    ax.text(
        frame_x,
        0.97,
        "Board Frames",
        ha="center",
        va="top",
        fontsize=10,
        fontweight="bold",
        color=LABEL_COLOR,
    )

    ax.set_title(
        "Stage 2: Pose Graph\n(cameras linked through shared board observations)",
        fontsize=11,
        color=LABEL_COLOR,
        pad=6,
    )

    legend_patches = [
        mpatches.Patch(facecolor=CAMERA_COLOR, label="Camera node"),
        mpatches.Patch(
            facecolor=BOARD_COLOR, edgecolor="#CC8800", label="Board frame node"
        ),
        mpatches.Patch(facecolor=WATER_SURFACE, label="Discovery edge (directed)"),
        mpatches.Patch(
            facecolor=GRID_COLOR,
            alpha=0.6,
            label="Redundant observation edge (undirected)",
        ),
    ]
    ax.legend(
        handles=legend_patches,
        loc="lower center",
        fontsize=8,
        framealpha=0.9,
        edgecolor=GRID_COLOR,
        ncol=2,
        bbox_to_anchor=(0.5, -0.01),
    )

    ref_x, ref_y = node_pos[reference_camera]
    ax.annotate(
        "reference\n(R=I, t=0)",
        xy=(ref_x - node_size, ref_y),
        xytext=(ref_x - 0.18, ref_y),
        ha="right",
        va="center",
        fontsize=7.5,
        color=RAY_AIR,
        arrowprops=dict(arrowstyle="->", color=RAY_AIR, lw=1.2),
    )

    plt.tight_layout()
    output_path = Path(output_dir) / "pose_graph.png"
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved: {output_path}")


if __name__ == "__main__":
    import matplotlib

    matplotlib.use("Agg")
    output_dir = Path(__file__).parent.parent / "diagrams"
    output_dir.mkdir(parents=True, exist_ok=True)
    generate(output_dir)
