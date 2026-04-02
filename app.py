from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import json
import re
import time

app = Flask(__name__)
CORS(app)  # Разрешаем запросы из Google Sheets

# Простой кэш в памяти
cache = {}

def search_hltb(game_name):
    """Поиск игры на HowLongToBeat"""
    print(f"Поиск игры: {game_name}")
    
    # Очищаем название от года в скобках
    clean_name = re.sub(r'\s*\([0-9]{4}\)\s*$', '', game_name)
    
    # URL для поиска
    search_url = "https://howlongtobeat.com/search"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Referer': 'https://howlongtobeat.com/'
    }
    
    payload = {
        "searchType": "games",
        "searchTerms": [clean_name],
        "searchPage": 1,
        "size": 5
    }
    
    try:
        response = requests.post(search_url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('data') and len(data['data']) > 0:
                game = data['data'][0]
                
                # Извлекаем время прохождения (в часах)
                gameplay_main = game.get('comp_main', 0) / 3600  # конвертируем секунды в часы
                gameplay_main_extra = game.get('comp_plus', 0) / 3600
                gameplay_completionist = game.get('comp_100', 0) / 3600
                
                result = {
                    'title': game.get('game_name', game_name),
                    'mainStory': round(gameplay_main, 1),
                    'mainStoryWithExtras': round(gameplay_main_extra, 1),
                    'completionist': round(gameplay_completionist, 1)
                }
                
                print(f"Найдено: {result}")
                return result
        
        print(f"Игра не найдена: {game_name}")
        return None
        
    except Exception as e:
        print(f"Ошибка при поиске: {e}")
        return None

@app.route('/')
def home():
    """Главная страница с инструкцией"""
    return jsonify({
        'service': 'HLTB API Proxy',
        'status': 'running',
        'endpoints': {
            '/hltb': 'GET - поиск по названию игры',
            '/steam/<steam_id>': 'GET - поиск по Steam ID'
        },
        'example': '/hltb?game=The Witcher 3'
    })

@app.route('/hltb', methods=['GET'])
def get_hltb_by_name():
    """Поиск по названию игры"""
    game_name = request.args.get('game')
    
    if not game_name:
        return jsonify({'error': 'No game name provided'}), 400
    
    # Проверяем кэш
    if game_name in cache:
        print(f"Возвращаем из кэша: {game_name}")
        return jsonify(cache[game_name])
    
    # Ищем игру
    result = search_hltb(game_name)
    
    if result:
        # Сохраняем в кэш на 24 часа
        cache[game_name] = result
        return jsonify(result)
    
    return jsonify({'error': 'Game not found'}), 404

@app.route('/steam/<steam_id>', methods=['GET'])
def get_hltb_by_steam_id(steam_id):
    """Поиск по Steam ID (если есть соответствие)"""
    # Steam ID to HLTB mapping (можно расширять)
    # Это упрощённый вариант, в реальности нужно базу данных
    
    # Пока просто заглушка
    return jsonify({
        'steam_id': steam_id,
        'note': 'Для поиска по Steam ID нужна база соответствий',
        'try': f'/hltb?game=название_игры'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)