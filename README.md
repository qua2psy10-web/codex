# 盛土法面安定計算 Webアプリ

無限長斜面モデルによる簡易な安全率(FS)計算を行う、依存ライブラリ不要の Web アプリです。

## 使い方

```bash
python -m http.server 8000
```

ブラウザで `http://127.0.0.1:8000/web/` を開き、入力値を設定して計算してください。

## テスト

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

## 計算式（無限長斜面）

\[
FS = \frac{c' + (\sigma - u)\tan\phi'}{\tau}
\]

- \(\sigma = \gamma z \cos^2\beta\)
- \(u = m \gamma_w z \cos^2\beta\)
- \(\tau = \gamma z \sin\beta\cos\beta\)

> 注意: 本アプリは教育・概略検討用途の簡易計算です。実施設計には詳細地盤調査・適切な設計基準を使用してください。
