// Injects a handful of softly rising particles into the animated background.
(function () {
  const container = document.createElement("div");
  container.className = "bg-particles";
  const count = 18;
  for (let i = 0; i < count; i++) {
    const p = document.createElement("span");
    const left = Math.random() * 100;
    const size = 4 + Math.random() * 8;
    const duration = 12 + Math.random() * 14;
    const delay = Math.random() * duration;
    p.style.left = left + "vw";
    p.style.width = size + "px";
    p.style.height = size + "px";
    p.style.animationDuration = duration + "s";
    p.style.animationDelay = "-" + delay + "s";
    container.appendChild(p);
  }
  document.body.insertBefore(container, document.body.firstChild);
})();
