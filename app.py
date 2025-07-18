from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import random
import os
import json
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# --- 초기 설정 ---
app = Flask(__name__)
# Render와 같은 배포 환경에서는 환경 변수를 사용하는 것이 보안상 안전합니다.
# 로컬 테스트를 위해 기본값도 설정합니다.
app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret_key_for_local_testing')

# --- 데이터베이스 설정 ---
basedir = os.path.abspath(os.path.dirname(__file__))
# 'instance' 폴더가 없으면 생성합니다.
if not os.path.exists(os.path.join(basedir, 'instance')):
    os.makedirs(os.path.join(basedir, 'instance'))

# 데이터베이스 URI 설정
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or \
    'sqlite:///' + os.path.join(basedir, 'instance', 'cognitive_tests.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db) # Flask-Migrate 객체 초기화

# --- 데이터베이스 모델 정의 ---

# 1. 시각 순서 기억 검사 결과 모델
class Result(db.Model):
    __tablename__ = 'sequence_memory_results' # 테이블 이름 명시
    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(80), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    test_date = db.Column(db.String(20), nullable=False)
    test_name = db.Column(db.String(80), nullable=False, server_default='시각 순서 기억 검사')
    level = db.Column(db.String(50), nullable=False)
    correct = db.Column(db.Integer, nullable=False)
    wrong = db.Column(db.Integer, nullable=False)
    avg_similarity = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<Result {self.nickname} - {self.test_name} - {self.level}>'

# 2. 도형 패턴 인지 테스트 결과 모델 (새로운 요구사항 반영)
class PatternResult(db.Model):
    __tablename__ = 'pattern_recognition_results' # 테이블 이름 명시
    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(80), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    test_date = db.Column(db.String(20), nullable=False)
    level = db.Column(db.Integer, nullable=False) # 각 레벨별로 결과 저장
    score = db.Column(db.Integer, nullable=False) # 해당 레벨의 점수
    total_problems = db.Column(db.Integer, nullable=False) # 해당 레벨의 총 문제 수
    times_json = db.Column(db.String, nullable=False) # 각 문제별 소요 시간을 JSON 문자열로 저장

    def __repr__(self):
        return f'<PatternResult {self.nickname} - Level {self.level}>'


# --- 상수 정의 ---
# 첫 번째 테스트(시각 순서 기억) 설정
SEQUENCE_LEVELS = [
    {'name': 'Level 1', 'box_count': 5, 'flash_count': 3},
    {'name': 'Level 2', 'box_count': 7, 'flash_count': 4},
    {'name': 'Level 3', 'box_count': 7, 'flash_count': 5},
]
PROBLEMS_PER_SEQUENCE_LEVEL = 5
CANVAS_WIDTH = 500
CANVAS_HEIGHT = 500
BOX_SIZE = 50

# --- 핵심 로직 함수들 ---

def create_sequence_problem(level_index, is_practice=False):
    """(첫 번째 테스트) 지정된 레벨 또는 연습에 맞는 문제를 생성합니다."""
    if is_practice:
        level_info = {'name': 'Practice', 'box_count': 3, 'flash_count': 2}
    elif level_index >= len(SEQUENCE_LEVELS):
        return None
    else:
        level_info = SEQUENCE_LEVELS[level_index]

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

def save_sequence_results_to_db():
    """(첫 번째 테스트) 세션에 저장된 점수를 데이터베이스에 저장합니다."""
    try:
        if 'nickname' not in session or 'score' not in session:
            print("세션에 닉네임 또는 점수 정보가 없어 DB에 저장하지 않습니다.")
            return False

        nickname = session.get('nickname')
        name = session.get('name')
        age = session.get('age')
        gender = session.get('gender')
        test_date = session.get('test_date')
        
        # 데이터베이스 테이블이 존재하지 않으면 생성
        db.create_all()
        
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
                level=level_name,
                correct=data['correct'],
                wrong=data['wrong'],
                avg_similarity=round(avg_sim, 4)
            )
            db.session.add(result_entry)
        
        db.session.commit()
        print(f"{nickname}님의 시각 순서 기억 검사 결과가 DB에 저장되었습니다.")
        return True
        
    except Exception as e:
        print(f"DB 저장 중 오류 발생: {str(e)}")
        db.session.rollback()
        return False

# --- 라우트(URL 경로) 정의 ---

@app.route("/")
def index():
    """사용자 정보 입력 페이지를 렌더링합니다."""
    return render_template("index.html")

@app.route("/start-test", methods=['POST'])
def start_test():
    """사용자 정보를 받아 세션을 초기화하고 연습 페이지로 이동시킵니다."""
    try:
        session.clear()
        session['nickname'] = request.form.get('nickname', '').strip()
        session['name'] = request.form.get('name', '').strip()
        session['age'] = int(request.form.get('age', 0))
        session['gender'] = request.form.get('gender', '').strip()
        session['test_date'] = request.form.get('test_date', '').strip()
        
        # 입력 검증
        if not all([session['nickname'], session['name'], session['age'], session['gender'], session['test_date']]):
            return redirect(url_for('index'))
        
        # 첫 번째 테스트를 위한 세션 초기화
        session['level_index'] = 0
        session['problem_in_level'] = 1
        session['score'] = {lvl['name']: {'correct': 0, 'wrong': 0, 'similarities': []} for lvl in SEQUENCE_LEVELS}
        session['sequence_test_completed'] = False
        
        session.modified = True
        return redirect(url_for('practice_page'))
        
    except (ValueError, TypeError) as e:
        print(f"사용자 입력 처리 중 오류: {str(e)}")
        return redirect(url_for('index'))

@app.route("/practice")
def practice_page():
    """연습 테스트 페이지를 보여줍니다."""
    if 'nickname' not in session:
        return redirect(url_for('index'))
    return render_template('practice.html')

@app.route("/test")
def test_page():
    """첫 번째 테스트(시각 순서 기억) 페이지를 보여줍니다."""
    if 'nickname' not in session:
        return redirect(url_for('index'))
    return render_template('test.html')
    
@app.route("/pattern-test")
def pattern_test_page():
    """두 번째 테스트(도형 패턴 인지) 페이지를 보여줍니다."""
    if 'nickname' not in session:
        return redirect(url_for('index'))
    return render_template('pattern_test.html')

# --- API 엔드포인트 ---

@app.route('/api/get-practice-problem')
def get_practice_problem():
    """연습 문제 정보를 JSON으로 제공합니다."""
    try:
        if 'nickname' not in session:
            return jsonify({"error": "Session not started"}), 403
        
        problem = create_sequence_problem(0, is_practice=True)
        if not problem:
            return jsonify({"error": "Failed to create practice problem"}), 500
            
        session['practice_problem'] = problem
        session.modified = True
        
        return jsonify(problem)
        
    except Exception as e:
        print(f"연습 문제 생성 중 오류: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/submit-practice-answer', methods=['POST'])
def submit_practice_answer():
    """연습 답안을 받아 정답 여부를 반환합니다."""
    try:
        data = request.get_json()
        if not data or 'answer' not in data:
            return jsonify({"error": "Invalid request data"}), 400
            
        user_answer = data.get('answer')
        correct_answer = session.get('practice_problem', {}).get('flash_sequence')
        
        if not correct_answer:
            return jsonify({"error": "No practice problem found"}), 400
        
        if user_answer == correct_answer:
            return jsonify({"status": "correct", "message": "정답입니다! 잠시 후 본 테스트를 시작합니다."})
        else:
            return jsonify({"status": "incorrect", "message": "틀렸습니다. 다시 시도해보세요."})
            
    except Exception as e:
        print(f"연습 답안 처리 중 오류: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/get-problem')
def get_problem():
    """(첫 번째 테스트) 현재 진행해야 할 문제 정보를 JSON으로 제공합니다."""
    try:
        if 'nickname' not in session:
            return jsonify({"error": "Session not started. Please go to the main page."}), 403

        level_index = session.get('level_index', 0)
        
        # 모든 레벨을 완료했는지 확인
        if level_index >= len(SEQUENCE_LEVELS):
            # 결과 저장
            save_success = save_sequence_results_to_db()
            if save_success:
                # 첫 번째 테스트 완료 표시
                session['sequence_test_completed'] = True
                # 세션에서 점수 정보는 삭제하여 중복 저장을 방지
                session.pop('score', None)
                session.modified = True
                
                return jsonify({
                    "status": "completed", 
                    "message": "1차 검사가 완료되었습니다. 다음 검사를 진행합니다.", 
                    "next_url": url_for('pattern_test_page')
                })
            else:
                return jsonify({"error": "Failed to save results"}), 500
            
        problem = create_sequence_problem(level_index)
        if not problem:
            return jsonify({"error": "문제 생성에 실패했습니다."}), 500
            
        session['current_problem'] = problem
        session.modified = True
        
        frontend_data = {
            "level_name": problem.get('level_name'),
            "flash_count": problem.get('flash_count'),
            "boxes": problem.get('boxes'),
            "flash_sequence": problem.get('flash_sequence'), 
            "problem_in_level": session.get('problem_in_level'),
            "total_problems": PROBLEMS_PER_SEQUENCE_LEVEL
        }
        return jsonify(frontend_data)
        
    except Exception as e:
        print(f"문제 생성 중 오류: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/submit-answer', methods=['POST'])
def submit_answer():
    """(첫 번째 테스트) 사용자의 답안을 받아 처리하고 다음 상태를 결정합니다."""
    try:
        data = request.get_json()
        if not data or 'answer' not in data:
            return jsonify({"error": "Invalid request data"}), 400
            
        user_answer = data.get('answer')
        
        current_problem = session.get('current_problem')
        if not current_problem:
            return jsonify({"error": "No active problem in session"}), 400

        correct_answer = current_problem['flash_sequence']
        is_correct = (user_answer == correct_answer)
        
        matches = sum(1 for a, b in zip(user_answer, correct_answer) if a == b)
        similarity = matches / len(correct_answer) if len(correct_answer) > 0 else 0

        level_name = SEQUENCE_LEVELS[session.get('level_index', 0)]['name']
        
        # 점수 업데이트
        if level_name in session.get('score', {}):
            if is_correct:
                session['score'][level_name]['correct'] += 1
            else:
                session['score'][level_name]['wrong'] += 1
            session['score'][level_name]['similarities'].append(similarity)
        
        # 다음 문제로 진행
        session['problem_in_level'] += 1
        
        if session['problem_in_level'] > PROBLEMS_PER_SEQUENCE_LEVEL:
            session['level_index'] += 1
            session['problem_in_level'] = 1
        
        session.modified = True
        
        return jsonify({"status": "next_problem"})
        
    except Exception as e:
        print(f"답안 처리 중 오류: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/submit-pattern-result', methods=['POST'])
def submit_pattern_result():
    """(두 번째 테스트) 도형 패턴 인지 테스트 결과를 받아 DB에 저장합니다."""
    try:
        if 'nickname' not in session:
            return jsonify({"error": "Session not found"}), 403

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data received"}), 400
        
        # 클라이언트로부터 받은 데이터 검증
        required_fields = ['level', 'score', 'total_problems', 'times']
        if not all(k in data for k in required_fields):
            return jsonify({"error": "Missing required data fields"}), 400

        # 데이터베이스 테이블이 존재하지 않으면 생성
        db.create_all()
        
        result_entry = PatternResult(
            nickname=session.get('nickname'),
            name=session.get('name'),
            age=session.get('age'),
            gender=session.get('gender'),
            test_date=session.get('test_date'),
            level=int(data.get('level')),
            score=int(data.get('score')),
            total_problems=int(data.get('total_problems')),
            times_json=json.dumps(data.get('times', [])) # 리스트를 JSON 문자열로 변환
        )
        
        db.session.add(result_entry)
        db.session.commit()
        
        print(f"{session.get('nickname')}님의 도형 패턴 인지 Level {data.get('level')} 결과가 DB에 저장되었습니다.")
        
        return jsonify({"status": "success", "message": "결과가 저장되었습니다."})
        
    except ValueError as e:
        print(f"데이터 타입 변환 오류: {str(e)}")
        return jsonify({"error": "Invalid data format"}), 400
    except Exception as e:
        print(f"패턴 결과 저장 중 오류: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "Failed to save pattern result"}), 500

# --- 결과 페이지 ---

@app.route("/results")
def show_results():
    """두 테스트의 모든 결과를 관리자에게 보여주는 페이지입니다."""
    try:
        password = request.args.get('pw')
        # Render 대시보드에서 설정한 환경 변수 값을 가져옵니다.
        admin_pw = os.environ.get('ADMIN_PASSWORD', 'local_admin_pw')
        if password != admin_pw:
            return "Access Denied. 관리자 암호를 확인하세요.", 403

        # 각 테스트 결과를 ID 내림차순으로 가져옴
        sequence_results = Result.query.order_by(Result.id.desc()).all()
        pattern_results_raw = PatternResult.query.order_by(PatternResult.id.desc()).all()
        
        # JSON으로 저장된 시간 데이터를 Python 리스트로 변환
        pattern_results = []
        for r in pattern_results_raw:
            try:
                r.times_list = json.loads(r.times_json)
            except (json.JSONDecodeError, TypeError):
                r.times_list = [] # JSON 파싱 오류 시 빈 리스트로 처리
            pattern_results.append(r)
            
        return render_template('results.html', sequence_results=sequence_results, pattern_results=pattern_results)
        
    except Exception as e:
        print(f"결과 페이지 렌더링 중 오류: {str(e)}")
        return "Internal Server Error", 500

# --- 애플리케이션 실행 ---
if __name__ == "__main__":
    # 애플리케이션 컨텍스트 내에서 데이터베이스 테이블 생성
    with app.app_context():
        db.create_all()
    
    # 로컬에서 실행할 때 디버그 모드를 활성화합니다.
    # gunicorn으로 실행될 때는 이 부분이 실행되지 않습니다.
    app.run(debug=True, port=5001)