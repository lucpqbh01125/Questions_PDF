const API_BASE = 'http://127.0.0.1:8000';
let questions = [];
let selectedFileId = null; // File được chọn từ danh sách

// Kiểm tra authentication
function checkAuth() {
    const token = localStorage.getItem('access_token');
    const user = localStorage.getItem('user');
    
    if (!token || !user) {
        window.location.href = 'login.html';
        return null;
    }
    
    return { token, user: JSON.parse(user) };
}

// Hiển thị thông tin user
function displayUserInfo() {
    const auth = checkAuth();
    if (!auth) return;
    
    const user = auth.user;
    const header = document.querySelector('header');
    if (header && !document.getElementById('userInfo')) {
        const userInfo = document.createElement('div');
        userInfo.id = 'userInfo';
        userInfo.style.cssText = 'display: flex; align-items: center; gap: 15px; justify-content: flex-end; margin-top: 15px;';
        userInfo.innerHTML = `
            <span style="color: #5a7a90;">Xin chào, <strong>${user.full_name}</strong></span>
            <button onclick="logout()" style="padding: 8px 16px; background: white; color: #d8a0a0; border: 1px solid #e0f4fd; border-radius: 8px; cursor: pointer;">Đăng xuất</button>
        `;
        header.appendChild(userInfo);
    }
}

// Logout
function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    window.location.href = 'login.html';
}

document.addEventListener('DOMContentLoaded', function() {
    const auth = checkAuth();
    if (!auth) return;
    
    displayUserInfo();
    loadMyFiles(); // Load danh sách file ngay khi vào trang
    
    document.getElementById('pdfFile').addEventListener('change', function() {
        const fileName = this.files[0] ? this.files[0].name : '';
        document.getElementById('fileName').textContent = fileName;
        // Clear selected file từ danh sách khi chọn file mới
        if (fileName) {
            selectedFileId = null;
            loadMyFiles();
        }
    });
    
    document.getElementById('uploadBtn').addEventListener('click', handleUpload);
    document.getElementById('exportBtn').addEventListener('click', exportToPDF);
});

// Load danh sách file đã tải lên
async function loadMyFiles() {
    const auth = checkAuth();
    if (!auth) return;
    
    console.log('🔄 Đang load danh sách file...');
    
    try {
        const response = await fetch(`${API_BASE}/my-files`, {
            headers: {
                'Authorization': `Bearer ${auth.token}`
            }
        });
        
        console.log('📡 Response status:', response.status);
        
        // Nếu 401 Unauthorized (token hết hạn) -> redirect về login
        if (response.status === 401) {
            alert('⏰ Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại!');
            localStorage.clear();
            window.location.href = 'login.html';
            return;
        }
        
        const data = await response.json();
        console.log('📦 Data received:', data);
        
        if (response.ok && data.success) {
            console.log('✅ Load thành công:', data.files.length, 'files');
            displayFilesList(data.files);
        } else {
            console.error('❌ Load thất bại:', data);
        }
    } catch (error) {
        console.error('❌ Error loading files:', error);
    }
}

// Hiển thị danh sách file
function displayFilesList(files) {
    const filesList = document.getElementById('filesList');
    
    console.log('📋 Hiển thị danh sách file:', files);
    
    if (!files || files.length === 0) {
        filesList.innerHTML = '<p class="empty-message">Chưa có file nào được tải lên</p>';
        return;
    }
    
    filesList.innerHTML = files.map(file => {
        const uploadDate = new Date(file.upload_date).toLocaleString('vi-VN');
        const fileSize = (file.file_size / 1024).toFixed(2);
        const isSelected = selectedFileId === file.id;
        
        console.log('📄 File:', file.original_filename, '- Size:', fileSize, 'KB');
        
        return `
            <div class="file-item ${isSelected ? 'selected' : ''}" onclick="selectFile(${file.id}, '${file.original_filename}')">
                <div class="file-icon">📄</div>
                <div class="file-info">
                    <div class="file-name-display">${file.original_filename}</div>
                    <div class="file-meta">${uploadDate} • ${fileSize} KB</div>
                </div>
                ${isSelected ? '<div class="file-selected-badge">✓ Đã chọn</div>' : ''}
                <button class="file-delete-btn" onclick="event.stopPropagation(); deleteFile(${file.id}, '${file.original_filename}')">🗑️</button>
            </div>
        `;
    }).join('');
    
    console.log('✅ Đã render', files.length, 'file items');
}

// Xóa file
async function deleteFile(fileId, fileName) {
    if (!confirm(`Bạn có chắc muốn xóa file "${fileName}"?`)) {
        return;
    }
    
    const auth = checkAuth();
    if (!auth) return;
    
    console.log('🗑️ Đang xóa file ID:', fileId, '- Token:', auth.token ? 'Có' : 'Không có');
    
    try {
        const response = await fetch(`${API_BASE}/delete-file/${fileId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${auth.token}`
            }
        });
        
        console.log('📡 Delete response status:', response.status);
        
        // Nếu 401 Unauthorized -> redirect về login
        if (response.status === 401) {
            alert('⏰ Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại!');
            localStorage.clear();
            window.location.href = 'login.html';
            return;
        }
        
        const data = await response.json();
        console.log('📦 Delete response data:', data);
        
        if (response.ok && data.success) {
            alert(`✅ ${data.message}`);
            
            // Nếu file vừa xóa đang được chọn, clear selection
            if (selectedFileId === fileId) {
                selectedFileId = null;
                document.getElementById('fileName').textContent = '';
            }
            
            // Reload danh sách
            loadMyFiles();
        } else {
            alert(`❌ Lỗi: ${data.detail || 'Không thể xóa file'}`);
        }
    } catch (error) {
        console.error('❌ Error deleting file:', error);
        alert('❌ Lỗi khi xóa file: ' + error.message);
    }
}

// Chọn file từ danh sách
function selectFile(fileId, fileName) {
    selectedFileId = fileId;
    
    // Clear file input
    document.getElementById('pdfFile').value = '';
    document.getElementById('fileName').textContent = `Sẽ dùng file: ${fileName}`;
    document.getElementById('fileName').style.color = '#5a7a90';
    
    loadMyFiles(); // Refresh để hiện badge "Đã chọn"
}

async function handleUpload() {
    const auth = checkAuth();
    if (!auth) return;
    
    const fileInput = document.getElementById('pdfFile');
    const file = fileInput.files[0];
    const prompt = document.getElementById('userPrompt').value.trim();

    // Kiểm tra: phải có file mới HOẶC chọn file từ danh sách
    if (!file && !selectedFileId) {
        return alert('❌ Vui lòng chọn file PDF mới hoặc chọn file từ danh sách phía trên!');
    }
    
    if (!prompt) {
        return alert('❌ Vui lòng nhập yêu cầu tạo câu hỏi');
    }

    const uploadBtn = document.getElementById('uploadBtn');
    const loading = document.getElementById('loading');
    const questionsSection = document.getElementById('questionsSection');

    uploadBtn.disabled = true;
    loading.style.display = 'block';
    questionsSection.style.display = 'none';

    try {
        let response;
        
        // Trường hợp 1: Có file mới - kiểm tra trùng và upload
        if (file) {
            // Kiểm tra file trùng tên
            const checkResponse = await fetch(`${API_BASE}/check-duplicate-file?filename=${encodeURIComponent(file.name)}`, {
                headers: {
                    'Authorization': `Bearer ${auth.token}`
                }
            });
            
            const checkData = await checkResponse.json();
            
            if (checkData.duplicate) {
                // File trùng tên - BẮT BUỘC dùng file cũ, không cho upload
                alert(`⚠️ File "${file.name}" đã tồn tại!\n\n✓ Hệ thống sẽ tự động sử dụng file đã có trong danh sách để tạo câu hỏi.`);
                
                selectedFileId = checkData.file_id;
                
                response = await fetch(`${API_BASE}/generate-from-file`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${auth.token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        file_id: selectedFileId,
                        prompt: prompt
                    })
                });
            } else {
                // File không trùng, upload bình thường
                const formData = new FormData();
                formData.append('file', file);
                formData.append('prompt', prompt);

                response = await fetch(`${API_BASE}/upload-pdf`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${auth.token}`
                    },
                    body: formData
                });
                
                // Reload danh sách file sau khi upload xong
                setTimeout(() => loadMyFiles(), 1000);
            }
        } 
        // Trường hợp 2: Dùng file từ danh sách
        else {
            response = await fetch(`${API_BASE}/generate-from-file`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${auth.token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    file_id: selectedFileId,
                    prompt: prompt
                })
            });
        }

        const result = await response.json();

        // Nếu 401 Unauthorized -> redirect về login
        if (response.status === 401) {
            alert('⏰ Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại!');
            localStorage.clear();
            window.location.href = 'login.html';
            return;
        }

        if (response.ok && result.success) {
            questions = result.questions;
            displayQuestions();
            questionsSection.style.display = 'block';
            // Bỏ alert - hiển thị câu hỏi trực tiếp
            console.log(`✅ Đã tạo ${questions.length} câu hỏi thành công!`);
        } else {
            // Xử lý lỗi chi tiết từ backend
            let errorMsg = '❌ ';
            
            if (result.detail) {
                // Nếu detail là object (lỗi kiểm tra nội dung)
                if (typeof result.detail === 'object') {
                    errorMsg += result.detail.error || 'Lỗi không xác định';
                    errorMsg += '\n\n📝 ' + (result.detail.reason || '');
                    
                    if (result.detail.topics_found && result.detail.topics_found.length > 0) {
                        errorMsg += '\n\n✅ Chủ đề có trong file: ' + result.detail.topics_found.join(', ');
                    }
                    
                    if (result.detail.topics_missing && result.detail.topics_missing.length > 0) {
                        errorMsg += '\n\n❌ Chủ đề thiếu: ' + result.detail.topics_missing.join(', ');
                    }
                    
                    if (result.detail.suggestion) {
                        errorMsg += '\n\n💡 ' + result.detail.suggestion;
                    }
                } else {
                    errorMsg += result.detail;
                }
            } else {
                errorMsg += result.error || 'Lỗi không xác định';
            }
            
            alert(errorMsg);
        }
    } catch (error) {
        console.error('Error:', error);
        if (error.message && error.message.includes('Failed to fetch')) {
            alert('❌ Lỗi kết nối đến server');
        } else {
            alert('❌ Có lỗi xảy ra: ' + error.message);
        }
    } finally {
        loading.style.display = 'none';
        uploadBtn.disabled = false;
    }
}

function displayQuestions() {
    const questionsContainer = document.getElementById('questionsContainer');
    const questionCount = document.getElementById('questionCount');
    
    questionsContainer.innerHTML = '';
    questionCount.textContent = `${questions.length} câu hỏi`;
    questions.forEach((question, index) => {
        questionsContainer.appendChild(createQuestionElement(question, index));
    });
}

function createQuestionElement(question, index) {
    const div = document.createElement('div');
    div.className = 'question-item';
    div.innerHTML = `
        <div class="question-header">
            <span class="question-number">Câu ${index + 1}</span>
            <div class="question-actions">
                <button class="show-answer-btn" onclick="toggleAnswer(${index})" id="toggle-answer-${index}">👁️ Hiện đáp án</button>
                <button class="edit-btn" onclick="editQuestion(${index})">✏️ Sửa</button>
                <button class="delete-btn" onclick="deleteQuestion(${index})">🗑️ Xóa</button>
            </div>
        </div>
        <div class="question-content" id="question-content-${index}">
            ${renderQuestionContent(question, index)}
        </div>
    `;
    return div;
}

function renderQuestionContent(question, index) {
    let html = `
        <div class="question-text">${question.question}</div>
        <span class="question-type">Trắc nghiệm</span>
    `;

    // 🔥 TRẮC NGHIỆM - ĐẢM BẢO LUÔN CÓ 4 ĐÁP ÁN A, B, C, D
    let choices = [];
    
    if (question.choices && Array.isArray(question.choices) && question.choices.length > 0) {
        choices = question.choices.map(c => {
            // Loại bỏ prefix A. B. C. D. nếu đã có
            let text = String(c).trim();
            text = text.replace(/^[ABCD]\.\s*/i, '');
            return text;
        });
    } else {
        // Nếu không có choices, tạo từ answer
        const answerText = question.answer || 'Đáp án đúng';
        choices = [answerText, 'Đáp án khác 1', 'Đáp án khác 2', 'Đáp án khác 3'];
    }
    
    // Đảm bảo có đúng 4 đáp án
    while (choices.length < 4) {
        choices.push(`Đáp án ${choices.length + 1}`);
    }
    choices = choices.slice(0, 4); // Chỉ lấy 4 đáp án
    
    // Hiển thị 4 đáp án với prefix A, B, C, D
    html += '<div class="choices">';
    ['A', 'B', 'C', 'D'].forEach((letter, i) => {
        html += `<div class="choice">${letter}. ${choices[i]}</div>`;
    });
    html += '</div>';

    html += `
        <div class="answer" id="answer-${index}" style="display: none;">
            <div class="answer-label">Đáp án:</div>
            ${question.answer}
        </div>
    `;

    return html;
}

function toggleAnswer(index) {
    const answerDiv = document.getElementById(`answer-${index}`);
    const btn = document.getElementById(`toggle-answer-${index}`);
    
    if (answerDiv.style.display === 'none') {
        answerDiv.style.display = 'block';
        btn.textContent = '🙈 Ẩn đáp án';
        btn.classList.add('active');
    } else {
        answerDiv.style.display = 'none';
        btn.textContent = '👁️ Hiện đáp án';
        btn.classList.remove('active');
    }
}

function editQuestion(index) {
    const contentDiv = document.getElementById(`question-content-${index}`);
    const question = questions[index];
    
    // TRẮC NGHIỆM - BẮT BUỘC có 4 choices
    let choicesHtml = '';
    if (question.choices && question.choices.length > 0) {
        question.choices.forEach((choice, i) => {
            choicesHtml += `<input type="text" value="${choice}" id="choice-${index}-${i}" placeholder="Lựa chọn ${i + 1}">`;
        });
    } else {
        // Tạo 4 choices mặc định nếu thiếu
        for (let i = 0; i < 4; i++) {
            choicesHtml += `<input type="text" value="" id="choice-${index}-${i}" placeholder="Lựa chọn ${i + 1}">`;
        }
    }
    
    contentDiv.innerHTML = `
        <div class="edit-form">
            <label>Câu hỏi:</label>
            <textarea id="edit-question-${index}" rows="3">${question.question}</textarea>
            
            <label>Loại: TRẮC NGHIỆM (MCQ)</label>
            
            <label>Các lựa chọn A, B, C, D:</label>
            ${choicesHtml}
            
            <label>Đáp án:</label>
            <textarea id="edit-answer-${index}" rows="2">${question.answer}</textarea>
            
            <div class="edit-form-actions">
                <button class="save-btn" onclick="saveQuestion(${index})">💾 Lưu</button>
                <button class="cancel-btn" onclick="cancelEdit(${index})">❌ Hủy</button>
            </div>
        </div>
    `;
}

function saveQuestion(index) {
    const question = questions[index];
    question.question = document.getElementById(`edit-question-${index}`).value;
    question.type = 'mcq'; // BẮT BUỘC = TRẮC NGHIỆM
    question.answer = document.getElementById(`edit-answer-${index}`).value;
    
    // TRẮC NGHIỆM - BẮT BUỘC có 4 choices
    question.choices = [];
    for (let i = 0; i < 4; i++) {
        const choiceInput = document.getElementById(`choice-${index}-${i}`);
        if (choiceInput) {
            question.choices.push(choiceInput.value);
        }
    }
    
    displayQuestions();
}

function cancelEdit(index) {
    displayQuestions();
}

function deleteQuestion(index) {
    if (confirm('Bạn có chắc muốn xóa câu hỏi này?')) {
        questions.splice(index, 1);
        displayQuestions();
    }
}

async function exportToPDF() {
    if (questions.length === 0) {
        alert('Không có câu hỏi nào để xuất!');
        return;
    }

    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    
    doc.addFont('https://cdnjs.cloudflare.com/ajax/libs/pdfmake/0.1.66/fonts/Roboto/Roboto-Regular.ttf', 'Roboto', 'normal');
    doc.setFont('Roboto');
    
    let yPos = 20;
    const pageHeight = doc.internal.pageSize.height;
    const pageWidth = doc.internal.pageSize.width;
    const margin = 20;
    
    // Header - Tiêu đề
    doc.setFontSize(20);
    doc.setFont('Roboto', 'bold');
    doc.text('DE THI TRAC NGHIEM', pageWidth / 2, yPos, { align: 'center' });
    yPos += 10;
    
    doc.setFontSize(10);
    doc.setFont('Roboto', 'normal');
    doc.text(`Tong so cau: ${questions.length}`, pageWidth / 2, yPos, { align: 'center' });
    yPos += 15;
    
    // Vẽ đường kẻ
    doc.setLineWidth(0.5);
    doc.line(margin, yPos, pageWidth - margin, yPos);
    yPos += 10;
    
    // In các câu hỏi với 4 đáp án
    questions.forEach((question, index) => {
        // Kiểm tra nếu cần sang trang mới
        if (yPos > pageHeight - 60) {
            doc.addPage();
            yPos = 20;
        }
        
        // Số thứ tự và câu hỏi
        doc.setFontSize(12);
        doc.setFont('Roboto', 'bold');
        doc.text(`Cau ${index + 1}:`, margin, yPos);
        yPos += 7;
        
        doc.setFont('Roboto', 'normal');
        const questionLines = doc.splitTextToSize(question.question, 170);
        doc.text(questionLines, margin, yPos);
        yPos += questionLines.length * 7 + 3;
        
        // 🔥 XỬ LÝ 4 ĐÁP ÁN - LUÔN LUÔN CÓ A, B, C, D
        let choices = [];
        
        // Lấy choices từ question
        if (question.choices && Array.isArray(question.choices) && question.choices.length > 0) {
            choices = question.choices.map(c => {
                // Loại bỏ prefix A. B. C. D. nếu đã có
                let text = String(c).trim();
                text = text.replace(/^[ABCD]\.\s*/i, '');
                return text;
            });
        } else {
            // Nếu không có choices, tạo từ answer
            const answerText = question.answer || 'Dap an dung';
            choices = [answerText, 'Dap an khac 1', 'Dap an khac 2', 'Dap an khac 3'];
        }
        
        // Đảm bảo có đúng 4 đáp án
        while (choices.length < 4) {
            choices.push(`Dap an ${choices.length + 1}`);
        }
        choices = choices.slice(0, 4); // Chỉ lấy 4 đáp án
        
        // In 4 đáp án với prefix A, B, C, D
        ['A', 'B', 'C', 'D'].forEach((letter, i) => {
            const choiceText = `${letter}. ${choices[i]}`;
            const choiceLines = doc.splitTextToSize(choiceText, 165);
            doc.text(choiceLines, margin + 5, yPos);
            yPos += choiceLines.length * 6 + 1;
        });
        
        yPos += 8;
    });
    
    // Trang mới cho bảng đáp án
    doc.addPage();
    yPos = 20;
    
    // Tiêu đề bảng đáp án
    doc.setFontSize(16);
    doc.setFont('Roboto', 'bold');
    doc.text('BANG DAP AN', pageWidth / 2, yPos, { align: 'center' });
    yPos += 15;
    
    // Vẽ bảng đáp án
    const tableStartY = yPos;
    const cellWidth = 30;
    const cellHeight = 10;
    const cols = 5; // 5 cột
    const rows = Math.ceil(questions.length / cols);
    
    doc.setFont('Roboto', 'normal');
    doc.setFontSize(10);
    
    // Vẽ từng ô trong bảng
    for (let row = 0; row < rows; row++) {
        for (let col = 0; col < cols; col++) {
            const questionIndex = row * cols + col;
            
            if (questionIndex >= questions.length) break;
            
            const x = margin + col * cellWidth;
            const y = tableStartY + row * cellHeight;
            
            // Vẽ border ô
            doc.setDrawColor(0);
            doc.setLineWidth(0.3);
            doc.rect(x, y, cellWidth, cellHeight);
            
            // Số câu hỏi
            doc.setFont('Roboto', 'bold');
            doc.text(`${questionIndex + 1}.`, x + 2, y + 6.5);
            
            // Đáp án (lấy ký tự đầu tiên của answer hoặc phân tích)
            const question = questions[questionIndex];
            let answerLetter = '';
            
            if (question.answer) {
                const answerLower = question.answer.toLowerCase().trim();
                // Tìm A, B, C, D trong đáp án
                const match = answerLower.match(/^[abcd](?=\.|:|\s|$)/);
                if (match) {
                    answerLetter = match[0].toUpperCase();
                } else if (answerLower.startsWith('a') || answerLower.includes('đáp án a')) {
                    answerLetter = 'A';
                } else if (answerLower.startsWith('b') || answerLower.includes('đáp án b')) {
                    answerLetter = 'B';
                } else if (answerLower.startsWith('c') || answerLower.includes('đáp án c')) {
                    answerLetter = 'C';
                } else if (answerLower.startsWith('d') || answerLower.includes('đáp án d')) {
                    answerLetter = 'D';
                } else {
                    answerLetter = '?';
                }
            }
            
            doc.setFont('Roboto', 'normal');
            doc.text(answerLetter, x + cellWidth - 8, y + 6.5);
        }
    }
    
    // Ghi chú phía dưới bảng
    yPos = tableStartY + rows * cellHeight + 15;
    doc.setFontSize(9);
    doc.setFont('Roboto', 'italic');
    doc.text('Luu y: Kiem tra ky dap an truoc khi su dung', margin, yPos);
    
    // Thông tin footer
    yPos += 10;
    doc.setFont('Roboto', 'normal');
    doc.text(`Ngay xuat: ${new Date().toLocaleDateString('vi-VN')}`, margin, yPos);
    doc.text(`Tong cau hoi: ${questions.length}`, pageWidth - margin - 40, yPos);
    
    doc.save('questions.pdf');
    alert('Đã xuất PDF thành công!');
}
