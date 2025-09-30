import os
import sys
from web_app import app

def run_with_gunicorn():
    try:
        import gunicorn.app.wsgiapp as wsgi
        
        sys.argv = [
            'gunicorn',
            '--bind', '0.0.0.0:5000',
            '--workers', '4',
            '--worker-class', 'sync',
            '--timeout', '60',
            '--keep-alive', '5',
            '--max-requests', '1000',
            '--max-requests-jitter', '100',
            '--access-logfile', 'logs/access.log',
            '--error-logfile', 'logs/error.log',
            '--log-level', 'info',
            'web_app:app'
        ]
        
        os.makedirs('logs', exist_ok=True)
        
        print("🚀 Starting production server with Gunicorn...")
        print("   URL: http://0.0.0.0:5000")
        print("   Workers: 4")
        print("   Logs: logs/access.log, logs/error.log")
        
        wsgi.run()
        
    except ImportError:
        print("❌ Gunicorn not installed!")
        print("Install: pip install gunicorn")
        return False
    except Exception as e:
        print(f"❌ Gunicorn error: {e}")
        return False

def run_with_waitress():
    try:
        from waitress import serve
        
        print("🚀 Starting production server with Waitress...")
        print("   URL: http://0.0.0.0:5000")
        print("   Cross-platform compatible")
        
        serve(app, host='0.0.0.0', port=5000, threads=4)
        
    except ImportError:
        print("❌ Waitress not installed!")
        print("Install: pip install waitress")
        return False
    except Exception as e:
        print(f"❌ Waitress error: {e}")
        return False

def run_development():
    print("🔧 Starting development server...")
    print("⚠️  WARNING: Development server - not for production!")
    print("   URL: http://localhost:5000")
    
    app.run(host='0.0.0.0', port=5000, debug=False)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Bank AI Web Server')
    parser.add_argument('--server', choices=['gunicorn', 'waitress', 'dev'], 
                       default='dev', help='Server type')
    parser.add_argument('--port', type=int, default=5000, help='Port number')
    parser.add_argument('--host', default='0.0.0.0', help='Host address')
    
    args = parser.parse_args()
    
    print("🏦 Bank AI Data Analyst - Production Server")
    print("=" * 50)
    
    os.environ['FLASK_ENV'] = 'production' if args.server != 'dev' else 'development'
    
    if args.server == 'gunicorn':
        success = run_with_gunicorn()
        if not success:
            print("Falling back to Waitress...")
            run_with_waitress()
            
    elif args.server == 'waitress':
        success = run_with_waitress()
        if not success:
            print("Falling back to development server...")
            run_development()
            
    else:
        run_development()

if __name__ == "__main__":
    main()