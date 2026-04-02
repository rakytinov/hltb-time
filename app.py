from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import re

app = Flask(__name__)
CORS(app)

cache = {}

@app.route('/')
def home():
    return jsonify({
        'service': 'Game Time API',
        'status': 'running',
        'endpoints': {
            '/time?game=НАЗВАНИЕ': 'GET - время прохождения игры',
        },
        'example': '/time?game=The Witcher 3'
    })

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

@app.route('/time', methods=['GET'])
def get_game_time():
    game_name = request.args.get('game')
    
    if not game_name:
        return jsonify({'error': 'No game name provided'}), 400
    
    # Проверяем кэш
    if game_name in cache:
        return jsonify(cache[game_name])
    
    # Ищем игру через RAWG API
    result = search_rawg(game_name)
    
    if result:
        cache[game_name] = result
        return jsonify(result)
    
    return jsonify({'error': 'Game not found', 'game': game_name}), 404

def search_rawg(game_name):
    """Поиск времени прохождения через RAWG API"""
    print(f"Поиск в RAWG: {game_name}")
    
    # Очищаем название от года в скобках
    clean_name = re.sub(r'\s*\([0-9]{4}\)\s*$', '', game_name).strip()
    
    # RAWG API (не требует ключа для базовых запросов)
    url = "https://api.rawg.io/api/games"
    params = {
        'search': clean_name,
        'page_size': 5
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"RAWG статус: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('results') and len(data['results']) > 0:
                # Ищем точное совпадение
                best_match = None
                for game in data['results']:
                    game_title = game.get('name', '').lower()
                    clean_lower = clean_name.lower()
                    
                    if game_title == clean_lower:
                        best_match = game
                        break
                
                if not best_match:
                    best_match = data['results'][0]
                
                # playtime в часах
                playtime = best_match.get('playtime', 0)
                
                result = {
                    'title': best_match.get('name', clean_name),
                    'playtime': playtime,
                    'playtime_formatted': format_time(playtime)
                }
                
                print(f"Найдено: {result}")
                return result
        
        print(f"Игра не найдена: {clean_name}")
        return None
        
    except Exception as e:
        print(f"Ошибка RAWG: {e}")
        return None

def format_time(hours):
    """Форматирует часы в читаемый вид"""
    if hours <= 0:
        return "Нет данных"
    
    whole_hours = int(hours)
    minutes = int((hours - whole_hours) * 60)
    
    if whole_hours == 0:
        return f"{minutes}м"
    elif minutes == 0:
        return f"{whole_hours}ч"
    else:
        return f"{whole_hours}ч {minutes}м"

@app.route('/debug/<game_name>')
def debug(game_name):
    """Отладочный эндпоинт"""
    result = search_rawg(game_name)
    return jsonify({
        'search': game_name,
        'result': result
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
