// --- DOM 요소 선택 ---
const gameBoard = document.getElementById('game-board');
const startBtn = document.getElementById('start-btn');
const statusMessage = document.getElementById('status-message');
const timerDisplay = document.getElementById('timer');

// --- 게임 설정 (변경 없음) ---
const SYMBOLS = [
    { id: 'star', svg: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M12,17.27L18.18,21L17,14.64L22,9.24L14.81,8.62L12,2L9.19,8.62L2,9.24L7,14.64L5.82,21L12,17.27Z"/></svg>' },
    { id: 'circle', svg: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z"/></svg>' },
    { id: 'square', svg: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M3,3V21H21V3H3Z"/></svg>' },
    { id: 'triangle', svg: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M1,21H23L12,2L1,21Z"/></svg>' },
    { id: 'heart', svg: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M12,21.35L10.55,20.03C5.4,15.36 2,12.27 2,8.5C2,5.41 4.42,3 7.5,3C9.24,3 10.91,3.81 12,5.08C13.09,3.81 14.76,3 16.5,3C19.58,3 22,5.41 22,8.5C22,12.27 18.6,15.36 13.45,20.03L12,21.35Z"/></svg>' },
    { id: 'cross', svg: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z"/></svg>' }
];
const LEVELS = [
    { name: '연습', pairs: 2, revealTime: 3 },
    { name: '1차 검사', pairs: 3, revealTime: 3 },
    { name: '2차 검사', pairs: 6, revealTime: 5 }
];

// --- 게임 상태 변수 ---
let currentLevelIndex = 0;
let cards = [];
let flippedCards = [];
let matchedPairs = 0;
let lockBoard = false;
let timerInterval;
let gameResults = [];
let levelStartTime; // [신규] 레벨 시작 시간 기록

// --- 이벤트 리스너 ---
startBtn.addEventListener('click', handleStart);

// --- 게임 로직 함수 ---

function handleStart() {
    if (currentLevelIndex >= LEVELS.length) {
        finishGameAndSubmit();
        return;
    }
    startBtn.disabled = true;
    setupLevel(currentLevelIndex);
}

function setupLevel(levelIndex) {
    const level = LEVELS[levelIndex];
    matchedPairs = 0;
    flippedCards = [];
    lockBoard = true;

    statusMessage.textContent = `${level.name}: 잠시 후 카드가 뒤집힙니다.`;
    startBtn.textContent = `${level.name} 진행 중...`;

    gameBoard.className = `level-${levelIndex}`;

    const shuffledSymbols = [...SYMBOLS].sort(() => 0.5 - Math.random());
    const levelSymbols = shuffledSymbols.slice(0, level.pairs);
    
    let cardData = [...levelSymbols, ...levelSymbols];
    cardData.sort(() => 0.5 - Math.random());
    
    gameResults[levelIndex] = {
        level: level.name,
        pairs: level.pairs,
        correct_card_pairs: {},
        user_click_sequence: [],
        time_taken: null // [신규] 시간 필드 추가
    };
    
    gameBoard.innerHTML = '';
    cards = cardData.map((symbolData, index) => {
        if (!gameResults[levelIndex].correct_card_pairs[symbolData.id]) {
            gameResults[levelIndex].correct_card_pairs[symbolData.id] = [];
        }
        gameResults[levelIndex].correct_card_pairs[symbolData.id].push(index);

        return createCardElement(symbolData, index);
    });
    cards.forEach(card => gameBoard.appendChild(card));

    let countdown = level.revealTime;
    timerDisplay.textContent = `카드 기억 시간: ${countdown}초`;
    timerInterval = setInterval(() => {
        countdown--;
        timerDisplay.textContent = `카드 기억 시간: ${countdown}초`;
        if (countdown <= 0) {
            clearInterval(timerInterval);
            timerDisplay.textContent = '';
            hideCards();
        }
    }, 1000);
}

function createCardElement(symbolData, index) {
    const card = document.createElement('div');
    card.classList.add('card');
    card.dataset.symbolId = symbolData.id;
    card.dataset.cardIndex = index;
    card.innerHTML = `<div class="card-inner"><div class="card-face card-front"></div><div class="card-face card-back">${symbolData.svg}</div></div>`;
    card.classList.add('flipped');
    card.addEventListener('click', () => handleCardClick(card));
    return card;
}

function hideCards() {
    cards.forEach(card => card.classList.remove('flipped'));
    lockBoard = false;
    statusMessage.textContent = `${LEVELS[currentLevelIndex].name}: 같은 그림의 카드를 찾으세요.`;
    levelStartTime = new Date().getTime(); // [신규] 답변 시작 시간 기록
}

function handleCardClick(card) {
    if (lockBoard || card.classList.contains('flipped') || card.classList.contains('matched')) {
        return;
    }
    
    gameResults[currentLevelIndex].user_click_sequence.push(parseInt(card.dataset.cardIndex));
    card.classList.add('flipped');
    flippedCards.push(card);

    if (flippedCards.length === 2) {
        lockBoard = true;
        checkForMatch();
    }
}

function checkForMatch() {
    const [card1, card2] = flippedCards;
    const isMatch = card1.dataset.symbolId === card2.dataset.symbolId;
    isMatch ? disableMatchedCards() : unflipMismatchedCards();
}

function disableMatchedCards() {
    flippedCards.forEach(card => card.classList.add('matched'));
    matchedPairs++;
    resetTurn();
    if (matchedPairs === LEVELS[currentLevelIndex].pairs) {
        setTimeout(completeLevel, 1000);
    }
}

function unflipMismatchedCards() {
    setTimeout(() => {
        flippedCards.forEach(card => card.classList.remove('flipped'));
        resetTurn();
    }, 1200);
}

function resetTurn() {
    flippedCards = [];
    lockBoard = false;
}

function completeLevel() {
    // --- [신규] 레벨 완료 시 시간 계산 및 저장 ---
    const timeTaken = (new Date().getTime() - levelStartTime) / 1000;
    gameResults[currentLevelIndex].time_taken = parseFloat(timeTaken.toFixed(2));

    statusMessage.textContent = `${LEVELS[currentLevelIndex].name} 성공!`;
    currentLevelIndex++;
    startBtn.textContent = (currentLevelIndex < LEVELS.length) ? '다음 단계로' : '결과 저장 및 종료';
    startBtn.disabled = false;
}

async function finishGameAndSubmit() {
    statusMessage.textContent = '모든 검사가 완료되었습니다. 결과를 서버로 전송합니다...';
    startBtn.disabled = true;

    try {
        const response = await fetch('/api/submit-card-result', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(gameResults)
        });

        if (!response.ok) {
            throw new Error('서버 응답 오류');
        }

        const result = await response.json();
        statusMessage.textContent = '결과가 성공적으로 저장되었습니다!';
        
        setTimeout(() => {
            window.location.href = '/finish';
        }, 2000);

    } catch (error) {
        console.error('결과 전송 실패:', error);
        statusMessage.textContent = '결과 저장에 실패했습니다. 다시 시도해주세요.';
        startBtn.disabled = false;
    }
}