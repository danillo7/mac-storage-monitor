#!/usr/bin/env python3
"""
Script de Liberação de Espaço iCloud
Executa brctl evict em todos os arquivos locais do iCloud Drive
"""

import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

ICLOUD_DIR = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs"
LOG_FILE = Path(f"/tmp/icloud_evict_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

def get_size_gb(path: Path) -> float:
    """Calcula tamanho em GB"""
    try:
        result = subprocess.run(['du', '-sk', str(path)], capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            return round(int(result.stdout.split()[0]) / (1024**2), 2)
    except:
        pass
    return 0

def count_local_files(path: Path) -> int:
    """Conta arquivos locais (não .icloud)"""
    try:
        result = subprocess.run(
            f'find "{path}" -type f ! -name "*.icloud" 2>/dev/null | wc -l',
            shell=True, capture_output=True, text=True, timeout=120
        )
        return int(result.stdout.strip())
    except:
        return 0

def evict_folder(folder: Path, log_file):
    """Executa evict em uma pasta"""
    print(f"\n📂 Processando: {folder.name}")

    size_before = get_size_gb(folder)
    file_count = count_local_files(folder)

    print(f"   Tamanho: {size_before} GB | Arquivos: {file_count}")

    if file_count == 0:
        print("   ⏭️  Já está otimizada")
        return 0

    # Executar evict
    processed = 0
    try:
        result = subprocess.run(
            f'find "{folder}" -type f ! -name "*.icloud" -print0 2>/dev/null',
            shell=True, capture_output=True, timeout=300
        )

        files = result.stdout.split(b'\x00')
        total = len([f for f in files if f])

        for i, file_path in enumerate(files):
            if not file_path:
                continue

            file_str = file_path.decode('utf-8', errors='ignore')
            try:
                subprocess.run(['brctl', 'evict', file_str], capture_output=True, timeout=10)
                processed += 1
                log_file.write(f"EVICTED: {file_str}\n")

                # Progresso a cada 100 arquivos
                if processed % 100 == 0:
                    print(f"   ⏳ Progresso: {processed}/{total} ({(processed/total*100):.1f}%)")
            except:
                pass

        size_after = get_size_gb(folder)
        freed = size_before - size_after
        print(f"   ✅ Concluído! Liberado: {freed:.2f} GB")
        return freed

    except subprocess.TimeoutExpired:
        print("   ⚠️  Timeout - pulando para próxima pasta")
        return 0
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        return 0

def main():
    print("=" * 60)
    print("🚀 LIBERADOR DE ESPAÇO ICLOUD")
    print("=" * 60)
    print(f"\n📁 Diretório: {ICLOUD_DIR}")
    print(f"📝 Log: {LOG_FILE}")

    # Verificar espaço antes
    print("\n📊 Status Inicial:")
    result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
    print(result.stdout)

    total_before = get_size_gb(ICLOUD_DIR)
    print(f"💾 iCloud local total: {total_before} GB")

    # Listar pastas ordenadas por tamanho
    folders = []
    for item in ICLOUD_DIR.iterdir():
        if item.is_dir():
            size = get_size_gb(item)
            folders.append((item, size))

    folders.sort(key=lambda x: x[1], reverse=True)

    print("\n📂 Pastas a processar:")
    for folder, size in folders[:10]:
        print(f"   {size:>8} GB - {folder.name}")

    # Abrir log
    total_freed = 0
    with open(LOG_FILE, 'w') as log:
        log.write(f"# Liberação de Espaço iCloud - {datetime.now()}\n")
        log.write(f"# Total antes: {total_before} GB\n\n")

        for folder, size in folders:
            if size > 0:
                freed = evict_folder(folder, log)
                total_freed += freed

    # Status final
    print("\n" + "=" * 60)
    print("📊 RESULTADO FINAL")
    print("=" * 60)

    result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
    print(result.stdout)

    total_after = get_size_gb(ICLOUD_DIR)
    print(f"💾 iCloud antes: {total_before} GB")
    print(f"💾 iCloud depois: {total_after} GB")
    print(f"✅ Total liberado: {total_before - total_after:.2f} GB")
    print(f"\n📝 Log salvo em: {LOG_FILE}")

if __name__ == "__main__":
    main()
