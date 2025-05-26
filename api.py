from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error
import os
import logging
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    handlers=[logging.FileHandler("slagboom.log")]
)
logger = logging.getLogger()

for lib in ["azure", "urllib3", "azure.identity", "azure.core", "flask", "werkzeug"]:
    logging.getLogger(lib).setLevel(logging.WARNING)

load_dotenv()

KEYVAULT_NAME = os.getenv("KEYVAULT_NAME")
if not KEYVAULT_NAME:
    raise EnvironmentError("KEYVAULT_NAME is niet ingesteld als omgevingsvariabele.")

KV_URI = f"https://{KEYVAULT_NAME}.vault.azure.net"
credential = DefaultAzureCredential()
secret_client = SecretClient(vault_url=KV_URI, credential=credential)

def get_secret(name):
    try:
        value = secret_client.get_secret(name).value
        logger.info(f"✅ Secret '{name}' succesvol opgehaald.")
        return value
    except Exception as e:
        logger.error(f"❌ Fout bij ophalen secret '{name}': {e}")
        raise RuntimeError(f"Secret '{name}' kon niet worden opgehaald.")

DB_CONFIG = {
    'host': get_secret("DBHOST"),
    'user': get_secret("DBUSER"),
    'password': get_secret("DBPW"),
    'database': get_secret("DBNAME"),
    'ssl_ca': get_secret("DBSSLPATH")
}

app = Flask(__name__)
CORS(app, origins="*", methods=["GET", "POST", "OPTIONS"], allow_headers="*")

def voeg_toe_aan_logboek(kenteken):
    try:
        tijdstip = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = mysql.connector.connect(**DB_CONFIG)
        logger.info("✅ Verbinding met database succesvol.")
        cursor = conn.cursor()

        cursor.execute("SELECT naam FROM gasten WHERE kenteken = %s", (kenteken,))
        result = cursor.fetchone()
        if not result:
            logger.info(f"❌ Ongeautoriseerde poging: kenteken '{kenteken}' is niet geregistreerd.")
            conn.close()
            raise PermissionError(f"{kenteken} is geen geregistreerde gast.")
        eigenaar_naam = result[0]

        cursor.execute("""
            SELECT actie FROM logboek
            WHERE kenteken = %s
            ORDER BY tijdstip DESC
            LIMIT 1
        """, (kenteken,))
        laatste = cursor.fetchone()
        actie = "Uitgang" if laatste and laatste[0] == "Binnenkomst" else "Binnenkomst"

        cursor.execute("""
            INSERT INTO logboek (kenteken, eigenaar_naam, actie, tijdstip)
            VALUES (%s, %s, %s, %s)
        """, (kenteken, eigenaar_naam, actie, tijdstip))
        conn.commit()
        conn.close()

        logger.info(f"✅ {actie} geregistreerd voor kenteken '{kenteken}' ({eigenaar_naam}) om {tijdstip}")
        return actie

    except PermissionError as pe:
        raise pe
    except Error as db_err:
        logger.error(f"❌ Databasefout: {db_err}")
        raise ConnectionError("Databaseverbinding mislukt")
    except Exception as e:
        logger.error(f"❌ Onbekende fout in logboekregistratie: {e}")
        raise e

def haal_logboek_op():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM logboek ORDER BY tijdstip DESC')
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Error as db_err:
        logger.error(f"❌ Databasefout bij ophalen logboek: {db_err}")
        raise ConnectionError("Databaseverbinding mislukt")
    except Exception as e:
        logger.error(f"❌ Onbekende fout bij ophalen logboek: {e}")
        raise e

@app.route('/api/slagboom', methods=['POST', 'OPTIONS'])
def slagboom():
    if request.method == 'OPTIONS':
        return '', 200
    data = request.get_json()
    kenteken = data.get('kenteken', '').strip().upper()
    if not kenteken:
        return jsonify({"message": "Kenteken is verplicht"}), 400
    try:
        actie = voeg_toe_aan_logboek(kenteken)
        return jsonify({"message": f"{actie} geregistreerd voor {kenteken}"}), 200
    except PermissionError as pe:
        return jsonify({"message": str(pe)}), 403
    except (ConnectionError, RuntimeError) as ce:
        return jsonify({"message": str(ce)}), 500
    except Exception as e:
        logger.error(f"❌ Onbekende fout in endpoint /slagboom: {e}")
        return jsonify({"message": "Er is een fout opgetreden bij toegang"}), 500

@app.route('/api/logboek', methods=['GET', 'OPTIONS'])
def logboek():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = haal_logboek_op()
        return jsonify(data), 200
    except ConnectionError as ce:
        logger.error(f"❌ Connectiefout logboek: {ce}")
        return jsonify({"message": str(ce)}), 500
    except Exception as e:
        logger.error(f"❌ Onbekende fout logboek: {e}")
        return jsonify({"message": "Er is een fout opgetreden bij het ophalen van het logboek"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='127.0.0.1')
