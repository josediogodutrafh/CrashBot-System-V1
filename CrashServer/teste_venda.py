import json

import requests

# URL do seu servidor no Render (Produção)
URL_API = "https://crash-api-jose.onrender.com/api/pagamento/criar"

# Dados do cliente (Simulação)
# DICA: Use um e-mail real seu (diferente da conta do MP) para ver a notificação chegando
payload = {"email": "cliente.teste.compra@gmail.com", "plano": "mensal"}

print(f"⏳ Conectando ao servidor: {URL_API}...")
print(f"📦 Enviando pedido de compra para: {payload['email']}")

try:
    # Faz o pedido POST para a sua API
    response = requests.post(URL_API, json=payload)

    # Verifica se deu certo (Código 200)
    if response.status_code == 200:
        dados = response.json()

        if "checkout_url" in dados:
            print("\n" + "=" * 40)
            print("✅ SUCESSO! O Servidor gerou o link:")
            print("=" * 40)
            print(f"\n🔗 CLIQUE PARA PAGAR: {dados['checkout_url']}\n")
            print("=" * 40)
            print(
                "👉 Próximo passo: Abra o link, pague R$ 1,00 via Pix e verifique seu e-mail!"
            )
        else:
            print("\n⚠️ O servidor respondeu, mas não mandou o link:")
            print(dados)

    else:
        print(f"\n❌ Erro do Servidor: {response.status_code}")
        print("Resposta:", response.text)

except Exception as e:
    print(f"\n❌ Erro de conexão: {str(e)}")
