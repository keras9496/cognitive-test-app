from flask import Flask, render_template, jsonify, request, session, redirect, url_for, send_file
import random
from datetime import datetime, timedelta
import os
import json

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.permanent_session_lifetime = timedelta(minutes=30)

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "w123456789")

# --- 데이터베이스 설정 ---
INSTANCE_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
DATABASE_FILE = os.path.join(INSTANCE_FOLDER, 'database.json')

# --- 순서 기억 검사의 최대 레벨 설정 ---
SEQUENCE_MAX_LEVEL = 12 

def load_database():
    """통합 데이터베이스 파일을 불러옵니다."""
    os.makedirs(INSTANCE_FOLDER, exist_ok=True)
    if not os.path.exists(DATABASE_FILE):
        return {"users": []}
    try:
        with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
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
        
def save_sequence_test_result(final_level):
    """순서 기억 검사 결과를 DB에 저장하는 헬퍼 함수"""
    db = load_database()
    user_info = session.get('user_info', {})
    for user in db['users']:
        if user.get('name') == user_info.get('name') and user.get('age') == user_info.get('age'):
            user.setdefault('tests', []).append({
                "test_type": "sequence",
                "timestamp": datetime.now().isoformat(),
                "final_level": final_level,
                "history": session.get('history', [])
            })
            break
    save_database(db)

def init_session_for_sequence_test(level=1):
    """순서 기억 검사를 위한 세션을 초기화합니다."""
    user_info = session.get('user_info', {})
    # session.clear() # 세션 전체를 지우면 안됨 (current_test_flow 유지)
    session['current_level'] = level
    session['chances_left'] = 2
    session['history'] = []
    session.permanent = True

def create_sequence_problem(level):
    if level == 0:
        num_boxes = 4
        sequence_length = 2
    else:
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

@app.route('/')
def index():
    session.clear()
    return render_template('index.html')

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
    
    user_entry = None
    for user in db['users']:
        if user.get('name') == user_info.get('name') and user.get('age') == user_info.get('age'):
            user_entry = user
            break

    if user_entry is None:
        user_entry = {
            "name": user_info['name'],
            "age": user_info['age'],
            "gender": user_info['gender'],
            "tests": []
        }
        db['users'].append(user_entry)
        save_database(db)
    
    # [수정] 핵심 테스트(sequence, card_matching, stroop)의 개수를 세어 다음 검사를 결정
    primary_tests = [t for t in user_entry.get('tests', []) if t.get('test_type') in ['sequence', 'card_matching', 'stroop']]
    primary_test_count = len(primary_tests)
    
    if primary_test_count % 3 == 0:
        # 순서 기억 검사 회차
        session['current_test_flow'] = 'sequence'
        return redirect(url_for('practice'))
    elif primary_test_count % 3 == 1:
        # 카드 짝 맞추기 검사 회차
        session['current_test_flow'] = 'card'
        return redirect(url_for('card_test'))
    else:
        # 스트룹 검사 회차
        session['current_test_flow'] = 'stroop'
        return redirect(url_for('stroop_test'))


@app.route('/practice')
def practice():
    if 'user_info' not in session:
        return redirect(url_for('index'))
    init_session_for_sequence_test(level=0)
    return redirect(url_for('intermission'))

@app.route('/test')
def test():
    if 'user_info' not in session:
        return redirect(url_for('index'))
    init_session_for_sequence_test(level=1)
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
    data = request.get_json()
    if not data: return jsonify({"error": "Invalid request"}), 400

    user_answer = data.get('answer')
    level = session.get('current_level', 0)
    problem = session.get('current_problem')
    
    time_taken = data.get('time_taken', None)

    if not problem: return jsonify({"error": "No problem in session"}), 400

    correct_answer = problem['flash_sequence']
    is_correct = (user_answer == correct_answer)

    if level > 0:
        session.setdefault('history', []).append({
            "level": level, 
            "correct": is_correct, 
            "user_answer": user_answer, 
            "correct_answer": correct_answer,
            "time_taken": time_taken 
        })

    if level == 0:
        status = "correct_practice" if is_correct else "incorrect_practice"
        if is_correct: session['current_level'] = 1
        return jsonify({"status": status, "correct": is_correct})

    if is_correct:
        next_level = session['current_level'] + 1
        if next_level > SEQUENCE_MAX_LEVEL:
            status = "test_complete"
            save_sequence_test_result(final_level=session['current_level'])
        else:
            session['current_level'] = next_level
            session['chances_left'] = 2
            status = "next_level"
    else:
        session['chances_left'] -= 1
        if session['chances_left'] <= 0:
            status = "game_over"
            save_sequence_test_result(final_level=session['current_level'])
        else:
            status = "retry"
            
    session.modified = True
    return jsonify({"status": status, "correct": is_correct, "chances_left": session.get('chances_left')})

@app.route('/trail_making_test')
def trail_making_test():
    if 'user_info' not in session:
        return redirect(url_for('index'))
    return render_template('trail_making_test.html')

@app.route('/save_trail_making_results', methods=['POST'])
def save_trail_making_results():
    if 'user_info' not in session:
        return jsonify({"success": False, "error": "User session not found"}), 401
    
    result_data = request.get_json()
    if not result_data:
        return jsonify({"success": False, "error": "No result data provided"}), 400

    db = load_database()
    user_info = session.get('user_info')
    user_found = False
    for user in db['users']:
        if user.get('name') == user_info.get('name') and user.get('age') == user_info.get('age'):
            user.setdefault('tests', []).append({
                "test_type": "trail_making",
                "timestamp": datetime.now().isoformat(),
                "result": result_data
            })
            user_found = True
            break
    
    if not user_found:
        return jsonify({"success": False, "error": "User not found in database"}), 404

    save_database(db)
    return jsonify({"success": True, "next_url": url_for('final_finish')})

@app.route('/card-test')
def card_test():
    if 'user_info' not in session:
        return redirect(url_for('index'))
    return render_template('card_test.html')

@app.route('/api/submit-card-result', methods=['POST'])
def submit_card_result():
    if 'user_info' not in session: return jsonify({"error": "사용자 정보가 없습니다."}), 401
    result_data = request.get_json()
    if not result_data: return jsonify({"error": "결과 데이터가 없습니다."}), 400
    db = load_database()
    user_info = session.get('user_info')
    user_found = False
    for user in db['users']:
        if user.get('name') == user_info.get('name') and user.get('age') == user_info.get('age'):
            user.setdefault('tests', []).append({
                "test_type": "card_matching",
                "timestamp": datetime.now().isoformat(),
                "result": result_data
            })
            user_found = True
            break
    if not user_found: return jsonify({"error": "데이터베이스에서 사용자를 찾을 수 없습니다."}), 404
    save_database(db)
    # [수정] 카드 테스트 후에는 스트룹 테스트로 이동
    return jsonify({"status": "success", "message": "결과가 성공적으로 저장되었습니다."})

# 스트룹 테스트 관련 라우트 추가
@app.route('/stroop-test')
def stroop_test():
    if 'user_info' not in session:
        return redirect(url_for('index'))
    return render_template('stroop_test.html')

@app.route('/api/submit-stroop-result', methods=['POST'])
def submit_stroop_result():
    if 'user_info' not in session: 
        return jsonify({"error": "사용자 정보가 없습니다."}), 401
    
    result_data = request.get_json()
    if not result_data: 
        return jsonify({"error": "결과 데이터가 없습니다."}), 400
    
    # 스트룹 테스트 결과 포맷 검증 및 처리
    processed_result = process_stroop_result(result_data)
    
    db = load_database()
    user_info = session.get('user_info')
    user_found = False
    
    for user in db['users']:
        if user.get('name') == user_info.get('name') and user.get('age') == user_info.get('age'):
            user.setdefault('tests', []).append({
                "test_type": "stroop",
                "timestamp": datetime.now().isoformat(),
                "result": processed_result
            })
            user_found = True
            break
    
    if not user_found: 
        return jsonify({"error": "데이터베이스에서 사용자를 찾을 수 없습니다."}), 404
    
    save_database(db)
    return jsonify({"status": "success", "message": "스트룹 테스트 결과가 성공적으로 저장되었습니다."})

def process_stroop_result(raw_data):
    """
    스트룹 테스트 원본 데이터를 분석하여 정리된 결과 포맷으로 변환
    
    예상 입력 포맷:
    {
        "practice_trials": [
            {"word": "빨강", "color": "blue", "user_response": true/false/null, "response_time": 1200, "correct_answer": false},
            ...
        ],
        "test_trials": [
            {"word": "파랑", "color": "red", "user_response": true/false/null, "response_time": 800, "correct_answer": false},
            ...
        ]
    }
    """
    
    # 연습 문항 분석
    practice_trials = raw_data.get('practice_trials', [])
    practice_failures = 0
    
    for trial in practice_trials:
        user_response = trial.get('user_response')
        correct_answer = trial.get('correct_answer')
        
        # 연습에서 실패한 경우 카운트 (정답과 다르게 응답한 경우)
        if user_response != correct_answer:
            practice_failures += 1
    
    # 본 검사 분석
    test_trials = raw_data.get('test_trials', [])
    total_trials = len(test_trials)
    
    if total_trials > 0:
        # 평균 응답 시간 계산
        total_response_time = sum(trial.get('response_time', 0) for trial in test_trials)
        avg_response_time = total_response_time / total_trials
        
        # 오답율 계산
        incorrect_responses = 0
        no_response_errors = 0  # 정답인데 미입력
        false_positive_errors = 0  # 오답인데 입력
        
        for trial in test_trials:
            user_response = trial.get('user_response')
            correct_answer = trial.get('correct_answer')
            
            if user_response != correct_answer:
                incorrect_responses += 1
                
                # 세부 오답 유형 분류
                if correct_answer and (user_response is False or user_response is None):
                    no_response_errors += 1  # 정답인데 미입력
                elif not correct_answer and user_response:
                    false_positive_errors += 1  # 오답인데 입력
        
        error_rate = (incorrect_responses / total_trials) * 100
        no_response_error_rate = (no_response_errors / total_trials) * 100
        false_positive_error_rate = (false_positive_errors / total_trials) * 100
    else:
        avg_response_time = 0
        error_rate = 0
        no_response_error_rate = 0
        false_positive_error_rate = 0
        incorrect_responses = 0
        no_response_errors = 0
        false_positive_errors = 0
    
    # 정리된 결과 포맷
    processed_result = {
        "summary": {
            "practice_failures": practice_failures,
            "total_practice_trials": len(practice_trials),
            "total_test_trials": total_trials,
            "avg_response_time_ms": round(avg_response_time, 2),
            "overall_error_rate_percent": round(error_rate, 2),
            "no_response_error_rate_percent": round(no_response_error_rate, 2),
            "false_positive_error_rate_percent": round(false_positive_error_rate, 2),
            "total_incorrect": incorrect_responses,
            "no_response_errors": no_response_errors,
            "false_positive_errors": false_positive_errors
        },
        "detailed_data": {
            "practice_trials": practice_trials,
            "test_trials": test_trials
        },
        "raw_data": raw_data  # 원본 데이터도 보존
    }
    
    return processed_result

@app.route('/finish')
def finish():
    # [수정] 어떤 테스트를 했는지에 따라 분기
    if session.get('current_test_flow') == 'sequence':
        # 순서 기억 검사 후에는 트레일 메이킹으로
        return redirect(url_for('trail_making_test'))
    elif session.get('current_test_flow') == 'card':
        # 카드 짝 맞추기 후에는 스트룹 테스트로
        return redirect(url_for('stroop_test'))
    else:
        # 스트룹 테스트 후에는 최종 종료
        return redirect(url_for('final_finish'))

@app.route('/finish')
def finish():
    # 현재 테스트 흐름을 세션에서 가져옵니다.
    current_flow = session.get('current_test_flow')
    print(f"finish 엔드포인트 접근 - 현재 플로우: {current_flow}")

    if current_flow == 'sequence':
        # 다음 테스트인 'card'로 상태를 변경합니다.
        session['current_test_flow'] = 'card'
        # 이 프로젝트의 실제 흐름에서는 이 분기가 바로 사용되지는 않지만,
        # start_test의 로직에 따라 다음 테스트가 card가 맞습니다.
        return redirect(url_for('card_test'))

    elif current_flow == 'card':
        # 카드 테스트가 끝났으므로, 다음 테스트인 'stroop'으로 상태를 변경합니다.
        session['current_test_flow'] = 'stroop'
        return redirect(url_for('stroop_test'))

    elif current_flow == 'stroop':
        # 스트룹 테스트가 끝났으므로, 모든 과정이 완료된 페이지로 이동합니다.
        return redirect(url_for('final_finish'))
        
    else:
        # 만약 세션에 유효한 테스트 흐름 정보가 없다면, 안전하게 첫 페이지로 보냅니다.
        return redirect(url_for('index'))

@app.route('/results')
def results():
    password = request.args.get('pw')
    if password != ADMIN_PASSWORD:
        return "접근 권한이 없습니다.", 403
    db = load_database()
    return render_template('results.html', data=db)

@app.route('/download-results')
def download_results():
    password = request.args.get('pw')
    if password != ADMIN_PASSWORD:
        return "결과 파일이 아직 생성되지 않았습니다.", 403
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