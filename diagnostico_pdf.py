#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de diagnóstico para entender o PDF profissional
"""

from PyPDF2 import PdfReader
import json

# Abrir o PDF profissional
pdf_path = "Plano Alimentar de Guilherme Silva Moraes .pdf"

print("=" * 80)
print("DIAGNÓSTICO DO PDF PROFISSIONAL")
print("=" * 80)

try:
    with open(pdf_path, 'rb') as file:
        reader = PdfReader(file)

        print(f"\nArquivo: {pdf_path}")
        print(f"Total de paginas: {len(reader.pages)}")
        print("\n" + "=" * 80)
        print("TEXTO EXTRAÍDO:")
        print("=" * 80 + "\n")

        texto_completo = ""
        for i, page in enumerate(reader.pages, 1):
            texto_pagina = page.extract_text() or ""
            texto_completo += texto_pagina

            print(f"\n--- PÁGINA {i} ---")
            print(texto_pagina)
            print("\n" + "-" * 80)

        print("\n" + "=" * 80)
        print("ESTATÍSTICAS:")
        print("=" * 80)
        print(f"Total de caracteres: {len(texto_completo)}")
        print(f"Total de linhas: {len(texto_completo.splitlines())}")

        # Análise de palavras-chave
        print("\n" + "=" * 80)
        print("ANÁLISE DE PALAVRAS-CHAVE:")
        print("=" * 80)

        texto_lower = texto_completo.lower()

        keywords = {
            "Horários": ["07:", "08:", "09:", "10:", "11:", "12:", "13:", "14:", "15:", "16:", "17:", "18:", "19:", "20:"],
            "Refeições": ["café da manhã", "almoço", "jantar", "lanche", "ceia"],
            "Alimentos base": ["arroz", "feijão", "frango", "carne", "peixe", "ovo"],
            "Frutas": ["banana", "maçã", "uva", "morango", "melão", "kiwi", "abacaxi"],
            "Indicadores": ["grama", "unidade", "colher", "ou"]
        }

        for categoria, palavras in keywords.items():
            print(f"\n{categoria}:")
            for palavra in palavras:
                count = texto_lower.count(palavra)
                if count > 0:
                    print(f"  OK '{palavra}': {count}x")

        print("\n" + "=" * 80)
        print("PRIMEIRAS 500 CARACTERES:")
        print("=" * 80)
        print(texto_completo[:500])

        # Salvar em arquivo para análise
        with open("pdf_extraido.txt", "w", encoding="utf-8") as f:
            f.write(texto_completo)

        print("\nOK - Texto completo salvo em: pdf_extraido.txt")

except Exception as e:
    print(f"\nERRO: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
