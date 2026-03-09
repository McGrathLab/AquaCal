# Key Techniques in AquaCal Calibration Pipeline

A survey of the principal algorithms and methods underlying AquaCal's
refractive multi-camera calibration workflow, suitable for citation in an
accompanying journal article.

---

## 1. Zhang's Flexible Camera Calibration

Stage 1 uses Zhang's planar-pattern method (via `cv2.calibrateCamera`) to
recover per-camera intrinsics (focal length, principal point, distortion
coefficients) from checkerboard images captured in air.

## 2. Equidistant Fisheye Model

Wide-angle auxiliary cameras are calibrated with the equidistant (Kannala–Brandt)
fisheye projection model (`cv2.fisheye.calibrate`), which replaces the standard
Brown–Conrady distortion with a 4-coefficient radial mapping suited to FOVs
exceeding 120°.

## 3. Rational Distortion Model (8-Coefficient)

An optional extension to Stage 1 replaces the 5-coefficient Brown–Conrady model
with an 8-coefficient rational function that better captures distortion in
moderate wide-angle (non-fisheye) lenses.

## 4. Perspective-n-Point (PnP) Pose Estimation

Board poses are initialized via iterative PnP (`cv2.solvePnP` with the
ITERATIVE flag), providing 6-DOF pose estimates from known 3D–2D
correspondences.

## 5. Refractive PnP

A custom PnP variant refines board poses through Snell's law by casting the
problem as a Levenberg–Marquardt minimization of refractive reprojection error,
using the non-refractive PnP solution as the initial guess.

## 6. BFS Pose-Graph Traversal with Priority Weighting

Extrinsic initialization constructs a bipartite graph (cameras and frames as
nodes, observations as edges) and traverses it with a priority-queue BFS that
favors high-corner-count observations, reducing error accumulation along pose
chains.

## 7. Weighted Chordal L2 Mean of Rotations

During Stage 2 extrinsic initialization, when multiple frames yield independent
rotation estimates for the same camera (or board), these are fused into a single
consensus rotation by computing their corner-count-weighted Frobenius-norm
(chordal L2) mean and projecting the result back onto SO(3) via SVD with a
determinant correction.

## 8. Snell's Law — 3D Vector Form

All refractive geometry is built on the 3D vector formulation of Snell's law,
with explicit total-internal-reflection detection and automatic interface-normal
orientation handling.

## 9. Newton–Raphson Refractive Projection (Flat Interface)

For the common horizontal-interface case, forward projection is cast as a 1D
root-finding problem and solved with Newton–Raphson iterations seeded by the
pinhole intersection point, converging in 2–4 iterations for roughly 50× speedup
over general solvers.

## 10. Brent's Method Refractive Projection (General Interface)

When the interface is tilted (non-horizontal), forward projection falls back to
Brent's bracketed root-finding method, which guarantees convergence without
requiring a derivative.

## 11. Trust-Region Reflective Bundle Adjustment

Stages 3 and 4 jointly optimize camera extrinsics, global water-surface height,
and board poses via `scipy.optimize.least_squares` with the trust-region
reflective (TRF) method.

## 12. Sparse Finite-Difference Jacobians via Column Grouping

The Jacobian is approximated with finite differences using Curtis–Powell–Reid
column grouping (implemented via `scipy.optimize._numdiff.group_columns`),
exploiting the block-sparse structure of the bundle-adjustment problem to reduce
the number of function evaluations from N to ~log(N) while retaining
compatibility with the exact (QR-based) trust-region solver.

## 13. Rodrigues (Axis-Angle) Rotation Parameterization

All rotations are parameterized as 3-element Rodrigues vectors (exponential map)
throughout the optimization, providing a minimal, singularity-free
representation with efficient conversion to rotation matrices via
`cv2.Rodrigues`.

## 14. Huber (and Cauchy) Robust Loss Functions

The bundle adjustment uses Huber loss by default, with configurable alternatives
(soft-L1, Cauchy), to down-weight outlier corner detections without hard
rejection.

## 15. Global Water-Surface Z Parameterization

Instead of per-camera interface distances, a single global water-surface height
(`water_z`) is optimized; per-camera physical gaps are derived as
`h_c = water_z − C_z`, eliminating the inherent height/distance degeneracy by
construction.

## 16. Post-Hoc Auxiliary Camera Registration

Auxiliary cameras are registered against the fixed board poses from Stage 3 in
a separate 6-DOF (or 10-DOF with intrinsics) optimization, preventing
lower-quality observations from degrading the primary joint solution.

## 17. Refractive Ray Tracing (Back-Projection)

Pixel rays are back-projected through the air–water interface via Snell's law to
obtain refracted ray origins and directions in the underwater volume, enabling
downstream triangulation and 3D reconstruction.

---

## Citations

| # | Technique | Reference |
|---|-----------|-----------|
| 1 | Zhang's camera calibration | Z. Zhang, "A Flexible New Technique for Camera Calibration," *IEEE Trans. PAMI*, vol. 22, no. 11, pp. 1330–1334, 2000. |
| 2 | Equidistant fisheye model | J. Kannala and S. S. Brandt, "A Generic Camera Model and Calibration Method for Conventional, Wide-Angle, and Fish-Eye Lenses," *IEEE Trans. PAMI*, vol. 28, no. 8, pp. 1335–1340, 2006. |
| 3 | Rational distortion model | J. Mallon and P. F. Whelan, "Precise Radial Un-distortion of Images," in *Proc. ICPR*, 2004; also documented in OpenCV as `CALIB_RATIONAL_MODEL`. |
| 4 | Iterative PnP | D. G. Lowe, "Fitting Parameterized Three-Dimensional Models to Images," *IEEE Trans. PAMI*, vol. 13, no. 5, pp. 441–450, 1991; OpenCV implementation based on iterative Gauss–Newton refinement. |
| 5 | Refractive PnP | Adaptation of standard PnP to refractive media; see A. Agrawal et al., "A Theory of Multi-Layer Flat Refractive Geometry," in *Proc. CVPR*, 2012. |
| 6 | BFS pose-graph traversal | General graph-based extrinsic initialization; see C. Wu, "VisualSFM: A Visual Structure from Motion System," 2011, http://ccwu.me/vsfm/; priority weighting is a local contribution. |
| 7 | Chordal L2 rotation mean | R. Hartley et al., "Rotation Averaging," *IJCV*, vol. 103, no. 3, pp. 267–305, 2013. |
| 8 | Snell's law (3D vector form) | M. Born and E. Wolf, *Principles of Optics*, 7th ed., Cambridge Univ. Press, 1999, Ch. 3. |
| 9 | Newton–Raphson root finding | J. F. Traub, *Iterative Methods for the Solution of Equations*, Prentice-Hall, 1964; applied to refractive projection as in T. Treibitz et al., "Flat Refractive Geometry," *IEEE Trans. PAMI*, vol. 34, no. 1, pp. 51–65, 2012. |
| 10 | Brent's method | R. P. Brent, *Algorithms for Minimization Without Derivatives*, Prentice-Hall, 1973; SciPy implementation via `scipy.optimize.brentq`. |
| 11 | Trust-region reflective method | M. A. Branch et al., "A Subspace, Interior, and Conjugate Gradient Method for Large-Scale Bound-Constrained Minimization Problems," *SIAM J. Sci. Comput.*, vol. 21, no. 1, pp. 1–23, 1999. |
| 12 | Curtis–Powell–Reid column grouping | A. R. Curtis et al., "On the Estimation of Sparse Jacobian Matrices," *IMA J. Appl. Math.*, vol. 13, no. 1, pp. 117–119, 1974; T. F. Coleman and J. J. Moré, "Estimation of Sparse Jacobian Matrices and Graph Coloring Problems," *SIAM J. Numer. Anal.*, vol. 20, no. 1, pp. 187–209, 1983. |
| 13 | Rodrigues parameterization | O. Rodrigues, "Des lois géométriques qui régissent les déplacements d'un système solide…," *J. Math. Pures Appl.*, vol. 5, pp. 380–440, 1840; practical treatment in R. Hartley and A. Zisserman, *Multiple View Geometry in Computer Vision*, 2nd ed., Cambridge Univ. Press, 2003, §A4.3. |
| 14 | Huber robust loss | P. J. Huber, "Robust Estimation of a Location Parameter," *Ann. Math. Statist.*, vol. 35, no. 1, pp. 73–101, 1964. |
| 15 | Flat refractive geometry | T. Treibitz et al., "Flat Refractive Geometry," *IEEE Trans. PAMI*, vol. 34, no. 1, pp. 51–65, 2012; A. Agrawal et al., "A Theory of Multi-Layer Flat Refractive Geometry," in *Proc. CVPR*, 2012. |
| 16 | Bundle adjustment | B. Triggs et al., "Bundle Adjustment — A Modern Synthesis," in *Vision Algorithms: Theory and Practice*, LNCS 1883, Springer, 2000, pp. 298–372. |
| 17 | Refractive ray tracing | A. Agrawal et al., "A Theory of Multi-Layer Flat Refractive Geometry," in *Proc. CVPR*, 2012; M. Born and E. Wolf, *Principles of Optics*, 7th ed., Ch. 3. |
