function calculateInfiniteSlopeFS(input) {
  const beta = (input.slope_angle_deg * Math.PI) / 180;
  const phi = (input.friction_angle_deg * Math.PI) / 180;

  if (!(input.failure_depth_m > 0)) throw new Error('failure_depth_m must be greater than 0');
  if (!(input.unit_weight_kn_m3 > 0)) throw new Error('unit_weight_kn_m3 must be greater than 0');
  if (!(input.slope_angle_deg > 0 && input.slope_angle_deg < 90)) throw new Error('slope_angle_deg must be between 0 and 90');
  if (!(input.groundwater_ratio >= 0 && input.groundwater_ratio <= 1)) throw new Error('groundwater_ratio must be between 0 and 1');

  const waterGamma = 9.81;
  const normalTotal = input.unit_weight_kn_m3 * input.failure_depth_m * Math.cos(beta) ** 2;
  const porePressure = input.groundwater_ratio * waterGamma * input.failure_depth_m * Math.cos(beta) ** 2;
  const normalEffective = Math.max(normalTotal - porePressure, 0);
  const shearResistance = input.cohesion_kpa + normalEffective * Math.tan(phi);
  const drivingShear = input.unit_weight_kn_m3 * input.failure_depth_m * Math.sin(beta) * Math.cos(beta);
  const fs = shearResistance / drivingShear;

  return {
    factor_of_safety: fs,
    is_stable: fs >= input.required_fs,
  };
}

const btn = document.getElementById('calc');
const form = document.getElementById('calc-form');
const resultEl = document.getElementById('result');

btn.addEventListener('click', () => {
  try {
    const payload = Object.fromEntries(new FormData(form).entries());
    Object.keys(payload).forEach((k) => (payload[k] = Number(payload[k])));

    const result = calculateInfiniteSlopeFS(payload);
    resultEl.innerHTML = `
      <strong>安全率 FS = ${result.factor_of_safety.toFixed(3)}</strong><br/>
      判定: ${result.is_stable ? '安定（必要安全率を満足）' : '不安定（対策が必要）'}
    `;
  } catch (error) {
    resultEl.textContent = `エラー: ${error.message}`;
  }
});
