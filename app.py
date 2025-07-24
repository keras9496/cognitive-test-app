from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import random
import os
import json
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# --- 초기 설정 ---
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret_key_for_local_testing')

# --- 데이터베이스 설정 ---
basedir = os.path.abspath(os.path.dirname(__file__))
if not os.path.exists(os.path.join(basedir, 'instance')):
    os.makedirs(os.path.join(basedir, 'instance'))

database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or \
    'sqlite:///' + os.path.join(basedir, 'instance', 'cognitive_tests.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --- 데이터베이스 모델 정의 ---

# 1. 시각 순서 기억 검사 결과 모델 (nickname 제거)
class Result(db.Model):
    __tablename__ = 'sequence_memory_results'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    test_date = db.Column(db.String(20), nullable=False)
    test_name = db.Column(db.String(80), nullable=False, server_default='시각 순서 기억 검사')
    level = db.Column(db.Integer, nullable=False) # 레벨을 숫자로 저장
    correct = db.Column(db.Integer, nullable=False)
    wrong = db.Column(db.Integer, nullable=False)
    avg_similarity = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<Result {self.name} - {self.test_name} - Level {self.level}>'

# 2. 도형 패턴 인지 테스트 결과 모델 (nickname 제거)
class PatternResult(db.Model):
    __tablename__ = 'pattern_recognition_results'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    test_date = db.Column(db.String(20), nullable=False)
    level = db.Column(db.Integer, nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total_problems = db.Column(db.Integer, nullable=False)
    times_json = db.Column(db.String, nullable=False)

    def __repr__(self):
        return f'<PatternResult {self.name} - Level {self.level}>'


# --- 상수 정의 ---
CANVAS_WIDTH = 500
CANVAS_HEIGHT = 500
BOX_SIZE = 50

# --- 핵심 로직 함수들 ---

def create_sequence_problem(level, is_practice=False):
    """지정된 레벨 또는 연습에 맞는 문제를 생성합니다."""
    if is_practice:
        level_info = {'name': 'Practice', 'box_count': 3, 'flash_count': 2}
    else:
        # 레벨에 따라 박스 수와 깜빡임 수를 동적으로 계산
        level_info = {
            'name': f'Level {level}',
            'box_count': level + 4, # 레벨 1일 때 5개
            'flash_count': level + 2  # 레벨 1일 때 3개
        }

    box_count = level_info['box_count']
    flash_count = level_info['flash_count']
    boxes = []
    max_x = CANVAS_WIDTH - BOX_SIZE
    max_y = CANVAS_HEIGHT - BOX_SIZE
    while len(boxes) < box_count:
        x1 = random.randint(0, max_x)
        y1 = random.randint(0, max_y)
        x2, y2 = x1 + BOX_SIZE, y1 + BOX_SIZE
        is_overlapping = False
        for existing_box in boxes:
            if not (x2 < existing_box['x1'] or x1 > existing_box['x2'] or y2 < existing_box['y1'] or y1 > existing_box['y2']):
                is_overlapping = True
                break
        if not is_overlapping:
            boxes.append({'id': len(boxes), 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2})
    flash_sequence = random.sample(range(box_count), flash_count)
    return {
        "level_name": level_info['name'],
        "level": level if not is_practice else 0,
        "flash_count": flash_count,
        "boxes": boxes,
        "flash_sequence": flash_sequence
    }

def save_sequence_results_to_db():
    """세션에 저장된 점수를 데이터베이스에 저장합니다."""
    try:
        if 'name' not in session or 'level_results' not in session:
            print("세션에 사용자 정보 또는 결과 정보가 없어 DB에 저장하지 않습니다.")
            return False

        name = session.get('name')
        age = session.get('age')
        gender = session.get('gender')
        test_date = session.get('test_date')

        db.create_all()

        for level, data in session.get('level_results', {}).items():
            if not data.get('similarities'):
                continue

            avg_sim = sum(data['similarities']) / len(data['similarities'])

            result_entry = Result(
                name=name,
                age=age,
                gender=gender,
                test_date=test_date,
                level=level,
                correct=data['correct'],
                wrong=data['wrong'],
                avg_similarity=round(avg_sim, 4)
            )
            db.session.add(result_entry)

        db.session.commit()
        print(f"{name}님의 시각 순서 기억 검사 결과가 DB에 저장되었습니다.")
        return True

    except Exception as e:
        print(f"DB 저장 중 오류 발생: {str(e)}")
        db.session.rollback()
        return False

# --- 라우트(URL 경로) 정의 ---

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start-test", methods=['POST'])
def start_test():
    """사용자 정보를 받아 세션을 초기화하고 연습 페이지로 이동시킵니다."""
    try:
        session.clear()
        # nickname 제거
        session['name'] = request.form.get('name', '').strip()
        session['age'] = int(request.form.get('age', 0))
        session['gender'] = request.form.get('gender', '').strip()
        session['test_date'] = request.form.get('test_date', '').strip()

        if not all([session['name'], session['age'], session['gender'], session['test_date']]):
            return redirect(url_for('index'))

        # 새로운 레벨 시스템을 위한 세션 초기화
        session['current_level'] = 1
        session['chances_left'] = 2 # 각 레벨당 기회 (2번 = 처음 시도 + 재시도)
        session['level_results'] = {} # 레벨별 결과 저장
        session['sequence_test_completed'] = False

        session.modified = True
        return redirect(url_for('practice_page'))

    except (ValueError, TypeError) as e:
        print(f"사용자 입력 처리 중 오류: {str(e)}")
        return redirect(url_for('index'))

@app.route("/practice")
def practice_page():
    if 'name' not in session:
        return redirect(url_for('index'))
    return render_template('practice.html')

@app.route("/test")
def test_page():
    if 'name' not in session:
        return redirect(url_for('index'))
    return render_template('test.html')

@app.route("/pattern-test")
def pattern_test_page():
    if 'name' not in session:
        return redirect(url_for('index'))
    return render_template('pattern_test.html')

# --- API 엔드포인트 ---

@app.route('/api/get-practice-problem')
def get_practice_problem():
    """연습 문제 정보를 JSON으로 제공합니다."""
    try:
        if 'name' not in session:
            return jsonify({"error": "Session not started"}), 403

        problem = create_sequence_problem(0, is_practice=True)
        session['practice_problem'] = problem
        session.modified = True
        return jsonify(problem)

    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/submit-practice-answer', methods=['POST'])
def submit_practice_answer():
    """연습 답안을 받아 정답 여부를 반환합니다."""
    try:
        data = request.get_json()
        user_answer = data.get('answer')
        correct_answer = session.get('practice_problem', {}).get('flash_sequence')

        if user_answer == correct_answer:
            return jsonify({"status": "correct", "message": "정답입니다! 잠시 후 본 테스트를 시작합니다."})
        else:
            return jsonify({"status": "incorrect", "message": "틀렸습니다. 다시 시도해보세요."})

    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500


@app.route('/api/get-problem')
def get_problem():
    """(첫 번째 테스트) 현재 레벨에 맞는 문제 정보를 JSON으로 제공합니다."""
    try:
        if 'name' not in session:
            return jsonify({"error": "Session not started."}), 403
        
        # 테스트가 종료되었는지 확인
        if session.get('sequence_test_completed'):
            save_success = save_sequence_results_to_db()
            if save_success:
                session.pop('level_results', None)
                session.modified = True
                return jsonify({
                    "status": "completed",
                    "message": "1차 검사가 완료되었습니다. 다음 검사를 진행합니다.",
                    "next_url": url_for('pattern_test_page')
                })
            else:
                 return jsonify({"error": "Failed to save results"}), 500

        current_level = session.get('current_level', 1)
        problem = create_sequence_problem(current_level)
        session['current_problem'] = problem
        session.modified = True

        return jsonify(problem)

    except Exception as e:
        print(f"문제 생성 중 오류: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/api/submit-answer', methods=['POST'])
def submit_answer():
    """(첫 번째 테스트) 사용자의 답안을 받아 처리하고 다음 상태를 결정합니다."""
    try:
        data = request.get_json()
        user_answer = data.get('answer')
        current_problem = session.get('current_problem')
        
        if not current_problem:
            return jsonify({"error": "No active problem"}), 400

        correct_answer = current_problem['flash_sequence']
        is_correct = (user_answer == correct_answer)
        
        level = session.get('current_level', 1)
        if level not in session.get('level_results', {}):
            session['level_results'][level] = {'correct': 0, 'wrong': 0, 'similarities': []}

        matches = sum(1 for a, b in zip(user_answer, correct_answer) if a == b)
        similarity = matches / len(correct_answer) if correct_answer else 0
        session['level_results'][level]['similarities'].append(similarity)

        if is_correct:
            # 정답일 경우: 레벨을 올리고 기회를 2번으로 초기화
            session['level_results'][level]['correct'] += 1
            session['current_level'] += 1
            session['chances_left'] = 2
            
        else:
            # 오답일 경우: 기회를 1번 줄임
            session['level_results'][level]['wrong'] += 1
            session['chances_left'] -= 1
            
            # 남은 기회가 없으면 테스트 종료 플래그 설정
            if session['chances_left'] <= 0:
                session['sequence_test_completed'] = True

        session.modified = True
        return jsonify({"status": "next_problem", "correct": is_correct})

    except Exception as e:
        print(f"답안 처리 중 오류: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/submit-pattern-result', methods=['POST'])
def submit_pattern_result():
    """(두 번째 테스트) 도형 패턴 인지 테스트 결과를 받아 DB에 저장합니다."""
    try:
        if 'name' not in session:
            return jsonify({"error": "Session not found"}), 403

        data = request.get_json()
        db.create_all()

        result_entry = PatternResult(
            name=session.get('name'),
            age=session.get('age'),
            gender=session.get('gender'),
            test_date=session.get('test_date'),
            level=int(data.get('level')),
            score=int(data.get('score')),
            total_problems=int(data.get('total_problems')),
            times_json=json.dumps(data.get('times', []))
        )
        db.session.add(result_entry)
        db.session.commit()

        print(f"{session.get('name')}님의 도형 패턴 인지 Level {data.get('level')} 결과가 DB에 저장되었습니다.")
        return jsonify({"status": "success", "message": "결과가 저장되었습니다."})

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to save pattern result"}), 500

# --- 결과 페이지 ---

@app.route("/results")
def show_results():
    """두 테스트의 모든 결과를 관리자에게 보여주는 페이지입니다."""
    try:
        password = request.args.get('pw')
        admin_pw = os.environ.get('ADMIN_PASSWORD', 'local_admin_pw')
        if password != admin_pw:
            return "Access Denied.", 403

        sequence_results = Result.query.order_by(Result.id.desc()).all()
        pattern_results_raw = PatternResult.query.order_by(PatternResult.id.desc()).all()

        pattern_results = []
        for r in pattern_results_raw:
            try:
                r.times_list = json.loads(r.times_json)
            except (json.JSONDecodeError, TypeError):
                r.times_list = []
            pattern_results.append(r)

        return render_template('results.html', sequence_results=sequence_results, pattern_results=pattern_results)

    except Exception as e:
        return "Internal Server Error", 500

# --- 애플리케이션 실행 ---
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5001)