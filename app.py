# Write a fixed version of the Streamlit app (v2.1) without the escaped triple-quotes.
from pathlib import Path
import zipfile

root = Path("/mnt/data/etiqueta_webapp_v2_fix")
(root / ".streamlit").mkdir(parents=True, exist_ok=True)

app_py_fixed = '''# -*- coding: utf-8 -*-
# app.py (v2.1) — inclui nome do destinatário nos nomes dos arquivos (fix de aspas)
import io, re, unicodedata
from copy import deepcopy
from datetime import datetime

import streamlit as st
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2 import Transformation
from PyPDF2.generic import RectangleObject

st.set_page_config(page_title="Cortar Etiqueta PagBank (100×150 mm)", page_icon="📦", layout="centered")

st.title("Cortar Etiqueta PagBank (100×150 mm)")
st.caption("Faça upload do PDF A4 do Envio Fácil, ajuste coordenadas em mm e baixe o recorte exato e o 100×150 mm. Agora com nome do destinatário no arquivo!")

MM_TO_PT = 72.0 / 25.4  # pontos por milímetro

def mm_to_pt(mm: float) -> float:
    return mm * MM_TO_PT

def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return text or "destinatario"

def guess_recipient_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extrai texto do 1º page do PDF (cropped) e tenta achar o nome após 'DESTINAT'."""
    try:
        r = PdfReader(io.BytesIO(pdf_bytes))
        t = r.pages[0].extract_text() or ""
    except Exception:
        return "destinatario"
    lines = [re.sub(r"\\s+", " ", (ln or "").strip()) for ln in t.splitlines() if (ln or "").strip()]
    if not lines:
        return "destinatario"
    bad_words = {"documento", "assinatura", "recebedor", "correios", "remetente", "cep", "quadra", "bloco", "logradouro", "cnpj", "cpf"}
    for i, ln in enumerate(lines):
        if "destinat" in ln.lower():
            for j in range(i+1, min(i+6, len(lines))):
                cand = lines[j]
                if sum(ch.isdigit() for ch in cand) > 2:
                    continue
                low = cand.lower()
                if any(w in low for w in bad_words):
                    continue
                if len(cand.split()) >= 2 and len(cand) <= 64:
                    return cand
    for cand in lines:
        if len(cand.split()) >= 2 and sum(ch.isdigit() for ch in cand) <= 1 and len(cand) <= 64:
            return cand
    return "destinatario"

def build_crop_and_fit(pdf_bytes: bytes, page_index: int,
    x_left_mm: float, y_top_mm: float, width_mm: float, height_mm: float,
    extra_top_mm: float=0.0, extra_right_mm: float=0.0, extra_left_mm: float=0.0, extra_bottom_mm: float=0.0,
    target_width_mm: float=100.0, target_height_mm: float=150.0):
    """Retorna (crop_pdf_bytes, fit_pdf_bytes, debug_info:str)"""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    if page_index < 0 or page_index >= len(reader.pages):
        raise ValueError("Índice de página inválido.")
    page = reader.pages[page_index]
    pw, ph = float(page.mediabox.width), float(page.mediabox.height)
    page_h_mm = ph / MM_TO_PT

    x0_mm = x_left_mm - extra_left_mm
    y0_base_mm = page_h_mm - (y_top_mm + height_mm)
    y0_mm = y0_base_mm - extra_bottom_mm
    w_mm = width_mm + extra_left_mm + extra_right_mm
    h_mm = height_mm + extra_top_mm + extra_bottom_mm

    x0, y0 = mm_to_pt(x0_mm), mm_to_pt(y0_mm)
    x1, y1 = mm_to_pt(x0_mm + w_mm), mm_to_pt(y0_mm + h_mm)
    x0, y0 = max(0.0, x0), max(0.0, y0)
    x1, y1 = min(pw, x1), min(ph, y1)

    page_crop = deepcopy(page)
    page_crop.cropbox.lower_left  = (x0, y0)
    page_crop.cropbox.upper_right = (x1, y1)
    page_crop.mediabox.lower_left  = (x0, y0)
    page_crop.mediabox.upper_right = (x1, y1)
    w_pt, h_pt = float(page_crop.mediabox.width), float(page_crop.mediabox.height)

    w_out, h_out = mm_to_pt(target_width_mm), mm_to_pt(target_height_mm)
    tx, ty = -x0, -y0
    sx, sy = (w_out / w_pt if w_pt else 1.0), (h_out / h_pt if h_pt else 1.0)
    s = min(sx, sy)

    wr_crop = PdfWriter(); wr_crop.add_page(page_crop)
    buf_crop = io.BytesIO(); wr_crop.write(buf_crop)
    b_crop = buf_crop.getvalue()

    page_fit = deepcopy(page)
    page_fit.cropbox.lower_left  = (x0, y0)
    page_fit.cropbox.upper_right = (x1, y1)
    page_fit.mediabox.lower_left  = (x0, y0)
    page_fit.mediabox.upper_right = (x1, y1)
    page_fit.add_transformation(Transformation().translate(tx, ty).scale(s, s))
    page_fit.mediabox = RectangleObject([0, 0, w_out, h_out])
    page_fit.cropbox  = RectangleObject([0, 0, w_out, h_out])

    wr_fit = PdfWriter(); wr_fit.add_page(page_fit)
    buf_fit = io.BytesIO(); wr_fit.write(buf_fit)
    b_fit = buf_fit.getvalue()

    dbg = f"page_pt=({pw:.2f},{ph:.2f}) rect_pt=({x0:.2f},{y0:.2f},{x1:.2f},{y1:.2f}) fit_to=({w_out:.2f},{h_out:.2f}) scale={s:.6f}"
    return b_crop, b_fit, dbg

with st.sidebar:
    st.header("Parâmetros (mm)")
    x_left_mm = st.number_input("X da esquerda (mm)", value=85.0, step=0.1)
    y_top_mm  = st.number_input("Y do topo (mm)", value=182.5, step=0.1)
    width_mm  = st.number_input("Largura base (mm)", value=100.0, step=0.1)
    height_mm = st.number_input("Altura base (mm)", value=150.0, step=0.1)

    st.subheader("Margens extras (mm)")
    extra_top_mm    = st.number_input("Extra topo (mm)", value=14.0, step=0.1)
    extra_right_mm  = st.number_input("Extra direita (mm)", value=18.6, step=0.1)
    extra_left_mm   = st.number_input("Extra esquerda (mm)", value=0.0, step=0.1)
    extra_bottom_mm = st.number_input("Extra base/embaixo (mm)", value=0.0, step=0.1)

    st.subheader("Página de saída")
    target_width_mm  = st.number_input("Largura alvo (mm)", value=100.0, step=0.1)
    target_height_mm = st.number_input("Altura alvo (mm)", value=150.0, step=0.1)

st.write(":orange[Envie o PDF A4 do Envio Fácil (página contendo a etiqueta).]")
uploaded = st.file_uploader("PDF A4", type=["pdf"], accept_multiple_files=False)
page_index = st.number_input("Página (0 = 1ª página)", min_value=0, value=0, step=1)

if st.button("Gerar etiqueta (crop + fit 100×150)"):
    if not uploaded:
        st.error("Envie um arquivo PDF primeiro.")
    else:
        try:
            pdf_bytes = uploaded.read()
            b_crop, b_fit, dbg = build_crop_and_fit(
                pdf_bytes, int(page_index),
                x_left_mm, y_top_mm, width_mm, height_mm,
                extra_top_mm, extra_right_mm, extra_left_mm, extra_bottom_mm,
                target_width_mm, target_height_mm
            )
            # Extrair nome do destinatário a partir do CROP
            try:
                recip = PdfReader(io.BytesIO(b_crop)).pages[0].extract_text() or ""
            except Exception:
                recip = ""
            import re
            lines = [re.sub(r"\\s+", " ", (ln or "").strip()) for ln in recip.splitlines() if (ln or "").strip()]
            name = "destinatario"
            for i, ln in enumerate(lines):
                if "destinat" in ln.lower() and i+1 < len(lines):
                    candidate = lines[i+1]
                    if len(candidate.split()) >= 2 and sum(ch.isdigit() for ch in candidate) <= 1 and len(candidate) <= 64:
                        name = candidate; break
            slug = slugify(name)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")

            st.success(f"Arquivos gerados! Destinatário: **{name}**")
            st.caption(dbg)
            st.download_button("⬇️ Baixar recorte exato", data=b_crop, file_name=f"{slug}_{ts}_crop.pdf", mime="application/pdf")
            st.download_button("⬇️ Baixar versão 100×150 mm", data=b_fit, file_name=f"{slug}_{ts}_fit.pdf", mime="application/pdf")
        except Exception as e:
            st.error(f"Falha ao processar o PDF: {e}")
            st.stop()

st.divider()
st.markdown(
    """**Dicas para a Coibeu WKZ-80D:**
- Mídia **100×150 mm (10×15 cm)**
- **Tamanho real / 100%**, sem "Ajustar à página"
- Sem margens do driver"""
)
'''

(root / "app.py").write_text(app_py_fixed, encoding="utf-8")
(root / "requirements.txt").write_text("streamlit>=1.30\nPyPDF2>=3.0.0\n", encoding="utf-8")
(root / ".streamlit" / "config.toml").write_text("[server]\nmaxUploadSize = 200\n", encoding="utf-8")

zip_path = "/mnt/data/etiqueta_webapp_streamlit_v2_fix.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    z.write(root / "app.py", arcname="app.py")
    z.write(root / "requirements.txt", arcname="requirements.txt")
    z.write(root / ".streamlit" / "config.toml", arcname=".streamlit/config.toml")

zip_path
