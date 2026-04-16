function validateCommon(input) {
  if (!(input.slope_angle_deg > 0 && input.slope_angle_deg < 90)) throw new Error('slope_angle_deg must be between 0 and 90');
  if (!(input.unit_weight_kn_m3 > 0)) throw new Error('unit_weight_kn_m3 must be greater than 0');
  if (!(input.groundwater_ratio >= 0 && input.groundwater_ratio <= 1)) throw new Error('groundwater_ratio must be between 0 and 1');
}

function calculateInfiniteSlopeFS(input) {
  validateCommon(input);
  if (!(input.failure_depth_m > 0)) throw new Error('failure_depth_m must be greater than 0');

  const beta = (input.slope_angle_deg * Math.PI) / 180;
  const phi = (input.friction_angle_deg * Math.PI) / 180;

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
    method: 'infinite_slope',
  };
}

function felleniusFSForCenter(input, tRatio) {
  const beta = (input.slope_angle_deg * Math.PI) / 180;
  const phi = (input.friction_angle_deg * Math.PI) / 180;

  const h = input.slope_height_m;
  const b = h / Math.tan(beta);

  const x1 = 0;
  const y1 = h;
  const x2 = b;
  const y2 = 0;

  const midX = (x1 + x2) / 2;
  const midY = (y1 + y2) / 2;

  const chord = Math.hypot(x2 - x1, y2 - y1);
  const nx = h / chord;
  const ny = b / chord;
  const t = tRatio * chord;

  const xc = midX + t * nx;
  const yc = midY + t * ny;
  const r = Math.hypot(x1 - xc, y1 - yc);

  const dx = b / input.slices;
  let resisting = 0;
  let driving = 0;

  for (let i = 0; i < input.slices; i += 1) {
    const xMid = (i + 0.5) * dx;
    const yTop = h - (h / b) * xMid;

    const inside = r ** 2 - (xMid - xc) ** 2;
    if (!(inside > 0)) throw new Error('invalid slip circle geometry');
    const ySlip = yc - Math.sqrt(inside);

    const sliceHeight = yTop - ySlip;
    if (!(sliceHeight > 0)) throw new Error('slip surface is above slope surface');

    const tangent = (xMid - xc) / Math.sqrt(inside);
    const alpha = Math.atan(tangent);

    const area = sliceHeight * dx;
    const weight = input.unit_weight_kn_m3 * area;

    const baseLength = dx / Math.max(Math.cos(alpha), 1e-6);
    const porePressure = input.groundwater_ratio * 9.81 * sliceHeight;

    const normalEffective = Math.max(weight * Math.cos(alpha) - porePressure * baseLength, 0);
    const shearResistance = input.cohesion_kpa * baseLength + normalEffective * Math.tan(phi);
    const shearDriving = weight * Math.sin(Math.abs(alpha));

    resisting += shearResistance;
    driving += shearDriving;
  }

  if (!(driving > 0)) throw new Error('driving shear must be positive');
  return resisting / driving;
}

function calculateFelleniusFS(input) {
  validateCommon(input);
  if (!(input.slope_height_m > 0)) throw new Error('slope_height_m must be greater than 0');
  if (!(input.slices >= 8)) throw new Error('slices must be 8 or greater');
  if (!(input.search_steps >= 10)) throw new Error('search_steps must be 10 or greater');

  const candidates = [];
  for (let k = 0; k < input.search_steps; k += 1) {
    const tRatio = 0.2 + (2.8 * k) / (input.search_steps - 1);
    try {
      candidates.push(felleniusFSForCenter(input, tRatio));
    } catch (error) {
      // invalid geometry candidate is skipped
    }
  }

  if (!candidates.length) throw new Error('no valid slip circle found');
  const fs = Math.min(...candidates);

  return {
    factor_of_safety: fs,
    is_stable: fs >= input.required_fs,
    method: 'fellenius',
  };
}

const methodEl = document.getElementById('method');
const btn = document.getElementById('calc');
const resetBtn = document.getElementById('reset');
const form = document.getElementById('calc-form');
const resultEl = document.getElementById('result');
const methodLabelEl = document.getElementById('method-label');
const fsValueEl = document.getElementById('fs-value');
const judgeTextEl = document.getElementById('judge-text');
const statusChipEl = document.getElementById('status-chip');
const infiniteFields = document.getElementById('infinite-fields');
const felleniusFields = document.getElementById('fellenius-fields');

function refreshVisibility() {
  const isInfinite = methodEl.value === 'infinite_slope';
  infiniteFields.style.display = isInfinite ? 'contents' : 'none';
  felleniusFields.style.display = isInfinite ? 'none' : 'contents';
}

function parsePayload() {
  const payload = Object.fromEntries(new FormData(form).entries());
  Object.keys(payload).forEach((key) => {
    if (key !== 'method') payload[key] = Number(payload[key]);
  });
  return payload;
}

function updateResult(result, requiredFs) {
  const methodLabel = result.method === 'fellenius' ? 'Fellenius法（円弧探索付き分割法）' : '無限長斜面法';
  const stableText = result.is_stable ? '安定（必要安全率を満足）' : '不安定（対策が必要）';
  methodLabelEl.innerHTML = `<strong>${methodLabel}</strong>`;
  fsValueEl.textContent = result.factor_of_safety.toFixed(3);
  judgeTextEl.textContent = `${stableText} / 要求FS: ${requiredFs.toFixed(2)}`;

  statusChipEl.textContent = result.is_stable ? '判定: 安定' : '判定: 不安定';
  statusChipEl.className = `status-chip ${result.is_stable ? 'status-ok' : 'status-ng'}`;

  resultEl.innerHTML = [
    `<strong>計算手法:</strong> ${methodLabel}`,
    `<strong>安全率 FS:</strong> ${result.factor_of_safety.toFixed(3)}`,
    `<strong>判定:</strong> ${stableText}`,
  ].join('<br/>');
}

function showError(error) {
  methodLabelEl.innerHTML = '<strong>エラー</strong>';
  fsValueEl.textContent = '-';
  judgeTextEl.textContent = '入力値を確認してください';
  statusChipEl.textContent = '判定: エラー';
  statusChipEl.className = 'status-chip status-ng';
  resultEl.textContent = `エラー: ${error.message}`;
}

methodEl.addEventListener('change', refreshVisibility);
refreshVisibility();

btn.addEventListener('click', () => {
  try {
    const payload = parsePayload();
    const result = methodEl.value === 'infinite_slope'
      ? calculateInfiniteSlopeFS(payload)
      : calculateFelleniusFS(payload);
    updateResult(result, payload.required_fs);
  } catch (error) {
    showError(error);
  }
});

resetBtn.addEventListener('click', () => {
  form.reset();
  refreshVisibility();
  methodLabelEl.innerHTML = '<strong>未計算</strong>';
  fsValueEl.textContent = '-';
  judgeTextEl.textContent = '計算待ち';
  statusChipEl.textContent = '未判定';
  statusChipEl.className = 'status-chip';
  resultEl.textContent = '結果待ち';
});
