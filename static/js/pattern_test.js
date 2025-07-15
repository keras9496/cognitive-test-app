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
const attemptsEl = document.getElementById('attempts');
const answerButtons = document.getElementById('answer-buttons');

const levelSelectionDiv = document.getElementById('level-selection');
const gameContainerDiv = document.getElementById('game-container');
const levelButtons = document.querySelectorAll('.levelBtn');
const backToMenuBtn = document.getElementById('backToMenuBtn');
const subHeader = document.getElementById('sub-header');
const finishTestBtn = document.getElementById('finish-test-btn');

const COLORS = ['#ef4444', '#3b82f6', '#22c55e', '#f97316', '#8b5cf6']; // Red, Blue, Green, Orange, Violet
const BOX_SIZE = 22;
const STROKE_COLOR = '#4b5563';

const ALL_SHAPES = [
    { coords: [[1,0], [0,1], [1,1], [2,1], [1,2]] }, { coords: [[0,0], [0,1], [0,2], [1,2], [2,2]] }, { coords: [[0,0], [1,0], [0,1], [1,1], [0,2]] }, { coords: [[0,0], [1,0], [2,0], [0,1], [2,1]] }, { coords: [[0,0], [0,1], [1,1], [1,2], [2,2]] },
    { coords: [[0,0], [0,1], [0,2], [1,2], [2,2], [2,1]]}, { coords: [[0,0], [1,0], [2,0], [0,1], [1,1], [2,1]]}, { coords: [[0,0], [1,0], [2,0], [3,0], [0,1], [1,1]]}, { coords: [[1,0], [0,1], [1,1], [2,1], [0,2], [1,2]]}, { coords: [[0,1], [1,1], [2,1], [0,0], [2,0], [1,2]]},
    { coords: [[0,0], [1,0], [2,0], [0,1], [2,1], [0,2], [2,2]]}, { coords: [[1,0], [0,1], [1,1], [2,1], [1,2], [0,3], [2,3]]}, { coords: [[0,0], [1,0], [2,0], [3,0], [0,1], [0,2], [0,3]]}, { coords: [[1,0], [0,1], [1,1], [2,1], [3,1], [1,2], [1,3]]}, { coords: [[0,0], [1,0], [2,0], [1,1], [1,2], [1,3], [1,4]]}
];

const LEVEL_CONFIG = {
    1: { boxCount: 5, colorCount: 3 },
    2: { boxCount: 6, colorCount: 4 },
    3: { boxCount: 7, colorCount: 5 }
};

let currentLevel, currentShape, originalColorPattern, testColorPattern, correctAnswer;
let score = 0;
let attempts = 0;
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

function isAllSameColor(pattern) {
    if (pattern.length < 2) return true;
    return pattern.every(color => color === pattern[0]);
}

function generateValidColorPattern(length, colorCount) {
    let pattern;
    do {
        pattern = Array.from({ length }, () => getRandomInt(0, colorCount - 1));
    } while (isAllSameColor(pattern) && colorCount > 1); // 단일 색상만 가능한 경우는 무한 루프 방지
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
    try {
        feedbackEl.textContent = '';
        feedbackEl.className = '';
        nextBtn.classList.add('hidden');
        answerButtons.classList.remove('hidden');
        sameBtn.disabled = false;
        differentBtn.disabled = false;

        const config = LEVEL_CONFIG[currentLevel];
        // availableShapes 배열이 비어있는지 다시 한번 확인
        if (!availableShapes || availableShapes.length === 0) {
            throw new Error(`레벨 ${currentLevel}에 사용할 수 있는 도형이 없습니다.`);
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
            } while (JSON.stringify(testColorPattern) === JSON.stringify(originalColorPattern));
            correctAnswer = 'different';
        }

        const rotationAngle = getRandomInt(20, 310);
        drawShape(originalCtx, currentShape, originalColorPattern, 0);
        drawShape(testCtx, currentShape, testColorPattern, rotationAngle);

        questionStartTime = new Date().getTime();
    } catch (error) {
        console.error("문제 생성 중 오류 발생:", error);
        feedbackEl.textContent = '문제를 불러오는 중 오류가 발생했습니다. 새로고침 후 다시 시도해주세요.';
        feedbackEl.className = 'text-red-500';
        answerButtons.classList.add('hidden'); // 오류 시 버튼 숨김
    }
}

function checkAnswer(userAnswer) {
    const endTime = new Date().getTime();
    const timeTaken = (endTime - questionStartTime) / 1000;
    answerTimes.push(timeTaken);

    sameBtn.disabled = true;
    differentBtn.disabled = true;
    attempts++;
    let isCorrect = userAnswer === correctAnswer;
    if (isCorrect) {
        score++;
        feedbackEl.textContent = '정답입니다!';
        feedbackEl.className = 'text-green-500';
    } else {
        feedbackEl.textContent = '오답입니다!';
        feedbackEl.className = 'text-red-500';
    }
    scoreEl.textContent = score;
    attemptsEl.textContent = attempts;
    answerButtons.classList.add('hidden');
    nextBtn.classList.remove('hidden');
}

function startGame(level) {
    currentLevel = level;
    const config = LEVEL_CONFIG[level];
    
    // 도형 필터링 로직
    availableShapes = ALL_SHAPES.filter(shape => shape.coords.length === config.boxCount);

    // **[오류 방지]** 필터링 후 도형이 없는 경우를 확인하고 오류 메시지를 표시합니다.
    if (!availableShapes || availableShapes.length === 0) {
        alert(`오류: 레벨 ${level}에 해당하는 도형 데이터를 찾을 수 없습니다. 스크립트를 확인해주세요.`);
        return; 
    }

    score = 0;
    attempts = 0;
    answerTimes = [];
    scoreEl.textContent = score;
    attemptsEl.textContent = attempts;

    levelSelectionDiv.classList.add('hidden');
    gameContainerDiv.classList.remove('hidden');
    subHeader.textContent = `두 도형의 색상 패턴이 같은지 다른지 맞춰보세요. (레벨 ${level})`;

    generateNewQuestion();
}

async function backToMenu() {
    if (attempts > 0) {
        const resultData = {
            level: currentLevel,
            score: score,
            attempts: attempts,
            times: answerTimes
        };

        try {
            await fetch('/api/submit-pattern-result', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(resultData)
            });
        } catch (error) {
            console.error('결과 저장 중 서버 통신 오류:', error);
        }
    }

    gameContainerDiv.classList.add('hidden');
    levelSelectionDiv.classList.remove('hidden');
    subHeader.textContent = '도전할 레벨을 선택해주세요.';
}

function finishTest() {
    alert("모든 테스트가 종료되었습니다. 수고하셨습니다!");
    window.location.href = "/";
}

// --- 이벤트 리스너 설정 ---
sameBtn.addEventListener('click', () => checkAnswer('same'));
differentBtn.addEventListener('click', () => checkAnswer('different'));
nextBtn.addEventListener('click', generateNewQuestion);
backToMenuBtn.addEventListener('click', backToMenu);
finishTestBtn.addEventListener('click', finishTest);

levelButtons.forEach(button => {
    button.addEventListener('click', () => {
        const level = parseInt(button.dataset.level);
        startGame(level);
    });
});