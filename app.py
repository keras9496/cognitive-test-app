from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import random
import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

# --- 초기 설정 ---
app = Flask(__name__)
# Flask 세션을 사용하기 위해 비밀 키가 필요합니다.
# 실제 서비스에서는 아무도 모르는 복잡한 문자열로 변경하세요.
app.secret_key = 'dev_secret_key_for_testing' 

# --- 데이터베이스 설정 ---
basedir = os.path.abspath(os.path.dirname(__file__))
# instance 폴더가 없으면 생성
if not os.path.exists(os.path.join(basedir, 'instance')):
    os.makedirs(os.path.join(basedir, 'instance'))
    
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'results.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- 데이터베이스 모델 정의 (name, gender 추가) ---
class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(80), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
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

def create_problem(level_index, is_practice=False):
    """지정된 레벨 또는 연습에 맞는 문제를 생성합니다."""
    if is_practice:
        level_info = {'name': 'Practice', 'box_count': 3, 'flash_count': 2}
    elif level_index >= len(LEVELS):
        return None
    else:
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
    with app.app_context():
        nickname = session.get('nickname')
        name = session.get('name')
        age = session.get('age')
        gender = session.get('gender')
        test_date = session.get('test_date')
        
        for level_name, data in session.get('score', {}).items():
            if not data.get('similarities'):
                continue
                
            avg_sim = sum(data['similarities']) / len(data['similarities'])
            
            result_entry = Result(
                nickname=nickname,
                name=name,
                age=age,
                gender=gender,
                test_date=test_date,
                test_name='시각 순서 기억 검사',
                level=level_name,
                correct=data['correct'],
                wrong=data['wrong'],
                avg_similarity=round(avg_sim, 4)
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
    """사용자 정보를 받아 세션을 초기화하고 연습 페이지로 이동시킵니다."""
    session.clear()
    session['nickname'] = request.form['nickname']
    session['name'] = request.form['name']
    session['age'] = request.form['age']
    session['gender'] = request.form['gender']
    session['test_date'] = request.form['test_date']
    session['level_index'] = 0
    session['problem_in_level'] = 1
    session['score'] = {lvl['name']: {'correct': 0, 'wrong': 0, 'similarities': []} for lvl in LEVELS}
    
    # 본 테스트 시작 전 연습 페이지로 리디렉션
    return redirect(url_for('practice_page'))

@app.route("/practice")
def practice_page():
    """연습 테스트 페이지를 보여줍니다."""
    if 'nickname' not in session:
        return redirect(url_for('index'))
    return render_template('practice.html')

@app.route("/test")
def test_page():
    """테스트 페이지를 보여줍니다."""
    # 사용자가 직접 /test 로 접근하는 것을 방지
    if 'nickname' not in session:
        return redirect(url_for('index'))
    return render_template('test.html')

@app.route('/api/get-practice-problem')
def get_practice_problem():
    """연습 문제 정보를 JSON으로 제공합니다."""
    if 'nickname' not in session:
        return jsonify({"error": "Session not started"}), 403
    
    problem = create_problem(0, is_practice=True)
    session['practice_problem'] = problem
    session.modified = True
    
    return jsonify(problem)

@app.route('/api/submit-practice-answer', methods=['POST'])
def submit_practice_answer():
    """연습 답안을 받아 정답 여부를 반환합니다."""
    data = request.get_json()
    user_answer = data.get('answer')
    
    correct_answer = session.get('practice_problem', {}).get('flash_sequence')
    
    if user_answer == correct_answer:
        return jsonify({"status": "correct", "message": "정답입니다! 잠시 후 본 테스트를 시작합니다."})
    else:
        return jsonify({"status": "incorrect", "message": "틀렸습니다. 다시 시도해보세요."})

@app.route('/api/get-problem')
def get_problem():
    """현재 진행해야 할 문제 정보를 JSON으로 제공합니다."""
    if 'nickname' not in session:
        return jsonify({"error": "Session not started. Please go to the main page."}), 403

    level_index = session.get('level_index', 0)
    
    # 새로운 문제 생성
    problem = create_problem(level_index)
    if not problem:
        return jsonify({"status": "completed", "message": "모든 검사가 완료되었습니다. 감사합니다!"})
        
    session['current_problem'] = problem
    session.modified = True
    
    # 프론트엔드에는 정답을 포함한 모든 정보 전달
    frontend_data = {
        "level_name": problem.get('level_name'),
        "flash_count": problem.get('flash_count'),
        "boxes": problem.get('boxes'),
        "flash_sequence": problem.get('flash_sequence'), 
        "problem_in_level": session.get('problem_in_level'),
        "total_problems": PROBLEMS_PER_LEVEL
    }
    return jsonify(frontend_data)

@app.route('/api/submit-answer', methods=['POST'])
def submit_answer():
    """사용자의 답안을 받아 처리하고 다음 문제 또는 종료 신호를 보냅니다."""
    data = request.get_json()
    user_answer = data.get('answer')
    
    current_problem = session.get('current_problem')
    if not current_problem:
        return jsonify({"error": "No active problem in session"}), 400

    # 1. 채점
    correct_answer = current_problem['flash_sequence']
    is_correct = (user_answer == correct_answer)
    
    matches = sum(1 for a, b in zip(user_answer, correct_answer) if a == b)
    similarity = matches / len(correct_answer) if len(correct_answer) > 0 else 0

    # 2. 점수 기록 (세션에 저장)
    level_name = LEVELS[session['level_index']]['name']
    if is_correct:
        session['score'][level_name]['correct'] += 1
    else:
        session['score'][level_name]['wrong'] += 1
    session['score'][level_name]['similarities'].append(similarity)
    
    # 3. 다음 문제로 진행 또는 종료
    session['problem_in_level'] += 1
    
    if session['problem_in_level'] > PROBLEMS_PER_LEVEL:
        session['level_index'] += 1
        session['problem_in_level'] = 1
    
    session.modified = True

    if session['level_index'] >= len(LEVELS):
        # 모든 레벨 완료 -> 결과 저장 후 종료
        save_results_to_db()
        session.clear()
        return jsonify({"status": "completed", "message": "모든 검사가 완료되었습니다. 감사합니다!"})
    else:
        # 다음 문제를 준비했다는 신호만 보냄
        return jsonify({"status": "next_problem", "message": "다음 문제로 넘어갑니다."})

# --- 데이터베이스 초기화 명령어 ---
# 터미널에서 `flask init-db` 실행
@app.cli.command('init-db')
def init_db_command():
    """데이터베이스 테이블을 생성합니다."""
    with app.app_context():
        db.create_all()
    print('Initialized the database.')


@app.route("/results")
def show_results():
    # 간단한 비밀번호 확인 (실제로는 더 안전한 방식 사용)
    password = request.args.get('pw')
    if password != 'admin1234': # 비밀번호를 원하는 값으로 변경
        return "Access Denied.", 403

    # 데이터베이스에서 모든 결과를 시간순으로 정렬하여 가져옴
    all_results = Result.query.order_by(Result.id.desc()).all()
    return render_template('results.html', results=all_results)



if __name__ == "__main__":
    app.run(debug=True)