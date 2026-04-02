from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import re
import os
import time

app = Flask(__name__)
CORS(app)

cache = {}

def search_hltb(game_name):
    """Поиск игры на HowLongToBeat через их API"""
    print(f"Поиск игры: {game_name}")
    
    # Очищаем название
    clean_name = re.sub(r'\s*\([0-9]{4}\)\s*$', '', game_name).strip()
    
    # API эндпоинт HLTB
    url = "https://howlongtobeat.com/api/search"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Origin': 'https://howlongtobeat.com',
        'Referer': 'https://howlongtobeat.com/',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'no-cache'
    }
    
    payload = {
        "searchType": "games",
        "searchTerms": [clean_name],
        "searchPage": 1,
        "size": 10,
        "style": "complete"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        print(f"Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('data') and len(data['data']) > 0:
                # Ищем точное совпадение
                best_match = None
                best_score = 0
                
                for game in data['data']:
                    game_title = game.get('game_name', '').lower()
                    clean_lower = clean_name.lower()
                    
                    # Проверяем точное совпадение
                    if game_title == clean_lower:
                        best_match = game
                        break
                    
                    # Или частичное совпадение
                    if clean_lower in game_title or game_title in clean_lower:
                        score = len(game_title)
                        if score > best_score:
                            best_score = score
                            best_match = game
                
                if not best_match:
                    best_match = data['data'][0]
                
                # Получаем время (в секундах)
                comp_main = best_match.get('comp_main', 0)
                comp_plus = best_match.get('comp_plus', 0)
                comp_100 = best_match.get('comp_100', 0)
                
                # Если значение очень маленькое (меньше 100), вероятно это уже часы
                # HLTB хранит время в секундах, но иногда возвращает часы
                if comp_main < 100 and comp_main > 0:
                    # Это уже часы
                    main_hours = comp_main
                    plus_hours = comp_plus
                    comp_hours = comp_100
                else:
                    # Конвертируем секунды в часы
                    main_hours = comp_main / 3600 if comp_main > 0 else 0
                    plus_hours = comp_plus / 3600 if comp_plus > 0 else 0
                    comp_hours = comp_100 / 3600 if comp_100 > 0 else 0
                
                result = {
                    'title': best_match.get('game_name', clean_name),
                    'mainStory': round(main_hours, 1),
                    'mainStoryWithExtras': round(plus_hours, 1),
                    'completionist': round(comp_hours, 1)
                }
                
                print(f"Найдено: {result}")
                return result
            else:
                print(f"Нет данных в ответе")
        else:
            print(f"Ошибка HTTP: {response.status_code}")
            
        return None
        
    except Exception as e:
        print(f"Ошибка при поиске: {e}")
        return None

@app.route('/')
def home():
    return jsonify({
        'service': 'HLTB API Proxy',
        'status': 'running',
        'endpoints': {
            '/hltb?game=НАЗВАНИЕ': 'GET - поиск по названию игры',
            '/health': 'GET - проверка здоровья'
        },
        'example': '/hltb?game=The Witcher 3'
    })

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

@app.route('/hltb', methods=['GET'])
def get_hltb_by_name():
    game_name = request.args.get('game')
    
    if not game_name:
        return jsonify({'error': 'No game name provided'}), 400
    
    # Проверяем кэш
    if game_name in cache:
        print(f"Возвращаем из кэша: {game_name}")
        return jsonify(cache[game_name])
    
    # Ищем игру
    result = search_hltb(game_name)
    
    if result and result['mainStory'] > 0:
        cache[game_name] = result
        return jsonify(result)
    
    return jsonify({'error': 'Game not found', 'game': game_name}), 404

@app.route('/debug/<game_name>')
def debug(game_name):
    """Отладочный эндпоинт"""
    result = search_hltb(game_name)
    return jsonify({
        'search': game_name,
        'result': result
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
