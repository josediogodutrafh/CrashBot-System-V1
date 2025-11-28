import psycopg2

print("\n🔄 Conectando no banco...")

try:
    conn = psycopg2.connect(
        host="dpg-d4i9h3re5dus73egah5g-a.oregon-postgres.render.com",
        port=5432,
        database="crash_db",
        user="crash_db_user",
        password="BQudpCSoH52uCJ1Nn7qDT9bHyxeUllSU"
    )
    
    print("✅ Conectado!\n")
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'licenca'
        ORDER BY ordinal_position;
    """)
    
    print("🔍 COLUNAS DA TABELA LICENCA:\n")
    print(f"{'COLUNA':<25} {'TIPO':<30} {'NULLABLE'}")
    print("-" * 65)
    
    for row in cursor.fetchall():
        print(f"{row[0]:<25} {row[1]:<30} {row[2]}")
    
    cursor.close()
    conn.close()
    
    print("\n✅ Pronto!\n")

except Exception as e:
    print(f"\n❌ Erro: {e}\n")