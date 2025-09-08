# app.py
# Streamlit – Cortar Etiqueta PagBank (100×150 mm) com processamento em lote
#   - Upload de vários PDFs A4
#   - Para cada PDF: recorte EXATO e versão 100×150 (fit proporcional)
#   - Gera também PDFs COMBINADOS (multi-página) com todos os resultados

import io
from copy import deepcopy
from datetime import datetime

import streamlit as st
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2 import Transformation
from PyPDF2.generic import RectangleObject

st.set_page_config(
    page_title="Cortar Etiqueta PagBank (100×150 mm) – Lote",
    page_icon="📦",
    layout="centered",
)

st.title("Cortar Etiqueta PagBank (100×150 mm) – Lote")
st.caption(
    "Envie **um ou vários** PDFs A4 do PagBank/Envio Fácil, informe as coordenadas em mm "
    "e gere: (1) recortes **exatos** e (2) versões **100×150 mm** (fit). "
    "Também produzimos **um único PDF combinado** com todas as páginas de saída."
)

MM_TO_PT = 72.0 / 25.4  # pontos por mm


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
    """Retorna (crop_pdf_bytes, fit_pdf_bytes, debug_info:str) para UM PDF."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    if page_index < 0 or page_index >= len(reader.pages):
        raise ValueError("Índice de página inválido.")

    page = reader.pages[page_index]
    pw = float(page.mediabox.width)
    ph = float(page.mediabox.height)

    # Altura real da página em mm
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

    # Clamp
    x0 = max(0.0, x0)
    y0 = max(0.0, y0)
    x1 = min(pw, x1)
    y1 = min(ph, y1)

    # (1) Recorte EXATO
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

    # (2) Fit 100×150 mm
    target_w_pt = mm_to_pt(target_width_mm)
    target_h_pt = mm_to_pt(target_height_mm)
    crop_w = float(page_crop.mediabox.width)
    crop_h = float(page_crop.mediabox.height)

    tx = -x0
    ty = -y0
    sx = target_w_pt / crop_w if crop_w else 1.0
    sy = target_h_pt / crop_h if crop_h else 1.0
    s = min(sx, sy)

    page_fit = deepcopy(page)
    page_fit.cropbox.lower_left = (x0, y0)
    page_fit.cropbox.upper_right = (x1, y1)
    page_fit.mediabox.lower_left = (x0, y0)
    page_fit.mediabox.upper_right = (x1, y1)
    page_fit.add_transformation(Transformation().translate(tx, ty).scale(s, s))
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


# ------------------------ UI ------------------------
with st.sidebar:
    st.header("Parâmetros (mm) – aplicados a TODOS os PDFs enviados")
    st.caption("Use ponto decimal. Defaults = seus valores calibrados.")
    x_left_mm = st.number_input("X da esquerda (mm)", value=85.0, step=0.1)
    y_top_mm = st.number_input("Y do topo (mm)", value=34.0, step=0.1)
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

st.write(":orange[Envie **um ou vários** PDFs A4 com a etiqueta.]")
uploaded_files = st.file_uploader("PDF(s) A4", type=["pdf"], accept_multiple_files=True)
page_index = st.number_input("Página a processar (0 = 1ª)", min_value=0, value=0, step=1)

col1, col2 = st.columns(2)
with col1:
    combine_fit = st.checkbox("Gerar COMBINADO (100×150) único", value=True)
with col2:
    combine_crop = st.checkbox("Gerar COMBINADO (recortes exatos) único", value=False)

if st.button("Processar (lote)"):
    if not uploaded_files:
        st.error("Envie pelo menos um PDF.")
    else:
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")

            combined_fit_writer = PdfWriter() if combine_fit else None
            combined_crop_writer = PdfWriter() if combine_crop else None

            per_file_downloads = []

            for f in uploaded_files:
                pdf_bytes = f.read()
                crop_bytes, fit_bytes, _ = build_crop_and_fit(
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

                # Guardar individuais (opcional – mostramos botões)
                per_file_downloads.append((f.name, crop_bytes, fit_bytes))

                # Adicionar ao combinado (se selecionado)
                if combined_fit_writer:
                    r_fit = PdfReader(io.BytesIO(fit_bytes))
                    combined_fit_writer.add_page(r_fit.pages[0])

                if combined_crop_writer:
                    r_crop = PdfReader(io.BytesIO(crop_bytes))
                    combined_crop_writer.add_page(r_crop.pages[0])

            st.success("Processamento concluído!")

            # Downloads individuais (por arquivo)
            with st.expander("Baixar arquivos individuais"):
                for name, crop_b, fit_b in per_file_downloads:
                    base = name.rsplit(".", 1)[0]
                    st.write(f"**{base}**")
                    st.download_button(
                        f"⬇️ {base}_crop.pdf",
                        data=crop_b,
                        file_name=f"{base}_crop.pdf",
                        mime="application/pdf",
                    )
                    st.download_button(
                        f"⬇️ {base}_fit.pdf",
                        data=fit_b,
                        file_name=f"{base}_fit.pdf",
                        mime="application/pdf",
                    )
                    st.markdown("---")

            # Downloads combinados
            if combined_fit_writer:
                buf = io.BytesIO()
                combined_fit_writer.write(buf)
                st.download_button(
                    "⬇️ Baixar COMBINADO (100×150) – todos",
                    data=buf.getvalue(),
                    file_name=f"etiquetas_fit_{ts}.pdf",
                    mime="application/pdf",
                )

            if combined_crop_writer:
                bufc = io.BytesIO()
                combined_crop_writer.write(bufc)
                st.download_button(
                    "⬇️ Baixar COMBINADO (recortes exatos) – todos",
                    data=bufc.getvalue(),
                    file_name=f"etiquetas_crop_{ts}.pdf",
                    mime="application/pdf",
                )

        except Exception as e:
            st.error(f"Falha ao processar: {e}")
            st.stop()

st.divider()
st.markdown(
    "**Dicas para imprimir na térmica (Coibeu WKZ-80D):**\n"
    "- Selecione mídia **100×150 mm (10×15 cm)**.\n"
    "- Use **Tamanho real / 100%** (desative “Ajustar à página”).\n"
    "- Desative margens automáticas do driver.\n"
)
