const menuBtn = document.querySelector("#menu-icon");
const menuIcon = document.querySelector("#menu-icon i");
const navbar = document.querySelector(".navbar");
const navLinks = document.querySelectorAll(".navbar a");
const header = document.querySelector(".header");
const themeToggle = document.querySelector("#theme-toggle");
const themeIcon = document.querySelector("#theme-toggle i");
const sections = document.querySelectorAll("section");
const revealElements = document.querySelectorAll(".reveal");

document.querySelector("#year").textContent = new Date().getFullYear();

const savedTheme = localStorage.getItem("theme");
if (savedTheme === "dark") {
    document.body.classList.add("dark");
    themeIcon.classList.replace("bx-moon", "bx-sun");
}

const updateThemeButton = () => {
    const isDark = document.body.classList.contains("dark");

    themeToggle.setAttribute(
        "aria-label",
        isDark ? "Switch to light mode" : "Switch to dark mode"
    );

    themeToggle.setAttribute("aria-pressed", String(isDark));
};

updateThemeButton();

themeToggle.addEventListener("click", () => {
    document.body.classList.toggle("dark");

    const isDark = document.body.classList.contains("dark");

    localStorage.setItem("theme", isDark ? "dark" : "light");

    themeIcon.classList.toggle("bx-moon", !isDark);
    themeIcon.classList.toggle("bx-sun", isDark);

    updateThemeButton();
});

menuBtn.addEventListener("click", () => {
    const isOpen = navbar.classList.toggle("active");

    menuIcon.classList.toggle("bx-menu", !isOpen);
    menuIcon.classList.toggle("bx-x", isOpen);

    menuBtn.setAttribute("aria-expanded", String(isOpen));
    menuBtn.setAttribute(
        "aria-label",
        isOpen ? "Close navigation menu" : "Open navigation menu"
    );
});

navLinks.forEach((link) => {
    link.addEventListener("click", () => {
        navbar.classList.remove("active");
        menuIcon.classList.add("bx-menu");
        menuIcon.classList.remove("bx-x");
        menuBtn.setAttribute("aria-expanded", "false");
        menuBtn.setAttribute("aria-label", "Open navigation menu");
    });
});

themeToggle.addEventListener("click", () => {
    document.body.classList.toggle("dark");
    const isDark = document.body.classList.contains("dark");
    localStorage.setItem("theme", isDark ? "dark" : "light");
    themeIcon.classList.toggle("bx-moon", !isDark);
    themeIcon.classList.toggle("bx-sun", isDark);
});

window.addEventListener("scroll", () => {
    header.classList.toggle("scrolled", window.scrollY > 40);

    let current = "";
    sections.forEach((section) => {
        const sectionTop = section.offsetTop - 160;
        if (window.scrollY >= sectionTop) {
            current = section.getAttribute("id");
        }
    });

    navLinks.forEach((link) => {
        link.classList.remove("active");
        if (link.getAttribute("href") === `#${current}`) {
            link.classList.add("active");
        }
    });
});

const revealObserver = new IntersectionObserver(
    (entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.classList.add("show");
            }
        });
    },
    { threshold: 0.15 }
);

revealElements.forEach((el) => revealObserver.observe(el));
