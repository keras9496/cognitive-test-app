document.addEventListener('DOMContentLoaded', function() {
    // --- 전역 상태 변수 ---
    let currentStage = '';
    let currentTest = null;
    const userResults = {
        testA_time: 0,
        testA_errors: 0,
        testA_completed: false, // 완료 여부 추가
        testA_terminated: false, // A형 본검사에서 중지 여부
        testA_practice_terminated: false, // A형 연습에서 중지 여부
        testA_practice_time: 0, // A형 연습 소요시간
        testA_practice_errors: 0, // A형 연습 오류수
        consonant_check_failures: 0,
        consonant_check_time: 0,
        consonant_check_completed: false, // 완료 여부 추가
        consonant_check_terminated: false, // 자음체크에서 중지 여부
        testB_time: 0,
        testB_errors: 0,
        testB_completed: false, // 완료 여부 추가
        testB_terminated: false, // B형 본검사에서 중지 여부
        testB_practice_terminated: false, // B형 연습에서 중지 여부
        testB_practice_time: 0, // B형 연습 소요시간
        testB_practice_errors: 0, // B형 연습 오류수
        termination_reason: null, // 종료 사유 추가
        termination_stage: null, // 종료된 단계 추가
    };

    const KOREAN_CONSONANTS = ['가', '나', '다', '라', '마', '바', '사', '아', '자', '차', '카', '타', '파', '하'];
    let currentConsonantIndex = 0;
    let consonantCheckStartTime = 0;

    // --- 화면 전환 함수 ---
    const screens = document.querySelectorAll('#app-container > div');
    function showScreen(screenId) {
        screens.forEach(screen => {
            screen.classList.add('hidden');
        });
        const targetScreen = document.getElementById(screenId);
        if (targetScreen) {
            targetScreen.classList.remove('hidden');
        }
    }

    // --- 시험 중지 기능 ---
    function showTerminationDialog(callback) {
        const dialog = document.createElement('div');
        dialog.className = 'termination-dialog-overlay';
        dialog.innerHTML = `
            <div class="termination-dialog">
                <h3>시험 중지</h3>
                <p>정말로 시험을 중지하시겠습니까?</p>
                <p class="warning">지금까지의 결과가 저장되고 다음 단계로 넘어갑니다.</p>
                <div class="dialog-buttons">
                    <button class="btn btn-secondary" id="continue-test">계속하기</button>
                    <button class="btn btn-danger" id="terminate-test">중지하기</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(dialog);
        
        document.getElementById('continue-test').addEventListener('click', () => {
            document.body.removeChild(dialog);
        });
        
        document.getElementById('terminate-test').addEventListener('click', () => {
            document.body.removeChild(dialog);
            callback();
        });
    }

    function terminateCurrentTest() {
        userResults.termination_reason = 'user_terminated';
        userResults.termination_stage = currentStage;
        
        // 현재 진행 중인 테스트의 중간 결과 저장
        if (currentTest) {
            const currentTime = Date.now();
            const elapsedTime = currentTest.startTime > 0 ? (currentTime - currentTest.startTime) / 1000 : 0;
            
            switch (currentStage) {
                case 'A_PRACTICE':
                    // 연습도 기록을 남김
                    userResults.testA_practice_terminated = true;
                    userResults.testA_practice_time = parseFloat(elapsedTime.toFixed(2));
                    userResults.testA_practice_errors = currentTest.errorCount;
                    runTestAMain();
                    return;
                    
                case 'A_MAIN':
                    userResults.testA_terminated = true;
                    userResults.testA_time = parseFloat(elapsedTime.toFixed(2));
                    userResults.testA_errors = currentTest.errorCount;
                    userResults.testA_completed = false;
                    runConsonantCheck();
                    return;
                    
                case 'B_PRACTICE':
                    // 연습도 기록을 남김
                    userResults.testB_practice_terminated = true;
                    userResults.testB_practice_time = parseFloat(elapsedTime.toFixed(2));
                    userResults.testB_practice_errors = currentTest.errorCount;
                    runTestBMain();
                    return;
                    
                case 'B_MAIN':
                    userResults.testB_terminated = true;
                    userResults.testB_time = parseFloat(elapsedTime.toFixed(2));
                    userResults.testB_errors = currentTest.errorCount;
                    userResults.testB_completed = false;
                    submitResults();
                    return;
            }
        }
        
        // 자음 체크 중인 경우
        if (currentStage === 'CONSONANT_CHECK') {
            const currentTime = Date.now();
            const elapsedTime = consonantCheckStartTime > 0 ? (currentTime - consonantCheckStartTime) / 1000 : 0;
            userResults.consonant_check_terminated = true;
            userResults.consonant_check_time = parseFloat(elapsedTime.toFixed(2));
            userResults.consonant_check_completed = false;
            runTestBPractice();
        }
    }

    // --- 테스트 로직 클래스 (수정) ---
    class TrailMakingTest {
        constructor(containerId, items, onComplete) {
            this.container = document.getElementById(containerId);
            this.items = items;
            this.onComplete = onComplete;
            this.correctIndex = 0;
            this.errorCount = 0;
            this.startTime = 0;
            this.lastClickedCircle = null;
            this.circles = [];
            this.init();
        }

        init() {
            this.container.innerHTML = '<svg class="line-svg"></svg>';
            this.svg = this.container.querySelector('svg');
            this.generateCircles();
            this.addClickListeners();
        }
        
        generateCircles() {
            const positions = [];
            const containerRect = this.container.getBoundingClientRect();
            const margin = 30;

            for (let i = 0; i < this.items.length; i++) {
                let newPos;
                let attempts = 0;
                while (attempts < 100) {
                    const x = Math.random() * (containerRect.width - (2 * margin) - 50) + margin;
                    const y = Math.random() * (containerRect.height - (2 * margin) - 50) + margin;
                    newPos = { x, y };

                    let isOverlapping = false;
                    for (const pos of positions) {
                        const dist = Math.sqrt(Math.pow(pos.x - newPos.x, 2) + Math.pow(pos.y - newPos.y, 2));
                        if (dist < 70) {
                            isOverlapping = true;
                            break;
                        }
                    }
                    if (!isOverlapping) break;
                    attempts++;
                }
                positions.push(newPos);

                const circle = document.createElement('div');
                circle.className = 'circle';
                circle.style.left = `${newPos.x}px`;
                circle.style.top = `${newPos.y}px`;
                circle.textContent = this.items[i];
                circle.dataset.value = this.items[i];
                this.container.appendChild(circle);
                this.circles.push(circle);
            }
        }

        addClickListeners() {
            this.container.addEventListener('click', this.handleCircleClick.bind(this));
        }

        handleCircleClick(e) {
            if (!e.target.classList.contains('circle')) return;

            const clickedValue = e.target.dataset.value;
            const expectedValue = this.items[this.correctIndex];
            
            if (clickedValue == expectedValue) {
                if (this.correctIndex === 0) {
                    this.startTime = Date.now();
                }

                e.target.classList.add('correct');
                e.target.style.pointerEvents = 'none';

                if (this.lastClickedCircle) {
                    this.drawLine(this.lastClickedCircle, e.target);
                }
                this.lastClickedCircle = e.target;
                
                this.correctIndex++;
                
                if (this.correctIndex === this.items.length) {
                    const endTime = Date.now();
                    const duration = (endTime - this.startTime) / 1000;
                    this.onComplete(duration, this.errorCount);
                }
            } else {
                this.errorCount++;
                e.target.classList.add('error');
                setTimeout(() => e.target.classList.remove('error'), 500);
            }
        }
        
        drawLine(fromCircle, toCircle) {
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            const fromRect = fromCircle.getBoundingClientRect();
            const toRect = toCircle.getBoundingClientRect();
            const containerRect = this.container.getBoundingClientRect();

            line.setAttribute('x1', fromRect.left - containerRect.left + fromRect.width / 2);
            line.setAttribute('y1', fromRect.top - containerRect.top + fromRect.height / 2);
            line.setAttribute('x2', toRect.left - containerRect.left + toRect.width / 2);
            line.setAttribute('y2', toRect.top - containerRect.top + toRect.height / 2);
            line.setAttribute('stroke', '#333');
            line.setAttribute('stroke-width', '2');
            this.svg.appendChild(line);
        }
    }
    
    // --- 자음 순서 맞추기 로직 (수정) ---
    function setupConsonantCheck() {
        currentConsonantIndex = 0;
        userResults.consonant_check_failures = 0;
        document.getElementById('consonant-failures').textContent = '0';
        
        const shuffledConsonants = [...KOREAN_CONSONANTS].sort(() => Math.random() - 0.5);

        const sourceArea = document.getElementById('consonant-source-area');
        const targetArea = document.getElementById('consonant-target-area');
        sourceArea.innerHTML = '';
        targetArea.innerHTML = '';

        // 하단에 섞인 자음 박스 생성
        shuffledConsonants.forEach(consonant => {
            const box = document.createElement('div');
            box.className = 'consonant-box';
            box.textContent = consonant;
            box.dataset.value = consonant;
            box.addEventListener('click', handleConsonantClick);
            sourceArea.appendChild(box);
        });

        // 상단에 빈칸 박스 생성
        for (let i = 0; i < 14; i++) {
            const placeholder = document.createElement('div');
            placeholder.className = 'consonant-placeholder';
            targetArea.appendChild(placeholder);
        }

        consonantCheckStartTime = Date.now();
    }

    function handleConsonantClick(event) {
        const clickedBox = event.target;
        const clickedConsonant = clickedBox.dataset.value;
        const expectedConsonant = KOREAN_CONSONANTS[currentConsonantIndex];

        if (clickedConsonant === expectedConsonant) {
            const targetArea = document.getElementById('consonant-target-area');
            const placeholder = targetArea.children[currentConsonantIndex];
            
            placeholder.textContent = clickedConsonant;
            placeholder.classList.add('correct');
            
            clickedBox.style.visibility = 'hidden';
            clickedBox.removeEventListener('click', handleConsonantClick);
            
            currentConsonantIndex++;

            if (currentConsonantIndex === KOREAN_CONSONANTS.length) {
                const endTime = Date.now();
                userResults.consonant_check_time = parseFloat(((endTime - consonantCheckStartTime) / 1000).toFixed(2));
                userResults.consonant_check_completed = true;
                document.getElementById('start-test-b-practice-button').disabled = false;
            }
        } else {
            userResults.consonant_check_failures++;
            document.getElementById('consonant-failures').textContent = userResults.consonant_check_failures;
            
            clickedBox.classList.add('error');
            setTimeout(() => {
                clickedBox.classList.remove('error');
            }, 500);
        }
    }
    
    // --- 단계별 진행 함수 (수정) ---
    function runTestAPractice() {
        currentStage = 'A_PRACTICE';
        showScreen('test-a-practice-screen');
        const items = Array.from({length: 8}, (_, i) => i + 1);
        currentTest = new TrailMakingTest('test-a-practice-area', items, () => {
            document.getElementById('start-test-a-button').disabled = false;
        });
        document.getElementById('start-test-a-button').disabled = true;
    }

    function runTestAMain() {
        currentStage = 'A_MAIN';
        showScreen('test-a-main-screen');
        const items = Array.from({length: 25}, (_, i) => i + 1);
        currentTest = new TrailMakingTest('test-a-main-area', items, (duration, errors) => {
            userResults.testA_time = parseFloat(duration.toFixed(2));
            userResults.testA_errors = errors;
            userResults.testA_completed = true;
            runConsonantCheck();
        });
    }
    
    function runConsonantCheck() {
        currentStage = 'CONSONANT_CHECK';
        showScreen('consonant-check-screen');
        document.getElementById('start-test-b-practice-button').disabled = true;
        setupConsonantCheck();
    }

    function runTestBPractice() {
        currentStage = 'B_PRACTICE';
        showScreen('test-b-practice-screen');
        const items = [];
        for (let i = 0; i < 4; i++) {
            items.push(i + 1);
            items.push(KOREAN_CONSONANTS[i]);
        }
        currentTest = new TrailMakingTest('test-b-practice-area', items, () => {
            document.getElementById('start-test-b-button').disabled = false;
        });
        document.getElementById('start-test-b-button').disabled = true;
    }

    function runTestBMain() {
        currentStage = 'B_MAIN';
        showScreen('test-b-main-screen');
        const items = [];
        for (let i = 0; i < 14; i++) {
            items.push(i + 1);
            items.push(KOREAN_CONSONANTS[i]);
        }
        
        currentTest = new TrailMakingTest('test-b-main-area', items, (duration, errors) => {
            userResults.testB_time = parseFloat(duration.toFixed(2));
            userResults.testB_errors = errors;
            userResults.testB_completed = true;
            submitResults();
        });
    }

    async function submitResults() {
        currentStage = 'SUBMITTING';
        showScreen('loading-screen');

        try {
            const response = await fetch('/save_trail_making_results', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(userResults),
            });
            const data = await response.json();
            if (data.success && data.next_url) {
                window.location.href = data.next_url;
            } else {
                console.error('결과 저장 실패:', data.error);
                alert('결과 저장에 실패했습니다. 관리자에게 문의하세요.');
            }
        } catch (error) {
            console.error('결과 전송 중 오류 발생:', error);
            alert('결과 전송 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.');
        }
    }

    // --- 시험중지 버튼 이벤트 리스너 추가 ---
    function addTerminationButton() {
        const terminationButtons = document.querySelectorAll('.terminate-btn');
        terminationButtons.forEach(button => {
            button.addEventListener('click', () => {
                showTerminationDialog(terminateCurrentTest);
            });
        });
    }
    
    // --- 기존 이벤트 리스너 ---
    document.getElementById('start-button').addEventListener('click', runTestAPractice);
    document.getElementById('start-test-a-button').addEventListener('click', runTestAMain);
    document.getElementById('start-test-b-practice-button').addEventListener('click', runTestBPractice);
    document.getElementById('start-test-b-button').addEventListener('click', runTestBMain);

    // --- 시험중지 버튼 이벤트 리스너 등록 ---
    addTerminationButton();

    // --- 앱 초기화 ---
    showScreen('welcome-screen');
    currentStage = 'WELCOME';
});