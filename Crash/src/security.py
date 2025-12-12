import hashlib
import platform


def get_hwid():
    """
    Gera uma assinatura unica (Fingerprint) do computador.
    Usa o nome da maquina para gerar um hash consistente.
    """
    # Usa platform.node() que retorna o nome do computador
    # Isso e consistente e nao depende de comandos externos
    return hashlib.md5(platform.node().encode()).hexdigest().upper()


if __name__ == "__main__":
    print(f"SEU HWID: {get_hwid()}")
