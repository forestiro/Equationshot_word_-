from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, model_validator
from typing import Optional
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime

from .texgen import build_tex_from_items, JSONLItem, sanitize_item


class DocxRequest(BaseModel):
    latex: Optional[str] = None
    jsonl: Optional[str] = None

    @model_validator(mode="after")
    def validate_one_of(self):
        if (self.latex and self.jsonl) or (not self.latex and not self.jsonl):
            raise ValueError("Provide exactly one of 'latex' or 'jsonl'.")
        return self


app = FastAPI(title="EquationShot Batch API", version="0.1.0")


INDEX_HTML = """
<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>EquationShot (簡易版)</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 24px; }
    textarea { width: 100%; height: 240px; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
    .row { display: flex; gap: 16px; align-items: center; }
    .row > * { margin: 8px 0; }
    .small { color: #666; font-size: 12px; }
    fieldset { border: 1px solid #ddd; padding: 12px; }
    legend { color: #444; }
    button { padding: 8px 16px; font-weight: 600; }
    .status { margin-top: 8px; min-height: 1.2em; }
  </style>
  <script>
    async function submitForm(ev) {
      ev.preventDefault();
      const mode = document.querySelector('input[name="mode"]:checked').value;
      const text = document.getElementById('input').value;
      const status = document.getElementById('status');
      status.textContent = '生成中…';
      try {
        const payload = mode === 'jsonl' ? { jsonl: text } : { latex: text };
        const res = await fetch('/api/docx', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          status.textContent = 'エラー: ' + (err.detail || res.statusText);
          return;
        }
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'equations.docx';
        a.click();
        URL.revokeObjectURL(url);
        status.textContent = 'equations.docx をダウンロードしました。';
      } catch (e) {
        status.textContent = 'エラー: ' + e.message;
      }
    }
  </script>
  </head>
  <body>
    <h1>EquationShot（簡易バッチ版）</h1>
    <p class="small">JSONL か LaTeX行テキストを貼り付け、.docx を生成します。Pandoc が必要です。</p>
    <form onsubmit="submitForm(event)">
      <fieldset>
        <legend>モード</legend>
        <label><input type="radio" name="mode" value="jsonl" checked /> JSONL</label>
        <label><input type="radio" name="mode" value="text" /> Text</label>
      </fieldset>
      <div class="row">
        <textarea id="input" placeholder="JSONL 例:\n{\"id\":\"jac\",\"latex\":\"\\\\operatorname{Jaccard}(A,B)=...\",\"caption\":\"Jaccard similarity\",\"inline\":false}\n{\"id\":\"bayes\",\"latex\":\"P(A\\\\mid B)=...\",\"inline\":false}"></textarea>
      </div>
      <div class="row">
        <button type="submit">.docx を生成</button>
        <span id="status" class="status"></span>
      </div>
    </form>
  </body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(content=INDEX_HTML)

@app.get("/healthz")
def healthz():
    return JSONResponse({"status": "ok"})


def parse_text_mode(latex_text: str) -> list[JSONLItem]:
    items: list[JSONLItem] = []
    counter = 1
    for raw in latex_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        item = JSONLItem(id=f"eq{counter:03d}", latex=line, inline=False, caption=None)
        items.append(item)
        counter += 1
    return items


def parse_jsonl_mode(jsonl_text: str) -> list[JSONLItem]:
    items: list[JSONLItem] = []
    counter = 1
    seen_ids: set[str] = set()

    text = jsonl_text.strip()
    # 1) 許容: JSON 配列をそのまま貼った場合
    if text.startswith('['):
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=422, detail=f"JSON array parse error: {e}")
        if not isinstance(data, list):
            raise HTTPException(status_code=422, detail="Expected a JSON array or JSONL text")
        objs = data
        lines_iter = enumerate([json.dumps(o) for o in objs], start=1)
    else:
        # 2) 標準: 1行=1 JSON（JSONL）
        lines_iter = enumerate(jsonl_text.splitlines(), start=1)

    for ln, raw in lines_iter:
        row = raw.strip()
        if not row:
            continue
        try:
            obj = json.loads(row)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=422, detail=f"JSONL parse error at line {ln}: {e}")
        if not isinstance(obj, dict):
            raise HTTPException(status_code=422, detail=f"Line {ln}: JSON object required")
        _id = obj.get("id") or f"eq{counter:03d}"
        # ensure uniqueness
        cand = _id
        suffix_char = ord('a')
        while cand in seen_ids:
            cand = f"{_id}{chr(suffix_char)}"
            suffix_char += 1
        _id = cand
        seen_ids.add(_id)
        counter += 1
        latex = obj.get("latex", "")
        caption = obj.get("caption")
        inline = bool(obj.get("inline", False))
        items.append(JSONLItem(id=_id, latex=latex, caption=caption, inline=inline))
    if not items:
        raise HTTPException(status_code=400, detail="Empty JSONL input")
    return items


def _run_pandoc(tex_path: str, docx_path: str):
    # Try system pandoc first
    completed = None
    try:
        completed = subprocess.run(
            ["pandoc", tex_path, "-o", docx_path],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        # Fallback: attempt to download pandoc via pypandoc
        try:
            import pypandoc  # type: ignore
            pandoc_path = pypandoc.download_pandoc()
            completed = subprocess.run(
                [pandoc_path, tex_path, "-o", docx_path],
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail="pandoc not found and auto-download failed. Please install pandoc.")

    if completed is None or completed.returncode != 0:
        err = (completed.stderr if completed else "").strip()
        raise HTTPException(status_code=500, detail=f"pandoc failed: {err}")


@app.post("/api/docx")
def generate_docx(req: DocxRequest = Body(...)):
    # Build items
    if req.latex:
        items = parse_text_mode(req.latex)
    else:
        items = parse_jsonl_mode(req.jsonl or "")

    # sanitize & validate
    sanitized: list[JSONLItem] = []
    for idx, item in enumerate(items, start=1):
        try:
            sanitized.append(sanitize_item(item))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Line {idx}: {e}")

    # Build TeX
    tex = build_tex_from_items(sanitized, batch_title="Batch Summary")

    # Prepare temp files under a dedicated workspace dir
    workspace = os.path.join(os.getcwd(), ".equationshot_tmp")
    os.makedirs(workspace, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    tex_path = os.path.join(workspace, f"eq_{ts}.tex")
    docx_path = os.path.join(workspace, f"equations_{ts}.docx")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(tex)

    # Run pandoc with fallback
    _run_pandoc(tex_path, docx_path)

    if not os.path.exists(docx_path):
        raise HTTPException(status_code=500, detail="pandoc did not produce output.")

    headers = {"Content-Disposition": "attachment; filename=equations.docx"}
    return FileResponse(
        path=docx_path,
        filename="equations.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers=headers,
    )


if __name__ == "__main__":
    try:
        import uvicorn  # type: ignore
    except Exception as e:
        print("Uvicorn is required. Install with: pip install -r requirements.txt")
        raise
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
