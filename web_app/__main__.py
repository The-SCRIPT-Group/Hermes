from waitress import serve

from web_app import app

if __name__ == '__main__':
    serve(app=app, host="127.0.0.1")
