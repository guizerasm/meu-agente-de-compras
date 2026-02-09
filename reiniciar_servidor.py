#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para reiniciar o servidor do Agente de Compras
Mata processos na porta 8000 e inicia um novo servidor
"""

import subprocess
import time
import sys
import os

def matar_processo_porta_8000():
    """Mata todos os processos usando a porta 8000"""
    print("Procurando processos na porta 8000...")

    try:
        # Encontrar processos na porta 8000
        result = subprocess.run(
            'netstat -ano | findstr :8000',
            shell=True,
            capture_output=True,
            text=True
        )

        if result.returncode == 0 and result.stdout:
            linhas = result.stdout.strip().split('\n')
            pids = set()

            for linha in linhas:
                if 'LISTENING' in linha:
                    partes = linha.split()
                    if len(partes) >= 5:
                        pid = partes[-1]
                        if pid.isdigit():
                            pids.add(pid)

            if pids:
                print(f"Encontrados {len(pids)} processo(s) na porta 8000")
                for pid in pids:
                    try:
                        subprocess.run(f'taskkill /F /PID {pid}', shell=True, check=True)
                        print(f"  [OK] Processo {pid} finalizado")
                    except subprocess.CalledProcessError:
                        print(f"  [ERRO] Não foi possível finalizar processo {pid}")

                time.sleep(2)
                return True
            else:
                print("Nenhum processo encontrado na porta 8000")
                return False
        else:
            print("Porta 8000 está livre")
            return False

    except Exception as e:
        print(f"Erro ao verificar porta: {e}")
        return False

def iniciar_servidor():
    """Inicia o servidor"""
    print("\nIniciando servidor...")
    print("="*60)
    print("Servidor iniciado! Pressione Ctrl+C para parar")
    print("Acesse: http://localhost:8000")
    print("="*60 + "\n")

    try:
        # Iniciar servidor
        subprocess.run([sys.executable, 'server.py'], check=True)
    except KeyboardInterrupt:
        print("\n\nServidor finalizado pelo usuário")
    except Exception as e:
        print(f"\nErro ao iniciar servidor: {e}")
        sys.exit(1)

def main():
    print("="*60)
    print("REINICIAR SERVIDOR - AGENTE DE COMPRAS")
    print("="*60 + "\n")

    # Verificar se está na pasta correta
    if not os.path.exists('server.py'):
        print("ERRO: arquivo server.py não encontrado!")
        print("Certifique-se de estar na pasta do projeto")
        sys.exit(1)

    # Matar processos existentes
    matar_processo_porta_8000()

    # Iniciar novo servidor
    iniciar_servidor()

if __name__ == "__main__":
    main()
