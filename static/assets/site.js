const header = document.querySelector("[data-header]");
const menuButton = document.querySelector("[data-menu-button]");
const mobileNav = document.querySelector("[data-mobile-nav]");

function updateHeader() {
  header?.classList.toggle("is-scrolled", window.scrollY > 16);
}

updateHeader();
window.addEventListener("scroll", updateHeader, { passive: true });

menuButton?.addEventListener("click", () => {
  const open = !mobileNav.classList.contains("is-open");
  mobileNav.classList.toggle("is-open", open);
  menuButton.setAttribute("aria-expanded", String(open));
});

mobileNav?.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", () => {
    mobileNav.classList.remove("is-open");
    menuButton?.setAttribute("aria-expanded", "false");
  });
});

const revealObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        revealObserver.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.16, rootMargin: "0px 0px -40px 0px" }
);

document.querySelectorAll(".reveal").forEach((el) => revealObserver.observe(el));

window.setTimeout(() => {
  document.querySelectorAll(".reveal:not(.is-visible)").forEach((el) => {
    el.classList.add("is-visible");
  });
}, 900);

document.querySelectorAll("[data-glow]").forEach((host) => {
  host.addEventListener("pointermove", (event) => {
    const rect = host.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 100;
    const y = ((event.clientY - rect.top) / rect.height) * 100;
    host.style.setProperty("--mx", `${x}%`);
    host.style.setProperty("--my", `${y}%`);
  });
});

document.querySelectorAll("[data-tilt]").forEach((host) => {
  const reset = () => {
    host.style.setProperty("--tilt-x", "0deg");
    host.style.setProperty("--tilt-y", "0deg");
    host.style.setProperty("--lift", "0px");
  };

  host.addEventListener("pointermove", (event) => {
    const rect = host.getBoundingClientRect();
    const px = ((event.clientX - rect.left) / rect.width - 0.5) * 2;
    const py = ((event.clientY - rect.top) / rect.height - 0.5) * 2;
    host.style.setProperty("--tilt-y", `${px * 4}deg`);
    host.style.setProperty("--tilt-x", `${py * -4}deg`);
    host.style.setProperty("--lift", "8px");
  });

  host.addEventListener("pointerleave", reset);
  reset();
});

document.querySelectorAll("[data-tool]").forEach((tool) => {
  tool.addEventListener("mouseenter", () => {
    document.querySelectorAll("[data-tool]").forEach((el) => el.classList.remove("is-active"));
    tool.classList.add("is-active");
  });
});

const prayerToggle = document.querySelector("[data-prayer-toggle]");
const prayerPanel = document.querySelector("[data-prayer-panel]");

prayerToggle?.addEventListener("click", () => {
  const open = !prayerPanel?.classList.contains("is-open");
  prayerPanel?.classList.toggle("is-open", open);
  prayerPanel?.setAttribute("aria-hidden", String(!open));
  prayerToggle.setAttribute("aria-expanded", String(open));

  if (open) {
    window.setTimeout(() => {
      prayerPanel?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 360);
  }
});
