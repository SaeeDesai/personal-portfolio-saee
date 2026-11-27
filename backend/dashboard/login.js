"use strict";

const form = document.getElementById("login-form");
const button = document.getElementById("login-button");
const loginStatus = document.getElementById("login-status");

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    button.disabled = true;
    button.textContent = "Signing in...";
    loginStatus.textContent = "";

    try {
        const response = await fetch("/auth/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            credentials: "same-origin",
            body: JSON.stringify({
                username: document.getElementById("username").value,
                password: document.getElementById("password").value,
            }),
        });

        if (response.ok) {
            window.location.replace("/dashboard");
            return;
        }

        loginStatus.textContent = response.status === 401
            ? "Invalid username or password."
            : "Unable to sign in. Please try again.";

    } catch {
        loginStatus.textContent = "Unable to connect to PortfolioPulse.";

    } finally {
        document.getElementById("password").value = "";
        button.disabled = false;
        button.textContent = "Sign in";
    }
});