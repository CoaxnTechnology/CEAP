function togglePassword() {
    const input = document.getElementById('password');
    const icon  = document.getElementById('togglePass');
    if (input.type === 'password') {
        input.type = 'text';
        icon.className = 'fas fa-eye-slash toggle-pass';
    } else {
        input.type = 'password';
        icon.className = 'fas fa-eye toggle-pass';
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const email    = document.getElementById('email').value.trim().toLowerCase();
    const password = document.getElementById('password').value;
    const btn      = document.getElementById('loginBtn');
    const err      = document.getElementById('errorMsg');

    err.classList.remove('show');
    btn.classList.add('loading');

    try {
        const res  = await fetch('/api/login', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ email, password }),
        });
        const data = await res.json();

        btn.classList.remove('loading');

        if (res.ok && data.success) {
            sessionStorage.setItem('user', email);
            sessionStorage.setItem('username', data.username || email.split('@')[0]);
            window.location.href = '/chat';
            return;
        }

        err.classList.add('show');
    } catch {
        btn.classList.remove('loading');
        err.classList.add('show');
    }
}

const demoHint = document.querySelector('.demo-hint');
if (demoHint) {
    demoHint.addEventListener('click', () => {
        document.getElementById('email').value = 'admin@documind.ai';
        document.getElementById('password').value = 'demo1234';
    });
}
