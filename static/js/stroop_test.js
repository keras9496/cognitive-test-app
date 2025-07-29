document.addEventListener('DOMContentLoaded', () => {
    // --- DOM 요소 ---
    const startScreen = document.getElementById('start-screen');
    const prePracticeScreen = document.getElementById('pre-practice-screen');
    const practiceScreen = document.getElementById('practice-screen');
    const preRoundScreen = document.getElementById('pre-round-screen');
    const testScreen = document.getElementById('test-screen');
    const betweenRoundsScreen = document.getElementById('between-rounds-screen');
    const resultsScreen = document.getElementById('results-screen');
    const practiceFailModal = document.getElementById('practice-fail-modal');

    const startButton = document.getElementById('start-button');
    const startPracticeButton = document.getElementById('start-practice-button');
    const practiceResponseButton = document.getElementById('practice-response-button');
    const practiceFailConfirmButton = document.getElementById('practice-fail-confirm-button');
    const startMainGameButton = document.getElementById('start-main-game-button');
    const responseButton = document.getElementById('response-button');
    const nextRoundButton = document.getElementById('next-round-button');
    const restartButton = document.getElementById('restart-button');

    const instructionArea = document.getElementById('instruction-area');
    const stimulusWord = document.getElementById('stimulus-word');
    const correctCountDisplay = document.getElementById('correct-count');
    const trialCounterDisplay = document.getElementById('trial-counter');
    const feedbackArea = document.getElementById('feedback-area');
    
    const prePracticeInstructionArea = document.getElementById('pre-practice-instruction-area');
    const practiceInstructionArea = document.getElementById('practice-instruction-area');
    const practiceStimulusWord = document.getElementById('practice-stimulus-word');
    const practiceTimerBar = document.getElementById('practice-timer-bar');
    const practiceFeedbackArea = document.getElementById('practice-feedback-area');
    const practiceFailText = document.getElementById('practice-fail-text');
    const preRoundInstructionArea = document.getElementById('pre-round-instruction-area');
    
    const round1ResultsDisplay = document.getElementById('round-1-results');
    const finalResultsDisplay = document.getElementById('final-results');

    // --- 설정 ---
    const PRACTICE_STIMULUS_DURATION = 2000;
    const PRACTICE_RESPONSE_WINDOW = 3500;
    const PRACTICE_TRIAL_COUNT = 4;
    const MAIN_GAME_START_DELAY = 2000;
    const STIMULUS_DURATION = 500;
    const RESPONSE_WINDOW = 2000;
    const INTER_TRIAL_INTERVAL = 1200;
    const TOTAL_TRIALS_PER_ROUND = 30;
    const TARGET_RATIO = 0.3;
    const HIGH_CONFLICT_RATIO = 0.4;

    const COLORS = [ { name: '빨강', code: 'text-red-600', kor: '빨강' }, { name: '파랑', code: 'text-blue-600', kor: '파랑' }, { name: '초록', code: 'text-green-600', kor: '초록' }, { name: '검정', code: 'text-black', kor: '검정' }, { name: '노랑', code: 'text-yellow-500', kor: '노랑' }];

    // --- 상태 변수 ---
    let currentRound = 1;
    let correctCount = 0;
    let reactionTimes = [];
    let trials = [];
    let targetColor;
    let waitingForInput = false;
    let startTime = 0;
    let responseTimeout, practiceResponseTimeout, timerInterval;
    let roundResults = {};
    let practiceTrials = [];
    let currentPracticeIndex = 0;
    let mainTrialIndex = 0;
    
    // --- 데이터 수집을 위한 변수들 ---
    let allPracticeTrials = []; // 전체 연습 시행 데이터
    let allTestTrials = [];     // 전체 본 검사 시행 데이터
    let practiceFailures = 0;   // 연습에서 실패한 총 횟수

    // --- 유틸리티 및 문항 생성 ---
    function shuffleArray(array) { for (let i = array.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [array[i], array[j]] = [array[j], array[i]]; } }
    function getRandomElement(arr, exclude = null) { let el; do { el = arr[Math.floor(Math.random() * arr.length)]; } while (exclude && el.name === exclude.name); return el; }
    
    function generateTrials(round) {
        const newTrials = [];
        const targetCount = Math.round(TOTAL_TRIALS_PER_ROUND * TARGET_RATIO);
        const highConflictCount = Math.round(TOTAL_TRIALS_PER_ROUND * HIGH_CONFLICT_RATIO);
        const otherNonTargetCount = TOTAL_TRIALS_PER_ROUND - targetCount - highConflictCount;
        
        for (let i = 0; i < targetCount; i++) {
            let word, color;
            if (round === 1) { color = targetColor; word = getRandomElement(COLORS, color); } 
            else { word = targetColor; color = getRandomElement(COLORS, word); }
            newTrials.push({ word: word.kor, color: color.code, isTarget: true });
        }

        for (let i = 0; i < highConflictCount; i++) {
            let word, color;
            if (round === 1) { word = targetColor; color = getRandomElement(COLORS, word); } 
            else { color = targetColor; word = getRandomElement(COLORS, color); }
            newTrials.push({ word: word.kor, color: color.code, isTarget: false });
        }

        const nonTargetColors = COLORS.filter(c => c.name !== targetColor.name);
        for (let i = 0; i < otherNonTargetCount; i++) {
            const nonTargetStimulus = getRandomElement(nonTargetColors);
            let word, color;
            if(Math.random() > 0.5) {
                 color = nonTargetStimulus;
                 word = getRandomElement(COLORS.filter(c => c.name !== color.name && c.name !== targetColor.name));
            } else {
                word = nonTargetStimulus;
                color = nonTargetStimulus;
            }
            newTrials.push({ word: word.kor, color: color.code, isTarget: false });
        }

        shuffleArray(newTrials);

        for (let i = 1; i < newTrials.length; i++) {
            if (newTrials[i].word === newTrials[i-1].word && newTrials[i].color === newTrials[i-1].color) {
                let swapIndex = -1;
                for (let j = i + 1; j < newTrials.length; j++) {
                    if (newTrials[j].word !== newTrials[i].word || newTrials[j].color !== newTrials[i].color) {
                        swapIndex = j;
                        break;
                    }
                }
                if (swapIndex !== -1) {
                    [newTrials[i], newTrials[swapIndex]] = [newTrials[swapIndex], newTrials[i]];
                }
            }
        }
        return newTrials;
    }

    function generatePracticeTrials(round) {
        const practiceSet = [];
        const targetCount = 2;
        for (let i = 0; i < targetCount; i++) { let word, color; if (round === 1) { color = targetColor; word = getRandomElement(COLORS, color); } else { word = targetColor; color = getRandomElement(COLORS, word); } practiceSet.push({ word: word.kor, color: color.code, isTarget: true }); }
        for (let i = 0; i < PRACTICE_TRIAL_COUNT - targetCount; i++) { let word, color; const nonTarget = getRandomElement(COLORS, targetColor); if (Math.random() > 0.5) { word = getRandomElement(COLORS, nonTarget); color = nonTarget; } else { word = nonTarget; color = nonTarget; } practiceSet.push({ word: word.kor, color: color.code, isTarget: false }); }
        shuffleArray(practiceSet);
        return practiceSet;
    }

    // --- 게임 흐름 제어 ---
    function showPrePracticeScreen(roundNum) {
        currentRound = roundNum;
        targetColor = getRandomElement(COLORS);
        hideAllScreens();
        prePracticeScreen.classList.remove('hidden');
        const instructionText = roundNum === 1 
            ? `글자의 <strong class="font-bold">색상</strong>이 <strong class="${targetColor.code}">${targetColor.kor}</strong>일 때만 '일치'를 누르세요.`
            : `글자의 <strong class="font-bold">의미</strong>가 <strong class="${targetColor.code}">${targetColor.kor}</strong>일 때만 '일치'를 누르세요.`;
        prePracticeInstructionArea.innerHTML = instructionText;
    }

    function startPractice() {
        currentPracticeIndex = 0;
        practiceTrials = generatePracticeTrials(currentRound);
        hideAllScreens();
        practiceScreen.classList.remove('hidden');
        const instructionText = prePracticeInstructionArea.innerHTML;
        practiceInstructionArea.innerHTML = instructionText + `<br>4문제를 연속으로 맞춰야 통과합니다. (${currentPracticeIndex}/${PRACTICE_TRIAL_COUNT})`;
        runPracticeTrial();
    }

    function runPracticeTrial() {
        practiceFeedbackArea.textContent = '';
        const trial = practiceTrials[currentPracticeIndex];
        practiceStimulusWord.textContent = trial.word;
        practiceStimulusWord.className = `text-8xl font-black ${trial.color}`;
        waitingForInput = true;
        startTimerBar();
        practiceResponseTimeout = setTimeout(() => handlePracticeResponse(false), PRACTICE_RESPONSE_WINDOW);
    }

    function handlePracticeResponse(buttonPressed) {
        if (!waitingForInput) return;
        clearTimeout(practiceResponseTimeout);
        clearInterval(timerInterval);
        waitingForInput = false;

        const trial = practiceTrials[currentPracticeIndex];
        const correct = (trial.isTarget === buttonPressed);
        
        // 연습 데이터 기록
        allPracticeTrials.push({
            round: currentRound,
            word: trial.word,
            color: trial.color.replace('text-', ''), // 'text-red-600' -> 'red-600'
            user_response: buttonPressed,
            correct_answer: trial.isTarget,
            is_correct: correct
        });

        if (correct) {
            currentPracticeIndex++;
            practiceInstructionArea.innerHTML = practiceInstructionArea.innerHTML.replace(/\(\d\/\d\)/, `(${currentPracticeIndex}/${PRACTICE_TRIAL_COUNT})`);
            if (currentPracticeIndex >= PRACTICE_TRIAL_COUNT) {
                practiceSuccess();
            } else {
                practiceFeedbackArea.className = 'mt-4 h-12 text-xl font-bold flex items-center justify-center text-blue-600';
                practiceFeedbackArea.textContent = '정답입니다!';
                setTimeout(runPracticeTrial, 1000);
            }
        } else {
            practiceFailures++;
            showPracticeFailPopup(trial, buttonPressed);
        }
    }

    function startTimerBar() {
        practiceTimerBar.style.transition = 'none';
        practiceTimerBar.style.width = '100%';
        setTimeout(() => {
            practiceTimerBar.style.transition = `width ${PRACTICE_RESPONSE_WINDOW / 1000}s linear`;
            practiceTimerBar.style.width = '0%';
        }, 50);
    }

    function showPracticeFailPopup(trial, buttonPressed) {
        let alertMsg = '';
        const rule = currentRound === 1 ? '글자 색상' : '글자 의미';
        if (buttonPressed && !trial.isTarget) {
            alertMsg = `방금 문제의 ${rule}은(는) 목표인 '${targetColor.kor}'이 아니었으므로, 버튼을 누르면 안 됐습니다.`;
        } else if (!buttonPressed && trial.isTarget) {
            alertMsg = `방금 문제의 ${rule}은(는) 목표인 '${targetColor.kor}'이었으므로, 버튼을 눌러야 했습니다.`;
        }
        practiceFailText.innerHTML = alertMsg;
        practiceFailModal.classList.remove('hidden');
    }

    function practiceSuccess() {
        hideAllScreens();
        preRoundScreen.classList.remove('hidden');
        preRoundInstructionArea.innerHTML = prePracticeInstructionArea.innerHTML;
    }

    function startRound() {
        mainTrialIndex = 0;
        correctCount = 0;
        reactionTimes = [];
        trials = generateTrials(currentRound);
        updateScoreAndTrial();
        instructionArea.innerHTML = preRoundInstructionArea.innerHTML;
        hideAllScreens();
        testScreen.classList.remove('hidden');
        
        stimulusWord.textContent = "준비...";
        stimulusWord.className = "text-6xl font-bold text-gray-500";

        setTimeout(() => {
            nextTrial();
        }, MAIN_GAME_START_DELAY);
    }
    
    function nextTrial() {
        if (mainTrialIndex >= TOTAL_TRIALS_PER_ROUND) {
            endRound();
            return;
        }
        feedbackArea.textContent = '';
        const trial = trials[mainTrialIndex];
        stimulusWord.textContent = trial.word;
        stimulusWord.className = `text-8xl font-black ${trial.color}`;
        stimulusWord.classList.remove('hidden');

        waitingForInput = true;
        startTime = Date.now();
        responseTimeout = setTimeout(() => handleMainResponse(false), RESPONSE_WINDOW);
    }

    function handleMainResponse(buttonPressed) {
        if (!waitingForInput) return;
        clearTimeout(responseTimeout);
        waitingForInput = false;

        const trial = trials[mainTrialIndex];
        const correct = (trial.isTarget === buttonPressed);
        const responseTime = Date.now() - startTime;
        
        // 본 검사 데이터 기록
        allTestTrials.push({
            round: currentRound,
            trial_number: mainTrialIndex + 1,
            word: trial.word,
            color: trial.color.replace('text-', ''),
            user_response: buttonPressed,
            response_time: responseTime,
            correct_answer: trial.isTarget,
            is_correct: correct
        });

        if (correct) {
            correctCount++;
            if (buttonPressed) {
                reactionTimes.push(responseTime / 1000);
            }
        }
        
        mainTrialIndex++;
        updateScoreAndTrial();
        setTimeout(nextTrial, INTER_TRIAL_INTERVAL);
    }
    
    function showFeedback(text, colorClass) {
        feedbackArea.textContent = text;
        feedbackArea.className = `mt-4 h-6 text-xl font-bold ${colorClass}`;
    }

    function updateScoreAndTrial() {
        correctCountDisplay.textContent = correctCount;
        trialCounterDisplay.textContent = TOTAL_TRIALS_PER_ROUND - mainTrialIndex;
    }

    function endRound() {
        const accuracy = (correctCount / TOTAL_TRIALS_PER_ROUND) * 100;
        const avgReactionTime = reactionTimes.length > 0 ? (reactionTimes.reduce((a, b) => a + b, 0) / reactionTimes.length).toFixed(3) : 'N/A';
        roundResults[currentRound] = { correctCount, accuracy, avgReactionTime };
        hideAllScreens();
        if (currentRound === 1) {
            showPrePracticeScreen(2);
        } else {
            showFinalResults();
        }
    }

    async function showFinalResults() {
        // 1. 화면에 결과 전송 중 메시지 표시
        hideAllScreens();
        resultsScreen.classList.remove('hidden');
        finalResultsDisplay.innerHTML = `
            <h2 class="text-3xl font-bold text-gray-800 mb-6">테스트 종료</h2>
            <p class="text-xl text-gray-700">결과를 서버로 전송 중입니다. 잠시만 기다려주세요...</p>
        `;

        // 2. 서버에 전송할 최종 데이터 객체 생성
        const finalResultData = {
            practice_trials: allPracticeTrials,
            test_trials: allTestTrials,
            summary: {
                round1: roundResults[1],
                round2: roundResults[2],
                practice_failures: practiceFailures
            }
        };

        // 3. fetch를 사용하여 서버에 결과 전송
        try {
            const response = await fetch('/api/submit-stroop-result', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(finalResultData)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            console.log('결과 저장 성공:', result);

            // 4. 최종 완료 페이지로 이동
            finalResultsDisplay.innerHTML += '<p class="text-green-500 font-bold mt-4">결과가 성공적으로 저장되었습니다. 곧 다음 페이지로 이동합니다.</p>';
            setTimeout(() => {
                window.location.href = '/finish';
            }, 2000);

        } catch (error) {
            console.error('결과 전송 실패:', error);
            finalResultsDisplay.innerHTML += '<p class="text-red-500 font-bold mt-4">결과 저장에 실패했습니다. 관리자에게 문의하세요.</p>';
        }
    }
    
    function hideAllScreens() {
        startScreen.classList.add('hidden');
        prePracticeScreen.classList.add('hidden');
        practiceScreen.classList.add('hidden');
        preRoundScreen.classList.add('hidden');
        testScreen.classList.add('hidden');
        betweenRoundsScreen.classList.add('hidden');
        resultsScreen.classList.add('hidden');
    }

    // --- 이벤트 리스너 ---
    startButton.addEventListener('click', () => showPrePracticeScreen(1));
    startPracticeButton.addEventListener('click', startPractice);
    practiceResponseButton.addEventListener('click', () => handlePracticeResponse(true));
    practiceFailConfirmButton.addEventListener('click', () => {
        practiceFailModal.classList.add('hidden');
        showPrePracticeScreen(currentRound);
    });
    startMainGameButton.addEventListener('click', startRound);
    responseButton.addEventListener('click', () => handleMainResponse(true));
    nextRoundButton.addEventListener('click', () => showPrePracticeScreen(2));
    if(restartButton) {
        restartButton.addEventListener('click', () => {
            hideAllScreens();
            startScreen.classList.remove('hidden');
        });
    }

    // 초기 화면 표시
    hideAllScreens();
    startScreen.classList.remove('hidden');
});
