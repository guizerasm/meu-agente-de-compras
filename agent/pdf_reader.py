import pdfplumber


def extrair_texto_pdf(file) -> str:
    """Extrai texto de PDF usando pdfplumber (melhor para layouts complexos
    como dietas de nutricionistas com colunas e tabelas)."""
    with pdfplumber.open(file.file) as pdf:
        texto = ""
        for page in pdf.pages:
            texto += (page.extract_text() or "") + "\n"
    return texto
