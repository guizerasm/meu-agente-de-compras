"""
Gerador de PDF para lista de compras
"""
from io import BytesIO
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from datetime import datetime
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def gerar_pdf_lista_compras(lista_compras: list) -> bytes:
    """
    Gera um PDF a partir de uma lista de compras - VERSÃO ULTRA-ROBUSTA

    Args:
        lista_compras: Lista de dicionários com 'nome', 'quantidade', 'motivo'

    Returns:
        bytes do PDF gerado
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError("reportlab não está instalado. Execute: pip install reportlab")

    # Função de sanitização global
    def sanitizar(texto):
        if not texto:
            return ""
        texto = str(texto)

        # Correções de caracteres comuns ANTES de remover acentos
        correcoes = {
            'ã': 'a', 'á': 'a', 'à': 'a', 'â': 'a',
            'é': 'e', 'ê': 'e',
            'í': 'i',
            'ó': 'o', 'ô': 'o', 'õ': 'o',
            'ú': 'u', 'ü': 'u',
            'ç': 'c',
            'Ã': 'A', 'Á': 'A', 'À': 'A', 'Â': 'A',
            'É': 'E', 'Ê': 'E',
            'Í': 'I',
            'Ó': 'O', 'Ô': 'O', 'Õ': 'O',
            'Ú': 'U', 'Ü': 'U',
            'Ç': 'C'
        }

        for char_acentuado, char_normal in correcoes.items():
            texto = texto.replace(char_acentuado, char_normal)

        # Remover outros caracteres não-ASCII
        texto = texto.encode('ascii', 'ignore').decode('ascii')

        # Remover caracteres problemáticos que passaram
        for char in ['&', '<', '>', '\n', '\r', '\t']:
            texto = texto.replace(char, ' ')

        return texto.strip()[:200]  # Limitar tamanho

    # TENTAR GERAR PDF COMPLETO (Método 1)
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#0f766e'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )

        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.grey,
            spaceAfter=20,
            alignment=TA_CENTER
        )

        elements = []

        # Título SEM EMOJI (caracteres ASCII apenas)
        elements.append(Paragraph("Lista de Compras", title_style))

        # Data
        data_atual = datetime.now().strftime("%d/%m/%Y as %H:%M")  # Sem "à" com acento
        elements.append(Paragraph(f"Gerada em {data_atual}", subtitle_style))
        elements.append(Spacer(1, 0.5*cm))

        # Verificar se há itens
        if not lista_compras or len(lista_compras) == 0:
            elements.append(Paragraph("Nenhum item na lista.", styles['Normal']))
        else:
            # Criar tabela
            data = [['#', 'Item', 'Quantidade', 'Observacoes']]

            for i, item in enumerate(lista_compras, 1):
                nome = sanitizar(item.get('nome', 'Item sem nome'))
                qtd = sanitizar(item.get('quantidade', 'N/A'))
                motivo = sanitizar(item.get('motivo', 'Conforme dieta'))

                # Usar texto simples curto (max 40 chars para caber bem)
                data.append([
                    str(i),
                    nome[:25],  # Limitar nome
                    qtd[:15],    # Limitar quantidade
                    motivo[:40]  # Limitar motivo
                ])

        # Criar tabela com larguras ajustadas (Observações com mais espaço)
        table = Table(data, colWidths=[1.2*cm, 4.5*cm, 2.8*cm, 7.5*cm])
        table.setStyle(TableStyle([
            # Cabeçalho
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f766e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),

            # Conteúdo
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Número centralizado
            ('ALIGN', (1, 1), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),

            # Bordas
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#0f766e')),

            # Alternância de cores
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.beige]),
        ]))

        elements.append(table)

        # Rodapé
        elements.append(Spacer(1, 1*cm))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
        elements.append(Paragraph(
            f"Total de itens: {len(lista_compras)} | Gerado por Agente de Compras",
            footer_style
        ))

        # Construir e retornar PDF
        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    except Exception as e:
        print(f"Erro no PDF completo: {e}")
        # FALLBACK: PDF MINIMALISTA (Método 2)
        try:
            buffer2 = BytesIO()
            doc2 = SimpleDocTemplate(buffer2, pagesize=A4)
            styles2 = getSampleStyleSheet()

            simple_elements = [
                Paragraph("Lista de Compras", styles2['Title']),
                Spacer(1, 1*cm)
            ]

            # Adicionar itens como parágrafos simples
            for i, item in enumerate(lista_compras, 1):
                nome = sanitizar(item.get('nome', 'Item'))
                qtd = sanitizar(item.get('quantidade', 'N/A'))

                simple_elements.append(Paragraph(
                    f"{i}. {nome} - {qtd}",
                    styles2['Normal']
                ))
                simple_elements.append(Spacer(1, 0.2*cm))

            doc2.build(simple_elements)
            pdf_bytes2 = buffer2.getvalue()
            buffer2.close()
            return pdf_bytes2

        except Exception as e2:
            print(f"Erro no PDF simples: {e2}")
            # ÚLTIMO RECURSO: Retornar erro
            raise Exception(f"Nao foi possivel gerar PDF: {str(e2)}")


# Função auxiliar para gerar texto simples (fallback)
def gerar_texto_lista_compras(lista_compras: list) -> str:
    """
    Gera uma versão em texto da lista de compras
    """
    if not lista_compras:
        return "Nenhum item na lista."

    texto = "=" * 60 + "\n"
    texto += "        LISTA DE COMPRAS\n"
    texto += "=" * 60 + "\n\n"

    for i, item in enumerate(lista_compras, 1):
        nome = item.get('nome', 'Item')
        qtd = item.get('quantidade', 'N/A')
        motivo = item.get('motivo', 'Conforme dieta')

        texto += f"{i:2d}. {nome.upper()}\n"
        texto += f"    Quantidade: {qtd}\n"
        texto += f"    Observação: {motivo}\n\n"

    texto += "=" * 60 + "\n"
    texto += f"Total: {len(lista_compras)} itens\n"

    return texto
