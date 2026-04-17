// Central API handler — all fetch calls go here

const BASE_URL = "http://localhost:8000";

// Get token from localStorage
function getToken() {
    return localStorage.getItem("token");
}

// Get current user from localStorage
function getUser() {
    const user = localStorage.getItem("user");
    return user ? JSON.parse(user) : null;
}

// Save login data
function saveAuth(token, user) {
    localStorage.setItem("token", token);
    localStorage.setItem("user", JSON.stringify(user));
}

// Clear login data
function clearAuth() {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
}

// Check if logged in
function isLoggedIn() {
    return !!getToken();
}

// Redirect based on role
function redirectByRole(role) {
    if (role === "manager")  window.location.href = "manager.html";
    if (role === "employee") window.location.href = "employee.html";
    if (role === "expert")   window.location.href = "expert.html";
}

// Main API call function
async function apiCall(method, endpoint, body = null) {
    const headers = {
        "Content-Type": "application/json"
    };

    const token = getToken();
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    const config = { method, headers };
    if (body) config.body = JSON.stringify(body);

    try {
        const response = await fetch(`${BASE_URL}${endpoint}`, config);
        const data = await response.json();

        if (response.status === 401) {
            clearAuth();
            window.location.href = "index.html";
            return null;
        }

        return { ok: response.ok, status: response.status, data };
    } catch (error) {
        return { ok: false, data: { detail: "Cannot connect to server" } };
    }
}

// Shorthand functions
const api = {
    get:    (endpoint)       => apiCall("GET",    endpoint),
    post:   (endpoint, body) => apiCall("POST",   endpoint, body),
    put:    (endpoint, body) => apiCall("PUT",    endpoint, body),
    delete: (endpoint)       => apiCall("DELETE", endpoint)
};