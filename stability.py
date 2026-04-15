"""盛土法面の簡易安定計算モジュール。"""

from __future__ import annotations

from dataclasses import dataclass
from math import atan, cos, hypot, radians, sin, sqrt, tan


@dataclass(frozen=True)
class SlopeInput:
    slope_angle_deg: float
    cohesion_kpa: float
    friction_angle_deg: float
    unit_weight_kn_m3: float
    failure_depth_m: float
    groundwater_ratio: float = 0.0
    water_unit_weight_kn_m3: float = 9.81


@dataclass(frozen=True)
class CircularSlipInput:
    slope_height_m: float
    slope_angle_deg: float
    cohesion_kpa: float
    friction_angle_deg: float
    unit_weight_kn_m3: float
    groundwater_ratio: float = 0.0
    water_unit_weight_kn_m3: float = 9.81
    slices: int = 16
    search_steps: int = 36


@dataclass(frozen=True)
class StabilityResult:
    factor_of_safety: float
    is_stable: bool
    method: str


def calculate_infinite_slope_fs(inputs: SlopeInput, required_fs: float = 1.2) -> StabilityResult:
    if inputs.failure_depth_m <= 0:
        raise ValueError("failure_depth_m must be greater than 0")
    if inputs.unit_weight_kn_m3 <= 0:
        raise ValueError("unit_weight_kn_m3 must be greater than 0")
    if not (0 <= inputs.groundwater_ratio <= 1):
        raise ValueError("groundwater_ratio must be between 0 and 1")
    if not (0 < inputs.slope_angle_deg < 90):
        raise ValueError("slope_angle_deg must be between 0 and 90")

    beta = radians(inputs.slope_angle_deg)
    phi = radians(inputs.friction_angle_deg)

    normal_total = inputs.unit_weight_kn_m3 * inputs.failure_depth_m * cos(beta) ** 2
    pore_pressure = (
        inputs.groundwater_ratio
        * inputs.water_unit_weight_kn_m3
        * inputs.failure_depth_m
        * cos(beta) ** 2
    )
    normal_effective = max(normal_total - pore_pressure, 0.0)

    shear_resistance = inputs.cohesion_kpa + normal_effective * tan(phi)
    driving_shear = inputs.unit_weight_kn_m3 * inputs.failure_depth_m * sin(beta) * cos(beta)
    if driving_shear <= 0:
        raise ValueError("driving shear must be positive")

    fs = shear_resistance / driving_shear
    return StabilityResult(factor_of_safety=fs, is_stable=fs >= required_fs, method="infinite_slope")


def _fellenius_fs_for_center(inputs: CircularSlipInput, t_ratio: float) -> float:
    beta = radians(inputs.slope_angle_deg)
    phi = radians(inputs.friction_angle_deg)

    h = inputs.slope_height_m
    b = h / tan(beta)

    # 円弧端点: 法肩(0, h), 法尻(b, 0)
    x1, y1 = 0.0, h
    x2, y2 = b, 0.0

    mid_x = 0.5 * (x1 + x2)
    mid_y = 0.5 * (y1 + y2)

    chord = hypot(x2 - x1, y2 - y1)
    nx, ny = h / chord, b / chord  # 垂直二等分線の方向
    t = t_ratio * chord

    xc = mid_x + t * nx
    yc = mid_y + t * ny
    r = hypot(x1 - xc, y1 - yc)

    dx = b / inputs.slices
    resisting = 0.0
    driving = 0.0

    for i in range(inputs.slices):
        x_left = i * dx
        x_right = (i + 1) * dx
        x_mid = 0.5 * (x_left + x_right)

        y_top = h - (h / b) * x_mid

        inside = r * r - (x_mid - xc) ** 2
        if inside <= 0:
            raise ValueError("invalid slip circle geometry")
        y_slip = yc - sqrt(inside)

        slice_height = y_top - y_slip
        if slice_height <= 0:
            raise ValueError("slip surface is above slope surface")

        tangent = (x_mid - xc) / sqrt(inside)
        alpha = atan(tangent)

        area = slice_height * dx
        weight = inputs.unit_weight_kn_m3 * area

        base_length = dx / max(cos(alpha), 1e-6)
        pore_pressure = inputs.groundwater_ratio * inputs.water_unit_weight_kn_m3 * slice_height

        normal_effective = max(weight * cos(alpha) - pore_pressure * base_length, 0.0)
        shear_resistance = inputs.cohesion_kpa * base_length + normal_effective * tan(phi)
        shear_driving = weight * sin(abs(alpha))

        resisting += shear_resistance
        driving += shear_driving

    if driving <= 0:
        raise ValueError("driving shear must be positive")

    return resisting / driving


def calculate_fellenius_fs(inputs: CircularSlipInput, required_fs: float = 1.2) -> StabilityResult:
    if inputs.slope_height_m <= 0:
        raise ValueError("slope_height_m must be greater than 0")
    if not (0 < inputs.slope_angle_deg < 90):
        raise ValueError("slope_angle_deg must be between 0 and 90")
    if inputs.unit_weight_kn_m3 <= 0:
        raise ValueError("unit_weight_kn_m3 must be greater than 0")
    if not (0 <= inputs.groundwater_ratio <= 1):
        raise ValueError("groundwater_ratio must be between 0 and 1")
    if inputs.slices < 8:
        raise ValueError("slices must be 8 or greater")
    if inputs.search_steps < 10:
        raise ValueError("search_steps must be 10 or greater")

    candidates = []
    for k in range(inputs.search_steps):
        t_ratio = 0.2 + 2.8 * (k / (inputs.search_steps - 1))
        try:
            candidates.append(_fellenius_fs_for_center(inputs, t_ratio))
        except ValueError:
            continue

    if not candidates:
        raise ValueError("no valid slip circle found")

    fs = min(candidates)
    return StabilityResult(factor_of_safety=fs, is_stable=fs >= required_fs, method="fellenius")
