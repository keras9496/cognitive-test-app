from flask import Flask, render_template, jsonify, request, session, redirect, url_for
import random
from datetime import timedelta
import os
import json

app = Flask(__name__)
# 세션을 안전하게 암호화하기 위한 시크릿 키 설정
app.secret_key = os.urandom(24)
app.permanent_session_lifetime = timedelta(minutes=30)

# 관리자 암호 (실제 환경에서는 환경 변수 등을 사용하세요)
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "your_admin_password")
ALL_RESULTS_FILE = 'all_results.json'

def load_all_results():
    """모든 사용자 결과를 파일에서 불러옵니다."""
    if not os.path.exists(ALL_RESULTS_FILE):
        return []
    # 파일이 비어있는 경우 예외 처리
    if os.path.getsize(ALL_RESULTS_FILE) == 0:
        return []
    with open(ALL_RESULTS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_all_results(data):
    """모든 사용자 결과를 파일에 저장합니다."""
    with open(ALL_RESULTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def init_session():
    """세션을 초기화합니다."""
    user_info = session.get('user_info', {})
    session.clear()
    session['user_info'] = user_info
    session['current_level'] = 1
    session['chances_left'] = 2
    session['history'] = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start-test', methods=['POST'])
def start_test():
    """사용자 정보를 받아 세션에 저장하고 테스트 페이지로 리디렉션합니다."""
    session.clear()
    session['user_info'] = {
        'name': request.form.get('name', '익명'),
        'age': request.form.get('age', 'N/A'),
        'gender': request.form.get('gender', 'N/A'),
        'test_date': request.form.get('test_date', 'N/A')
    }
    return redirect(url_for('test'))

@app.route('/test')
def test():
    """세션에 사용자 정보가 있는지 확인하고 테스트 페이지를 렌더링합니다."""
    if 'user_info' not in session:
        return redirect(url_for('index'))
    
    init_session()
    return render_template('test.html')

def generate_box_positions(num_boxes, canvas_width, canvas_height):
    """캔버스 내에 박스 좌표들을 생성합니다."""
    boxes = []
    margin = 50
    box_size = 80
    gap = 20
    
    # 그리드 레이아웃 계산
    cols = 3 if num_boxes > 4 else (2 if num_boxes > 1 else 1)
    if num_boxes == 3:
        cols = 3
    elif num_boxes == 5:
        cols = 3
    elif num_boxes == 6:
        cols = 3
        
    rows = (num_boxes + cols - 1) // cols
    
    grid_width = cols * box_size + (cols - 1) * gap
    grid_height = rows * box_size + (rows - 1) * gap
    
    start_x = (canvas_width - grid_width) / 2
    start_y = (canvas_height - grid_height) / 2

    for i in range(num_boxes):
        row = i // cols
        col = i % cols
        x1 = start_x + col * (box_size + gap)
        y1 = start_y + row * (box_size + gap)
        boxes.append({
            "id": i,
            "x1": x1,
            "y1": y1,
            "x2": x1 + box_size,
            "y2": y1 + box_size,
        })
    return boxes

def create_sequence_problem(level):
    """[수정됨] 지정된 레벨에 맞는 순서 기억력 문제를 생성합니다."""
    num_boxes = level + 2
    sequence_length = level + 1
    
    flash_sequence = random.sample(range(num_boxes), sequence_length)
    boxes = generate_box_positions(num_boxes, 500, 500) # 캔버스 크기 (500, 500)
    
    return {
        "boxes": boxes,
        "flash_sequence": flash_sequence,
        "flash_count": sequence_length,
        "level_name": f"Level {level}"
    }

@app.route('/api/get-problem', methods=['GET'])
def get_problem():
    """[수정됨] 현재 레벨에 맞는 새로운 문제를 생성하여 반환합니다."""
    if 'current_level' not in session:
        init_session()

    current_level = session.get('current_level', 1)
    chances_left = session.get('chances_left', 2)
    
    problem = create_sequence_problem(current_level)
    session['current_problem'] = problem
    session.modified = True
    
    return jsonify({
        **problem,
        "current_level": current_level,
        "chances_left": chances_left
    })

@app.route('/api/submit-answer', methods=['POST'])
def submit_answer():
    data = request.json
    user_answer = data.get('answer')
    
    problem = session.get('current_problem')
    if not problem:
        return jsonify({"error": "No problem found in session"}), 400

    correct_answer = problem['flash_sequence'] # 'sequence' -> 'flash_sequence'
    is_correct = (user_answer == correct_answer)
    
    level = session.get('current_level', 1)

    session['history'].append({
        "level": level,
        "correct": is_correct,
        "user_answer": user_answer,
        "correct_answer": correct_answer
    })

    status = "next_problem"
    if is_correct:
        session['current_level'] += 1
        session['chances_left'] = 2
    else:
        session['chances_left'] -= 1
        if session['chances_left'] <= 0:
            status = "game_over"
            all_results = load_all_results()
            final_score = {
                "user_info": session.get('user_info', {}),
                "final_level": level,
                "history": session.get('history', [])
            }
            all_results.append(final_score)
            save_all_results(all_results)

    session.modified = True
    
    return jsonify({
        "status": status,
        "correct": is_correct,
        "current_level": session.get('current_level'),
        "chances_left": session.get('chances_left')
    })

@app.route('/results')
def results():
    password = request.args.get('pw')
    if password != ADMIN_PASSWORD:
        return "접근 권한이 없습니다.", 403
    
    all_results = load_all_results()
    return render_template('results.html', sequence_results=all_results, pattern_results=[])


if __name__ == '__main__':
    app.run(debug=True)