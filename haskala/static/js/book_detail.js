// book_detail.js
//
// Hosts the small client-side helpers that live on the entity detail
// pages (book, person, place):
//   1. TOC active-link highlighting driven by IntersectionObserver
//   2. Permalink copy buttons (any element with data-permalink)
//   3. "Show more" toggle on long text blocks (.detail-clamp)
//
// The page template ships this as <script type="module">; we wait for
// DOMContentLoaded and gracefully exit when the expected DOM nodes are
// missing so this file is also safe to include on pages that only have
// some of these features.

document.addEventListener("DOMContentLoaded", () => {
    initTocHighlight();
    initPermalinkButtons();
    initClampToggles();
});

// ---- 1. TOC active-link highlighting --------------------------------

function initTocHighlight() {
    const tocLinks = Array.from(document.querySelectorAll(
        ".book-toc__link, .person-toc__link, .place-toc__link"
    ));
    if (tocLinks.length === 0) return;
    if (typeof IntersectionObserver !== "function") return;

    const sections = tocLinks
        .map((link) => {
            const href = link.getAttribute("href") || "";
            if (!href.startsWith("#")) return null;
            const id = href.slice(1);
            const el = document.getElementById(id);
            return el ? { id, el, link } : null;
        })
        .filter(Boolean);

    if (sections.length === 0) return;

    const byId = new Map(sections.map((s) => [s.id, s.link]));
    const currentlyVisible = new Set();

    const observer = new IntersectionObserver((entries) => {
        for (const entry of entries) {
            if (entry.isIntersecting) currentlyVisible.add(entry.target.id);
            else currentlyVisible.delete(entry.target.id);
        }
        // Highlight the first section in document order that's visible.
        let active = null;
        for (const section of sections) {
            if (currentlyVisible.has(section.id)) {
                active = section.id;
                break;
            }
        }
        for (const link of byId.values()) link.classList.remove("is-active");
        if (active) byId.get(active).classList.add("is-active");
    }, {
        // Trigger when the section's top is between 80px from the top
        // and 60% down the viewport. Sticky header sits at the top.
        rootMargin: "-80px 0px -40% 0px",
        threshold: 0,
    });

    for (const section of sections) observer.observe(section.el);
}

// ---- 2. Permalink copy ----------------------------------------------

function initPermalinkButtons() {
    const buttons = document.querySelectorAll("[data-permalink]");
    if (buttons.length === 0) return;

    buttons.forEach((btn) => {
        btn.addEventListener("click", async (event) => {
            event.preventDefault();
            const url = btn.dataset.permalink || window.location.href;
            const ok = await copyToClipboard(url);
            flashLabel(btn, ok ? "Copied!" : "Copy failed");
        });
    });

    // Inside the cite modal, every code block gets a "Copy" affordance.
    document.querySelectorAll("[data-copy-target]").forEach((btn) => {
        btn.addEventListener("click", async (event) => {
            event.preventDefault();
            const selector = btn.dataset.copyTarget;
            const target = selector ? document.querySelector(selector) : null;
            const text = target ? (target.innerText || target.textContent || "") : "";
            const ok = await copyToClipboard(text.trim());
            flashLabel(btn, ok ? "Copied!" : "Copy failed");
        });
    });
}

async function copyToClipboard(text) {
    try {
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(text);
            return true;
        }
        // Fallback for older browsers / non-https contexts.
        const ta = document.createElement("textarea");
        ta.value = text;
        ta.setAttribute("readonly", "");
        ta.style.position = "fixed";
        ta.style.left = "-9999px";
        document.body.appendChild(ta);
        ta.select();
        const ok = document.execCommand("copy");
        document.body.removeChild(ta);
        return ok;
    } catch (e) {
        return false;
    }
}

function flashLabel(btn, message, ms = 1500) {
    const original = btn.innerHTML;
    btn.innerHTML = `<span>${message}</span>`;
    btn.disabled = true;
    setTimeout(() => {
        btn.innerHTML = original;
        btn.disabled = false;
    }, ms);
}

// ---- 3. Show-more clamp ---------------------------------------------

function initClampToggles() {
    document.querySelectorAll(".detail-clamp").forEach((block) => {
        // Only attach a toggle when the block is actually overflowing.
        if (block.scrollHeight <= block.clientHeight + 1) return;

        const toggle = document.createElement("button");
        toggle.type = "button";
        toggle.className = "detail-clamp-toggle btn btn-link p-0";
        toggle.textContent = "Show more";
        toggle.setAttribute("aria-expanded", "false");

        toggle.addEventListener("click", () => {
            const expanded = block.classList.toggle("is-expanded");
            toggle.setAttribute("aria-expanded", String(expanded));
            toggle.textContent = expanded ? "Show less" : "Show more";
        });

        block.insertAdjacentElement("afterend", toggle);
    });
}
