from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import uuid
import os

app = Flask(__name__)

# 데이터베이스 설정
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'postgresql://user:password@localhost/cognitive_test_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key') # 프로덕션 환경에서는 환경 변수 사용

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# 기존 데이터베이스 모델
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

# --- 신규 추가된 트레일 메이킹 테스트 모델 ---
class TrailMakingResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(80), nullable=False)
    test_a_time = db.Column(db.Float, nullable=False)
    test_a_errors = db.Column(db.Integer, nullable=False)
    consonant_check_failures = db.Column(db.Integer, nullable=False)
    test_b_time = db.Column(db.Float, nullable=False)
    test_b_errors = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<TrailMakingResult {self.id} for user {self.user_id}>'
# -----------------------------------------

@app.before_request
def make_session_permanent():
    session.permanent = True


@app.route('/')
def index():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    return render_template('index.html')


# --- 아래 코드를 추가해주세요 ---
@app.route('/start-test', methods=['POST'])
def start_test():
    # form에서 전송된 사용자 정보를 세션에 저장할 수 있습니다 (선택 사항)
    # session['user_name'] = request.form.get('name')
    # session['user_age'] = request.form.get('age')
    # session['user_gender'] = request.form.get('gender')
    # session['test_date'] = request.form.get('test_date')
    
    # 첫 번째 테스트인 practice 페이지로 리다이렉트
    return redirect(url_for('practice'))
# -----------------------------


@app.route('/practice')
def practice():
    return render_template('practice.html')

@app.route('/intermission')
def intermission():
    return render_template('intermission.html')

@app.route('/test')
def test():
    return render_template('test.html')

@app.route('/submit_test', methods=['POST'])
def submit_test():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 403
    data = request.get_json()
    new_result = TestResult(
        user_id=session['user_id'],
        level=data.get('level'),
        score=data.get('score'),
        reaction_times=data.get('reactionTimes')
    )
    db.session.add(new_result)
    db.session.commit()
    # 다음 페이지를 card_test에서 trail_making_test로 변경
    return jsonify({'success': True, 'next_url': url_for('trail_making_test')})

# --- 신규 추가된 트레일 메이킹 테스트 라우트 ---
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
    
    # 트레일 메이킹 테스트가 끝나면 card_test로 이동
    return jsonify({'success': True, 'next_url': url_for('card_test')})
# -----------------------------------------

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
    # 세션에서 사용자 ID를 제거하여 다시 시작할 때 새로운 세션을 갖도록 함
    session.pop('user_id', None)
    return render_template('finish.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)