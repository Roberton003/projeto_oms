
import sqlite3
import os

def create_database():
    """
    Creates the SQLite database and the initial tables based on the star schema.
    """
    # Define the database file path
    db_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'database')
    os.makedirs(db_folder, exist_ok=True)
    db_path = os.path.join(db_folder, 'who_gho.db')

    try:
        # Connect to the database (creates the file if it doesn't exist)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Drop tables if they exist to ensure a clean start
        cursor.execute('DROP TABLE IF EXISTS fact_observations')
        cursor.execute('DROP TABLE IF EXISTS dim_indicators')
        cursor.execute('DROP TABLE IF EXISTS dim_locations')
        cursor.execute('DROP TABLE IF EXISTS dim_periods')
        cursor.execute('DROP TABLE IF EXISTS dim_sex')

        # Create the dimension tables
        cursor.execute('''
            CREATE TABLE dim_indicators (
                indicator_id INTEGER PRIMARY KEY AUTOINCREMENT,
                indicator_code TEXT UNIQUE,
                indicator_name TEXT,
                category TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE dim_locations (
                location_id INTEGER PRIMARY KEY AUTOINCREMENT,
                country_code TEXT UNIQUE,
                country_name TEXT,
                region_code TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE dim_periods (
                period_id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER UNIQUE
            )
        ''')

        cursor.execute('''
            CREATE TABLE dim_sex (
                sex_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sex_code TEXT UNIQUE,
                sex_name TEXT
            )
        ''')

        # Create the fact table
        cursor.execute('''
            CREATE TABLE fact_observations (
                observation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                indicator_id INTEGER,
                location_id INTEGER,
                period_id INTEGER,
                sex_id INTEGER,
                value REAL,
                FOREIGN KEY (indicator_id) REFERENCES dim_indicators (indicator_id),
                FOREIGN KEY (location_id) REFERENCES dim_locations (location_id),
                FOREIGN KEY (period_id) REFERENCES dim_periods (period_id),
                FOREIGN KEY (sex_id) REFERENCES dim_sex (sex_id)
            )
        ''')

        conn.commit()
        print(f"Database created successfully at {db_path}")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    create_database()
