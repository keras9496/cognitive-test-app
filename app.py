from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import random
import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

# --- 초기 설정 ---
app = Flask(__name__)
app.secret_key = 'your_very_secret_key' # 실제 운영 시에는 아무도 모르는 값으로 변경하세요.

# --- 데이터베이스 설정 ---
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'results.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- 데이터베이스 모델 정의 ---
class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(80), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    test_date = db.Column(db.String(20), nullable=False)
    test_name = db.Column(db.String(80), nullable=False)
    level = db.Column(db.String(50), nullable=False)
    correct = db.Column(db.Integer, nullable=False)
    wrong = db.Column(db.Integer, nullable=False)
    avg_similarity = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<Result {self.nickname} - {self.test_name} - {self.level}>'

# --- 상수 정의 ---
LEVELS = [
    {'name': 'Level 1', 'box_count': 5, 'flash_count': 3},
    {'name': 'Level 2', 'box_count': 7, 'flash_count': 4},
    {'name': 'Level 3', 'box_count': 7, 'flash_count': 5},
]
PROBLEMS_PER_LEVEL = 3
CANVAS_WIDTH = 500
CANVAS_HEIGHT = 500
BOX_SIZE = 50

# --- 핵심 로직 함수들 ---

def create_problem(level_index):
    """지정된 레벨에 맞는 문제를 생성합니다."""
    if level_index >= len(LEVELS):
        return None
    level_info = LEVELS[level_index]
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
        "flash_count": flash_count,
        "boxes": boxes,
        "flash_sequence": flash_sequence
    }

def save_results_to_db():
    """세션에 저장된 점수를 데이터베이스에 저장합니다."""
    nickname = session.get('nickname')
    age = session.get('age')
    date_str = session.get('test_date')
    
    for level_name, data in session.get('score', {}).items():
        if not data.get('similarities'): continue
        avg_sim = sum(data['similarities']) / len(data['similarities'])
        
        result_entry = Result(
            nickname=nickname,
            age=age,
            test_date=date_str,
            test_name='시각 순서 기억 검사',
            level=level_name,
            correct=data['correct'],
            wrong=data['wrong'],
            avg_similarity=avg_sim
        )
        db.session.add(result_entry)
    db.session.commit()

# --- 라우트(URL 경로) 정의 ---

@app.route("/")
def index():
    """사용자 정보 입력 페이지를 렌더링합니다."""
    return render_template("index.html")

@app.route("/start-test", methods=['POST'])
def start_test():
    """사용자 정보를 받아 세션을 초기화하고 테스트 페이지로 이동시킵니다."""
    session.clear()
    session['nickname'] = request.form['nickname']
    session['age'] = request.form['age']
    session['test_date'] = request.form['test_date']
    session['level_index'] = 0
    session['problem_in_level'] = 1
    session['score'] = {lvl['name']: {'correct': 0, 'wrong': 0, 'similarities': []} for lvl in LEVELS}

    problem = create_problem(session['level_index'])
    session['current_problem'] = problem
    
    return redirect(url_for('test_page'))
    
@app.route("/test")
def test_page():
    """테스트 페이지를 보여줍니다."""
    if 'current_problem' not in session:
        return redirect(url_for('index'))
    return render_template('test.html')

@app.route('/api/get-problem')
def get_problem():
    """현재 진행해야 할 문제 정보를 JSON으로 제공합니다."""
    if 'current_problem' in session:
        problem = session['current_problem']
        # 정답은 세션에만 남기고 프론트엔드로는 보내지 않습니다.
        frontend_data = {
            "level_name": problem.get('level_name'),
            "flash_count": problem.get('flash_count'),
            "boxes": problem.get('boxes')
        }
        return jsonify(frontend_data)
    return jsonify({"error": "No problem found"}), 404

@app.route('/api/submit-answer', methods=['POST'])
def submit_answer():
    """사용자의 답안을 받아 처리하고 다음 문제 또는 종료 신호를 보냅니다."""
    data = request.get_json()
    user_answer = data.get('answer')
    
    current_problem = session.get('current_problem')
    if not current_problem:
        return jsonify({"error": "No active problem"}), 400

    # 1. 채점
    correct_answer = current_problem['flash_sequence']
    is_correct = (user_answer == correct_answer)
    
    matches = sum(1 for a, b in zip(user_answer, correct_answer) if a == b)
    similarity = matches / len(correct_answer) if len(correct_answer) > 0 else 0

    # 2. 점수 기록
    level_name = LEVELS[session['level_index']]['name']
    if is_correct:
        session['score'][level_name]['correct'] += 1
    else:
        session['score'][level_name]['wrong'] += 1
    session['score'][level_name]['similarities'].append(similarity)
    session.modified = True

    # 3. 다음 문제로 진행 또는 종료
    session['problem_in_level'] += 1
    
    if session['problem_in_level'] > PROBLEMS_PER_LEVEL:
        session['level_index'] += 1
        session['problem_in_level'] = 1
    
    if session['level_index'] >= len(LEVELS):
        save_results_to_db()
        session.clear()
        return jsonify({"status": "completed", "message": "모든 검사가 완료되었습니다. 감사합니다!"})
    else:
        next_problem = create_problem(session['level_index'])
        session['current_problem'] = next_problem
        # 정답은 세션에만 남기고 프론트엔드로는 보내지 않습니다.
        frontend_data = {
            "level_name": next_problem.get('level_name'),
            "flash_count": next_problem.get('flash_count'),
            "boxes": next_problem.get('boxes')
        }
        return jsonify({"status": "next_problem", "data": frontend_data})

# --- 데이터베이스 초기화 명령어 ---
@app.cli.command('init-db')
def init_db_command():
    """데이터베이스 테이블을 생성합니다."""
    with app.app_context():
        db.create_all()
    print('Initialized the database.')

# --- 애플리케이션 실행 ---
if __name__ == "__main__":
    app.run(debug=True)