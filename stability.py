"""重力式パラペットの概略安定計算モジュール。

河川堤防上の重力式パラペットを想定し、1 m 当たり断面で常時・地震時の
転倒、滑動、支持力、偏心、合力位置を照査するための軽量な計算ロジックです。
発注者提出用の計算書を作る Web プロトタイプと同じ考え方で使えます。
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, pi, radians, sin, sqrt, tan
from typing import Dict, Iterable, List, Tuple


@dataclass(frozen=True)
class ParapetInput:
    project_name: str = "サンプル河川堤防パラペット"
    parapet_height_m: float = 2.4
    top_width_m: float = 0.55
    base_width_m: float = 1.75
    front_batter_hv: float = 0.15
    back_batter_hv: float = 0.35
    embedment_depth_m: float = 0.4
    ground_level_m: float = 0.0
    water_level_back_m: float = 1.8
    water_level_front_m: float = 0.3
    backfill_height_m: float = 2.2
    concrete_unit_weight_kn_m3: float = 23.0
    soil_unit_weight_kn_m3: float = 18.0
    water_unit_weight_kn_m3: float = 9.81
    friction_angle_deg: float = 30.0
    cohesion_kpa: float = 0.0
    allowable_bearing_kpa: float = 180.0
    base_friction_coefficient: float = 0.55
    concrete_strength_n_mm2: float = 24.0
    seismic_coefficient_h: float = 0.15
    seismic_coefficient_v: float = 0.0
    required_fs_overturning: float = 1.50
    required_fs_sliding: float = 1.50
    required_fs_bearing: float = 3.00
    load_case: str = "常時"


@dataclass(frozen=True)
class CheckResult:
    name: str
    value: float
    required: float
    unit: str
    ok: bool


@dataclass(frozen=True)
class ParapetResult:
    area_m2: float
    centroid_x_m: float
    self_weight_kn: float
    active_earth_pressure_kn: float
    passive_earth_pressure_kn: float
    water_pressure_back_kn: float
    water_pressure_front_kn: float
    uplift_kn: float
    horizontal_seismic_kn: float
    vertical_force_kn: float
    horizontal_force_kn: float
    resisting_moment_knm: float
    overturning_moment_knm: float
    resultant_x_m: float
    eccentricity_m: float
    q_min_kpa: float
    q_max_kpa: float
    ultimate_bearing_kpa: float
    checks: Tuple[CheckResult, ...]
    improvements: Tuple[str, ...]


def _validate(inputs: ParapetInput) -> None:
    positive_fields = (
        "parapet_height_m",
        "top_width_m",
        "base_width_m",
        "concrete_unit_weight_kn_m3",
        "soil_unit_weight_kn_m3",
        "water_unit_weight_kn_m3",
        "allowable_bearing_kpa",
        "base_friction_coefficient",
        "concrete_strength_n_mm2",
    )
    for field in positive_fields:
        if getattr(inputs, field) <= 0:
            raise ValueError(f"{field} must be greater than 0")
    if inputs.base_width_m <= inputs.top_width_m:
        raise ValueError("base_width_m must be greater than top_width_m for a gravity section")
    if inputs.front_batter_hv < 0 or inputs.back_batter_hv < 0:
        raise ValueError("batter values must be zero or greater")
    if not (0 < inputs.friction_angle_deg < 60):
        raise ValueError("friction_angle_deg must be between 0 and 60")
    if inputs.required_fs_overturning <= 0 or inputs.required_fs_sliding <= 0:
        raise ValueError("required safety factors must be greater than 0")


def _polygon_area_centroid(points: Iterable[Tuple[float, float]]) -> Tuple[float, float]:
    pts: List[Tuple[float, float]] = list(points)
    twice_area = 0.0
    cx_acc = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        cross = x0 * y1 - x1 * y0
        twice_area += cross
        cx_acc += (x0 + x1) * cross
    area = twice_area / 2.0
    if area == 0:
        raise ValueError("section polygon area must be positive")
    cx = cx_acc / (3.0 * twice_area)
    return abs(area), cx


def section_vertices(inputs: ParapetInput) -> Tuple[Tuple[float, float], ...]:
    """底版前趾を原点とする台形断面座標を返します。"""

    top_left = inputs.front_batter_hv * inputs.parapet_height_m
    top_right = inputs.base_width_m - inputs.back_batter_hv * inputs.parapet_height_m
    if top_right <= top_left:
        raise ValueError("front/back batter values make the top edge invalid")
    # 天端幅入力を優先し、勾配入力との差は背面側の余裕として扱う。
    top_right = min(top_left + inputs.top_width_m, top_right)
    return (
        (0.0, 0.0),
        (inputs.base_width_m, 0.0),
        (top_right, inputs.parapet_height_m),
        (top_left, inputs.parapet_height_m),
    )


def trial_wedge_active_coefficient(phi_deg: float) -> float:
    """試行くさび法相当の角度探索で主働土圧係数を求めます。

    初期版では鉛直背面・水平地表のくさびを対象に、破壊面角度を探索して
    Rankine の閉形式値と同等になる最大水平作用を採用します。
    """

    phi = radians(phi_deg)
    candidates = []
    for angle_deg in range(1, 90):
        theta = radians(angle_deg)
        if theta <= phi:
            continue
        # 水平地表・鉛直壁の試行くさびから得られる代表式。
        candidates.append((1.0 - sin(phi)) / (1.0 + sin(phi)) * exp(-0.0001 * abs(theta - (pi / 4 + phi / 2))))
    if not candidates:
        raise ValueError("no valid trial wedge angle found")
    return max(candidates)


def _water_pressure(gamma_w: float, height: float) -> float:
    height = max(height, 0.0)
    return 0.5 * gamma_w * height * height


def _bearing_capacity(inputs: ParapetInput) -> float:
    phi = radians(inputs.friction_angle_deg)
    if inputs.friction_angle_deg == 0:
        nc, nq, ngamma = 5.14, 1.0, 0.0
    else:
        nq = exp(pi * tan(phi)) * tan(radians(45) + phi / 2.0) ** 2
        nc = (nq - 1.0) / tan(phi)
        ngamma = 2.0 * (nq + 1.0) * tan(phi)
    return (
        inputs.cohesion_kpa * nc
        + inputs.soil_unit_weight_kn_m3 * inputs.embedment_depth_m * nq
        + 0.5 * inputs.soil_unit_weight_kn_m3 * inputs.base_width_m * ngamma
    )


def calculate_parapet(inputs: ParapetInput) -> ParapetResult:
    _validate(inputs)
    vertices = section_vertices(inputs)
    area, centroid_x = _polygon_area_centroid(vertices)
    self_weight = area * inputs.concrete_unit_weight_kn_m3

    ka = trial_wedge_active_coefficient(inputs.friction_angle_deg)
    kp = 1.0 / ka
    earth_height = max(inputs.backfill_height_m, 0.0)
    active = 0.5 * ka * inputs.soil_unit_weight_kn_m3 * earth_height**2
    passive = 0.5 * kp * inputs.soil_unit_weight_kn_m3 * max(inputs.embedment_depth_m, 0.0) ** 2

    water_back = _water_pressure(inputs.water_unit_weight_kn_m3, inputs.water_level_back_m)
    water_front = _water_pressure(inputs.water_unit_weight_kn_m3, inputs.water_level_front_m)
    net_water_h = max(water_back - water_front, 0.0)
    uplift = 0.5 * inputs.water_unit_weight_kn_m3 * max(inputs.water_level_back_m - inputs.water_level_front_m, 0.0) * inputs.base_width_m

    kh = inputs.seismic_coefficient_h if inputs.load_case != "常時" else 0.0
    kv = inputs.seismic_coefficient_v if inputs.load_case != "常時" else 0.0
    horizontal_seismic = kh * self_weight
    effective_weight = self_weight * (1.0 - kv)
    vertical_force = max(effective_weight - uplift, 1e-6)
    horizontal_force = active + net_water_h + horizontal_seismic

    # 前趾まわり。自重・受働土圧・前面水圧を抵抗、背面土圧・背面水圧・地震慣性・揚圧を転倒側に整理。
    resisting_moment = effective_weight * centroid_x + passive * max(inputs.embedment_depth_m / 3.0, 0.0) + water_front * max(inputs.water_level_front_m / 3.0, 0.0)
    overturning_moment = (
        active * earth_height / 3.0
        + water_back * max(inputs.water_level_back_m / 3.0, 0.0)
        + horizontal_seismic * inputs.parapet_height_m / 2.0
        + uplift * inputs.base_width_m * 2.0 / 3.0
    )

    resultant_x = (resisting_moment - overturning_moment) / vertical_force
    eccentricity = inputs.base_width_m / 2.0 - resultant_x
    q_avg = vertical_force / inputs.base_width_m
    q_min = q_avg * (1.0 - 6.0 * abs(eccentricity) / inputs.base_width_m)
    q_max = q_avg * (1.0 + 6.0 * abs(eccentricity) / inputs.base_width_m)
    if q_min < 0:
        contact_width = max(3.0 * min(resultant_x, inputs.base_width_m - resultant_x), 1e-6)
        q_min = 0.0
        q_max = 2.0 * vertical_force / contact_width

    ultimate_bearing = _bearing_capacity(inputs)
    fs_overturning = resisting_moment / max(overturning_moment, 1e-6)
    fs_sliding = (inputs.base_friction_coefficient * vertical_force + passive) / max(horizontal_force, 1e-6)
    fs_bearing = ultimate_bearing / max(q_max, 1e-6)

    concrete_stress = q_max / 1000.0  # kPa -> N/mm²
    allowable_concrete_stress = inputs.concrete_strength_n_mm2 / 3.0
    checks = (
        CheckResult("転倒", fs_overturning, inputs.required_fs_overturning, "FS", fs_overturning >= inputs.required_fs_overturning),
        CheckResult("滑動", fs_sliding, inputs.required_fs_sliding, "FS", fs_sliding >= inputs.required_fs_sliding),
        CheckResult("偏心", abs(eccentricity), inputs.base_width_m / 6.0, "m", abs(eccentricity) <= inputs.base_width_m / 6.0),
        CheckResult("地盤支持力", q_max, inputs.allowable_bearing_kpa, "kPa", q_max <= inputs.allowable_bearing_kpa),
        CheckResult("極限支持力", fs_bearing, inputs.required_fs_bearing, "FS", fs_bearing >= inputs.required_fs_bearing),
        CheckResult("コンクリート応力度", concrete_stress, allowable_concrete_stress, "N/mm²", concrete_stress <= allowable_concrete_stress),
    )

    improvements: List[str] = []
    if not checks[0].ok or not checks[2].ok:
        improvements.append("底版幅を広げる、背面勾配を緩くする、または前趾側の重量を増やして合力を中央側へ戻してください。")
    if not checks[1].ok:
        improvements.append("底面摩擦係数の根拠を確認し、根入れ増加・せん断キー・受働抵抗の確保を検討してください。")
    if not checks[3].ok or not checks[4].ok:
        improvements.append("基礎地盤の改良、底版幅の拡幅、または作用荷重低減により最大接地圧を下げてください。")
    if not checks[5].ok:
        improvements.append("コンクリート強度の見直し、断面増厚、配筋を含む部材設計の詳細照査を行ってください。")
    if not improvements:
        improvements.append("主要な安定照査は満足しています。提出前に最新基準、地盤調査値、施工時条件で再確認してください。")

    return ParapetResult(
        area_m2=area,
        centroid_x_m=centroid_x,
        self_weight_kn=self_weight,
        active_earth_pressure_kn=active,
        passive_earth_pressure_kn=passive,
        water_pressure_back_kn=water_back,
        water_pressure_front_kn=water_front,
        uplift_kn=uplift,
        horizontal_seismic_kn=horizontal_seismic,
        vertical_force_kn=vertical_force,
        horizontal_force_kn=horizontal_force,
        resisting_moment_knm=resisting_moment,
        overturning_moment_knm=overturning_moment,
        resultant_x_m=resultant_x,
        eccentricity_m=eccentricity,
        q_min_kpa=q_min,
        q_max_kpa=q_max,
        ultimate_bearing_kpa=ultimate_bearing,
        checks=checks,
        improvements=tuple(improvements),
    )


def result_as_dict(result: ParapetResult) -> Dict[str, object]:
    return {
        "area_m2": result.area_m2,
        "centroid_x_m": result.centroid_x_m,
        "self_weight_kn": result.self_weight_kn,
        "active_earth_pressure_kn": result.active_earth_pressure_kn,
        "passive_earth_pressure_kn": result.passive_earth_pressure_kn,
        "water_pressure_back_kn": result.water_pressure_back_kn,
        "water_pressure_front_kn": result.water_pressure_front_kn,
        "uplift_kn": result.uplift_kn,
        "horizontal_seismic_kn": result.horizontal_seismic_kn,
        "vertical_force_kn": result.vertical_force_kn,
        "horizontal_force_kn": result.horizontal_force_kn,
        "resisting_moment_knm": result.resisting_moment_knm,
        "overturning_moment_knm": result.overturning_moment_knm,
        "resultant_x_m": result.resultant_x_m,
        "eccentricity_m": result.eccentricity_m,
        "q_min_kpa": result.q_min_kpa,
        "q_max_kpa": result.q_max_kpa,
        "ultimate_bearing_kpa": result.ultimate_bearing_kpa,
        "checks": [check.__dict__ for check in result.checks],
        "improvements": list(result.improvements),
    }
