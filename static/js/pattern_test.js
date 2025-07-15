// --- 전역 변수 및 상수 설정 ---
const originalCanvas = document.getElementById('originalCanvas');
const testCanvas = document.getElementById('testCanvas');
const originalCtx = originalCanvas.getContext('2d');
const testCtx = testCanvas.getContext('2d');

const sameBtn = document.getElementById('sameBtn');
const differentBtn = document.getElementById('differentBtn');
const nextBtn = document.getElementById('nextBtn');
const feedbackEl = document.getElementById('feedback');
const scoreEl = document.getElementById('score');
const attemptsEl = document.getElementById('attempts'); // 이 요소는 이제 '문제 번호'를 표시하는 데 사용됩니다.
const answerButtons = document.getElementById('answer-buttons');
const subHeader = document.getElementById('sub-header');
const finishTestEarlyBtn = document.getElementById('finish-test-early-btn'); // 조기 종료 버튼

const COLORS = ['#ef4444', '#3b82f6', '#22c55e', '#f97316', '#8b5cf6']; // Red, Blue, Green, Orange, Violet
const BOX_SIZE = 22;
const STROKE_COLOR = '#4b5563';

// 각기 다른 박스 개수를 가진 도형 세트
const ALL_SHAPES = [
    // 5개 박스
    { coords: [[1,0], [0,1], [1,1], [2,1], [1,2]] }, { coords: [[0,0], [0,1], [0,2], [1,2], [2,2]] }, { coords: [[0,0], [1,0], [0,1], [1,1], [0,2]] }, { coords: [[0,0], [1,0], [2,0], [0,1], [2,1]] }, { coords: [[0,0], [0,1], [1,1], [1,2], [2,2]] },
    // 6개 박스
    { coords: [[0,0], [0,1], [0,2], [1,2], [2,2], [2,1]]}, { coords: [[0,0], [1,0], [2,0], [0,1], [1,1], [2,1]]}, { coords: [[0,0], [1,0], [2,0], [3,0], [0,1], [1,1]]}, { coords: [[1,0], [0,1], [1,1], [2,1], [0,2], [1,2]]}, { coords: [[0,1], [1,1], [2,1], [0,0], [2,0], [1,2]]},
    // 7개 박스
    { coords: [[0,0], [1,0], [2,0], [0,1], [2,1], [0,2], [2,2]]}, { coords: [[1,0], [0,1], [1,1], [2,1], [1,2], [0,3], [2,3]]}, { coords: [[0,0], [1,0], [2,0], [3,0], [0,1], [0,2], [0,3]]}, { coords: [[1,0], [0,1], [1,1], [2,1], [3,1], [1,2], [1,3]]}, { coords: [[0,0], [1,0], [2,0], [1,1], [1,2], [1,3], [1,4]]}
];

// 레벨별 설정
const LEVEL_CONFIG = {
    1: { boxCount: 5, colorCount: 3, totalProblems: 3 },
    2: { boxCount: 6, colorCount: 4, totalProblems: 3 },
    3: { boxCount: 7, colorCount: 5, totalProblems: 3 }
};
const MAX_LEVEL = Object.keys(LEVEL_CONFIG).length;

// 게임 상태 변수
let currentLevel = 1;
let problemInLevel = 1;
let currentShape, originalColorPattern, testColorPattern, correctAnswer;
let levelScore = 0;
let answerTimes = [];
let questionStartTime;
let availableShapes = [];


// --- 핵심 로직 함수 ---

function getRandomInt(min, max) { return Math.floor(Math.random() * (max - min + 1)) + min; }

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
    // 색상 종류가 1개 이상일 때만 유효성 검사
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
    const canvas = ctx.canvas;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.save();
    const coords = shape.coords;
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    coords.forEach(([x, y]) => {
        minX = Math.min(minX, x); maxX = Math.max(maxX, x);
        minY = Math.min(minY, y); maxY = Math.max(maxY, y);
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
}

function generateNewQuestion() {
    feedbackEl.textContent = '';
    feedbackEl.className = '';
    nextBtn.classList.add('hidden');
    answerButtons.classList.remove('hidden');
    sameBtn.disabled = false;
    differentBtn.disabled = false;

    const config = LEVEL_CONFIG[currentLevel];
    
    // 현재 문제 번호 업데이트
    attemptsEl.textContent = `${problemInLevel} / ${config.totalProblems}`;
    scoreEl.textContent = levelScore;

    // 레벨에 맞는 도형 필터링
    availableShapes = ALL_SHAPES.filter(shape => shape.coords.length === config.boxCount);
    if (!availableShapes || availableShapes.length === 0) {
        console.error(`레벨 ${currentLevel}에 해당하는 도형이 없습니다.`);
        feedbackEl.textContent = '오류: 문제를 불러올 수 없습니다. 관리자에게 문의하세요.';
        return;
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
    drawShape(originalCtx, currentShape, originalColorPattern, 0);
    drawShape(testCtx, currentShape, testColorPattern, rotationAngle);

    questionStartTime = new Date().getTime();
}

function checkAnswer(userAnswer) {
    const endTime = new Date().getTime();
    const timeTaken = (endTime - questionStartTime) / 1000;
    answerTimes.push(parseFloat(timeTaken.toFixed(2)));

    sameBtn.disabled = true;
    differentBtn.disabled = true;
    
    let isCorrect = userAnswer === correctAnswer;
    if (isCorrect) {
        levelScore++;
        feedbackEl.textContent = '정답입니다!';
        feedbackEl.className = 'text-green-500';
    } else {
        feedbackEl.textContent = '오답입니다.';
        feedbackEl.className = 'text-red-500';
    }
    scoreEl.textContent = levelScore;
    
    answerButtons.classList.add('hidden');
    nextBtn.classList.remove('hidden');
}

async function submitLevelResultsAndProceed() {
    const resultData = {
        level: currentLevel,
        score: levelScore,
        total_problems: LEVEL_CONFIG[currentLevel].totalProblems,
        times: answerTimes
    };

    try {
        const response = await fetch('/api/submit-pattern-result', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(resultData)
        });
        if (!response.ok) {
            throw new Error('서버에 결과 저장 실패');
        }
        console.log(`레벨 ${currentLevel} 결과 저장 성공`);

        // 다음 단계로 진행
        currentLevel++;
        if (currentLevel > MAX_LEVEL) {
            finishAllTests();
        } else {
            startLevel(currentLevel);
        }

    } catch (error) {
        console.error('결과 저장 중 오류:', error);
        feedbackEl.textContent = '결과 저장에 실패했습니다. 인터넷 연결을 확인해주세요.';
        // 실패 시에도 다음 레벨로 넘어갈 수 있도록 버튼을 보여줄 수 있음 (선택적)
        // nextBtn.textContent = "다음 레벨로";
        // nextBtn.classList.remove('hidden');
    }
}

function startLevel(level) {
    currentLevel = level;
    problemInLevel = 1;
    levelScore = 0;
    answerTimes = [];

    subHeader.textContent = `레벨 ${level} - 두 도형의 색상 패턴이 같은지 다른지 맞춰보세요.`;
    
    generateNewQuestion();
}

function finishAllTests() {
    document.getElementById('game-container').innerHTML = `
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


// --- 이벤트 리스너 설정 ---
sameBtn.addEventListener('click', () => checkAnswer('same'));
differentBtn.addEventListener('click', () => checkAnswer('different'));

nextBtn.addEventListener('click', () => {
    problemInLevel++;
    const config = LEVEL_CONFIG[currentLevel];

    if (problemInLevel > config.totalProblems) {
        // 레벨 종료, 결과 전송
        feedbackEl.textContent = `레벨 ${currentLevel} 종료. 결과를 저장합니다...`;
        nextBtn.classList.add('hidden');
        submitLevelResultsAndProceed();
    } else {
        // 다음 문제 진행
        generateNewQuestion();
    }
});

// 사용자가 중간에 테스트를 종료하고 싶을 때
finishTestEarlyBtn.addEventListener('click', async () => {
    const confirmExit = confirm("테스트를 중단하시겠습니까? 현재 레벨까지의 진행 상황이 저장됩니다.");
    if (confirmExit) {
        // 진행 중인 문제가 있으면 현재 레벨 결과 저장
        if (answerTimes.length > 0) {
            await submitLevelResultsAndProceed();
        }
        // 모든 테스트 종료 처리
        finishAllTests();
    }
});


// 페이지가 로드되면 바로 레벨 1 시작
document.addEventListener('DOMContentLoaded', () => {
    startLevel(1);
});
