import hashlib
import json
import platform
import random
import string
import subprocess

import requests

# ==============================================================================
# CONFIGURAÇÕES E CONSTANTES
# ==============================================================================
URL_BASE = "https://crash-api-jose.onrender.com"

# Chaves de teste antigas (mantidas para referência)
CHAVE_VALIDA = "TESTE-CRASH-VALIDA"
CHAVE_OUTRO_PC = "TESTE-CRASH-OUTRO"
HWID_SIMULADO_CONFLITO = "DEADC0DE1234567890ABCDEF"


# ==============================================================================
# FUNÇÃO DE HWID (Útil se você quiser testar validação localmente)
# ==============================================================================
def get_hwid():
    """
    Gera uma assinatura única (Fingerprint) do computador.
    """
    raw_id = ""
    try:
        if platform.system() == "Windows":
            cmd = "wmic csproduct get uuid"
            uuid = subprocess.check_output(cmd, encoding="cp850").split("\n")[1].strip()

            cmd_disk = "vol c:"
            disk = (
                subprocess.check_output(cmd_disk, shell=True)
                .decode("cp850")
                .split()[-1]
                .strip()
            )
            raw_id = f"{uuid}-{disk}"
        else:
            raw_id = platform.node()

        if not raw_id:
            raw_id = platform.node()

        return hashlib.md5(raw_id.encode()).hexdigest().upper()

    except Exception as e:
        print(f"Erro ao gerar HWID: {e}")
        return hashlib.md5(platform.node().encode()).hexdigest().upper()


# Obtém o HWID local uma vez
HWID_LOCAL = get_hwid()


# ==============================================================================
# FUNÇÕES AUXILIARES DE REQUISIÇÃO
# ==============================================================================
def simular_requisicao(endpoint, dados):
    """Envia requisição POST para o servidor e exibe a resposta."""
    try:
        response = requests.post(f"{URL_BASE}/{endpoint}", json=dados)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        try:
            return e.response.json()
        except json.JSONDecodeError:
            return {
                "status": "erro",
                "mensagem": f"Erro HTTP: {e.response.status_code} {e.response.reason}",
            }
    except requests.exceptions.RequestException as e:
        return {"status": "erro", "mensagem": f"Erro de conexão: {e}"}


def imprimir_resultado_validacao(resposta):
    """Helper para imprimir o resultado de forma amigável."""
    status = resposta.get("status", "??")
    mensagem = resposta.get("mensagem", "N/A")

    if status == "sucesso":
        print(f"✅ SUCESSO! Mensagem: {mensagem}")
        return True
    else:
        print(f"❌ ERRO! Status: {status}, Mensagem: {mensagem}")
        return False


def _criar_chave_helper(chave, nome, dias=30):
    """Função auxiliar para enviar a requisição de criação."""
    data = {"chave": chave, "dias": dias, "nome": nome}
    resp = simular_requisicao("admin/criar_licenca", data)
    imprimir_resultado_validacao(resp)


def gerar_serial_key():
    """Gera uma chave estilo Office: XXXX-XXXX-XXXX-XXXX"""
    chars = string.ascii_uppercase + string.digits
    # Gera 4 blocos de 4 caracteres
    key_parts = ["".join(random.choices(chars, k=4)) for _ in range(4)]
    return "-".join(key_parts)


# ==============================================================================
# FUNÇÕES DE TESTE ANTIGAS (Mantidas para histórico)
# ==============================================================================
def passo_limpar_banco():
    print("\n--- 0. LIMPANDO BANCO DE DADOS ---")
    resp = simular_requisicao("admin/limpar_licencas", {})
    print(f"Limpeza: {resp.get('mensagem', 'Falha na limpeza')}")


def passo_criar_chave_antigo():
    print("\n--- 1. CRIANDO CHAVES TESTE ---")
    _criar_chave_helper(CHAVE_VALIDA, "Cliente Local")
    _criar_chave_helper(CHAVE_OUTRO_PC, "Cliente Outro PC")


def passo_validar_local(chave, hwid, descricao):
    print(f"\n--- 2. VALIDANDO CHAVE {chave} ({descricao}) ---")
    dados_validacao = {"chave": chave, "hwid": hwid}
    resposta = simular_requisicao("validar", dados_validacao)
    imprimir_resultado_validacao(resposta)


def passo_simular_conflito():
    print("\n--- 3. SIMULANDO CONFLITO DE HWID ---")
    dados_conflito = {"chave": CHAVE_VALIDA, "hwid": HWID_SIMULADO_CONFLITO}
    resposta = simular_requisicao("validar", dados_conflito)
    print("Tentativa de uso em novo PC:")
    imprimir_resultado_validacao(resposta)


# ==============================================================================
# EXECUÇÃO PRINCIPAL (GERADOR DE LICENÇAS)
# ==============================================================================
if __name__ == "__main__":

    print("--- GERADOR DE LICENÇAS PROFISSIONAIS ---")
    print(f"Conectado em: {URL_BASE}")

    # 1. CONFIGURAÇÃO DO NOVO CLIENTE
    # Mude o nome aqui para cada cliente novo que você vender
    nome_cliente = "Cliente: Oi Arylio"
    dias_validade = 30

    # 2. Gerar a chave aleatória automaticamente
    nova_chave = gerar_serial_key()

    # 3. Enviar para o servidor
    print(f"\nGerando licença para: {nome_cliente} ({dias_validade} dias)...")
    _criar_chave_helper(nova_chave, nome_cliente, dias=dias_validade)

    # 4. Exibir para você copiar
    print("\n" + "=" * 40)
    print(f"🔑 NOVA CHAVE GERADA: {nova_chave}")
    print("=" * 40)
    print("👉 Copie a chave acima e envie para o cliente colocar no license_key.txt")
