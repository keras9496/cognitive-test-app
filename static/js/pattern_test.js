// --- 전역 변수 및 상수 설정 ---
// DOM 요소 안전하게 가져오기
function getRequiredElement(id) {
    const element = document.getElementById(id);
    if (!element) {
        throw new Error(`필수 요소를 찾을 수 없습니다: ${id}`);
    }
    return element;
}

// 초기화 함수
function initializeElements() {
    try {
        const originalCanvas = getRequiredElement('originalCanvas');
        const testCanvas = getRequiredElement('testCanvas');
        const originalCtx = originalCanvas.getContext('2d');
        const testCtx = testCanvas.getContext('2d');

        if (!originalCtx || !testCtx) {
            throw new Error('Canvas 컨텍스트를 가져올 수 없습니다.');
        }

        const sameBtn = getRequiredElement('sameBtn');
        const differentBtn = getRequiredElement('differentBtn');
        const nextBtn = getRequiredElement('nextBtn');
        const feedbackEl = getRequiredElement('feedback');
        const scoreEl = getRequiredElement('score');
        const attemptsEl = getRequiredElement('attempts');
        const answerButtons = getRequiredElement('answer-buttons');
        const subHeader = getRequiredElement('sub-header');
        const finishTestEarlyBtn = getRequiredElement('finish-test-early-btn');

        return {
            originalCanvas,
            testCanvas,
            originalCtx,
            testCtx,
            sameBtn,
            differentBtn,
            nextBtn,
            feedbackEl,
            scoreEl,
            attemptsEl,
            answerButtons,
            subHeader,
            finishTestEarlyBtn
        };
    } catch (error) {
        console.error('요소 초기화 실패:', error);
        document.body.innerHTML = `
            <div class="text-center p-10">
                <h2 class="text-2xl font-bold text-red-600 mb-4">오류 발생</h2>
                <p class="text-lg text-gray-700">페이지를 다시 로드해주세요.</p>
                <p class="text-sm text-gray-500 mt-4">오류: ${error.message}</p>
            </div>
        `;
        throw error;
    }
}

const COLORS = ['#ef4444', '#3b82f6', '#22c55e', '#f97316', '#8b5cf6'];
const BOX_SIZE = 22;
const STROKE_COLOR = '#4b5563';

// 각기 다른 박스 개수를 가진 도형 세트
const ALL_SHAPES = [
    // 5개 박스
    { coords: [[1,0], [0,1], [1,1], [2,1], [1,2]] }, 
    { coords: [[0,0], [0,1], [0,2], [1,2], [2,2]] }, 
    { coords: [[0,0], [1,0], [0,1], [1,1], [0,2]] }, 
    { coords: [[0,0], [1,0], [2,0], [0,1], [2,1]] }, 
    { coords: [[0,0], [0,1], [1,1], [1,2], [2,2]] },
    // 6개 박스
    { coords: [[0,0], [0,1], [0,2], [1,2], [2,2], [2,1]]}, 
    { coords: [[0,0], [1,0], [2,0], [0,1], [1,1], [2,1]]}, 
    { coords: [[0,0], [1,0], [2,0], [3,0], [0,1], [1,1]]}, 
    { coords: [[1,0], [0,1], [1,1], [2,1], [0,2], [1,2]]}, 
    { coords: [[0,1], [1,1], [2,1], [0,0], [2,0], [1,2]]},
    // 7개 박스
    { coords: [[0,0], [1,0], [2,0], [0,1], [2,1], [0,2], [2,2]]}, 
    { coords: [[1,0], [0,1], [1,1], [2,1], [1,2], [0,3], [2,3]]}, 
    { coords: [[0,0], [1,0], [2,0], [3,0], [0,1], [0,2], [0,3]]}, 
    { coords: [[1,0], [0,1], [1,1], [2,1], [3,1], [1,2], [1,3]]}, 
    { coords: [[0,0], [1,0], [2,0], [1,1], [1,2], [1,3], [1,4]]}
];

// 레벨별 설정
const LEVEL_CONFIG = {
    1: { boxCount: 5, colorCount: 3, totalProblems: 3 },
    2: { boxCount: 6, colorCount: 4, totalProblems: 3 },
    3: { boxCount: 7, colorCount: 5, totalProblems: 3 }
};
const MAX_LEVEL = Object.keys(LEVEL_CONFIG).length;

// 전역 변수들
let elements = {};
let currentLevel = 1;
let problemInLevel = 1;
let currentShape, originalColorPattern, testColorPattern, correctAnswer;
let levelScore = 0;
let answerTimes = [];
let questionStartTime;
let availableShapes = [];

// --- 핵심 로직 함수 ---
function getRandomInt(min, max) { 
    return Math.floor(Math.random() * (max - min + 1)) + min; 
}

function shuffleArray(array) {
    const newArray = [...array];
    for (let i = newArray.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [newArray[i], newArray[j]] = [newArray[j], newArray[i]];
    }
    return newArray;
}

// 모든 색이 동일한 패턴이 생성되지 않도록 방지
function generateValidColorPattern(length, colorCount) {
    let pattern;
    if (colorCount > 1) {
        do {
            pattern = Array.from({ length }, () => getRandomInt(0, colorCount - 1));
        } while (pattern.every(color => color === pattern[0]));
    } else {
        pattern = Array.from({ length }, () => 0);
    }
    return pattern;
}

function drawShape(ctx, shape, colorPattern, rotation) {
    try {
        const canvas = ctx.canvas;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.save();
        
        const coords = shape.coords;
        let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
        
        coords.forEach(([x, y]) => {
            minX = Math.min(minX, x); 
            maxX = Math.max(maxX, x);
            minY = Math.min(minY, y); 
            maxY = Math.max(maxY, y);
        });
        
        const shapeWidth = (maxX - minX + 1) * BOX_SIZE;
        const shapeHeight = (maxY - minY + 1) * BOX_SIZE;
        const centerX = minX * BOX_SIZE + shapeWidth / 2;
        const centerY = minY * BOX_SIZE + shapeHeight / 2;
        
        ctx.translate(canvas.width / 2, canvas.height / 2);
        ctx.rotate(rotation * Math.PI / 180);
        ctx.translate(-centerX, -centerY);
        
        coords.forEach((pos, index) => {
            const [x, y] = pos;
            ctx.fillStyle = COLORS[colorPattern[index]];
            ctx.strokeStyle = STROKE_COLOR;
            ctx.lineWidth = 2;
            ctx.fillRect(x * BOX_SIZE, y * BOX_SIZE, BOX_SIZE, BOX_SIZE);
            ctx.strokeRect(x * BOX_SIZE, y * BOX_SIZE, BOX_SIZE, BOX_SIZE);
        });
        
        ctx.restore();
    } catch (error) {
        console.error('도형 그리기 오류:', error);
        elements.feedbackEl.textContent = '도형을 그릴 수 없습니다.';
        elements.feedbackEl.className = 'text-red-500';
    }
}

function generateNewQuestion() {
    try {
        elements.feedbackEl.textContent = '';
        elements.feedbackEl.className = '';
        elements.nextBtn.classList.add('hidden');
        elements.answerButtons.classList.remove('hidden');
        elements.sameBtn.disabled = false;
        elements.differentBtn.disabled = false;

        const config = LEVEL_CONFIG[currentLevel];
        
        // 현재 문제 번호 업데이트
        elements.attemptsEl.textContent = `${problemInLevel} / ${config.totalProblems}`;
        elements.scoreEl.textContent = levelScore;

        // 레벨에 맞는 도형 필터링
        availableShapes = ALL_SHAPES.filter(shape => shape.coords.length === config.boxCount);
        if (!availableShapes || availableShapes.length === 0) {
            throw new Error(`레벨 ${currentLevel}에 해당하는 도형이 없습니다.`);
        }
        
        currentShape = availableShapes[getRandomInt(0, availableShapes.length - 1)];
        originalColorPattern = generateValidColorPattern(config.boxCount, config.colorCount);

        const isSameProblem = Math.random() < 0.5;
        if (isSameProblem) {
            testColorPattern = [...originalColorPattern];
            correctAnswer = 'same';
        } else {
            do {
                testColorPattern = shuffleArray(originalColorPattern);
            } while (JSON.stringify(testColorPattern) === JSON.stringify(originalColorPattern) && config.colorCount > 1);
            correctAnswer = 'different';
        }

        const rotationAngle = getRandomInt(20, 310);
        drawShape(elements.originalCtx, currentShape, originalColorPattern, 0);
        drawShape(elements.testCtx, currentShape, testColorPattern, rotationAngle);

        questionStartTime = new Date().getTime();
    } catch (error) {
        console.error('문제 생성 오류:', error);
        elements.feedbackEl.textContent = '문제를 생성할 수 없습니다. 페이지를 새로고침해주세요.';
        elements.feedbackEl.className = 'text-red-500';
    }
}

function checkAnswer(userAnswer) {
    try {
        const endTime = new Date().getTime();
        const timeTaken = (endTime - questionStartTime) / 1000;
        answerTimes.push(parseFloat(timeTaken.toFixed(2)));

        elements.sameBtn.disabled = true;
        elements.differentBtn.disabled = true;
        
        let isCorrect = userAnswer === correctAnswer;
        if (isCorrect) {
            levelScore++;
            elements.feedbackEl.textContent = '정답입니다!';
            elements.feedbackEl.className = 'text-green-500';
        } else {
            elements.feedbackEl.textContent = '오답입니다.';
            elements.feedbackEl.className = 'text-red-500';
        }
        elements.scoreEl.textContent = levelScore;
        
        elements.answerButtons.classList.add('hidden');
        elements.nextBtn.classList.remove('hidden');
    } catch (error) {
        console.error('답안 확인 오류:', error);
        elements.feedbackEl.textContent = '답안 처리 중 오류가 발생했습니다.';
        elements.feedbackEl.className = 'text-red-500';
    }
}

// API 요청 함수 (타임아웃 및 재시도 로직 추가)
async function submitLevelResultsAndProceed() {
    const resultData = {
        level: currentLevel,
        score: levelScore,
        total_problems: LEVEL_CONFIG[currentLevel].totalProblems,
        times: answerTimes
    };

    const maxRetries = 3;
    let attempt = 0;

    while (attempt < maxRetries) {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000); // 10초 타임아웃

            const response = await fetch('/api/submit-pattern-result', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(resultData),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            console.log(`레벨 ${currentLevel} 결과 저장 성공`);
            
            // 다음 단계로 진행
            currentLevel++;
            if (currentLevel > MAX_LEVEL) {
                finishAllTests();
            } else {
                startLevel(currentLevel);
            }
            return;

        } catch (error) {
            attempt++;
            console.error(`결과 저장 시도 ${attempt}/${maxRetries} 실패:`, error);
            
            if (attempt >= maxRetries) {
                elements.feedbackEl.textContent = '결과 저장에 실패했습니다. 인터넷 연결을 확인해주세요.';
                elements.feedbackEl.className = 'text-red-500';
                // 실패 시에도 계속 진행할 수 있도록 버튼 표시
                elements.nextBtn.textContent = "다음 레벨로 (결과 저장 실패)";
                elements.nextBtn.classList.remove('hidden');
                return;
            }
            
            // 재시도 전 잠시 대기
            await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
        }
    }
}

function startLevel(level) {
    try {
        currentLevel = level;
        problemInLevel = 1;
        levelScore = 0;
        answerTimes = [];

        elements.subHeader.textContent = `레벨 ${level} - 두 도형의 색상 패턴이 같은지 다른지 맞춰보세요.`;
        
        generateNewQuestion();
    } catch (error) {
        console.error('레벨 시작 오류:', error);
        elements.feedbackEl.textContent = '레벨을 시작할 수 없습니다.';
        elements.feedbackEl.className = 'text-red-500';
    }
}

function finishAllTests() {
    try {
        const gameContainer = document.getElementById('game-container');
        if (gameContainer) {
            gameContainer.innerHTML = `
                <div class="text-center p-10">
                    <h2 class="text-3xl font-bold text-blue-600 mb-4">모든 검사가 완료되었습니다.</h2>
                    <p class="text-xl text-gray-700">수고하셨습니다. 결과가 모두 저장되었습니다.</p>
                    <p class="text-lg text-gray-500 mt-8">잠시 후 첫 화면으로 돌아갑니다.</p>
                </div>
            `;
            
            setTimeout(() => {
                window.location.href = "/";
            }, 4000);
        }
    } catch (error) {
        console.error('테스트 완료 처리 오류:', error);
    }
}

// 이벤트 리스너 설정 함수
function setupEventListeners() {
    elements.sameBtn.addEventListener('click', () => checkAnswer('same'));
    elements.differentBtn.addEventListener('click', () => checkAnswer('different'));

    elements.nextBtn.addEventListener('click', () => {
        problemInLevel++;
        const config = LEVEL_CONFIG[currentLevel];

        if (problemInLevel > config.totalProblems) {
            // 레벨 종료, 결과 전송
            elements.feedbackEl.textContent = `레벨 ${currentLevel} 종료. 결과를 저장합니다...`;
            elements.nextBtn.classList.add('hidden');
            submitLevelResultsAndProceed();
        } else {
            // 다음 문제 진행
            generateNewQuestion();
        }
    });

    // 사용자가 중간에 테스트를 종료하고 싶을 때
    elements.finishTestEarlyBtn.addEventListener('click', async () => {
        const confirmExit = confirm("테스트를 중단하시겠습니까? 현재 레벨까지의 진행 상황이 저장됩니다.");
        if (confirmExit) {
            // 진행 중인 문제가 있으면 현재 레벨 결과 저장
            if (answerTimes.length > 0) {
                await submitLevelResultsAndProceed();
            } else {
                // 모든 테스트 종료 처리
                finishAllTests();
            }
        }
    });
}

// 페이지 언로드 시 정리
function cleanup() {
    // 필요한 경우 여기에 정리 코드 추가
}

// 초기화 함수
function initialize() {
    try {
        elements = initializeElements();
        setupEventListeners();
        
        // 페이지 언로드 시 정리
        window.addEventListener('beforeunload', cleanup);
        
        // 레벨 1 시작
        startLevel(1);
    } catch (error) {
        console.error('초기화 실패:', error);
    }
}

// 페이지가 로드되면 초기화
document.addEventListener('DOMContentLoaded', initialize);