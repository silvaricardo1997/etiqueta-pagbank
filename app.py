# app.py
# Streamlit – Cortar Etiqueta PagBank (100×150 mm) – SOMENTE FIT + Lote
#   - Upload de vários PDFs A4
#   - Página 1 de cada PDF: etiqueta recortada → 100×150 mm (fit proporcional)
#   - Página 2 de cada PDF: DACE RESUMIDA → 100×150 mm (página inteira)
#   - Gera 1 PDF COMBINADO (multi-página): etiqueta + DACE intercalados
#   - Pré-visualização de cada etiqueta e DACE antes do download

import io
from copy import deepcopy
from datetime import datetime

import fitz  # PyMuPDF
import streamlit as st
from pypdf import PdfReader, PdfWriter, Transformation
from pypdf.generic import RectangleObject

st.set_page_config(
    page_title="Etiqueta + DACE PagBank (100×150 mm) – Lote",
    page_icon="📦",
    layout="centered",
)

st.title("Etiqueta + DACE PagBank (100×150 mm) – Lote")
st.caption(
    "Envie **um ou vários** PDFs do PagBank/Envio Fácil. "
    "Para cada arquivo: recorta a **etiqueta (pág. 1)** e adapta a **DACE RESUMIDA (pág. 2)** "
    "para **100×150 mm**, gerando um **PDF combinado** pronto para impressão térmica."
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
) -> tuple[bytes, str]:
    """Recorta e redimensiona proporcionalmente (fit) uma página para o tamanho alvo."""
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

    if x0 < 0:
        x1 += x0
        x0 = 0.0
    if y0 < 0:
        y1 += y0
        y0 = 0.0
    x1 = min(pw, x1)
    y1 = min(ph, y1)

    target_w_pt = mm_to_pt(target_width_mm)
    target_h_pt = mm_to_pt(target_height_mm)

    crop_w = x1 - x0
    crop_h = y1 - y0

    tx = -x0
    ty = -y0
    sx = target_w_pt / crop_w if crop_w else 1.0
    sy = target_h_pt / crop_h if crop_h else 1.0
    s  = min(sx, sy)

    page_fit = deepcopy(page)
    page_fit.cropbox.lower_left  = (x0, y0)
    page_fit.cropbox.upper_right = (x1, y1)
    page_fit.mediabox.lower_left  = (x0, y0)
    page_fit.mediabox.upper_right = (x1, y1)
    page_fit.add_transformation(Transformation().translate(tx, ty).scale(s, s))
    page_fit.mediabox = RectangleObject([0, 0, target_w_pt, target_h_pt])
    page_fit.cropbox  = RectangleObject([0, 0, target_w_pt, target_h_pt])

    writer_fit = PdfWriter()
    writer_fit.add_page(page_fit)
    buf = io.BytesIO()
    writer_fit.write(buf)

    debug = (
        f"page_size_pt=({pw:.2f},{ph:.2f}) | "
        f"rect_pt=({x0:.2f},{y0:.2f},{x1:.2f},{y1:.2f}) | "
        f"target_pt=({target_w_pt:.2f},{target_h_pt:.2f}) | "
        f"scale=(sx={sx:.6f}, sy={sy:.6f}) used={s:.6f}"
    )
    return buf.getvalue(), debug


def fit_full_page(pdf_bytes: bytes, page_index: int) -> bytes:
    """Redimensiona uma página inteira para 100×150 mm sem recorte."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    page = reader.pages[page_index]
    pw = float(page.mediabox.width)
    ph = float(page.mediabox.height)

    target_w_pt = mm_to_pt(100.0)
    target_h_pt = mm_to_pt(150.0)

    sx = target_w_pt / pw if pw else 1.0
    sy = target_h_pt / ph if ph else 1.0
    s  = min(sx, sy)

    page_fit = deepcopy(page)
    page_fit.add_transformation(Transformation().scale(s, s))
    page_fit.mediabox = RectangleObject([0, 0, target_w_pt, target_h_pt])
    page_fit.cropbox  = RectangleObject([0, 0, target_w_pt, target_h_pt])

    writer = PdfWriter()
    writer.add_page(page_fit)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def pdf_to_png(pdf_bytes: bytes, dpi: int = 150) -> bytes:
    """Renderiza a página 0 de um PDF como PNG."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = doc[0].get_pixmap(matrix=mat, colorspace=fitz.csRGB)
    return pix.tobytes("png")


# ------------------------ UI ------------------------
with st.sidebar:
    st.header("Recorte da etiqueta (pág. 1)")
    st.caption("Coordenadas em mm. Use ponto decimal.")
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

st.write(":orange[Envie **um ou vários** PDFs do PagBank. Cada arquivo deve ter a etiqueta na pág. 1 e a DACE na pág. 2.]")
uploaded_files = st.file_uploader("PDF(s)", type=["pdf"], accept_multiple_files=True)

combine_fit = st.checkbox("Gerar COMBINADO único (etiqueta + DACE intercalados)", value=True)

if st.button("Processar"):
    if not uploaded_files:
        st.error("Envie pelo menos um PDF.")
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        combined_writer = PdfWriter() if combine_fit else None

        # (nome, label_bytes, dace_bytes, label_png, dace_png)
        per_file: list[tuple[str, bytes, bytes | None, bytes, bytes | None]] = []
        errors: list[str] = []
        progress = st.progress(0, text="Processando...")

        for i, f in enumerate(uploaded_files):
            progress.progress(i / len(uploaded_files), text=f"Processando {f.name}…")
            try:
                pdf_bytes = f.read()
                n_pages = len(PdfReader(io.BytesIO(pdf_bytes)).pages)

                label_bytes, _ = build_fit_only(
                    pdf_bytes=pdf_bytes,
                    page_index=0,
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

                dace_bytes = fit_full_page(pdf_bytes, 1) if n_pages >= 2 else None

                label_png = pdf_to_png(label_bytes)
                dace_png  = pdf_to_png(dace_bytes) if dace_bytes else None

                per_file.append((f.name, label_bytes, dace_bytes, label_png, dace_png))

                if combined_writer:
                    combined_writer.add_page(PdfReader(io.BytesIO(label_bytes)).pages[0])
                    if dace_bytes:
                        combined_writer.add_page(PdfReader(io.BytesIO(dace_bytes)).pages[0])

            except Exception as e:
                errors.append(f"**{f.name}:** {e}")

        progress.progress(1.0, text="Concluído!")

        if errors:
            st.warning("Alguns arquivos falharam:")
            for err in errors:
                st.markdown(f"- {err}")

        if per_file:
            st.success(f"{len(per_file)} de {len(uploaded_files)} arquivo(s) processado(s) com sucesso.")

            # ── Pré-visualização ──────────────────────────────────────────
            st.subheader("Pré-visualização")
            for name, label_b, dace_b, label_png, dace_png in per_file:
                base = name.rsplit(".", 1)[0]
                with st.expander(f"📄 {base}", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.caption("Etiqueta (100×150 mm)")
                        st.image(label_png, use_container_width=True)
                        st.download_button(
                            "⬇️ Baixar etiqueta",
                            data=label_b,
                            file_name=f"{base}_etiqueta.pdf",
                            mime="application/pdf",
                            key=f"dl_label_{name}",
                        )
                    with col2:
                        st.caption("DACE RESUMIDA (100×150 mm)")
                        if dace_png:
                            st.image(dace_png, use_container_width=True)
                            st.download_button(
                                "⬇️ Baixar DACE",
                                data=dace_b,
                                file_name=f"{base}_dace.pdf",
                                mime="application/pdf",
                                key=f"dl_dace_{name}",
                            )
                        else:
                            st.info("DACE não encontrada (apenas 1 página no arquivo).")

            # ── Download combinado ────────────────────────────────────────
            if combined_writer:
                buf = io.BytesIO()
                combined_writer.write(buf)
                st.download_button(
                    "⬇️ Baixar COMBINADO (etiqueta + DACE) – todos",
                    data=buf.getvalue(),
                    file_name=f"etiquetas_dace_{ts}.pdf",
                    mime="application/pdf",
                )

st.divider()
st.markdown(
    "**Dicas para imprimir na térmica (Coibeu WKZ-80D):**\n"
    "- Selecione mídia **100×150 mm (10×15 cm)**.\n"
    "- Use **Tamanho real / 100%** (desative \"Ajustar à página\").\n"
    "- Desative margens automáticas do driver.\n"
)
