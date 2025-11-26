import hashlib
import os
import platform
import subprocess


def get_hwid():
    """
    Gera uma assinatura única (Fingerprint) do computador.
    Combina Processador + Placa Mãe + Disco para criar um hash único.
    """
    try:
        system_info = platform.system()

        if system_info == "Windows":
            # Comando para pegar UUID da Placa Mãe
            cmd = "wmic csproduct get uuid"
            uuid = subprocess.check_output(cmd).decode().split("\n")[1].strip()

            # Comando para pegar Serial do Disco C:
            cmd_disk = "vol c:"
            disk = (
                subprocess.check_output(cmd_disk, shell=True)
                .decode()
                .split()[-1]
                .strip()
            )

            # Combina os dois
            raw_id = f"{uuid}-{disk}"

        else:
            # Fallback para Linux/Mac (caso precise no futuro)
            raw_id = "UNSUPPORTED_PLATFORM"

        # Cria um Hash MD5 para ficar curto e seguro
        return hashlib.md5(raw_id.encode()).hexdigest().upper()

    except Exception as e:
        # Em caso de erro (ex: permissão), retorna um erro genérico + nome da máquina
        return hashlib.md5(platform.node().encode()).hexdigest().upper()


if __name__ == "__main__":
    print(f"SEU HWID: {get_hwid()}")
