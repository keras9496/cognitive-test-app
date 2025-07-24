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
    if not os.path.exists(ALL_RESULTS_FILE) or os.path.getsize(ALL_RESULTS_FILE) == 0:
        return []
    with open(ALL_RESULTS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_all_results(data):
    """모든 사용자 결과를 파일에 저장합니다."""
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

@app.route('/practice')
def practice():
    """연습 문제 페이지를 렌더링합니다."""
    if 'user_info' not in session:
        return redirect(url_for('index'))
    init_session(level=0)
    return redirect(url_for('intermission'))

@app.route('/test')
def test():
    """세션에 사용자 정보가 있는지 확인하고 테스트 페이지를 렌더링합니다."""
    if 'user_info' not in session:
        return redirect(url_for('index'))
    init_session(level=1)
    return redirect(url_for('intermission'))

@app.route('/intermission')
def intermission():
    """다음 문제 정보를 보여주는 안내 페이지를 렌더링합니다."""
    level = session.get('current_level', 0)
    problem = create_sequence_problem(level)
    session['current_problem'] = problem
    session.modified = True
    return render_template('intermission.html', flash_count=problem['flash_count'])

@app.route('/problem')
def problem():
    """실제 문제를 푸는 페이지를 렌더링합니다."""
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
        session['history'].append({
            "level": level, "correct": is_correct,
            "user_answer": user_answer, "correct_answer": correct_answer,
            "similarity": similarity
        })

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
    """[수정됨] 상세 기록을 볼 수 있도록 전체 history를 전달합니다."""
    password = request.args.get('pw')
    if password != ADMIN_PASSWORD:
        return "접근 권한이 없습니다.", 403
    
    all_results = load_all_results()
    
    # 이제 템플릿에서 직접 history를 순회하며 상세 정보를 표시하므로
    # 서버에서 미리 가공할 필요가 줄어듭니다.
    # ID만 추가해줍니다.
    for i, res in enumerate(all_results):
        res['id'] = i + 1

    return render_template('results.html', all_results=all_results, pattern_results=[])


@app.route('/finish')
def finish():
    """테스트 완료 페이지를 렌더링합니다."""
    return render_template('finish.html')

if __name__ == '__main__':
    app.run(debug=True)