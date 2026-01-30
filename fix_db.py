import psycopg2

# YOUR EXTERNAL DATABASE CONNECTION STRING
DATABASE_URL = "postgresql://inventory_db_dr3s_user:BSFC367sQqHyII0jAGBg7mxCK2cBPv8G@dpg-d5t23b4oud1c73alfl2g-a.frankfurt-postgres.render.com/inventory_db_dr3s"

def add_barcode_column():
    print("🔌 Connecting to database...")
    try:
        # Connect using the external URL
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Run the SQL command to add the column
        print("🛠️  Adding 'barcode' column...")
        cursor.execute("ALTER TABLE chemicals ADD COLUMN IF NOT EXISTS barcode VARCHAR;")
        
        print("✅ Success! The 'barcode' column has been added.")
        conn.close()

    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    add_barcode_column()