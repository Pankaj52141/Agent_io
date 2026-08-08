const API_URL = 'https://agent-io.onrender.com';

const app = {
    state: {
        token: null,
        currentUser: null,
        messages: []
    },

    elements: {
        loginView: document.getElementById('login-view'),
        chatView: document.getElementById('chat-view'),
        loginForm: document.getElementById('login-form'),
        emailInput: document.getElementById('email'),
        passwordInput: document.getElementById('password'),
        loginError: document.getElementById('login-error'),
        
        userName: document.getElementById('user-name'),
        roleBadge: document.getElementById('user-role-badge'),
        accessLevel: document.getElementById('access-level'),
        logoutBtn: document.getElementById('logout-btn'),
        
        chatMessages: document.getElementById('chat-messages'),
        typingIndicator: document.getElementById('typing-indicator'),
        chatForm: document.getElementById('chat-form'),
        chatInput: document.getElementById('chat-input'),
        
        msgTemplate: document.getElementById('message-template')
    },

    demoAccounts: {
        ceo: { email: 'ceo@apple.com', pass: 'ceo123' },
        cto: { email: 'cto@apple.com', pass: 'cto123' },
        cfo: { email: 'cfo@apple.com', pass: 'cfo123' }
    },

    init() {
        this.bindEvents();
        
        // Check if already logged in
        const token = localStorage.getItem('agentio_token');
        const user = localStorage.getItem('agentio_user');
        
        if (token && user) {
            this.state.token = token;
            this.state.currentUser = JSON.parse(user);
            this.setupChatView();
            this.switchView('chat');
        }
    },

    bindEvents() {
        this.elements.loginForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.login(this.elements.emailInput.value, this.elements.passwordInput.value);
        });

        this.elements.logoutBtn.addEventListener('click', () => this.logout());

        this.elements.chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const query = this.elements.chatInput.value.trim();
            if (query) {
                this.elements.chatInput.value = '';
                this.sendMessage(query);
            }
        });
    },

    switchView(view) {
        if (view === 'login') {
            this.elements.loginView.classList.add('active');
            this.elements.chatView.classList.remove('active');
        } else {
            this.elements.loginView.classList.remove('active');
            this.elements.chatView.classList.add('active');
            this.scrollToBottom();
        }
    },

    quickLogin(role) {
        const creds = this.demoAccounts[role];
        if (creds) {
            this.elements.emailInput.value = creds.email;
            this.elements.passwordInput.value = creds.pass;
            this.login(creds.email, creds.pass);
        }
    },

    async login(email, password) {
        try {
            this.elements.loginError.textContent = '';
            const btn = this.elements.loginForm.querySelector('button');
            btn.textContent = 'Signing in...';
            btn.disabled = true;

            const response = await fetch(`${API_URL}/api/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });

            if (!response.ok) {
                throw new Error('Invalid credentials or server error');
            }

            const data = await response.json();
            
            this.state.token = data.access_token;
            this.state.currentUser = {
                name: data.user_name,
                role: data.user_role
            };

            localStorage.setItem('agentio_token', this.state.token);
            localStorage.setItem('agentio_user', JSON.stringify(this.state.currentUser));

            this.setupChatView();
            this.switchView('chat');
            
        } catch (error) {
            this.elements.loginError.textContent = error.message;
        } finally {
            const btn = this.elements.loginForm.querySelector('button');
            btn.textContent = 'Sign In';
            btn.disabled = false;
        }
    },

    logout() {
        this.state.token = null;
        this.state.currentUser = null;
        this.state.messages = [];
        
        localStorage.removeItem('agentio_token');
        localStorage.removeItem('agentio_user');
        
        // Reset chat messages to just the welcome message
        const welcomeMsg = this.elements.chatMessages.querySelector('.welcome-message').cloneNode(true);
        this.elements.chatMessages.innerHTML = '';
        this.elements.chatMessages.appendChild(welcomeMsg);
        
        this.elements.emailInput.value = '';
        this.elements.passwordInput.value = '';
        
        this.switchView('login');
    },

    setupChatView() {
        const user = this.state.currentUser;
        this.elements.userName.textContent = user.name;
        
        const badge = this.elements.roleBadge;
        badge.textContent = user.role.toUpperCase();
        badge.className = 'demo-role role-badge'; // reset
        
        let accessText = '';
        if (user.role.toLowerCase() === 'ceo') {
            badge.classList.add('badge-gold');
            accessText = 'Full Access';
        } else if (user.role.toLowerCase() === 'cto') {
            badge.classList.add('badge-blue');
            accessText = 'No Headcount/Compensation';
        } else if (user.role.toLowerCase() === 'cfo') {
            badge.classList.add('badge-green');
            accessText = 'No Strategy/R&D/Legal';
        }
        
        this.elements.accessLevel.textContent = `Access: ${accessText}`;
    },

    async sendMessage(query) {
        // Add user message
        this.addMessageToDOM({ role: 'user', content: query });
        
        // Show typing indicator
        this.elements.typingIndicator.classList.remove('hidden');
        this.scrollToBottom();

        try {
            const response = await fetch(`${API_URL}/api/query`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.state.token}`
                },
                body: JSON.stringify({ query })
            });

            if (response.status === 401) {
                this.logout();
                return;
            }

            const data = await response.json();
            
            // Hide typing indicator
            this.elements.typingIndicator.classList.add('hidden');
            
            // Add agent message
            const agentMsg = {
                role: 'agent',
                content: data.answer || "I'm sorry, I couldn't process that request.",
                sources: data.sources || [],
                access_note: data.access_note || null,
                query_id: data.query_id || Date.now().toString()
            };
            
            this.state.messages.push(agentMsg);
            this.addMessageToDOM(agentMsg);

        } catch (error) {
            console.error('Query error:', error);
            this.elements.typingIndicator.classList.add('hidden');
            this.addMessageToDOM({ 
                role: 'agent', 
                content: "Sorry, there was an error connecting to the server. Please try again later."
            });
        }
    },

    addMessageToDOM(msg) {
        const template = this.elements.msgTemplate.content.cloneNode(true);
        const msgDiv = template.querySelector('.message');
        msgDiv.classList.add(`${msg.role}-message`);
        
        const contentDiv = template.querySelector('.message-content');
        contentDiv.innerHTML = this.renderMarkdown(msg.content);

        if (msg.role === 'agent') {
            // Setup access note
            if (msg.access_note) {
                const accessNote = template.querySelector('.access-note');
                accessNote.textContent = `Note: ${msg.access_note}`;
                accessNote.classList.remove('hidden');
            }

            // Setup sources
            if (msg.sources && msg.sources.length > 0) {
                const sourcesSection = template.querySelector('.sources-section');
                const sourcesList = template.querySelector('.sources-list');
                const sourcesBtn = template.querySelector('.sources-toggle');
                
                sourcesSection.classList.remove('hidden');
                
                const ul = document.createElement('ul');
                msg.sources.forEach(src => {
                    const li = document.createElement('li');
                    li.textContent = typeof src === 'string' ? src : (src.file || JSON.stringify(src));
                    ul.appendChild(li);
                });
                sourcesList.appendChild(ul);
                
                sourcesBtn.addEventListener('click', () => {
                    sourcesList.classList.toggle('hidden');
                    sourcesBtn.textContent = sourcesList.classList.contains('hidden') ? 'View Sources' : 'Hide Sources';
                });
            }

            // Setup feedback
            if (msg.query_id) {
                const feedbackSection = template.querySelector('.feedback-section');
                feedbackSection.classList.remove('hidden');
                
                const upBtn = template.querySelector('.upvote');
                const downBtn = template.querySelector('.downvote');
                const correctionForm = template.querySelector('.correction-form');
                const cancelCorr = template.querySelector('.cancel-correction');
                const submitCorr = template.querySelector('.submit-correction');
                const corrInput = template.querySelector('.correction-input');
                
                upBtn.addEventListener('click', () => {
                    upBtn.classList.add('active');
                    downBtn.classList.remove('active');
                    correctionForm.classList.add('hidden');
                    this.submitFeedback(msg.query_id, 'positive');
                });
                
                downBtn.addEventListener('click', () => {
                    downBtn.classList.add('active');
                    upBtn.classList.remove('active');
                    correctionForm.classList.remove('hidden');
                    this.submitFeedback(msg.query_id, 'negative');
                });
                
                cancelCorr.addEventListener('click', () => {
                    correctionForm.classList.add('hidden');
                });
                
                submitCorr.addEventListener('click', () => {
                    const correction = corrInput.value.trim();
                    if (correction) {
                        this.submitFeedback(msg.query_id, 'negative', correction);
                        correctionForm.innerHTML = '<p class="success">Thank you for your feedback!</p>';
                        setTimeout(() => correctionForm.classList.add('hidden'), 2000);
                    }
                });
            }
        }

        this.elements.chatMessages.appendChild(msgDiv);
        this.scrollToBottom();
    },

    async submitFeedback(queryId, rating, correction = null) {
        try {
            await fetch(`${API_URL}/api/feedback`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.state.token}`
                },
                body: JSON.stringify({ 
                    query_id: queryId, 
                    rating: rating === 'positive',
                    correction: correction || null,
                    preferred_answer: correction || null
                })
            });
        } catch (error) {
            console.error('Feedback error:', error);
        }
    },

    scrollToBottom() {
        const main = document.querySelector('.chat-main');
        main.scrollTop = main.scrollHeight;
    },

    // Simple markdown renderer without external libraries
    renderMarkdown(text) {
        if (!text) return '';
        
        let html = text
            // Escape HTML tags to prevent XSS
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            
            // Bold (**text**)
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            
            // Italic (*text*)
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            
            // Inline code (`code`)
            .replace(/`(.*?)`/g, '<code>$1</code>');

        // Handle paragraphs, lists and tables block by block
        const lines = html.split('\n');
        let inList = false;
        let inTable = false;
        let result = [];
        
        for (let i = 0; i < lines.length; i++) {
            let line = lines[i];
            
            // Handle unordered lists
            if (line.match(/^[\s]*[-*+]\s+(.*)/)) {
                if (!inList) {
                    result.push('<ul>');
                    inList = true;
                }
                result.push(`<li>${line.replace(/^[\s]*[-*+]\s+/, '')}</li>`);
                continue;
            } else if (inList) {
                result.push('</ul>');
                inList = false;
            }
            
            // Handle simple tables
            if (line.includes('|')) {
                // Table header separator like |---|---|
                if (line.match(/^[\s]*\|?[\s-:]+\|[\s-:]+\|?/)) {
                    continue; // Skip separator line
                }
                
                const cells = line.split('|').filter(c => c.trim() !== '').map(c => c.trim());
                if (cells.length > 0) {
                    if (!inTable) {
                        result.push('<table>');
                        result.push('<thead><tr>' + cells.map(c => `<th>${c}</th>`).join('') + '</tr></thead><tbody>');
                        inTable = true;
                    } else {
                        result.push('<tr>' + cells.map(c => `<td>${c}</td>`).join('') + '</tr>');
                    }
                    continue;
                }
            } else if (inTable) {
                result.push('</tbody></table>');
                inTable = false;
            }
            
            // Empty lines or normal paragraphs
            if (line.trim() === '') {
                // Ignore empty lines unless we need spacing
            } else {
                result.push(`<p>${line}</p>`);
            }
        }
        
        // Close open blocks
        if (inList) result.push('</ul>');
        if (inTable) result.push('</tbody></table>');
        
        return result.join('\n');
    }
};

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    app.init();
});
