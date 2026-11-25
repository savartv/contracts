import uuid, subprocess, json, webbrowser, threading
from pathlib import Path
from fastapi import FastAPI, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from docxtpl import DocxTemplate

BASE = Path(__file__).parent
TPL_DIR = BASE / "templates_docx"
OUT_DIR = BASE / "output"
OUT_DIR.mkdir(exist_ok=True)

app = FastAPI()
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")

@app.get("/", response_class=HTMLResponse)
def index():
    return (BASE / "static" / "index.html").read_text(encoding="utf-8")

@app.get("/api/templates")
def list_templates():
    return [{"id": p.stem, "name": p.stem.replace("_", " ").title()}
            for p in sorted(TPL_DIR.glob("*.docx"))]

@app.post("/api/generate")
async def generate(template_id: str = Form(...), data: str = Form(...)):
    fields = json.loads(data)
    tpl_path = TPL_DIR / f"{template_id}.docx"
    if not tpl_path.exists():
        return {"error": "Шаблон не найден"}

    doc = DocxTemplate(str(tpl_path))
    doc.render(fields)

    uid = uuid.uuid4().hex[:8]
    docx_path = OUT_DIR / f"contract_{uid}.docx"
    doc.save(str(docx_path))

    pdf_ok = False
    try:
        subprocess.run([
            "soffice", "--headless", "--convert-to", "pdf",
            "--outdir", str(OUT_DIR), str(docx_path)
        ], check=True, timeout=60)
        pdf_ok = (OUT_DIR / f"contract_{uid}.pdf").exists()
    except Exception as e:
        print("PDF error:", e)

    return {
        "docx": f"/download/{docx_path.name}",
        "pdf":  f"/download/contract_{uid}.pdf" if pdf_ok else None,
    }

@app.get("/download/{name}")
def download(name: str):
    return FileResponse(OUT_DIR / name, filename=name)

def open_browser():
    webbrowser.open("http://127.0.0.1:8000")

if __name__ == "__main__":
    import uvicorn
    threading.Timer(1.2, open_browser).start()
    uvicorn.run(app, host="0.0.0.0", port=8000)