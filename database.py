import mysql.connector
from datetime import datetime

DB_CONFIG = {
    'host': 'fonteynslagboom.mysql.database.azure.com',
    'user': 'admin10',
    'password': 'Fonteyn10',
    'database': 'slagboomdb'  
}

def init_db():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logboek (
            logboek_id INT AUTO_INCREMENT PRIMARY KEY,
            kenteken VARCHAR(20) NOT NULL,
            eigenaar_naam VARCHAR(100),
            actie VARCHAR(50),
            tijdstip DATETIME
        )
    ''')
    conn.commit()
    conn.close()

def voeg_toe_aan_logboek(kenteken, actie="Binnenkomst", eigenaar_naam="Onbekend"):
    tijdstip = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO logboek (kenteken, eigenaar_naam, actie, tijdstip)
        VALUES (%s, %s, %s, %s)
    ''', (kenteken, eigenaar_naam, actie, tijdstip))
    conn.commit()
    conn.close()

def haal_logboek_op():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM logboek ORDER BY tijdstip DESC')
    results = cursor.fetchall()
    conn.close()
    return results
