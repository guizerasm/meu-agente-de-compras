from PyPDF2 import PdfReader

def extrair_texto_pdf(file) -> str:
    reader = PdfReader(file.file)
    texto = ""
    for page in reader.pages:
        texto += page.extract_text() or ""
    return texto
