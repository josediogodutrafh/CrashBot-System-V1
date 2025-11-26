from app import LogBot, app


def ler_logs():
    with app.app_context():
        # Busca os últimos 10 logs
        logs = LogBot.query.order_by(LogBot.timestamp.desc()).limit(10).all()

        print(f"\n--- ÚLTIMOS REGISTROS DE TELEMETRIA ({len(logs)}) ---")

        # CORREÇÃO: Cabeçalho fixo (simples e agrada o linter)
        # "HORA" (4 letras) + 6 espaços = 10 caracteres de largura
        # "TIPO" (4 letras) + 6 espaços = 10 caracteres de largura
        print("HORA       | TIPO       | DADOS")

        print("-" * 60)

        for log in logs:
            hora = log.timestamp.strftime("%H:%M:%S")
            # Aqui mantemos a f-string pois os dados MUDAM a cada linha
            print(f"{hora:<10} | {log.tipo:<10} | {log.dados}")


if __name__ == "__main__":
    ler_logs()
