from flask import Flask, render_template, jsonify, request, session, redirect, url_for, send_file
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

# [수정됨] 데이터 저장 경로를 Render의 영구 디스크 경로인 instance 폴더로 변경
INSTANCE_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
ALL_RESULTS_FILE = os.path.join(INSTANCE_FOLDER, 'all_results.json')

def load_all_results():
    """모든 사용자 결과를 파일에서 불러옵니다."""
    if not os.path.exists(ALL_RESULTS_FILE) or os.path.getsize(ALL_RESULTS_FILE) == 0:
        return []
    with open(ALL_RESULTS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_all_results(data):
    """모든 사용자 결과를 파일에 저장합니다."""
    # [수정됨] 저장 전 instance 폴더가 있는지 확인하고 없으면 생성
    os.makedirs(INSTANCE_FOLDER, exist_ok=True)
    with open(ALL_RESULTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def init_session(level=1):
    """세션을 초기화합니다."""
    user_info = session.get('user_info', {})
    session.clear()
    session['user_info'] = user_info
    session['current_level'] = level
    session['chances_left'] = 2
    session['history'] = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start-test', methods=['POST'])
def start_test():
    """사용자 정보를 세션에 저장하고 연습 페이지로 리디렉션합니다."""
    session.clear()
    session['user_info'] = {
        'name': request.form.get('name', '익명'),
        'age': request.form.get('age', 'N/A'),
        'gender': request.form.get('gender', 'N/A'),
        'test_date': request.form.get('test_date', 'N/A')
    }
    return redirect(url_for('practice'))

# ... (이전과 동일한 다른 라우트들) ...
@app.route('/practice')
def practice():
    if 'user_info' not in session:
        return redirect(url_for('index'))
    init_session(level=0)
    return redirect(url_for('intermission'))

@app.route('/test')
def test():
    if 'user_info' not in session:
        return redirect(url_for('index'))
    init_session(level=1)
    return redirect(url_for('intermission'))

@app.route('/intermission')
def intermission():
    level = session.get('current_level', 0)
    problem = create_sequence_problem(level)
    session['current_problem'] = problem
    session.modified = True
    return render_template('intermission.html', flash_count=problem['flash_count'])

@app.route('/problem')
def problem():
    if 'current_problem' not in session:
        return redirect(url_for('index'))
    problem_type = 'practice' if session.get('current_level', 0) == 0 else 'test'
    if problem_type == 'practice':
        return render_template('practice.html')
    else:
        return render_template('test.html')

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

def create_sequence_problem(level):
    if level == 0:
        num_boxes = 4
        sequence_length = 2
    else:
        num_boxes = level + 4
        sequence_length = level + 1
    flash_sequence = random.sample(range(num_boxes), sequence_length)
    boxes = generate_box_positions(num_boxes, 500, 500)
    return {"boxes": boxes, "flash_sequence": flash_sequence, "flash_count": sequence_length}

@app.route('/api/get-current-problem', methods=['GET'])
def get_current_problem():
    problem = session.get('current_problem')
    if not problem:
        return jsonify({"error": "문제를 찾을 수 없습니다."}), 404
    return jsonify(problem)

@app.route('/api/submit-answer', methods=['POST'])
def submit_answer():
    user_answer = request.json.get('answer')
    level = session.get('current_level', 0)
    problem = session.get('current_problem')
    if not problem:
        return jsonify({"error": "No problem in session"}), 400
    correct_answer = problem['flash_sequence']
    is_correct = (user_answer == correct_answer)
    similarity = 0
    if not is_correct:
        correct_items_at_position = sum(1 for i in range(len(correct_answer)) if i < len(user_answer) and user_answer[i] == correct_answer[i])
        if len(correct_answer) > 0:
            similarity = correct_items_at_position / len(correct_answer)
    if level > 0:
        session['history'].append({"level": level, "correct": is_correct, "user_answer": user_answer, "correct_answer": correct_answer, "similarity": similarity})
    if level == 0:
        if is_correct:
            session['current_level'] = 1
            return jsonify({"status": "correct_practice"})
        else:
            return jsonify({"status": "incorrect_practice"})
    if is_correct:
        session['current_level'] += 1
        session['chances_left'] = 2
        status = "next_level"
    else:
        session['chances_left'] -= 1
        if session['chances_left'] <= 0:
            status = "game_over"
            all_results = load_all_results()
            final_score = {"user_info": session.get('user_info', {}), "final_level": level, "history": session.get('history', [])}
            all_results.append(final_score)
            save_all_results(all_results)
        else:
            status = "retry"
    session.modified = True
    return jsonify({"status": status, "correct": is_correct, "chances_left": session.get('chances_left')})

@app.route('/results')
def results():
    password = request.args.get('pw')
    if password != ADMIN_PASSWORD:
        return "접근 권한이 없습니다.", 403
    all_results = load_all_results()
    for i, res in enumerate(all_results):
        res['id'] = i + 1
    return render_template('results.html', all_results=all_results, pattern_results=[])

@app.route('/finish')
def finish():
    return render_template('finish.html')

# [신규] DB 파일 다운로드 라우트
@app.route('/download-results')
def download_results():
    """관리자 암호 확인 후 all_results.json 파일을 다운로드합니다."""
    password = request.args.get('pw')
    if password != ADMIN_PASSWORD:
        return "접근 권한이 없습니다.", 403
    
    try:
        return send_file(
            ALL_RESULTS_FILE,
            as_attachment=True,
            download_name='results_backup.json' # 다운로드 시 파일 이름
        )
    except FileNotFoundError:
        return "결과 파일이 아직 생성되지 않았습니다.", 404


if __name__ == '__main__':
    app.run(debug=True)