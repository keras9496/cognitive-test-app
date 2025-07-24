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

# 1. 시각 순서 기억 검사 결과 모델
class Result(db.Model):
    __tablename__ = 'sequence_memory_results'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    test_date = db.Column(db.String(20), nullable=False)
    test_name = db.Column(db.String(80), nullable=False, server_default='시각 순서 기억 검사')
    level = db.Column(db.Integer, nullable=False)
    correct = db.Column(db.Integer, nullable=False)
    wrong = db.Column(db.Integer, nullable=False)
    avg_similarity = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<Result {self.name} - {self.test_name} - Level {self.level}>'

# 2. 도형 패턴 인지 테스트 결과 모델
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
    times_json = db.Column(db.Text, nullable=False)

    @property
    def times_list(self):
        try:
            return json.loads(self.times_json)
        except (json.JSONDecodeError, TypeError):
            return []

    def __repr__(self):
        return f'<PatternResult {self.name} - Level {self.level}>'

# --- 유틸리티 함수 등 ---
def create_sequence_problem(level, is_practice=False):
    # 예시: level에 따라 flash_sequence 길이 증가
    length = level + 3
    seq = [random.randint(1, 9) for _ in range(length)]
    return {"flash_sequence": seq}

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

        for lvl, stats in session['level_results'].items():
            avg_sim = sum(stats['similarities']) / len(stats['similarities']) if stats['similarities'] else 0
            result_entry = Result(
                name=name,
                age=age,
                gender=gender,
                test_date=test_date,
                level=lvl,
                correct=stats['correct'],
                wrong=stats['wrong'],
                avg_similarity=avg_sim
            )
            db.session.add(result_entry)
        db.session.commit()
        print(f"{name}님의 시각 순서 기억 검사 결과가 DB에 저장되었습니다.")
        return True

    except Exception as e:
        print(f"DB 저장 중 오류 발생: {str(e)}")
        db.session.rollback()
        return False

# --- 라우트 정의 ---
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start-test", methods=['POST'])
def start_test():
    data = request.get_json()
    session['name'] = data.get('name')
    session['age'] = data.get('age')
    session['gender'] = data.get('gender')
    session['test_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    session['current_level'] = 1
    session['chances_left'] = 2
    session['level_results'] = {}
    session['sequence_test_completed'] = False
    session.modified = True
    return jsonify({"status": "started"})

@app.route('/api/get-practice-problem')
def get_practice_problem():
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

        # 수정: 레벨 및 남은 기회 정보 포함
        return jsonify({**problem,
                        "current_level": current_level,
                        "chances_left": session.get("chances_left", 2)})

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
        current_level = session.get('current_level', 1)

        # 통계 업데이트
        if current_level not in session['level_results']:
            session['level_results'][current_level] = {'correct': 0, 'wrong': 0, 'similarities': []}

        # 유사도 계산
        matches = sum(1 for a, b in zip(user_answer, correct_answer) if a == b)
        similarity = matches / len(correct_answer) if correct_answer else 0
        session['level_results'][current_level]['similarities'].append(similarity)

        if is_correct:
            session['level_results'][current_level]['correct'] += 1
            session['current_level'] = current_level + 1
            session['chances_left'] = 2
            print(f"정답! 레벨 {current_level} -> {session['current_level']}로 증가")
        else:
            session['level_results'][current_level]['wrong'] += 1
            session['chances_left'] = session.get('chances_left', 2) - 1
            print(f"오답! 레벨 {current_level}, 남은 기회: {session['chances_left']}")
            if session['chances_left'] <= 0:
                session['sequence_test_completed'] = True
                print("테스트 종료")

        session.modified = True

        # 수정: 레벨 및 남은 기회 정보 포함
        return jsonify({
            "status": "next_problem",
            "correct": is_correct,
            "current_level": session.get('current_level'),
            "chances_left": session.get('chances_left')
        })

    except Exception as e:
        print(f"답안 처리 중 오류: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500

@app.route('/pattern-test')
def pattern_test_page():
    return render_template('pattern.html')

@app.route('/api/submit-pattern-result', methods=['POST'])
def submit_pattern_result():
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

@app.route("/results")
def results():
    try:
        sequence_results = Result.query.all()
        pattern_results = PatternResult.query.all()
        return render_template('results.html',
                               sequence_results=sequence_results,
                               pattern_results=pattern_results)
    except Exception as e:
        return "Internal Server Error", 500

# --- 애플리케이션 실행 ---
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5001)