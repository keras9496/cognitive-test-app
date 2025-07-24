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
    with open(ALL_RESULTS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_all_results(data):
    """모든 사용자 결과를 파일에 저장합니다."""
    with open(ALL_RESULTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def init_session():
    """세션을 초기화합니다."""
    session.clear()
    session['current_level'] = 1
    session['chances_left'] = 2  # 각 레벨당 기회
    session['history'] = []  # (level, correct, user_answer, correct_answer)
    session['user_info'] = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test')
def test():
    init_session()
    user_name = request.args.get('name', '익명')
    user_group = request.args.get('group', '미지정')
    session['user_info'] = {'name': user_name, 'group': user_group}
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
    
    # 프론트엔드가 현재 상태를 알 수 있도록 레벨과 기회 정보를 함께 반환
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
        # 정답: 레벨업, 기회 초기화
        session['current_level'] += 1
        session['chances_left'] = 2
    else:
        # 오답: 기회 감소
        session['chances_left'] -= 1
        if session['chances_left'] <= 0:
            status = "game_over"
            # 게임 종료 시 결과 저장
            all_results = load_all_results()
            final_score = {
                "user_info": session.get('user_info', {}),
                "final_level": level,
                "history": session.get('history', [])
            }
            all_results.append(final_score)
            save_all_results(all_results)

    session.modified = True
    
    # 프론트엔드에서 다음 행동을 결정할 수 있도록 상태 정보를 포함하여 반환
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
    return render_template('results.html', results=all_results)

if __name__ == '__main__':
    app.run(debug=True)