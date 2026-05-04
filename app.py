# app.py
# Streamlit – Cortar Etiqueta PagBank (100×150 mm) – SOMENTE FIT + Lote
#   - Upload de vários PDFs A4
#   - Para cada PDF: gera versão 100×150 (fit proporcional)
#   - Gera também 1 PDF COMBINADO (multi-página) com todos os resultados

import io
from copy import deepcopy
from datetime import datetime

import streamlit as st
from pypdf import PdfReader, PdfWriter, Transformation
from pypdf.generic import RectangleObject

st.set_page_config(
    page_title="Cortar Etiqueta PagBank (100×150 mm) – Fit em Lote",
    page_icon="📦",
    layout="centered",
)

st.title("Cortar Etiqueta PagBank (100×150 mm) – Fit em Lote")
st.caption(
    "Envie **um ou vários** PDFs A4 do PagBank/Envio Fácil, informe as coordenadas em mm "
    "e gere a versão **100×150 mm** (fit proporcional). Também produzimos **um único PDF combinado** com todas as páginas."
)

MM_TO_PT = 72.0 / 25.4
def mm_to_pt(mm: float) -> float: return mm * MM_TO_PT


def build_fit_only(
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
    """Retorna (fit_pdf_bytes, debug_info:str) para UM PDF."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    if page_index < 0 or page_index >= len(reader.pages):
        raise ValueError(f"Índice de página {page_index} inválido (o PDF tem {len(reader.pages)} página(s)).")

    page = reader.pages[page_index]
    pw = float(page.mediabox.width)
    ph = float(page.mediabox.height)

    page_h_mm = ph / MM_TO_PT

    x0_mm = x_left_mm - extra_left_mm
    y0_base_mm = page_h_mm - (y_top_mm + height_mm)
    y0_mm = y0_base_mm - extra_bottom_mm

    width_final_mm  = width_mm  + extra_left_mm + extra_right_mm
    height_final_mm = height_mm + extra_top_mm  + extra_bottom_mm

    x0 = mm_to_pt(x0_mm)
    y0 = mm_to_pt(y0_mm)
    x1 = mm_to_pt(x0_mm + width_final_mm)
    y1 = mm_to_pt(y0_mm + height_final_mm)

    # Clampar à página e ajustar largura/altura para não distorcer o fit
    if x0 < 0:
        x1 += x0  # reduz x1 pelo mesmo delta
        x0 = 0.0
    if y0 < 0:
        y1 += y0
        y0 = 0.0
    x1 = min(pw, x1)
    y1 = min(ph, y1)

    target_w_pt = mm_to_pt(target_width_mm)
    target_h_pt = mm_to_pt(target_height_mm)

    page_fit = deepcopy(page)
    page_fit.cropbox.lower_left  = (x0, y0)
    page_fit.cropbox.upper_right = (x1, y1)
    page_fit.mediabox.lower_left  = (x0, y0)
    page_fit.mediabox.upper_right = (x1, y1)

    crop_w = x1 - x0
    crop_h = y1 - y0

    tx = -x0
    ty = -y0
    sx = target_w_pt / crop_w if crop_w else 1.0
    sy = target_h_pt / crop_h if crop_h else 1.0
    s  = min(sx, sy)

    page_fit.add_transformation(Transformation().translate(tx, ty).scale(s, s))
    page_fit.mediabox = RectangleObject([0, 0, target_w_pt, target_h_pt])
    page_fit.cropbox  = RectangleObject([0, 0, target_w_pt, target_h_pt])

    writer_fit = PdfWriter()
    writer_fit.add_page(page_fit)
    buf = io.BytesIO()
    writer_fit.write(buf)
    fit_bytes = buf.getvalue()

    debug = (
        f"page_size_pt=({pw:.2f},{ph:.2f}) | "
        f"rect_pt=({x0:.2f},{y0:.2f},{x1:.2f},{y1:.2f}) | "
        f"target_pt=({target_w_pt:.2f},{target_h_pt:.2f}) | "
        f"scale=(sx={sx:.6f}, sy={sy:.6f}) used={s:.6f}"
    )
    return fit_bytes, debug


def find_declaracao_page(pdf_bytes: bytes) -> int | None:
    """Retorna o índice da primeira página com 'DECLARAÇÃO DE CONTEÚDO', ou None."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    for idx, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        if "DECLARAÇÃO DE CONTEÚDO" in text.upper():
            return idx
    return None


def process_declaracao(pdf_bytes: bytes, idx: int, combined_writer: PdfWriter | None) -> bytes | None:
    """Redimensiona a página de declaração para 100×150 mm e a adiciona ao combinado."""
    decl_bytes, _ = build_fit_only(
        pdf_bytes=pdf_bytes,
        page_index=idx,
        x_left_mm=0.0,
        y_top_mm=0.0,
        width_mm=210.0,
        height_mm=297.0,
        target_width_mm=100.0,
        target_height_mm=150.0,
    )
    if combined_writer is not None:
        r_decl = PdfReader(io.BytesIO(decl_bytes))
        combined_writer.add_page(r_decl.pages[0])
    return decl_bytes


# ------------------------ UI ------------------------
with st.sidebar:
    st.header("Parâmetros (mm) – aplicados a TODOS os PDFs")
    st.caption("Use ponto decimal. Defaults = seus valores calibrados.")
    x_left_mm = st.number_input("X da esquerda (mm)", value=85.0, step=0.1)
    y_top_mm  = st.number_input("Y do topo (mm)", value=34.0, step=0.1)
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

st.write(":orange[Envie **um ou vários** PDFs A4 com a etiqueta.]")
uploaded_files = st.file_uploader("PDF(s) A4", type=["pdf"], accept_multiple_files=True)
page_index = st.number_input("Página a processar (0 = 1ª)", min_value=0, value=0, step=1)

combine_fit = st.checkbox("Gerar COMBINADO (100×150) único", value=True)

if st.button("Processar (somente FIT 100×150)"):
    if not uploaded_files:
        st.error("Envie pelo menos um PDF.")
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        combined_fit_writer = PdfWriter() if combine_fit else None

        per_file = []
        errors = []
        progress = st.progress(0, text="Processando...")

        for i, f in enumerate(uploaded_files):
            progress.progress((i) / len(uploaded_files), text=f"Processando {f.name}…")
            try:
                pdf_bytes = f.read()

                fit_bytes, _ = build_fit_only(
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
                per_file.append((f.name, fit_bytes))

                if combined_fit_writer:
                    r_fit = PdfReader(io.BytesIO(fit_bytes))
                    combined_fit_writer.add_page(r_fit.pages[0])

                decl_idx = find_declaracao_page(pdf_bytes)
                if decl_idx is not None:
                    process_declaracao(pdf_bytes, decl_idx, combined_fit_writer)

            except Exception as e:
                errors.append(f"**{f.name}:** {e}")

        progress.progress(1.0, text="Concluído!")

        if errors:
            st.warning("Alguns arquivos falharam:")
            for err in errors:
                st.markdown(f"- {err}")

        if per_file:
            st.success(f"{len(per_file)} de {len(uploaded_files)} arquivo(s) processado(s) com sucesso.")

            with st.expander("Baixar 100×150 individuais"):
                for name, fit_b in per_file:
                    base = name.rsplit(".", 1)[0]
                    st.download_button(
                        f"⬇️ {base}_fit.pdf",
                        data=fit_b,
                        file_name=f"{base}_fit.pdf",
                        mime="application/pdf",
                    )

            if combined_fit_writer:
                buf = io.BytesIO()
                combined_fit_writer.write(buf)
                st.download_button(
                    "⬇️ Baixar COMBINADO (100×150) – todos",
                    data=buf.getvalue(),
                    file_name=f"etiquetas_fit_{ts}.pdf",
                    mime="application/pdf",
                )

st.divider()
st.markdown(
    "**Dicas para imprimir na térmica (Coibeu WKZ-80D):**\n"
    "- Selecione mídia **100×150 mm (10×15 cm)**.\n"
    "- Use **Tamanho real / 100%** (desative \"Ajustar à página\").\n"
    "- Desative margens automáticas do driver.\n"
)
