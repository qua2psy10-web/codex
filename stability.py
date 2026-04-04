"""盛土法面の簡易安定計算モジュール。"""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, radians, sin, tan


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
class StabilityResult:
    factor_of_safety: float
    is_stable: bool


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
    return StabilityResult(factor_of_safety=fs, is_stable=fs >= required_fs)
