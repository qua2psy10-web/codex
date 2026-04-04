const form = document.getElementById("slope-form");
const resultCard = document.getElementById("result-card");
const errorMessage = document.getElementById("error");

const betaEl = document.getElementById("beta");
const fsEl = document.getElementById("fs");
const judgeEl = document.getElementById("judge");

function toRadians(deg) {
  return (deg * Math.PI) / 180;
}

function validateInputs(values) {
  const { height, slopeRatio, gamma, cohesion, phi, ru } = values;

  if ([height, slopeRatio, gamma, cohesion, phi, ru].some((v) => Number.isNaN(v))) {
    return "数値を入力してください。";
  }

  if (height <= 0 || slopeRatio <= 0 || gamma <= 0 || phi <= 0 || phi >= 90) {
    return "入力範囲を確認してください。";
  }

  if (ru < 0 || ru >= 1) {
    return "r_u は 0 以上 1 未満にしてください。";
  }

  return "";
}

function calculateFs({ height, slopeRatio, gamma, cohesion, phi, ru }) {
  const beta = Math.atan(1 / slopeRatio); // rad
  const phiRad = toRadians(phi);

  const termC = cohesion / (gamma * height * Math.sin(beta) * Math.cos(beta));
  const termF = ((1 - ru) * Math.tan(phiRad)) / Math.tan(beta);
  const fs = termC + termF;

  return {
    betaDeg: (beta * 180) / Math.PI,
    fs,
  };
}

function judge(fs) {
  if (fs >= 1.3) {
    return { text: "安定（目安 Fs ≥ 1.3）", className: "ok" };
  }
  if (fs >= 1.1) {
    return { text: "やや低い（要詳細検討）", className: "warn" };
  }
  return { text: "不安定の可能性大", className: "ng" };
}

form.addEventListener("submit", (event) => {
  event.preventDefault();

  const values = {
    height: Number(document.getElementById("height").value),
    slopeRatio: Number(document.getElementById("slopeRatio").value),
    gamma: Number(document.getElementById("gamma").value),
    cohesion: Number(document.getElementById("cohesion").value),
    phi: Number(document.getElementById("phi").value),
    ru: Number(document.getElementById("ru").value),
  };

  const validationError = validateInputs(values);
  if (validationError) {
    errorMessage.textContent = validationError;
    resultCard.hidden = true;
    return;
  }

  errorMessage.textContent = "";

  const { betaDeg, fs } = calculateFs(values);
  const result = judge(fs);

  betaEl.textContent = betaDeg.toFixed(2);
  fsEl.textContent = fs.toFixed(3);

  judgeEl.textContent = result.text;
  judgeEl.className = result.className;

  resultCard.hidden = false;
});
