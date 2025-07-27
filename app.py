from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import uuid
import os
import random

app = Flask(__name__)

# --- 설정 ---
# 데이터베이스 설정
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://user:password@localhost/cognitive_test_db').replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_very_secret_key_that_should_be_changed')

# 순서 기억 검사의 최대 레벨 설정
SEQUENCE_MAX_LEVEL = 12

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --- 데이터베이스 모델 ---
class TestResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(80), nullable=False)
    level = db.Column(db.Integer, nullable=False)
    score = db.Column(db.Integer, nullable=False)
    reaction_times = db.Column(db.JSON, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class CardTestResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(80), nullable=False)
    correct_count = db.Column(db.Integer, nullable=False)
    total_time = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class PatternTestResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(80), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class TrailMakingResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(80), nullable=False)
    test_a_time = db.Column(db.Float, nullable=False)
    test_a_errors = db.Column(db.Integer, nullable=False)
    consonant_check_failures = db.Column(db.Integer, nullable=False)
    test_b_time = db.Column(db.Float, nullable=False)
    test_b_errors = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# --- 헬퍼 함수 (순서 기억 테스트용) ---
def create_sequence_problem(level):
    """레벨에 맞는 순서 기억 문제를 생성합니다."""
    if level == 0:  # 연습 문제
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
    """겹치지 않는 박스 위치를 생성합니다."""
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

# --- 라우트 (Routes) ---
@app.before_request
def make_session_permanent():
    session.permanent = True

@app.route('/')
def index():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    # 기존 테스트 세션 정보 초기화
    session.pop('current_level', None)
    session.pop('chances_left', None)
    session.pop('current_problem', None)
    session.pop('user_info', None)
    return render_template('index.html')

@app.route('/start-test', methods=['POST'])
def start_test():
    """사용자 정보 입력을 처리하고 첫 테스트를 시작합니다."""
    # 사용자 정보를 세션에 저장합니다.
    session['user_info'] = {
        'name': request.form.get('name'),
        'age': request.form.get('age'),
        'gender': request.form.get('gender'),
        'test_date': request.form.get('test_date')
    }
    # 첫 번째 테스트인 연습 페이지로 리디렉션합니다.
    return redirect(url_for('practice'))

# --- 순서 기억 테스트 (기존 기능 복원) ---
@app.route('/practice')
def practice():
    session['current_level'] = 0  # 연습 레벨
    session['chances_left'] = 1
    session['current_problem'] = create_sequence_problem(0)
    return render_template('practice.html')

@app.route('/test')
def test():
    session['current_level'] = 1 # 본 테스트 레벨
    session['chances_left'] = 2
    session['current_problem'] = create_sequence_problem(1)
    return render_template('test.html')

@app.route('/intermission')
def intermission():
    level = session.get('current_level', 1)
    session['current_problem'] = create_sequence_problem(level)
    return render_template('intermission.html', flash_count=session['current_problem']['flash_count'])

@app.route('/api/get-current-problem', methods=['GET'])
def get_current_problem():
    """JS에서 현재 문제 데이터를 요청할 때 호출됩니다."""
    problem = session.get('current_problem')
    if not problem:
        # 세션에 문제가 없으면 새로 생성 (예: 페이지 새로고침 시)
        level = session.get('current_level', 1)
        problem = create_sequence_problem(level)
        session['current_problem'] = problem
    return jsonify(problem)

@app.route('/api/submit-answer', methods=['POST'])
def submit_answer():
    """JS에서 사용자의 답안을 제출할 때 호출됩니다."""
    data = request.get_json()
    user_answer = data.get('answer')
    level = session.get('current_level', 0)
    problem = session.get('current_problem')
    
    if not problem:
        return jsonify({"error": "No problem in session"}), 400

    is_correct = (user_answer == problem['flash_sequence'])

    if level == 0: # 연습 문제 처리
        if is_correct:
            return jsonify({"status": "correct_practice", "next_url": url_for('test')})
        else:
            return jsonify({"status": "incorrect_practice", "next_url": url_for('practice')})

    # 본 테스트 결과 기록
    new_result = TestResult(
        user_id=session['user_id'],
        level=level,
        score=1 if is_correct else 0,
        reaction_times={'user_answer': user_answer, 'correct_answer': problem['flash_sequence']}
    )
    db.session.add(new_result)
    
    if is_correct:
        next_level = level + 1
        if next_level > SEQUENCE_MAX_LEVEL:
            db.session.commit()
            return jsonify({"status": "test_complete", "next_url": url_for('trail_making_test')})
        else:
            session['current_level'] = next_level
            session['chances_left'] = 2
            db.session.commit()
            return jsonify({"status": "next_level", "next_url": url_for('intermission')})
    else: # 오답 처리
        session['chances_left'] -= 1
        if session['chances_left'] <= 0:
            db.session.commit()
            return jsonify({"status": "game_over", "next_url": url_for('trail_making_test')})
        else:
            db.session.commit()
            return jsonify({"status": "retry", "chances_left": session.get('chances_left'), "next_url": url_for('intermission')})

# --- 트레일 메이킹 테스트 (신규 추가) ---
@app.route('/trail_making_test')
def trail_making_test():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('trail_making_test.html')

@app.route('/save_trail_making_results', methods=['POST'])
def save_trail_making_results():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 403
    
    data = request.get_json()
    new_result = TrailMakingResult(
        user_id=session['user_id'],
        test_a_time=data.get('testA_time'),
        test_a_errors=data.get('testA_errors'),
        consonant_check_failures=data.get('consonant_check_failures'),
        test_b_time=data.get('testB_time'),
        test_b_errors=data.get('testB_errors')
    )
    db.session.add(new_result)
    db.session.commit()
    return jsonify({'success': True, 'next_url': url_for('card_test')})

# --- 카드/패턴 테스트 및 종료 ---
@app.route('/card_test')
def card_test():
    return render_template('card_test.html')

@app.route('/submit_card_test', methods=['POST'])
def submit_card_test():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 403
    data = request.get_json()
    new_result = CardTestResult(
        user_id=session['user_id'],
        correct_count=data.get('correctCount'),
        total_time=data.get('totalTime')
    )
    db.session.add(new_result)
    db.session.commit()
    return jsonify({'success': True, 'next_url': url_for('pattern_test')})

@app.route('/pattern_test')
def pattern_test():
    return render_template('pattern_test.html')

@app.route('/submit_pattern_test', methods=['POST'])
def submit_pattern_test():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 403
    data = request.get_json()
    new_result = PatternTestResult(
        user_id=session['user_id'],
        score=data.get('score')
    )
    db.session.add(new_result)
    db.session.commit()
    return jsonify({'success': True, 'next_url': url_for('finish')})

@app.route('/finish')
def finish():
    session.clear()
    return render_template('finish.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)