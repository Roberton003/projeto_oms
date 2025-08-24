import sqlite3
import json
import os

def create_db_schema_summary(db_path: str, output_path: str):
    """
    Connects to a SQLite database, extracts table names and their schemas,
    and saves this information as a JSON file.
    """
    schema_summary = {}
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        for table_name_tuple in tables:
            table_name = table_name_tuple[0]
            schema_summary[table_name] = []

            # Get schema for each table
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            for col in columns:
                schema_summary[table_name].append({
                    "cid": col[0],
                    "name": col[1],
                    "type": col[2],
                    "notnull": bool(col[3]),
                    "dflt_value": col[4],
                    "pk": bool(col[5])
                })
        
        # Ensure the output directory exists
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(schema_summary, f, indent=4, ensure_ascii=False)
        
        print(f"Schema summary saved to {output_path}")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    db_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "database", "who_gho.db")
    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "database", "db_schema_summary.json")
    
    # Check if the database file exists
    if not os.path.exists(db_file):
        print(f"Erro: O arquivo do banco de dados não foi encontrado em '{db_file}'.")
        print("Por favor, certifique-se de que o banco de dados foi criado e populado.")
        print("Você pode criá-lo executando 'python scripts/create_database.py' e 'python scripts/populate_database.py'.")
    else:
        create_db_schema_summary(db_file, output_file)
