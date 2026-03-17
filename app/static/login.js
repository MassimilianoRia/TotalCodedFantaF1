const tokenKey = "fantaf1_token";
const messageBox = document.getElementById("messageBox");
const email = document.getElementById("email");
const password = document.getElementById("password");

if (localStorage.getItem(tokenKey)) {
  location.href = "/app";
}

function show(msg) {
  messageBox.textContent = msg;
}

async function call(path, payload) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
  return data;
}

async function authenticate(endpoint) {
  try {
    const payload = { email: email.value.trim(), password: password.value };
    if (!payload.email || !payload.password) throw new Error("Inserisci email e password");
    const out = await call(endpoint, payload);
    localStorage.setItem(tokenKey, out.access_token);
    location.href = "/app";
  } catch (err) {
    show(err.message);
  }
}

document.getElementById("loginBtn").onclick = () => authenticate("/auth/login");
document.getElementById("registerBtn").onclick = () => authenticate("/auth/register");
