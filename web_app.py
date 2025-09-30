from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS
import os
import sqlite3
import logging
from datetime import datetime
from bank_analyst import BankAnalystAssistant

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='.')
CORS(app)

DB_PATH = "bank_data.db"

assistant = None

def init_assistant():
    global assistant
    try:
        assistant = BankAnalystAssistant(DB_PATH)
        logger.info("✅ Assistant initialized")
        return True
    except Exception as e:
        logger.error(f"❌ Assistant error: {e}")
        return False

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/api/stats')
def get_database_stats():
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM clients")
        clients_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM accounts")
        accounts_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM transactions")
        transactions_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COALESCE(SUM(balance), 0) FROM accounts")
        total_balance = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'clients': clients_count,
            'accounts': accounts_count,
            'transactions': transactions_count,
            'total_balance': round(float(total_balance), 2)
        })
    
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({
            'clients': 0,
            'accounts': 0,
            'transactions': 0,
            'total_balance': 0,
            'error': str(e)
        }), 500

@app.route('/api/query', methods=['POST'])
def process_query():
    """Process query and return results"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        chart_type = data.get('chart_type', 'bar')
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Query kiritilmagan'
            }), 400
        
        result = assistant.process_query(query)
        
        if result['success']:
            return jsonify({
                'success': True,
                'sql_query': result['sql_query'],
                'data': result['data'][:100], 
                'row_count': result['row_count'],
                'total_rows': len(result['data'])
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'sql_query': result.get('sql_query', '')
            }), 400
    
    except Exception as e:
        logger.error(f"Query error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/generate_report', methods=['POST'])
def generate_report():
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        chart_type = data.get('chart_type', 'bar')
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Query kiritilmagan'
            }), 400
        
        filepath = assistant.generate_report(query, chart_type)
        
        if filepath and os.path.exists(filepath):
            filename = os.path.basename(filepath)
            return jsonify({
                'success': True,
                'filename': filename,
                'filepath': filepath,
                'download_url': f'/download/{filename}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Hisobot yaratishda xato'
            }), 500
    
    except Exception as e:
        logger.error(f"Report error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        filepath = os.path.join('reports', filename)
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
        else:
            return jsonify({'error': 'Fayl topilmadi'}), 404
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/examples')
def get_examples():
    examples = [
        {
            'title': 'Viloyatlar bo\'yicha',
            'query': 'Har bir viloyatdagi mijozlar sonini ko\'rsat',
            'chart': 'pie'
        },
        {
            'title': 'Eng katta balanslar',
            'query': 'Eng ko\'p balansga ega 10 ta hisobni ko\'rsat',
            'chart': 'bar'
        },
        {
            'title': 'Toshkent mijozlari',
            'query': 'Toshkent viloyatidagi mijozlar sonini ko\'rsat',
            'chart': 'bar'
        },
        {
            'title': 'Hisob turlari',
            'query': 'Har bir hisob turida qancha hisob borligini ko\'rsat',
            'chart': 'pie'
        },
        {
            'title': 'Tranzaksiyalar',
            'query': '2024 yildagi jami tranzaksiyalar sonini ko\'rsat',
            'chart': 'bar'
        }
    ]
    
    return jsonify({'examples': examples})

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'database': os.path.exists(DB_PATH),
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("🏦 Bank AI Data Analyst - Backend API")
    print("=" * 50)
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database topilmadi: {DB_PATH}")
        print("⚠️  Avval database yarating: python bank_analyst.py --setup")
    else:
        print(f"✅ Database mavjud: {DB_PATH}")
    
    if init_assistant():
        print("✅ Assistant tayyor")
    else:
        print("⚠️  Assistant xatosi, lekin server ishga tushadi")
    
    os.makedirs('reports', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    print("\n🚀 Server ishga tushmoqda...")
    print("📍 URL: http://localhost:5000")
    print("📍 API: http://localhost:5000/api/stats")
    print("📍 Health: http://localhost:5000/health")
    print("\n⚠️  Development server - production uchun emas!")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=False)