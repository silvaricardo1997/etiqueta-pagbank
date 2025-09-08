# app.py
# Streamlit web app – Cortar Etiqueta PagBank (100×150 mm)
# Rodar localmente:
#   pip install streamlit PyPDF2
#   streamlit run app.py

import io
from copy import deepcopy
from datetime import datetime

import streamlit as st
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2 import Transformation
from PyPDF2.generic import RectangleObject

st.set_page_config(
    page_title="Cortar Etiqueta PagBank (100×150 mm)",
    page_icon="📦",
    layout="centered",
)

APP_DESC = (
    "Envie um PDF A4 gerado pelo PagBank/Envio Fácil, informe as coordenadas em mm "
    "(canto inferior esquerdo da etiqueta a partir da borda esquerda e o topo a partir da borda superior) "
    "e gere dois arquivos: recorte EXATO e versão ajustada para 100×150 mm (fit proporcional)."
)
st.title("Cortar Etiqueta PagBank (100×150 mm)")
st.caption(APP_DESC)

MM_TO_PT = 72.0 / 25.4  # pontos por milímetro


def mm_to_pt(mm: float) -> float:
    return mm * MM_TO_PT


def build_crop_and_fit(
    pdf_bytes: bytes,
    page_index: int,
    x_left_mm: float,
    y_top_mm: float,
    width_mm: float,
    height_mm: float,
    extra_top_mm: float = 0.0,
    extra_right_mm: float = 0.0,
    extra_left_mm: float = 0.0,
    extra_bottom_mm: float = 0.0,
    target_width_mm: float = 100.0,
    target_height_mm: float = 150.0,
):
    """Retorna (crop_pdf_bytes, fit_pdf_bytes, debug_info:str)"""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    if page_index < 0 or page_index >= len(reader.pages):
        raise ValueError("Índice de página inválido.")

    page = reader.pages[page_index]
    pw = float(page.mediabox.width)
    ph = float(page.mediabox.height)

    # Altura real da página em mm (não assume A4 fixo)
    page_h_mm = ph / MM_TO_PT

    # Base: canto inferior esquerdo (x_left_mm, y_bottom_mm)
    # y_bottom_mm = page_h_mm - (y_top_mm + height_mm)
    x0_mm = x_left_mm - extra_left_mm
    y0_base_mm = page_h_mm - (y_top_mm + height_mm)
    y0_mm = y0_base_mm - extra_bottom_mm

    width_final_mm = width_mm + extra_left_mm + extra_right_mm
    height_final_mm = height_mm + extra_top_mm + extra_bottom_mm

    # Converter para pontos
    x0 = mm_to_pt(x0_mm)
    y0 = mm_to_pt(y0_mm)
    x1 = mm_to_pt(x0_mm + width_final_mm)
    y1 = mm_to_pt(y0_mm + height_final_mm)

    # Clamp aos limites da página
    x0 = max(0.0, x0)
    y0 = max(0.0, y0)
    x1 = min(pw, x1)
    y1 = min(ph, y1)

    # (1) Recorte EXATO (sem redimensionar)
    page_crop = deepcopy(page)
    page_crop.cropbox.lower_left = (x0, y0)
    page_crop.cropbox.upper_right = (x1, y1)
    page_crop.mediabox.lower_left = (x0, y0)
    page_crop.mediabox.upper_right = (x1, y1)

    writer_crop = PdfWriter()
    writer_crop.add_page(page_crop)
    crop_buf = io.BytesIO()
    writer_crop.write(crop_buf)
    crop_bytes = crop_buf.getvalue()

    # (2) Ajuste para página alvo (fit 100×150 mm por padrão)
    target_w_pt = mm_to_pt(target_width_mm)
    target_h_pt = mm_to_pt(target_height_mm)

    crop_w = float(page_crop.mediabox.width)
    crop_h = float(page_crop.mediabox.height)

    tx = -x0
    ty = -y0
    sx = target_w_pt / crop_w if crop_w else 1.0
    sy = target_h_pt / crop_h if crop_h else 1.0
    s = min(sx, sy)  # manter proporção e caber dentro

    page_fit = deepcopy(page)
    page_fit.cropbox.lower_left = (x0, y0)
    page_fit.cropbox.upper_right = (x1, y1)
    page_fit.mediabox.lower_left = (x0, y0)
    page_fit.mediabox.upper_right = (x1, y1)

    t = Transformation().translate(tx, ty).scale(s, s)
    page_fit.add_transformation(t)

    page_fit.mediabox = RectangleObject([0, 0, target_w_pt, target_h_pt])
    page_fit.cropbox = RectangleObject([0, 0, target_w_pt, target_h_pt])

    writer_fit = PdfWriter()
    writer_fit.add_page(page_fit)
    fit_buf = io.BytesIO()
    writer_fit.write(fit_buf)
    fit_bytes = fit_buf.getvalue()

    debug = (
        f"page_size_pt=({pw:.2f},{ph:.2f}) | "
        f"rect_pt=({x0:.2f},{y0:.2f},{x1:.2f},{y1:.2f}) | "
        f"target_pt=({target_w_pt:.2f},{target_h_pt:.2f}) | "
        f"scale=(sx={sx:.6f}, sy={sy:.6f}) used={s:.6f}"
    )

    return crop_bytes, fit_bytes, debug


with st.sidebar:
    st.header("Parâmetros (mm)")
    st.caption("Use ponto decimal. Padrões abaixo = os que funcionaram no seu caso.")
    x_left_mm = st.number_input("X da esquerda (mm)", value=85.0, step=0.1)
    y_top_mm = st.number_input("Y do topo (mm)", value=182.5, step=0.1)
    width_mm = st.number_input("Largura base (mm)", value=100.0, step=0.1)
    height_mm = st.number_input("Altura base (mm)", value=150.0, step=0.1)

    st.subheader("Margens extras (mm)")
    extra_top_mm = st.number_input("Extra topo (mm)", value=14.0, step=0.1)
    extra_right_mm = st.number_input("Extra direita (mm)", value=18.6, step=0.1)
    extra_left_mm = st.number_input("Extra esquerda (mm)", value=0.0, step=0.1)
    extra_bottom_mm = st.number_input("Extra base/embaixo (mm)", value=0.0, step=0.1)

    st.subheader("Página de saída")
    target_width_mm = st.number_input("Largura alvo (mm)", value=100.0, step=0.1)
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
            crop_bytes, fit_bytes, debug = build_crop_and_fit(
                pdf_bytes=pdf_bytes,
                page_index=int(page_index),
                x_left_mm=x_left_mm,
                y_top_mm=y_top_mm,
                width_mm=width_mm,
                height_mm=height_mm,
                extra_top_mm=extra_top_mm,
                extra_right_mm=extra_right_mm,
                extra_left_mm=extra_left_mm,
                extra_bottom_mm=extra_bottom_mm,
                target_width_mm=target_width_mm,
                target_height_mm=target_height_mm,
            )
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            base = f"etiqueta_{ts}"
            st.success("Arquivos gerados com sucesso!")
            st.caption(debug)
            st.download_button(
                "⬇️ Baixar recorte exato (_crop.pdf)",
                data=crop_bytes,
                file_name=f"{base}_crop.pdf",
                mime="application/pdf",
            )
            st.download_button(
                "⬇️ Baixar versão 100×150 mm (_fit.pdf)",
                data=fit_bytes,
                file_name=f"{base}_fit.pdf",
                mime="application/pdf",
            )
        except Exception as e:
            st.error(f"Falha ao processar o PDF: {e}")
            st.stop()

st.divider()
st.markdown(
    "**Dicas para imprimir na térmica (Coibeu WKZ-80D):**\n"
    "- Selecione mídia **100×150 mm (10×15 cm)**.\n"
    "- Use **Tamanho real / 100%** (desative “Ajustar à página”).\n"
    "- Desative margens automáticas do driver.\n"
)
