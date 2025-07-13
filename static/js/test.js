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
let gameState = 'loading'; // loading, memorizing, answering, processing

// --- 함수 정의 ---

/** 박스를 캔버스에 그리는 함수 */
function drawBoxes() {
    ctx.clearRect(0, 0, canvas.width, canvas.height); // 캔버스 초기화
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
    
    let delay = 1000; // 첫 깜빡임 시작 전 1초 대기
    problemData.flash_sequence.forEach(boxId => {
        const box = problemData.boxes.find(b => b.id === boxId);
        
        // 노란색으로 변경
        setTimeout(() => {
            if (box) {
                ctx.fillStyle = BOX_COLOR_FLASH;
                ctx.fillRect(box.x1, box.y1, box.x2 - box.x1, box.y2 - box.y1);
            }
        }, delay);

        delay += 500; // 0.5초 동안 보여줌

        // 원래 색으로 복귀
        setTimeout(() => {
            if (box) {
                ctx.fillStyle = BOX_COLOR_DEFAULT;
                ctx.fillRect(box.x1, box.y1, box.x2 - box.x1, box.y2 - box.y1);
            }
        }, delay);
        
        delay += 250; // 깜빡임 사이 0.25초 간격
    });

    // 모든 깜빡임이 끝난 후, 답변 상태로 전환
    setTimeout(() => {
        gameState = 'answering';
        messageLabel.textContent = "기억한 순서대로 클릭하세요!";
    }, delay);
}


/** 사용자의 답안을 서버로 전송하는 함수 */
async function submitAnswer() {
    gameState = 'processing';
    messageLabel.textContent = "결과를 확인 중입니다...";

    try {
        const response = await fetch('/api/submit-answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ answer: userSequence })
        });
        
        const result = await response.json();

        if (result.status === 'completed') {
            // 모든 테스트 완료
            messageLabel.textContent = result.message;
            canvas.style.display = 'none'; // 캔버스 숨기기
        } else if (result.status === 'next_problem') {
            // 다음 문제로 진행
            messageLabel.textContent = "다음 문제로 넘어갑니다.";
            setTimeout(initializeTest, 1500); // 1.5초 후 다음 문제 로드
        } else {
            // 오류 처리
            messageLabel.textContent = `오류가 발생했습니다: ${result.error || '알 수 없는 오류'}`;
        }
    } catch(error) {
        messageLabel.textContent = '서버 통신에 실패했습니다.';
        console.error('Submit Answer Error:', error);
    }
}

/** 다음 문제를 준비하고 시작하는 함수 */
function startNextProblem(newProblemData) {
    problemData = newProblemData;
    userSequence = [];
    
    messageLabel.textContent = `${problemData.level_name} (${problemData.problem_in_level}/${problemData.total_problems}) - 잠시 후 시작됩니다.`;
    
    drawBoxes();
    setTimeout(showFlashingSequence, 1500); // 1.5초 후 깜빡임 시작
}

/** 캔버스 클릭 이벤트 처리 함수 */
function handleCanvasClick(event) {
    if (gameState !== 'answering') return;

    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    problemData.boxes.forEach(box => {
        if (x >= box.x1 && x <= box.x2 && y >= box.y1 && y <= box.y2) {
            const boxId = box.id;
            
            if (userSequence.includes(boxId)) {
                // 이미 선택된 박스 클릭 시 선택 취소 (선택 사항)
                userSequence = userSequence.filter(id => id !== boxId);
            } else {
                userSequence.push(boxId);
            }
            
            drawBoxes();

            if (userSequence.length === problemData.flash_count) {
                submitAnswer();
            }
        }
    });
}

/** 페이지가 로드되거나 다음 문제로 넘어갈 때, 서버에서 문제를 가져와 테스트 시작 */
async function initializeTest() {
    userSequence = []; // 사용자 입력 초기화
    gameState = 'loading';
    messageLabel.textContent = '문제를 가져오는 중입니다...';

    try {
        const response = await fetch('/api/get-problem');
        if (!response.ok) throw new Error('서버에서 문제를 가져오는 데 실패했습니다.');
        
        const data = await response.json();

        if(data.status === 'completed') {
            messageLabel.textContent = data.message;
            canvas.style.display = 'none';
            return;
        }

        problemData = data;
        
        // 문제 데이터 로드 성공
        startNextProblem(problemData);

    } catch (error) {
        messageLabel.textContent = `오류: ${error.message}`;
        console.error(error);
    }
}

// 캔버스에 클릭 이벤트 리스너 추가
canvas.addEventListener('click', handleCanvasClick);

// 페이지가 처음 로드될 때 테스트 시작
document.addEventListener('DOMContentLoaded', initializeTest);