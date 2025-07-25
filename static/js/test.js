// --- 상수 설정 ---
const BOX_COLOR_DEFAULT = "#a0aec0";
const BOX_COLOR_FLASH = "#f6e05e";

// --- HTML 요소 가져오기 ---
const canvas = document.getElementById('test-canvas');
const ctx = canvas.getContext('2d');
const messageLabel = document.getElementById('message-label');

// --- 게임 상태 변수 ---
let problemData = null;
let userSequence = [];
let gameState = 'loading';
let levelStartTime; // [신규] 레벨 시작 시간 기록

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
    messageLabel.textContent = `순서를 기억하세요...`;

    let delay = 1000;
    problemData.flash_sequence.forEach(boxId => {
        const box = problemData.boxes.find(b => b.id === boxId);
        setTimeout(() => { if (box) { ctx.fillStyle = BOX_COLOR_FLASH; ctx.fillRect(box.x1, box.y1, box.x2 - box.x1, box.y2 - box.y1); } }, delay);
        delay += 500;
        setTimeout(() => { if (box) { ctx.fillStyle = BOX_COLOR_DEFAULT; ctx.fillRect(box.x1, box.y1, box.x2 - box.x1, box.y2 - box.y1); } }, delay);
        delay += 250;
    });

    setTimeout(() => {
        gameState = 'answering';
        // --- [수정] 안내 문구 변경 및 줄바꿈 적용 ---
        messageLabel.innerHTML = "기억한 순서대로 클릭하세요.<br><small style='font-size: 0.7em; color: #555;'>선택을 취소하려면 같은 박스를 다시 클릭하세요.</small>";
        levelStartTime = new Date().getTime(); // [신규] 답변 시작 시간 기록
    }, delay);
}

/** 사용자의 답안을 서버로 전송하는 함수 */
async function submitAnswer() {
    gameState = 'processing';
    messageLabel.textContent = "결과를 확인 중입니다...";

    // --- [신규] 소요 시간 계산 ---
    const timeTaken = (new Date().getTime() - levelStartTime) / 1000;

    try {
        const res = await fetch('/api/submit-answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            // --- [수정] 시간 데이터 추가 전송 ---
            body: JSON.stringify({ 
                answer: userSequence,
                time_taken: parseFloat(timeTaken.toFixed(2))
            })
        });
        const result = await res.json();
        
        if (result.status === 'test_complete') {
            messageLabel.textContent = '모든 단계를 성공적으로 완료했습니다!';
            setTimeout(() => window.location.href = '/finish', 2000);
        } else if (result.status === 'game_over') {
            messageLabel.textContent = '기회를 모두 소진하여 테스트를 종료합니다.';
            setTimeout(() => window.location.href = '/finish', 2000);
        } else if (result.status === 'next_level' || result.status === 'retry') {
            messageLabel.textContent = result.correct ? "정답입니다!" : `틀렸습니다. 남은 기회: ${result.chances_left}회.`;
            setTimeout(() => window.location.href = '/intermission', 2000);
        }
        
    } catch (error) {
        messageLabel.textContent = '서버 통신에 실패했습니다.';
        console.error('Submit Answer Error:', error);
    }
}

// (이하 나머지 코드는 변경 없음)
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

async function initializeTest() {
    gameState = 'loading';
    messageLabel.textContent = '문제를 가져오는 중입니다...';
    try {
        const response = await fetch('/api/get-current-problem');
        if (!response.ok) throw new Error('서버에서 문제를 가져오는 데 실패했습니다.');
        problemData = await response.json();
        if (problemData.error) {
            messageLabel.textContent = `오류: ${problemData.error}`;
            return;
        }
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