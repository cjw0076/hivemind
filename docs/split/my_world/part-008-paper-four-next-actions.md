<!--
Source: docs/my_world.md
Source lines: 4901-5600
Source byte range: 134436-151666
Split title source: first-text
Split note: Source is mostly a raw conversation export with sparse Markdown headings; split into stable line windows while preserving order.
-->

# Part 008: 지금 당장 할 일

Provenance: `docs/my_world.md` lines `4901-5600`, bytes `134436-151666`.

Local structure markers:

- Source line 4985: 0. 전체 한 줄 구조
- Source line 5004: 1. Model Architecture
- Source line 5203: 2. Network Architecture
- Source line 5357: 3. Loss Architecture
- Source line 5400: 4. Auditor Architecture
- Source line 5464: 5. Protocol DSL Architecture
- Source line 5514: 6. System Architecture
- Source line 5570: 7. Experiment Runner Architecture

---


지금 당장 할 일
1순위: auditor.py
가장 먼저 만든다.

입력:

obs_loss
heldout_loss
param_mean/std
ensemble variance
basis set
protocol type
known target params if synthetic
출력:

label
reason
failure mode
recommended next measurement
예시 출력:

{
  "label": "NON_IDENTIFIABLE",
  "reason": "KL_x and KL_p are near zero, but purity estimates split across ensemble.",
  "suggested_probe": "add rotated quadrature theta=pi/4"
}
2순위: protocol.py
P15 hardcode를 DSL로 바꾼다.

목표는 sequential intervention 실험을 쉽게 생성하는 것.

x@t1
x@t1 → p@t2
x@t1 → θ@t2
wrong-order
wrong-basis
no-collapse
3순위: Phase-12 v0 experiment
가장 작은 identifiability map.

basis: {x}, {x,p}, {x,p,π/4}
γ: 0, 0.05, 0.2, 0.5
rank: 1, 4, 8
state: boosted cat
arms: matched / mismatch
metrics: KL, purity error, γ error, V L2, ensemble spread
auditor label: 5-class
최종 판단
Claude 평가를 반영하면, 내 제안은 이렇게 재정렬돼야 해.

항목	결정
MIGS-World 이름	지금은 보류
새 대형 아키텍처 디렉토리	만들지 않음
기존 q_state_model	유지
바로 추가할 것	auditor.py, protocol.py, quadrature.py, mismatch.py
다음 논문	Identifiability Map
Posterior	Bayesian posterior가 아니라 ensemble disagreement로 시작
Rotated quadrature	optional 아님, Phase-12 핵심
Paper 1 pole-zero	diagnostic probe로 재삽입
Active / symbolic / ontology	지금은 보류
한 문장으로 정리하면:

MIGS-World는 북극성 아키텍처이고, 지금 들어갈 실제 아키텍처는 Identifiability Auditor + Protocol DSL 중심의 Phase-12 stack이다.

이게 가장 정직하고 강한 다음 스텝이야.



모델, network, 시스템 아키텍쳐는 ?


Thought for 16s
응. 이제는 3층으로 나눠야 해.

Model architecture: 수학적으로 무엇을 학습하는가

Network architecture: PyTorch 모듈이 어떻게 생기는가

System architecture: 코드/실험/로그/판정 파이프라인이 어떻게 돌아가는가

Claude 평가를 반영하면, 지금은 “MIGS-World 전체”가 아니라 Phase-12 Identifiability Stack으로 가야 한다. 즉, 기존 q_state_model/을 유지하고, auditor.py, protocol.py, quadrature.py, mismatch.py를 추가하는 구조가 맞다. Claude도 “MIGS-World는 북극성 아키텍처이고, 지금은 Identifiability Auditor + Protocol DSL 중심의 Phase-12 stack”이 적절하다고 평가했지. 


0. 전체 한 줄 구조
Born marginal observations
+ measurement/intervention protocol
        ↓
candidate hidden quantum worlds ensemble
        ↓
ρ₀, H, D, M reconstruction
        ↓
x / p / rotated θ Born rendering
        ↓
loss + held-out + intervention consistency
        ↓
Identifiability Auditor
        ↓
IDENTIFIABLE / NON_IDENTIFIABLE / MODEL_MISMATCH / OPTIMIZATION_FAILURE
핵심은 이거야.

모델은 정답 하나를 찾는 게 아니라, 관측을 똑같이 설명하는 hidden world 후보들이 얼마나 수렴/분산되는지를 본다.

1. Model Architecture
1.1 입력
입력은 단순 데이터셋이 아니라 관측 프로토콜이야.

D = {
  protocol,
  observed marginals
}
예:

Protocol:
  Evolve to t1
  Observe x
  Evolve to t2
  Observe p
  Measure x at t3
  Evolve to t4
  Observe θ=π/4
관측값:

p_x(x, t)
p_p(p, t)
p_θ(q, t)
post-intervention p_x, p_p, p_θ
1.2 hidden world 후보
각 모델 instance는 하나의 hidden world 후보를 가진다.

W_k = {ρ₀, H, D, M}
각각 의미는:

객체	의미
ρ₀	초기 quantum state
H	Hamiltonian / potential
D	Lindblad dissipation
M	measurement intervention / POVM
O_b	basis b에서 Born observation map
여기서 k는 ensemble seed 또는 model family index다.

1.3 State module: ρ₀
초기 상태는 low-rank density matrix로 둔다.

ρ₀ = L L† / Tr(L L†)
구조:

L ∈ C^(N × r)
N: grid size

r: rank

rank 1이면 pure state

rank > 1이면 mixed state

PyTorch 관점:

L_re, L_im = StateNet(x_grid)  # [N, r]
L = L_re + 1j * L_im
rho0 = L @ L.conj().T
rho0 = rho0 / trace(rho0)
이 구조의 장점:

Hermitian 보장

PSD 보장

trace 1 보장

mixed/decoherent state 표현 가능

1.4 Hamiltonian module: H
초기 Hamiltonian은:

H = T + V(x)
여기서 T는 kinetic operator, V(x)는 학습 대상.

단, V(x)를 완전 자유 MLP로만 두면 안 돼. P13에서 봤듯이 ρ₀와 V가 같이 움직이면 joint degeneracy가 생긴다.

그래서 초기 구조는 이렇게 가야 해.

Vθ(x) = a0 + a1 x + a2 x² + a3 x³ + a4 x⁴ + ε · MLP_residual(x)
즉:

harmonic prior

polynomial basis

작은 residual MLP

sparsity penalty

추천 구조:

class PotentialNet(nn.Module):
    def __init__(self):
        self.coeffs = nn.Parameter(torch.zeros(num_basis))
        self.residual = SmallMLP(1, hidden, 1)
        self.residual_scale = nn.Parameter(torch.tensor(-4.0))  # sigmoid로 작게 시작

    def forward(self, x):
        basis = [1, x, x**2, x**3, x**4]
        V_basis = sum(c * b for c, b in zip(self.coeffs, basis))
        eps = torch.sigmoid(self.residual_scale)
        return V_basis + eps * self.residual(x)
1.5 Dissipation module: D
Lindblad 형태:

dρ/dt = -i[H,ρ] + Σ_k γ_k (L_k ρ L_k† - 1/2 {L_k†L_k, ρ})
Phase-12 v0에서는 이렇게 시작한다.

L₁ = x      position dephasing
γ ≥ 0
그다음 mismatch arm에서 확장한다.

L ∈ {x, p, a, a†, learned diagonal, learned low-rank}
구조:

class LindbladModule(nn.Module):
    def __init__(self, jump_family="x"):
        self.raw_gamma = nn.Parameter(torch.tensor(-3.0))
        self.jump_family = jump_family

    def gamma(self):
        return F.softplus(self.raw_gamma)

    def dissipator(self, rho, L):
        gamma = self.gamma()
        LdL = L.conj().T @ L
        return gamma * (L @ rho @ L.conj().T - 0.5 * (LdL @ rho + rho @ LdL))
1.6 Propagator module
시간 전개:

ρ(t + Δt) = Φ_H,D(ρ(t))
v0는 RK4면 충분하다.

def rhs(rho, H, dissipator):
    return -1j * (H @ rho - rho @ H) + dissipator(rho)

def rk4_step(rho, dt):
    k1 = rhs(rho)
    k2 = rhs(rho + 0.5 * dt * k1)
    k3 = rhs(rho + 0.5 * dt * k2)
    k4 = rhs(rho + dt * k3)
    return rho + dt * (k1 + 2*k2 + 2*k3 + k4) / 6
추후:

v0: RK4
v1: matrix exponential
v2: split-step
v3: tensor network / neural operator
1.7 Observation heads
학습 신호는 Wigner가 아니라 Born marginal이다.

Position
p_x = diag(ρ)
Momentum
p_p = diag(F ρ F†)
Rotated quadrature
이건 이제 optional이 아니라 mandatory다.

x_θ = x cosθ + p sinθ
p_θ = diag(U_θ ρ U_θ†)
초기 구현:

rho_theta = U_theta @ rho @ U_theta.conj().T
p_theta = torch.real(torch.diag(rho_theta))
U_theta는 처음에는 precomputed fractional Fourier transform 계열로 둔다.

기본 basis set:

B0 = {x}
B1 = {x, p}
B2 = {x, p, π/4}
B3 = {x, p, π/4, 3π/4}
B4 = uniform θ grid
1.8 Intervention module
측정은 passive observation이 아니라 state update다.

ρ' = M ρ M† / Tr(M ρ M†)
Position Gaussian measurement:

M_x[i] = exp(-(x_i - x_obs)² / 4σ_m²)
구조:

class InterventionModule(nn.Module):
    def position_collapse(self, rho, x_grid, x_obs, sigma):
        m = torch.exp(-((x_grid - x_obs) ** 2) / (4 * sigma ** 2))
        M = torch.diag(m).to(rho.dtype)
        rho_new = M @ rho @ M.conj().T
        return rho_new / torch.trace(rho_new).real
Momentum collapse:

ρ_p = FρF†
collapse in p basis
ρ' = F†ρ_p'F
Rotated collapse:

ρ_θ = UθρUθ†
collapse in θ basis
ρ' = Uθ†ρ_θ'Uθ
2. Network Architecture
지금은 “amortized encoder”를 만들면 안 된다. 즉:

observation history → ρ₀, H, D posterior
이건 아직 이르다.

지금은 direct optimization network가 맞다.

각 synthetic target마다
ρ₀, V, γ, M parameters를 직접 최적화
2.1 전체 PyTorch module
class BornMarginalWorld(nn.Module):
    def __init__(
        self,
        grid,
        rank=4,
        potential_type="basis_residual",
        jump_family="x_dephasing",
        quadrature_thetas=(0.785,),
    ):
        super().__init__()

        self.state = LowRankStateNet(grid, rank)
        self.hamiltonian = HamiltonianNet(grid, potential_type)
        self.dissipation = LindbladNet(grid, jump_family)
        self.propagator = LindbladPropagator(grid)
        self.observer = BornObserver(grid, quadrature_thetas)
        self.intervention = InterventionModule(grid)

    def forward(self, protocol):
        rho = self.state.rho0()
        outputs = []

        for event in protocol:
            if event.kind == "evolve":
                H = self.hamiltonian()
                D = self.dissipation
                rho = self.propagator(rho, H, D, event.dt)

            elif event.kind == "measure":
                rho = self.intervention.apply(
                    rho,
                    basis=event.basis,
                    value=event.value,
                    sigma=event.sigma,
                    theta=event.theta,
                )

            elif event.kind == "observe":
                pred = self.observer(
                    rho,
                    basis=event.basis,
                    theta=event.theta,
                )
                outputs.append((event.name, pred))

        return outputs
2.2 StateNet
class LowRankStateNet(nn.Module):
    def __init__(self, x_grid, rank, hidden=128):
        self.x_grid = x_grid
        self.rank = rank
        self.net = MLP(1, hidden, 2 * rank)

    def L(self):
        out = self.net(self.x_grid[:, None])
        L_re, L_im = out[..., :self.rank], out[..., self.rank:]
        return L_re + 1j * L_im

    def rho0(self):
        L = self.L()
        rho = L @ L.conj().T
        rho = rho / torch.trace(rho).real
        return rho
처음에는 coordinate MLP가 좋다.
나중에 필요하면 그냥 L 자체를 free parameter table로 두는 arm도 추가한다.

2.3 PotentialNet
class HamiltonianNet(nn.Module):
    def __init__(self, grid):
        self.grid = grid
        self.coeffs = nn.Parameter(torch.zeros(5))
        self.residual = MLP(1, 64, 1)
        self.residual_gate = nn.Parameter(torch.tensor(-5.0))

    def potential(self):
        x = self.grid.x
        basis = torch.stack([
            torch.ones_like(x),
            x,
            x**2,
            x**3,
            x**4,
        ], dim=-1)

        V_basis = basis @ self.coeffs
        eps = torch.sigmoid(self.residual_gate)
        V_res = self.residual(x[:, None]).squeeze(-1)
        return V_basis + eps * V_res

    def forward(self):
        T = self.grid.kinetic_operator
        V = torch.diag(self.potential())
        return T + V
2.4 BornObserver
class BornObserver(nn.Module):
    def __init__(self, grid, theta_list):
        self.F = grid.fourier_matrix
        self.U_theta = {
            theta: build_fractional_fourier(theta, grid)
            for theta in theta_list
        }

    def observe_x(self, rho):
        p = torch.real(torch.diag(rho))
        return normalize_prob(p)

    def observe_p(self, rho):
        rho_p = self.F @ rho @ self.F.conj().T
        p = torch.real(torch.diag(rho_p))
        return normalize_prob(p)

    def observe_theta(self, rho, theta):
        U = self.U_theta[theta]
        rho_t = U @ rho @ U.conj().T
        p = torch.real(torch.diag(rho_t))
        return normalize_prob(p)
2.5 Ensemble Network
Posterior라고 부르지 말고, 지금은 이렇게 부른다.

candidate reconstruction ensemble

class ReconstructionEnsemble:
    def __init__(self, model_factory, seeds):
        self.models = [
            model_factory(seed=s)
            for s in seeds
        ]

    def fit_all(self, data, protocol):
        results = []
        for model in self.models:
            result = train_model(model, data, protocol)
            results.append(result)
        return results
출력은:

K개의 ρ₀
K개의 V(x)
K개의 γ
K개의 purity curve
K개의 KL trajectory
그리고 Auditor가 분산을 본다.

3. Loss Architecture
전체 loss:

L = L_obs + L_dyn + L_int + L_phys + L_reg + L_heldout
지금은 L_id, L_sparse를 학습 loss로 넣지 말고, 분석/평가 단계로 빼는 게 안전하다.

3.1 Observation loss
L_obs =
  KL(p_x_true || p_x_pred)
+ KL(p_p_true || p_p_pred)
+ KL(p_θ_true || p_θ_pred)
3.2 Dynamics / held-out loss
time point 일부는 train, 일부는 held-out으로 둔다.

L_train_time
L_heldout_time
판정:

train low, held-out low → dynamics consistent
train low, held-out high → overfit / wrong dynamics
3.3 Intervention loss
L_int =
  post_KL
+ purity_jump_error
+ wrong_basis_degradation_score
+ wrong_order_degradation_score
여기서 wrong-basis/wrong-order는 loss로 낮추는 게 아니라 비교 arm으로 둔다.

3.4 Physical regularization
대부분 parameterization으로 보장한다.

제약	처리
ρ PSD	LL†
Tr(ρ)=1	normalization
γ ≥ 0	softplus
H Hermitian	real diagonal V, Hermitian T
probability normalization	normalize heads
추가 regularization:

V smoothness
residual scale penalty
gamma prior
rank penalty
4. Auditor Architecture
이게 Phase-12의 핵심이다.

4.1 입력
AuditInput = {
    "obs_loss_mean": ...,
    "obs_loss_std": ...,
    "heldout_loss_mean": ...,
    "V_l2_mean": ...,
    "V_l2_std": ...,
    "gamma_error_mean": ...,
    "gamma_error_std": ...,
    "purity_error_mean": ...,
    "purity_error_std": ...,
    "ensemble_param_variance": ...,
    "basis_set": ...,
    "protocol_type": ...,
    "mismatch_type": ...,
}
4.2 출력 label
IDENTIFIABLE
WEAKLY_IDENTIFIABLE
NON_IDENTIFIABLE
MODEL_MISMATCH
OPTIMIZATION_FAILURE
4.3 rule-based classifier
class IdentifiabilityAuditor:
    def classify(self, r):
        low_obs = r.obs_loss_mean < r.obs_threshold
        low_heldout = r.heldout_loss_mean < r.heldout_threshold
        low_param_var = r.param_variance < r.param_var_threshold
        high_seed_var = r.success_rate_between_0_and_1

        if low_obs and low_heldout and low_param_var:
            return "IDENTIFIABLE"

        if low_obs and low_heldout and not low_param_var:
            return "NON_IDENTIFIABLE"

        if low_obs and not low_heldout:
            return "MODEL_MISMATCH"

        if high_seed_var:
            return "OPTIMIZATION_FAILURE"

        return "WEAKLY_IDENTIFIABLE"
4.4 Auditor output 예시
{
  "label": "NON_IDENTIFIABLE",
  "reason": "KL_x and KL_p are near zero across all seeds, but purity and rho eigen-spectrum vary significantly.",
  "evidence": {
    "KL_x": 0.00001,
    "KL_p": 0.00003,
    "purity_std": 0.18,
    "gamma_std": 0.004
  },
  "suggested_next_probe": {
    "basis": "theta",
    "theta": 0.785,
    "time": 1.5708
  }
}
처음에는 suggested probe도 rule-based면 충분하다.

5. Protocol DSL Architecture
5.1 event types
@dataclass
class Evolve:
    dt: float
    name: str = ""

@dataclass
class Observe:
    basis: Literal["x", "p", "theta"]
    theta: float | None = None
    name: str = ""

@dataclass
class Measure:
    basis: Literal["x", "p", "theta"]
    value: float
    sigma: float
    theta: float | None = None
    name: str = ""
5.2 protocol examples
Basic trajectory
protocol = [
    Evolve(0.1),
    Observe("x", name="x_t1"),
    Observe("p", name="p_t1"),
    Evolve(0.1),
    Observe("x", name="x_t2"),
    Observe("p", name="p_t2"),
]
Sequential intervention
protocol = [
    Evolve(t1),
    Measure("x", value=0.0, sigma=0.5, name="Mx_t1"),
    Evolve(t2 - t1),
    Measure("theta", theta=math.pi / 4, value=0.0, sigma=0.5, name="Mtheta_t2"),
    Evolve(t3 - t2),
    Observe("x", name="x_post"),
    Observe("p", name="p_post"),
]
Wrong order arm
protocol_wrong_order = [
    Evolve(t1),
    Measure("theta", theta=math.pi / 4, value=0.0, sigma=0.5),
    Evolve(t2 - t1),
    Measure("x", value=0.0, sigma=0.5),
    Evolve(t3 - t2),
    Observe("x"),
    Observe("p"),
]
6. System Architecture
기존 q_state_model/을 유지하고, 새 대형 디렉토리는 만들지 않는다.

추천 구조:

quantum/q_state_model/
  core/
    state.py
    hamiltonian.py
    lindblad.py
    propagator.py
    observation.py
    intervention.py
    wigner.py

  protocol.py
  auditor.py
  quadrature.py
  mismatch.py

  experiments/
    p12_*.py
    p13_*.py
    p14_*.py
    p15_*.py
    p16_*.py

    phase12_identifiability_v0.py
    phase12_quadrature_sweep.py
    phase12_mismatch_sweep.py
    phase13_sequential_intervention_v0.py

  analysis/
    metrics.py
    audit_report.py
    phase_diagram.py
    plot_curves.py
    pole_zero_probe.py

  configs/
    identifiability_v0.yaml
    quadrature_sweep.yaml
    mismatch_sweep.yaml
    sequential_intervention.yaml

  results/
    phase12/
      runs/
      audit/
      figures/
      tables/

  docs/
    Q_STATE_MODEL_NARRATIVE.md
    SESSION_*.md
    PHASE12_IDENTIFIABILITY.md
7. Experiment Runner Architecture
7.1 config
experiment: identifiability_v0

grid:
  nx: 64
  x_max: 7.0

state:
  target: boosted_cat
  alpha: 2.0
  p0: 3.0

basis_sets:
  - ["x"]
  - ["x", "p"]
  - ["x", "p", "theta:0.785"]

gamma_values: [0.0, 0.05, 0.2, 0.5]
ranks: [1, 4, 8]
seeds: [0, 1, 2, 3, 4]

potential:
  target_family: harmonic
  model_family: basis_residual

jump:
  target_family: x_dephasing
  model_family: x_dephasing

training:
