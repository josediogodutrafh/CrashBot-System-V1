"""
Script: Migrar chaves com caracteres ambíguos.

Normaliza chaves antigas que contêm 0 (zero), 1 (um) ou L
para usar apenas O, I — eliminando confusão visual.

Uso:
    python migrate_keys.py          # Modo dry-run (mostra mudanças sem aplicar)
    python migrate_keys.py --apply  # Aplica as mudanças no banco
"""

import asyncio
import sys

from app.database import AsyncSessionLocal
from app.models import Licenca
from sqlalchemy import select


def normalizar_chave(chave: str) -> str:
    """Normaliza caracteres ambíguos: 0→O, 1→I, L→I."""
    return (
        chave.upper()
        .replace("0", "O")
        .replace("1", "I")
        .replace("L", "I")
    )


async def migrate():
    apply = "--apply" in sys.argv

    print("=" * 60)
    print("MIGRAÇÃO DE CHAVES - Caracteres Ambíguos")
    print(f"Modo: {'APLICAR' if apply else 'DRY-RUN (simulação)'}")
    print("=" * 60)

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Licenca))
        licencas = result.scalars().all()

        alteradas = []

        for lic in licencas:
            chave_original = str(lic.chave)
            chave_nova = normalizar_chave(chave_original)

            if chave_nova != chave_original:
                alteradas.append((lic.id, lic.cliente_nome, chave_original, chave_nova))
                if apply:
                    lic.chave = chave_nova  # type: ignore

        if not alteradas:
            print("\nNenhuma chave precisa ser migrada.")
            return

        print(f"\n{len(alteradas)} chave(s) a alterar:\n")
        for lid, nome, antiga, nova in alteradas:
            print(f"  ID {lid:3d} | {nome or 'N/A':30s} | {antiga} → {nova}")

        if apply:
            await session.commit()
            print(f"\n{len(alteradas)} chave(s) migradas com sucesso!")
        else:
            print(f"\nUse --apply para aplicar as {len(alteradas)} mudança(s).")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(migrate())
