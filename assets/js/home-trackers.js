(() => {
  const feature = document.querySelector("#trackers");
  const controls = feature.querySelector(".tracker-controls");
  const choices = [...controls.querySelectorAll("[aria-controls]")];
  const slides = choices.map(button => document.getElementById(button.getAttribute("aria-controls")));
  const play = controls.querySelector(".tracker-play");
  const motion = matchMedia("(prefers-reduced-motion: reduce)");
  const dwell = 8000;
  let current = 0, paused = motion.matches, visible = false, hovering = false, timer;

  function schedule() {
    clearTimeout(timer);
    const frame = slides[current].querySelector("iframe");
    if (visible && !document.hidden && !hovering && !paused && frame && !frame.hasAttribute("data-loading")) {
      timer = setTimeout(() => show((current + 1) % slides.length), dwell);
    }
  }

  function pause(value) {
    paused = value;
    play.textContent = value ? "Play" : "Pause";
    play.setAttribute("aria-label", (value ? "Start" : "Pause") + " automatic switching");
    schedule();
  }

  function load(slide) {
    if (slide.querySelector("iframe")) return;
    const frame = document.createElement("iframe");
    frame.title = slide.querySelector("h2").textContent + " Interactive tracker";
    frame.setAttribute("data-loading", "");
    frame.addEventListener("load", () => {
      const doc = frame.contentDocument;
      const main = doc && doc.querySelector("main");
      const ready = () => { frame.removeAttribute("data-loading"); schedule(); };
      if (!main) { ready(); return; }

      // Reuse the actual release and its controls; compact styling is local to this frame.
      const css = doc.createElement("link");
      css.rel = "stylesheet";
      css.href = feature.dataset.embedStyle;
      css.onload = () => {
        const fit = () => {
          if (!slide.hidden) frame.style.height = Math.min(540, Math.ceil(main.getBoundingClientRect().height) + 2) + "px";
        };
        new ResizeObserver(fit).observe(main);
        fit();
        frame.contentWindow.dispatchEvent(new Event("resize"));
        ready();
      };
      css.onerror = ready;
      doc.head.append(css);
      for (const event of ["pointerdown", "focusin", "keydown", "wheel"]) {
        doc.addEventListener(event, () => pause(true), { capture: true, passive: true });
      }
    }, { once: true });
    frame.src = slide.querySelector("a").href;
    slide.querySelector(".tracker-canvas").append(frame);
  }

  function show(index) {
    current = index;
    slides.forEach((slide, i) => {
      slide.hidden = i !== index;
      choices[i].setAttribute("aria-pressed", String(i === index));
    });
    if (visible) load(slides[current]);
    schedule();
  }

  choices.forEach((button, i) => button.addEventListener("click", () => { pause(true); show(i); }));
  play.addEventListener("click", () => pause(!paused));
  feature.addEventListener("focusin", event => { if (event.target !== play) pause(true); });
  for (const canvas of feature.querySelectorAll(".tracker-canvas")) {
    canvas.addEventListener("pointerenter", event => { hovering = event.pointerType === "mouse"; schedule(); });
    canvas.addEventListener("pointerleave", () => { hovering = false; schedule(); });
  }
  document.addEventListener("visibilitychange", schedule);
  motion.addEventListener("change", () => { if (motion.matches) pause(true); });
  controls.hidden = false;
  show(0);
  pause(paused);
  new IntersectionObserver(([entry]) => {
    visible = entry.isIntersecting;
    if (visible) load(slides[current]);
    schedule();
  }, { threshold: 0.2 }).observe(feature);
})();
