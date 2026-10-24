"""Chạy GUI: python main.py  ->  mở http://127.0.0.1:5000"""
from gui.server import create_app

if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=True)
