document.addEventListener('DOMContentLoaded', function() {
    // --- 전역 상태 변수 ---
    let currentStage = '';
    let currentTest = null;
    const userResults = {
        testA_time: 0,
        testA_errors: 0,
        consonant_check_failures: 0,
        consonant_check_start_time: 0,
        consonant_check_end_time: 0,
        testB_time: 0,
        testB_errors: 0,
    };
    let consonantSequence = [...'가나다라마바사아자차카타파하'];
    let shuffledConsonants = [];
    let currentConsonantIndex = 0;
    const placedConsonants = Array(14).fill(null);
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
                circle.textContent = this.items;
                circle.dataset.value = this.items;
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
            const expectedValue = this.items;

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

    // --- 새로운 자음 순서 맞추기 로직 ---
    function setupConsonantCheck() {
        currentConsonantIndex = 0;
        placedConsonants.fill(null);
        shuffledConsonants = [...consonantSequence].sort(() => Math.random() - 0.5);

        const dragArea = document.getElementById('consonant-drag-area');
        const dropArea = document.getElementById('consonant-drop-area');
        dragArea.innerHTML = '';
        dropArea.innerHTML = '';

        shuffledConsonants.forEach(consonant => {
            const box = document.createElement('div');
            box.className = 'consonant-box flex justify-center items-center bg-white rounded-lg text-xl font-bold cursor-pointer';
            box.textContent = consonant;
            box.dataset.value = consonant;
            box.addEventListener('click', handleConsonantClick);
            dragArea.appendChild(box);
        });

        for (let i = 0; i < 14; i++) {
            const box = document.createElement('div');
            box.className = 'consonant-placeholder flex justify-center items-center bg-slate-200 rounded-lg text-xl font-bold';
            dropArea.appendChild(box);
        }

        consonantCheckStartTime = Date.now();
    }

    function handleConsonantClick(event) {
        const clickedConsonant = event.target;
        const expectedConsonant = consonantSequence.at(currentConsonantIndex);

        if (clickedConsonant.dataset.value === expectedConsonant) {
            const dropArea = document.getElementById('consonant-drop-area');
            const placeholder = dropArea.children.item(currentConsonantIndex);
            placeholder.textContent = clickedConsonant.dataset.value;
            clickedConsonant.removeEventListener('click', handleConsonantClick);
            clickedConsonant.remove();
            currentConsonantIndex++;

            if (currentConsonantIndex === consonantSequence.length) {
                const consonantCheckEndTime = Date.now();
                userResults.consonant_check_start_time = consonantCheckStartTime / 1000;
                userResults.consonant_check_end_time = consonantCheckEndTime / 1000;
                document.getElementById('start-test-b-practice-button').disabled = false;
            }
        } else {
            userResults.consonant_check_failures++;
            clickedConsonant.classList.add('incorrect');
            setTimeout(() => clickedConsonant.classList.remove('incorrect'), 500);
        }
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
        document.getElementById('start-test-b-practice-button').disabled = true;
        setupConsonantCheck();
    }

    function runTestBPractice() {
        currentStage = 'B_PRACTICE';
        showScreen('test-b-practice-screen');
        const items = [];
        for (let i = 0; i < 4; i++) {
            items.push(i + 1);
            items.push(consonantSequence); // 수정: 실제 자음 배열 대신 변수 사용
        }
        const flattenedItems = items.flat(); // 배열 평탄화
        currentTest = new TrailMakingTest('test-b-practice-area', flattenedItems, () => {
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
            items.push(consonantSequence); // 수정: 실제 자음 배열 대신 변수 사용
        }
        const flattenedItems = items.flat(); // 배열 평탄화
        currentTest = new TrailMakingTest('test-b-main-area', flattenedItems, (duration, errors) => {
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

    // Test B 연습 시작 버튼에 대한 이벤트 리스너는 consonant check 완료 후 활성화됩니다.
    document.getElementById('start-test-b-practice-button').addEventListener('click', runTestBPractice);
    document.getElementById('start-test-b-button').addEventListener('click', runTestBMain);

    // --- 앱 초기화 ---
    showScreen('welcome-screen');
    currentStage = 'WELCOME';
});