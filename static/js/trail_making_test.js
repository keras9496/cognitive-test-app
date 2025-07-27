document.addEventListener('DOMContentLoaded', function() {
    // --- 전역 상태 변수 ---
    let currentStage = '';
    let currentTest = null;
    const userResults = {
        testA_time: 0,
        testA_errors: 0,
        consonant_check_failures: 0,
        testB_time: 0,
        testB_errors: 0,
    };

    const KOREAN_CONSONANTS = ['가', '나', '다', '라', '마', '바', '사', '아', '자', '차', '카', '타', '파', '하'];

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

    // --- 테스트 로직 클래스 ---
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
    
    // --- 자음 순서 맞추기 로직 ---
    function setupConsonantCheck() {
        const dropArea = document.getElementById('consonant-drop-area');
        const dragArea = document.getElementById('consonant-drag-area');
        const failuresSpan = document.getElementById('consonant-failures');
        const nextButton = document.getElementById('start-test-b-practice-button');
        dropArea.innerHTML = '';
        dragArea.innerHTML = '';
        failuresSpan.textContent = '0';
        nextButton.classList.add('hidden');
        userResults.consonant_check_failures = 0;

        const missingConsonants = [];
        KOREAN_CONSONANTS.forEach((c, i) => {
            const isEven = (i + 1) % 2 === 0;
            if (isEven) {
                const dropZone = document.createElement('div');
                dropZone.className = 'drop-zone flex justify-center items-center rounded-lg';
                dropZone.dataset.correct = c;
                dropArea.appendChild(dropZone);
                missingConsonants.push(c);
            } else {
                const filledZone = document.createElement('div');
                filledZone.className = 'w-[60px] h-[60px] flex justify-center items-center bg-slate-200 rounded-lg text-xl font-bold';
                filledZone.textContent = c;
                dropArea.appendChild(filledZone);
            }
        });

        missingConsonants.sort(() => Math.random() - 0.5);
        missingConsonants.forEach(c => {
            const card = document.createElement('div');
            card.className = 'consonant-card draggable flex justify-center items-center bg-white rounded-lg text-xl font-bold';
            card.textContent = c;
            card.draggable = true;
            card.dataset.value = c;
            dragArea.appendChild(card);
        });

        let draggedItem = null;

        dragArea.addEventListener('dragstart', e => {
            if(e.target.classList.contains('draggable')) {
                draggedItem = e.target;
                setTimeout(() => e.target.classList.add('opacity-50'), 0);
            }
        });
        dragArea.addEventListener('dragend', e => {
             if(e.target.classList.contains('draggable')) {
                draggedItem.classList.remove('opacity-50');
                draggedItem = null;
             }
        });
        dropArea.addEventListener('dragover', e => {
            e.preventDefault();
            if (e.target.classList.contains('drop-zone') && !e.target.hasChildNodes()) {
                e.target.classList.add('over');
            }
        });
        dropArea.addEventListener('dragleave', e => {
            if (e.target.classList.contains('drop-zone')) {
                e.target.classList.remove('over');
            }
        });
        dropArea.addEventListener('drop', e => {
            e.preventDefault();
            if (e.target.classList.contains('drop-zone') && !e.target.hasChildNodes()) {
                e.target.classList.remove('over');
                if (e.target.dataset.correct === draggedItem.dataset.value) {
                    e.target.appendChild(draggedItem);
                    draggedItem.draggable = false;
                    draggedItem.classList.remove('draggable');
                    draggedItem.style.cursor = 'default';
                    
                    const dropZones = dropArea.querySelectorAll('.drop-zone');
                    const isComplete = Array.from(dropZones).every(zone => zone.hasChildNodes());
                    if (isComplete) {
                        nextButton.classList.remove('hidden');
                    }
                } else {
                    userResults.consonant_check_failures++;
                    failuresSpan.textContent = userResults.consonant_check_failures;
                    draggedItem.classList.add('error');
                    setTimeout(() => draggedItem.classList.remove('error'), 500);
                }
            }
        });
    }
    
    // --- 단계별 진행 함수 ---
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
            runConsonantCheck();
        });
    }
    
    function runConsonantCheck() {
        currentStage = 'CONSONANT_CHECK';
        showScreen('consonant-check-screen');
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
    
    // --- 이벤트 리스너 ---
    document.getElementById('start-button').addEventListener('click', runTestAPractice);
    document.getElementById('start-test-a-button').addEventListener('click', runTestAMain);
    document.getElementById('start-test-b-practice-button').addEventListener('click', runTestBPractice);
    document.getElementById('start-test-b-button').addEventListener('click', runTestBMain);

    // --- 앱 초기화 ---
    showScreen('welcome-screen');
    currentStage = 'WELCOME';
});
