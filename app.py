from flask import Flask, render_template, jsonify, request, session, redirect, url_for, send_file
import random
from datetime import datetime, timedelta
import os
import json

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.permanent_session_lifetime = timedelta(minutes=30)

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "w123456789")

# --- 새로운 데이터베이스 설정 ---
INSTANCE_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
DATABASE_FILE = os.path.join(INSTANCE_FOLDER, 'database.json')

def load_database():
    """통합 데이터베이스 파일을 불러옵니다."""
    os.makedirs(INSTANCE_FOLDER, exist_ok=True)
    if not os.path.exists(DATABASE_FILE):
        return {"users": []}
    try:
        with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
            # 파일이 비어있는 경우 json.load()가 에러를 일으키므로 확인
            content = f.read()
            if not content:
                return {"users": []}
            return json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"users": []}

def save_database(data):
    """통합 데이터베이스 파일을 저장합니다."""
    os.makedirs(INSTANCE_FOLDER, exist_ok=True)
    with open(DATABASE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 기존 세션 초기화 및 문제 생성 함수 (변경 없음) ---
def init_session_for_sequence_test(level=1):
    """순서 기억 검사를 위한 세션을 초기화합니다."""
    user_info = session.get('user_info', {})
    test_type = session.get('test_type') # test_type 유지
    
    session.clear() # 세션 초기화
    
    session['user_info'] = user_info
    session['test_type'] = test_type
    session['current_level'] = level
    session['chances_left'] = 2
    session['history'] = []
    session.permanent = True

def create_sequence_problem(level):
    if level == 0: # 연습
        num_boxes = 4
        sequence_length = 2
    else: # 본 검사
        num_boxes = level + 4
        sequence_length = level + 1
    
    all_box_ids = list(range(num_boxes))
    flash_sequence = random.sample(all_box_ids, sequence_length)
    
    boxes = generate_box_positions(num_boxes, 500, 500)
    return {"boxes": boxes, "flash_sequence": flash_sequence, "flash_count": sequence_length}

def generate_box_positions(num_boxes, canvas_width, canvas_height):
    boxes = []
    box_size = 80
    min_gap = 10
    for i in range(num_boxes):
        while True:
            x1 = random.randint(min_gap, canvas_width - box_size - min_gap)
            y1 = random.randint(min_gap, canvas_height - box_size - min_gap)
            x2 = x1 + box_size
            y2 = y1 + box_size
            is_overlapping = False
            for other_box in boxes:
                if not (x2 < other_box['x1'] - min_gap or x1 > other_box['x2'] + min_gap or y2 < other_box['y1'] - min_gap or y1 > other_box['y2'] + min_gap):
                    is_overlapping = True
                    break
            if not is_overlapping:
                boxes.append({"id": i, "x1": x1, "y1": y1, "x2": x2, "y2": y2})
                break
    return boxes

# --- 기본 페이지 라우트 ---
@app.route('/')
def index():
    return render_template('index.html')

# --- 핵심 로직: 검사 시작 및 분기 ---
@app.route('/start-test', methods=['POST'])
def start_test():
    user_info = {
        'name': request.form.get('name', '익명'),
        'age': request.form.get('age', 'N/A'),
        'gender': request.form.get('gender', 'N/A'),
        'test_date': request.form.get('test_date', datetime.now().strftime("%Y-%m-%d"))
    }
    session['user_info'] = user_info
    session.permanent = True

    db = load_database()
    
    # 사용자 찾기
    user_entry = None
    for user in db['users']:
        if user['name'] == user_info['name'] and user['age'] == user_info['age']:
            user_entry = user
            break

    if user_entry is None:
        # 새로운 사용자이면 등록
        user_entry = {
            "name": user_info['name'],
            "age": user_info['age'],
            "gender": user_info['gender'],
            "tests": []
        }
        db['users'].append(user_entry)
    
    # 이번이 몇 번째 검사인지 확인
    test_count = len(user_entry['tests'])
    
    if test_count % 2 == 0:
        # 짝수번째 검사 (0, 2, 4, ... 번째) -> 기존 순서 기억 검사
        session['test_type'] = 'sequence'
        return redirect(url_for('practice'))
    else:
        # 홀수번째 검사 (1, 3, 5, ... 번째) -> 새로운 카드 맞추기 검사
        session['test_type'] = 'card_matching'
        return redirect(url_for('card_test'))


# --- 1. 순서 기억 검사 관련 라우트 ---

@app.route('/practice')
def practice():
    if 'user_info' not in session or session.get('test_type') != 'sequence':
        return redirect(url_for('index'))
    init_session_for_sequence_test(level=0) # 연습 레벨
    return redirect(url_for('intermission'))

@app.route('/test')
def test():
    if 'user_info' not in session or session.get('test_type') != 'sequence':
        return redirect(url_for('index'))
    init_session_for_sequence_test(level=1) # 본 검사 레벨
    return redirect(url_for('intermission'))

@app.route('/intermission')
def intermission():
    if 'user_info' not in session:
        return redirect(url_for('index'))
    level = session.get('current_level', 0)
    problem = create_sequence_problem(level)
    session['current_problem'] = problem
    return render_template('intermission.html', flash_count=problem['flash_count'])

@app.route('/problem')
def problem():
    if 'current_problem' not in session:
        return redirect(url_for('index'))
    problem_type = 'practice' if session.get('current_level', 0) == 0 else 'test'
    template = 'practice.html' if problem_type == 'practice' else 'test.html'
    return render_template(template)

@app.route('/api/get-current-problem', methods=['GET'])
def get_current_problem():
    problem = session.get('current_problem')
    if not problem:
        return jsonify({"error": "문제를 찾을 수 없습니다."}), 404
    return jsonify(problem)

@app.route('/api/submit-answer', methods=['POST'])
def submit_answer():
    # ... (이하 기존 순서 기억 검사 답안 제출 로직은 변경 없음) ...
    # 정답/오답에 따라 DB 저장 로직만 마지막에 추가
    data = request.get_json()
    if not data: return jsonify({"error": "Invalid request"}), 400

    user_answer = data.get('answer')
    level = session.get('current_level', 0)
    problem = session.get('current_problem')
    if not problem: return jsonify({"error": "No problem in session"}), 400

    correct_answer = problem['flash_sequence']
    is_correct = (user_answer == correct_answer)

    if level > 0: # 본 검사 기록만 저장
        session.setdefault('history', []).append({
            "level": level, 
            "correct": is_correct, 
            "user_answer": user_answer, 
            "correct_answer": correct_answer
        })

    if level == 0: # 연습 단계
        status = "correct_practice" if is_correct else "incorrect_practice"
        if is_correct: session['current_level'] = 1
        return jsonify({"status": status, "correct": is_correct})

    # 본 검사 단계
    if is_correct:
        session['current_level'] += 1
        session['chances_left'] = 2
        status = "next_level"
    else:
        session['chances_left'] -= 1
        if session['chances_left'] <= 0:
            status = "game_over"
            # --- DB 저장 ---
            db = load_database()
            user_info = session.get('user_info', {})
            for user in db['users']:
                if user['name'] == user_info['name'] and user['age'] == user_info['age']:
                    user['tests'].append({
                        "test_type": "sequence",
                        "timestamp": datetime.now().isoformat(),
                        "final_level": level,
                        "history": session.get('history', [])
                    })
                    break
            save_database(db)
        else:
            status = "retry"
            
    session.modified = True
    return jsonify({"status": status, "correct": is_correct, "chances_left": session.get('chances_left')})

# --- 2. 카드 맞추기 검사 관련 라우트 (신규) ---

@app.route('/card-test')
def card_test():
    """카드 맞추기 게임 페이지를 렌더링합니다."""
    if 'user_info' not in session or session.get('test_type') != 'card_matching':
        return redirect(url_for('index'))
    return render_template('card_test.html')

@app.route('/api/submit-card-result', methods=['POST'])
def submit_card_result():
    """카드 맞추기 게임 결과를 받아 DB에 저장합니다."""
    if 'user_info' not in session:
        return jsonify({"error": "사용자 정보가 없습니다."}), 401

    result_data = request.get_json()
    if not result_data:
        return jsonify({"error": "결과 데이터가 없습니다."}), 400
        
    db = load_database()
    user_info = session.get('user_info')
    
    # 해당 사용자 찾아서 결과 추가
    user_found = False
    for user in db['users']:
        if user['name'] == user_info['name'] and user['age'] == user_info['age']:
            user['tests'].append({
                "test_type": "card_matching",
                "timestamp": datetime.now().isoformat(),
                "result": result_data # { level, pairs, correct, user_clicks }
            })
            user_found = True
            break
            
    if not user_found:
        return jsonify({"error": "데이터베이스에서 사용자를 찾을 수 없습니다."}), 404
        
    save_database(db)
    
    return jsonify({"status": "success", "message": "결과가 성공적으로 저장되었습니다."})


# --- 공통 라우트 ---

@app.route('/finish')
def finish():
    return render_template('finish.html')

@app.route('/results')
def results():
    """관리자 암호 확인 후 새로운 DB 구조에 맞춰 결과 표시"""
    password = request.args.get('pw')
    if password != ADMIN_PASSWORD:
        return "접근 권한이 없습니다.", 403
    
    db = load_database()
    return render_template('results.html', data=db)

@app.route('/download-results')
def download_results():
    """관리자 암호 확인 후 database.json 파일을 다운로드합니다."""
    password = request.args.get('pw')
    if password != ADMIN_PASSWORD:
        return "접근 권한이 없습니다.", 403
    
    try:
        return send_file(
            DATABASE_FILE,
            as_attachment=True,
            download_name='cognitive_tests_database.json'
        )
    except FileNotFoundError:
        return "결과 파일이 아직 생성되지 않았습니다.", 404

if __name__ == '__main__':
    app.run(debug=True, port=5001)