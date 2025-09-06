# EquationShot 用プロンプト集（JSONL / LaTeX）

ChatGPT などに貼り付ける「コピペ用プロンプト」を、モード別に明確に区分して掲載します。各ブロックをそのままコピーしてください。

---

## A. JSONL モード用（バッチ抽出・1行=1式）
想定: 画像が複数。各画像の主たる数式を JSONL 形式で出力させます。

### コピー用プロンプト（日本語）
```text
画像（複数）の数式を抽出し、1式=1行のJSONで出力してください（JSONL）。
各オブジェクトは次のキーを必ず含める：
- "id": 文字列（半角英数とハイフン/アンダースコア; 未指定なら "eq001" から連番）
- "latex": $や\[ \]を含まない本体のみ（Wordで崩れにくい書き方）
- "caption": 短い説明（任意）
- "inline": true/false（省略時は false; ディスプレイ数式）

出力は JSONL のみ（説明文やコードブロックは禁止）。
表記ルール：\dfrac→\frac、\left/\right は最小化、演算子は \operatorname{...}、行列は pmatrix、条件付き確率は \mid。

例（行の例）
{"id":"jac","latex":"\\operatorname{Jaccard}(A,B)=\\frac{\\lvert A\\cap B\\rvert}{\\lvert A\\cup B\\rvert}","caption":"Jaccard similarity","inline":false}
{"id":"bayes","latex":"P(A\\mid B)=\\frac{P(B\\mid A)P(A)}{P(B)}","caption":"Bayes' theorem","inline":false}
```

出力例（JSONLとして Web に貼り付け）
```jsonl
{"id":"jac","latex":"\\operatorname{Jaccard}(A,B)=\\frac{\\lvert A\\cap B\\rvert}{\\lvert A\\cup B\\rvert}","caption":"Jaccard similarity","inline":false}
{"id":"bayes","latex":"P(A\\mid B)=\\frac{P(B\\mid A)P(A)}{P(B)}","caption":"Bayes' theorem","inline":false}
```

### 英語版プロンプト
```text
Extract the main equations from multiple images and output one JSON object per line (JSONL).
Each object MUST include keys:
- "id": string (alnum, hyphen/underscore; if missing, start from "eq001" sequentially)
- "latex": Equation body only (no $ or \[ \]), robust for Word
- "caption": short description (optional)
- "inline": true/false (default false; display math)

Output JSONL ONLY (no explanations, no code fences).
Style: use \frac instead of \dfrac, minimize \left/\right, use \operatorname{...}, use pmatrix, use \mid.

Example lines:
{"id":"jac","latex":"\\operatorname{Jaccard}(A,B)=\\frac{\\lvert A\\cap B\\rvert}{\\lvert A\\cup B\\rvert}","caption":"Jaccard similarity","inline":false}
{"id":"bayes","latex":"P(A\\mid B)=\\frac{P(B\\mid A)P(A)}{P(B)}","caption":"Bayes' theorem","inline":false}
```

JSONLのセルフチェック
- 各行が完全な JSON（ダブルクォート・カンマ・エスケープ）
- `$`, `\[`, `\]` を含まない LaTeX 本体
- `inline` は用途に応じて true/false を設定

---

## B. LaTeX モード用（単発抽出・本体のみ）
想定: 画像1枚。LaTeX本体をコードブロックで返させます。

### コピー用プロンプト（日本語）
```text
あなたは数式抽出アシスタントです。添付画像内の主たる数式を、Wordで崩れにくいLaTeXで返してください。
- 余計な説明なし、コードブロック1つ（```latex ...```）
- 本体のみ（$ や \[ \] は付けない）
- \dfrac→\frac、\left \right は最小化、演算子は \operatorname{}、行列は pmatrix、条件付き確率は \mid

例: （出力は次のような1つの latex コードブロック）
\operatorname{Jaccard}(A,B)=\frac{\lvert A\cap B\rvert}{\lvert A\cup B\rvert}
```

期待する出力例（ChatGPTから返ってくる LaTeX コードブロック）
```latex
\operatorname{Jaccard}(A,B)=\frac{\lvert A\cap B\rvert}{\lvert A\cup B\rvert}
```

### 英語版プロンプト
```text
You are a formula extraction assistant. Return the main equation from the image in LaTeX robust for Word.
- No explanations, a single code block (```latex ...```)
- Equation body only (no $ or \[ \])
- Use \frac (not \dfrac), minimize \left/\right, use \operatorname{}, pmatrix, and \mid

Example output:
\\operatorname{Jaccard}(A,B)=\\frac{\\lvert A\\cap B\\rvert}{\\lvert A\\cup B\\rvert}
```

注意（共通）
- 関数名は `\operatorname{...}`（Var, Cov, KL 等）
- 行列は `pmatrix`、分数は `\frac`
- 条件付き確率は `\mid`
- `\left/\right` は最小限に

---

## C. よくある落とし穴と回避策
- JSONLに説明文やコードフェンスを混ぜない（パースが壊れる）
- JSON配列として出す場合は `[]` で包むか、純粋なJSONL（1行=1式）にする（どちらも受理可）
- LaTeXで `$` や `\[ \]` を付けない（Web側で二重ラップになる）
- `\dfrac` は避ける（Word変換で崩れることがある）
- 長い `aligned` は分割や `split` を検討

---

## D. ID・キャプションのヒント
- IDは意味のある命名（`bayes_rule`, `softmax_def`, `chap1_eq_001` など）
- キャプションは短い名詞句で（1行）
- 文中の短い式は `inline: true` を活用

---

必要に応じて、このページを配布/共有し、使うモード（JSONL / LaTeX）に応じて上の「コピー用プロンプト」ブロックをそのまま貼り付けてください。
