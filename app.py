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
    # user_info를 제외한 게임 관련 정보만 초기화하도록 수정
    user_info = session.get('user_info', {})
    session.clear()
    session['user_info'] = user_info # 사용자 정보는 유지
    session['current_level'] = 1
    session['chances_left'] = 2
    session['history'] = []

@app.route('/')
def index():
    return render_template('index.html')

# [수정됨] 사용자 정보 입력 폼을 처리하는 라우트 추가
@app.route('/start-test', methods=['POST'])
def start_test():
    """사용자 정보를 받아 세션에 저장하고 테스트 페이지로 리디렉션합니다."""
    session.clear() # 새 사용자를 위해 세션 완전 초기화
    session['user_info'] = {
        'name': request.form.get('name', '익명'),
        'age': request.form.get('age', 'N/A'),
        'gender': request.form.get('gender', 'N/A'),
        'test_date': request.form.get('test_date', 'N/A')
    }
    return redirect(url_for('test'))

# [수정됨] 테스트 페이지 라우트 로직 변경
@app.route('/test')
def test():
    """세션에 사용자 정보가 있는지 확인하고 테스트 페이지를 렌더링합니다."""
    # 만약 사용자가 정보 입력 없이 /test로 직접 접근하면 시작 페이지로 보냅니다.
    if 'user_info' not in session:
        return redirect(url_for('index'))
    
    # 테스트 시작을 위해 게임 관련 세션만 초기화
    init_session()
    return render_template('test.html')

def create_sequence_problem(level):
    """지정된 레벨에 맞는 순서 기억력 문제를 생성합니다."""
    num_boxes = level + 2
    sequence_length = level + 1
    
    sequence = random.sample(range(num_boxes), sequence_length)
    
    return {
        "num_boxes": num_boxes,
        "sequence": sequence,
        "sequence_length": sequence_length
    }

@app.route('/api/get-problem', methods=['GET'])
def get_problem():
    """현재 레벨에 맞는 새로운 문제를 생성하여 반환합니다."""
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
    """사용자가 제출한 답을 확인하고 결과를 반환합니다."""
    data = request.json
    user_answer = data.get('answer')
    
    problem = session.get('current_problem')
    if not problem:
        return jsonify({"error": "No problem found in session"}), 400

    correct_answer = problem['sequence']
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
    """관리자가 모든 테스트 결과를 볼 수 있는 페이지입니다."""
    password = request.args.get('pw')
    if password != ADMIN_PASSWORD:
        return "접근 권한이 없습니다.", 403
    
    all_results = load_all_results()
    # results.html 템플릿에 맞게 데이터 구조 변경
    return render_template('results.html', sequence_results=all_results, pattern_results=[])


if __name__ == '__main__':
    app.run(debug=True)