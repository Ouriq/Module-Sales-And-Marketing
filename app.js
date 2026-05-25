/* ===================================================================
   app.js – Indofood Login Frontend Logic
   Connects to the Python Flask backend (server.py) on port 5000
   =================================================================== */

const API_BASE = 'http://localhost:5000/api';

// ── DOM References ──────────────────────────────────────────────────
const form        = document.getElementById('loginForm');
const emailInput  = document.getElementById('email');
const pwdInput    = document.getElementById('password');
const emailErr    = document.getElementById('emailError');
const pwdErr      = document.getElementById('passwordError');
const alertBox    = document.getElementById('alertBox');
const submitBtn   = document.getElementById('submitBtn');
const btnText     = submitBtn.querySelector('.btn-text');
const spinner     = document.getElementById('spinner');
const togglePwd   = document.getElementById('togglePwd');
const eyeIcon     = document.getElementById('eyeIcon');
const forgotLink  = document.getElementById('forgotLink');
const modalOverlay = document.getElementById('modalOverlay');
const modalClose  = document.getElementById('modalClose');
const resetBtn    = document.getElementById('resetBtn');
const resetEmail  = document.getElementById('resetEmail');
const modalFeedback = document.getElementById('modalFeedback');

// ── Utility Helpers ─────────────────────────────────────────────────
function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
}

function showAlert(message, type = 'error') {
  alertBox.textContent = message;
  alertBox.className = 'alert ' + type;
  alertBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function clearAlert() {
  alertBox.textContent = '';
  alertBox.className = 'alert';
}

function setFieldError(input, errorEl, message) {
  errorEl.textContent = message;
  input.classList.add('invalid');
}

function clearFieldError(input, errorEl) {
  errorEl.textContent = '';
  input.classList.remove('invalid');
}

function setLoading(isLoading) {
  submitBtn.disabled = isLoading;
  btnText.hidden = isLoading;
  spinner.hidden = !isLoading;
}

// ── Real-time Validation ────────────────────────────────────────────
emailInput.addEventListener('input', () => {
  if (emailInput.value && !isValidEmail(emailInput.value)) {
    setFieldError(emailInput, emailErr, 'Format email tidak valid.');
  } else {
    clearFieldError(emailInput, emailErr);
  }
});

pwdInput.addEventListener('input', () => {
  if (pwdInput.value && pwdInput.value.length < 6) {
    setFieldError(pwdInput, pwdErr, 'Password minimal 6 karakter.');
  } else {
    clearFieldError(pwdInput, pwdErr);
  }
});

// ── Password Visibility Toggle ──────────────────────────────────────
togglePwd.addEventListener('click', () => {
  const isHidden = pwdInput.type === 'password';
  pwdInput.type = isHidden ? 'text' : 'password';
  eyeIcon.innerHTML = isHidden
    ? /* eye-off */
      `<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
       <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
       <line x1="1" y1="1" x2="23" y2="23"/>`
    : /* eye */
      `<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>`;
  togglePwd.setAttribute('aria-label', isHidden ? 'Sembunyikan password' : 'Tampilkan password');
});

// ── Form Submit ─────────────────────────────────────────────────────
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  clearAlert();

  const email    = emailInput.value.trim();
  const password = pwdInput.value;
  const remember = document.getElementById('remember').checked;
  let valid = true;

  // Validate email
  if (!email) {
    setFieldError(emailInput, emailErr, 'Email tidak boleh kosong.');
    valid = false;
  } else if (!isValidEmail(email)) {
    setFieldError(emailInput, emailErr, 'Format email tidak valid.');
    valid = false;
  } else {
    clearFieldError(emailInput, emailErr);
  }

  // Validate password
  if (!password) {
    setFieldError(pwdInput, pwdErr, 'Password tidak boleh kosong.');
    valid = false;
  } else if (password.length < 6) {
    setFieldError(pwdInput, pwdErr, 'Password minimal 6 karakter.');
    valid = false;
  } else {
    clearFieldError(pwdInput, pwdErr);
  }

  if (!valid) return;

  setLoading(true);

  try {
    const response = await fetch(`${API_BASE}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, remember }),
    });

    const data = await response.json();

    if (response.ok && data.success) {
      // Store token
      const storage = remember ? localStorage : sessionStorage;
      storage.setItem('auth_token', data.token);
      storage.setItem('user_name',  data.user.name);
      storage.setItem('user_email', data.user.email);

      showAlert(`Selamat datang, ${data.user.name}! Mengalihkan…`, 'success');

      // Simulate redirect after success
      setTimeout(() => {
        window.location.href = data.redirect_url || '/dashboard';
      }, 1500);
    } else {
      showAlert(data.message || 'Email atau password salah. Silakan coba lagi.');
    }
  } catch (err) {
    // Fallback demo mode when server isn't running
    if (err instanceof TypeError && err.message.includes('fetch')) {
      console.warn('[Demo Mode] Server tidak terdeteksi. Menggunakan simulasi login.');
      await simulateLogin(email, password, remember);
    } else {
      showAlert('Terjadi kesalahan. Periksa koneksi internet Anda.');
    }
  } finally {
    setLoading(false);
  }
});

// ── Demo / Offline Simulation ───────────────────────────────────────
async function simulateLogin(email, password, remember) {
  // Simulate network delay
  await new Promise(r => setTimeout(r, 800));

  // Demo credentials check
  const DEMO_USERS = [
    { email: 'admin@indofood.com',   password: 'admin123', name: 'Administrator'   },
    { email: 'user@indofood.com',    password: 'user123',  name: 'User Indofood'   },
    { email: 'demo@perusahaan.com',  password: 'demo123',  name: 'Demo Pengguna'   },
  ];

  const matched = DEMO_USERS.find(u => u.email === email && u.password === password);

  if (matched) {
    const storage = remember ? localStorage : sessionStorage;
    storage.setItem('user_name',  matched.name);
    storage.setItem('user_email', matched.email);

    showAlert(`[Demo] Selamat datang, ${matched.name}! Login berhasil.`, 'success');
    setTimeout(() => {
      alert(`✅ Login berhasil!\n\nNama: ${matched.name}\nEmail: ${matched.email}\n\n(Demo mode – server belum terhubung)`);
    }, 500);
  } else {
    showAlert('[Demo] Email atau password salah. Coba: admin@indofood.com / admin123');
  }
}

// ── Forgot Password Modal ───────────────────────────────────────────
forgotLink.addEventListener('click', (e) => {
  e.preventDefault();
  modalOverlay.classList.add('open');
  resetEmail.value = emailInput.value; // prefill if possible
  modalFeedback.textContent = '';
  modalFeedback.className = 'modal-feedback';
});

function closeModal() {
  modalOverlay.classList.remove('open');
}

modalClose.addEventListener('click', closeModal);
modalOverlay.addEventListener('click', (e) => {
  if (e.target === modalOverlay) closeModal();
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeModal();
});

resetBtn.addEventListener('click', async () => {
  const email = resetEmail.value.trim();
  if (!isValidEmail(email)) {
    modalFeedback.textContent = 'Masukkan email yang valid.';
    modalFeedback.className = 'modal-feedback error';
    return;
  }

  resetBtn.disabled = true;
  resetBtn.textContent = 'Mengirim…';

  try {
    const response = await fetch(`${API_BASE}/forgot-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    const data = await response.json();
    modalFeedback.textContent = data.message || 'Instruksi telah dikirim ke email Anda.';
    modalFeedback.className = 'modal-feedback ' + (response.ok ? 'success' : 'error');
  } catch {
    // Demo mode
    modalFeedback.textContent = `[Demo] Instruksi reset dikirim ke ${email}`;
    modalFeedback.className = 'modal-feedback success';
  } finally {
    resetBtn.disabled = false;
    resetBtn.textContent = 'Kirim Instruksi';
    if (modalFeedback.classList.contains('success')) {
      setTimeout(closeModal, 2500);
    }
  }
});

// ── On Page Load ────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  // Check if user is already logged in
  const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
  if (token) {
    const name = localStorage.getItem('user_name') || sessionStorage.getItem('user_name') || 'Pengguna';
    showAlert(`Anda sudah login sebagai ${name}.`, 'success');
  }

  // Autofocus email field
  emailInput.focus();
});
