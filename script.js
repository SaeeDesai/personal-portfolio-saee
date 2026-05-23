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

        menuBtn.addEventListener("click", () => {
            navbar.classList.toggle("active");
            menuIcon.classList.toggle("bx-menu");
            menuIcon.classList.toggle("bx-x");
        });

        navLinks.forEach((link) => {
            link.addEventListener("click", () => {
                navbar.classList.remove("active");
                menuIcon.classList.add("bx-menu");
                menuIcon.classList.remove("bx-x");
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
