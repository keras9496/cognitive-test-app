// --- 상수 설정 ---
const BOX_COLOR_DEFAULT = "#a0aec0";
const BOX_COLOR_FLASH = "#f6e05e";

// --- HTML 요소 가져오기 ---
const canvas = document.getElementById('practice-canvas');
const ctx = canvas.getContext('2d');
const messageLabel = document.getElementById('message-label');
const instructionP = document.getElementById('instruction');

// --- 게임 상태 변수 ---
let problemData = null;
let userSequence = [];
let gameState = 'loading'; // loading, memorizing, answering, processing

// --- 함수 정의 ---

/** 박스를 캔버스에 그리는 함수 */
function drawBoxes() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (!problemData || !problemData.boxes) return;

    problemData.boxes.forEach(box => {
        ctx.fillStyle = userSequence.includes(box.id) ? BOX_COLOR_FLASH : BOX_COLOR_DEFAULT;
        ctx.fillRect(box.x1, box.y1, box.x2 - box.x1, box.y2 - box.y1);
    });

    userSequence.forEach((boxId, index) => {
        const box = problemData.boxes.find(b => b.id === boxId);
        if (box) {
            ctx.fillStyle = "white";
            ctx.font = "bold 20px Helvetica";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            const centerX = box.x1 + (box.x2 - box.x1) / 2;
            const centerY = box.y1 + (box.y2 - box.y1) / 2;
            ctx.fillText(index + 1, centerX, centerY);
        }
    });
}

/** 문제의 정답 순서대로 박스를 깜빡이는 애니메이션 함수 */
function showFlashingSequence() {
    gameState = 'memorizing';
    messageLabel.textContent = "순서를 기억하세요...";
    instructionP.style.display = 'none';

    let delay = 1000;
    problemData.flash_sequence.forEach(boxId => {
        const box = problemData.boxes.find(b => b.id === boxId);
        setTimeout(() => {
            if (box) {
                ctx.fillStyle = BOX_COLOR_FLASH;
                ctx.fillRect(box.x1, box.y1, box.x2 - box.x1, box.y2 - box.y1);
            }
        }, delay);
        delay += 500;
        setTimeout(() => {
            if (box) {
                ctx.fillStyle = BOX_COLOR_DEFAULT;
                ctx.fillRect(box.x1, box.y1, box.x2 - box.x1, box.y2 - box.y1);
            }
        }, delay);
        delay += 250;
    });

    setTimeout(() => {
        gameState = 'answering';
        messageLabel.textContent = "기억한 순서대로 클릭하세요!";
    }, delay);
}

/** 사용자의 답안을 서버로 전송하는 함수 */
async function submitAnswer() {
    gameState = 'processing';
    messageLabel.textContent = "채점 중입니다...";

    try {
        const response = await fetch('/api/submit-answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ answer: userSequence })
        });
        const result = await response.json();

        if (result.status === 'correct_practice') {
            messageLabel.textContent = result.message;
            setTimeout(() => window.location.href = '/test', 2000);
        } else if (result.status === 'incorrect_practice') {
            messageLabel.textContent = result.message;
            setTimeout(() => window.location.href = '/practice', 2000);
        } else {
            messageLabel.textContent = `오류: ${result.message || '알 수 없는 오류'}`;
        }
    } catch (error) {
        messageLabel.textContent = '서버 통신에 실패했습니다.';
        console.error('Submit Practice Answer Error:', error);
    }
}

/** 캔버스 클릭 이벤트 처리 함수 */
function handleCanvasClick(event) {
    if (gameState !== 'answering') return;

    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    const clickedBox = problemData.boxes.find(box =>
        x >= box.x1 && x <= box.x2 && y >= box.y1 && y <= box.y2
    );

    if (clickedBox) {
        const boxId = clickedBox.id;
        const boxIndex = userSequence.indexOf(boxId);
        if (boxIndex > -1) {
            userSequence.splice(boxIndex, 1);
        } else {
            userSequence.push(boxId);
        }
        drawBoxes();
        if (userSequence.length === problemData.flash_count) {
            submitAnswer();
        }
    }
}

/** 페이지 로드 시, 서버에서 현재 문제를 가져와 테스트 시작 */
async function initializeTest() {
    gameState = 'loading';
    messageLabel.textContent = '연습 문제를 불러오는 중입니다...';

    try {
        const response = await fetch('/api/get-current-problem');
        if (!response.ok) throw new Error('서버에서 문제를 가져오는 데 실패했습니다.');

        problemData = await response.json();
        userSequence = [];
        drawBoxes();
        showFlashingSequence();

    } catch (error) {
        messageLabel.textContent = `오류: ${error.message}`;
        console.error(error);
    }
}

canvas.addEventListener('click', handleCanvasClick);
document.addEventListener('DOMContentLoaded', initializeTest);