(() => {
  /* —— Lazy load splash —— */
  const pageLoader = document.getElementById("pageLoader");
  if (pageLoader) {
    document.body.classList.add("is-loading");
    let loaderRemoved = false;
    const hideLoader = () => {
      if (loaderRemoved) return;
      loaderRemoved = true;
      pageLoader.classList.add("hidden");
      document.body.classList.remove("is-loading");
      setTimeout(() => pageLoader.remove(), 700);
    };
    if (document.readyState === "complete") {
      setTimeout(hideLoader, 480);
    } else {
      window.addEventListener("load", () => setTimeout(hideLoader, 480));
      // Safety fallback to hide loader anyway after 2 seconds
      setTimeout(hideLoader, 2000);
    }
  }

  /* —— UI global: island + scroll reveal —— */
  const islandWrap = document.getElementById("islandNav");
  const reveals = document.querySelectorAll(".reveal");

  if (reveals.length) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );
    reveals.forEach((el) => observer.observe(el));
  }

  if (islandWrap) {
    window.addEventListener(
      "scroll",
      () => {
        islandWrap.classList.toggle("scrolled", window.scrollY > 60);
      },
      { passive: true }
    );

    const sections = ["fitur", "cara-pakai", "belajar"];
    const navLinks = document.querySelectorAll(".island-links a[data-section]");

    if (navLinks.length && sections.length) {
      const sectionObserver = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              const id = entry.target.id;
              navLinks.forEach((link) => {
                link.classList.toggle("active", link.dataset.section === id);
              });
            }
          });
        },
        { threshold: 0.35, rootMargin: "-30% 0px -55% 0px" }
      );
      sections.forEach((id) => {
        const el = document.getElementById(id);
        if (el) sectionObserver.observe(el);
      });
    }
  }

  document.querySelectorAll('.island-links a[href^="#"], .island-cta[href^="#"]').forEach((link) => {
    link.addEventListener("click", (e) => {
      const id = link.getAttribute("href");
      if (id?.startsWith("#") && document.querySelector(id)) {
        e.preventDefault();
        const targetEl = document.querySelector(id);
        const rect = targetEl.getBoundingClientRect();
        const top = rect.top + window.pageYOffset - 140; // Perfect offset to center head below glass nav
        window.scrollTo({ top, behavior: "smooth" });
      }
    });
  });

  /* —— 3D Polar Scroll Wheel Carousel with Sticky Pinning & Inertia Physics —— */
  const track = document.querySelector(".hero-scroll-track");
  const collage = document.querySelector(".hero-collage");
  const collageCards = document.querySelectorAll(".collage-img");
  
  if (track && collage && collageCards.length) {
    let targetProgress = 0;
    let currentProgress = 0;
    const ease = 0.08; // Physics LERP ease factor (0.08 creates a highly organic momentum)
    let animationFrameId = null;
    
    window.addEventListener("scroll", () => {
      const rect = track.getBoundingClientRect();
      const trackHeight = rect.height;
      const scrolled = -rect.top; // Pixels scrolled past the top of the track container
      const scrollable = trackHeight - window.innerHeight;
      
      // Calculate scroll progress (0.0 to 1.0)
      let progress = scrolled / scrollable;
      progress = Math.max(0, Math.min(1, progress));
      
      targetProgress = progress;
      startLoop();
    }, { passive: true });
    
    function updateCarousel() {
      // Linear interpolation to catch up to target progress
      currentProgress += (targetProgress - currentProgress) * ease;
      
      // Stop the animation loop if we are extremely close
      if (Math.abs(targetProgress - currentProgress) < 0.001) {
        currentProgress = targetProgress;
      }
      
      const speed = 65; // Total rotation angle over the entire track scroll
      const rect = collage.getBoundingClientRect();
      const width = rect.width || 450;
      const height = rect.height || 480;
      
      const centerY = height / 2;
      const centerX = width * 1.05; // Center X placed beautifully inside or slightly right
      const radius = width * 0.88; // Radial offset
      
      // Calculate fly-away exit parameters at the end of scroll track (above 80% scroll progress)
      let exitOffset = 0;
      let exitScale = 1;
      let exitOpacity = 1;
      
      if (currentProgress > 0.88) {
        const exitProgress = (currentProgress - 0.88) / 0.12; // Normalize to 0.0 - 1.0 over the last 12%
        exitOffset = exitProgress * 450; // Slide 450px to the right
        exitScale = 1 - (exitProgress * 0.9); // Shrink cards down
        exitOpacity = 1 - exitProgress; // Fade out completely
      }
      
      collageCards.forEach((card, index) => {
        // Distribute cards symmetrically
        const baseAngle = 180 + (index - 2.5) * 18; 
        const currentAngle = baseAngle + (currentProgress * speed); // Add to rotate in reverse direction
        
        const rad = (currentAngle * Math.PI) / 180;
        
        // Calculate coordinates dynamically relative to actual container geometry and exit flight
        let x = centerX + radius * Math.cos(rad);
        x += exitOffset; // Add exit flight to the right
        
        const cardHeight = card.offsetHeight || 335;
        const y = centerY + radius * Math.sin(rad) - (cardHeight / 2);
        
        // Z-Index priority for center card
        const angleFromCenter = Math.abs(currentAngle - 180);
        const zIndex = Math.max(1, 20 - Math.round(angleFromCenter / 4));
        
        // Tilt matching the circular angle perfectly
        const rotationAngle = currentAngle - 180;
        
        // 3D scale and translate3d pop-out to make it feel organic and deep
        const distancePercent = Math.max(0, 1 - (angleFromCenter / 50)); // 1.0 when active at 180deg, 0.0 when far
        const scale = (0.78 + (distancePercent * 0.22)) * exitScale; // Combined with exitScale
        const zTranslate = distancePercent * 85; // 3D depth pop out in pixels
        
        // Y-axis tilt based on rotation angle to give a spherical rotation look
        const rotateY = - (rotationAngle * 0.45);
        
        card.style.transform = `translate3d(${x}px, ${y}px, ${zTranslate}px) scale(${scale}) rotate(${rotationAngle}deg) rotateY(${rotateY}deg)`;
        card.style.zIndex = zIndex;
        
        // Combined opacity combines position-based fade and exit flight fade
        const opacity = Math.max(0, 1.3 - (angleFromCenter / 45)) * exitOpacity;
        card.style.opacity = opacity;
        
        // Highlight center active card
        if (angleFromCenter < 9) {
          card.classList.add("active-center");
        } else {
          card.classList.remove("active-center");
        }
      });
      
      // Continue the rendering loop if inertia is still active
      if (Math.abs(targetProgress - currentProgress) >= 0.001) {
        animationFrameId = requestAnimationFrame(updateCarousel);
      } else {
        animationFrameId = null;
      }
    }
    
    function startLoop() {
      if (!animationFrameId) {
        animationFrameId = requestAnimationFrame(updateCarousel);
      }
    }
    
    // Initial draw
    updateCarousel();
    
    // Recalculate on screen resize to keep carousel perfectly positioned
    window.addEventListener("resize", () => {
      startLoop();
    }, { passive: true });
  }

  /* —— Guide page active section & smooth scroll click handler —— */
  const guideLinks = document.querySelectorAll(".guide-nav-link");
  const guideSections = document.querySelectorAll(".guide-content section");
  
  if (guideLinks.length && guideSections.length) {
    // 1. Precise click handler for immediate sidebar highlights and scroll positioning
    guideLinks.forEach((link) => {
      link.addEventListener("click", (e) => {
        const id = link.getAttribute("href");
        if (id?.startsWith("#") && document.querySelector(id)) {
          e.preventDefault();
          
          // Switch active state immediately without waiting for scroll lag
          guideLinks.forEach((l) => l.classList.remove("active"));
          link.classList.add("active");
          
          const targetSection = document.querySelector(id);
          // Show the card fully immediately (tampil full di awal)
          targetSection.classList.add("visible");
          
          // Precise absolute scrolling coordinate offset from body
          const rect = targetSection.getBoundingClientRect();
          const top = rect.top + window.pageYOffset - 120; // 120px offset fits below navbar perfectly
          
          window.scrollTo({ top, behavior: "smooth" });
        }
      });
    });

    // 2. Observer for updating sidebar highlight on manual scrolls
    const guideObserver = new IntersectionObserver(
      () => {
        let activeId = null;
        let minDistance = Infinity;

        guideSections.forEach((sec) => {
          const rect = sec.getBoundingClientRect();
          // We target a line just below the glassmorphic navbar (approx 140px from the top)
          const targetLine = 140;
          const distance = Math.abs(rect.top - targetLine);

          // If the section is currently in view (below targetLine and above window bottom)
          if (rect.bottom > targetLine && rect.top < window.innerHeight) {
            if (distance < minDistance) {
              minDistance = distance;
              activeId = sec.id;
            }
          }
        });

        if (activeId) {
          guideLinks.forEach((link) => {
            link.classList.toggle("active", link.getAttribute("href") === `#${activeId}`);
          });
        }
      },
      {
        threshold: [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        rootMargin: "-120px 0px -40px 0px"
      }
    );
    guideSections.forEach((sec) => guideObserver.observe(sec));
  }

  const ICONS = {
    user: `<div class="avatar user-avatar" aria-hidden="true"></div>`,
    bot: `<div class="avatar bot-avatar" aria-hidden="true"></div>`,
  };

  const MODE_LABELS = {
    mendalam: "Mode mendalam",
    ringkas: "Mode ringkas",
    langkah: "Mode langkah",
  };

  const uploadZone = document.getElementById("uploadZone");
  const fileInput = document.getElementById("fileInput");
  const docInfo = document.getElementById("docInfo");
  const docName = document.getElementById("docName");
  const docStats = document.getElementById("docStats");
  const manualContext = document.getElementById("manualContext");
  const askForm = document.getElementById("askForm");
  const questionInput = document.getElementById("questionInput");
  const askBtn = document.getElementById("askBtn");
  const chatMessages = document.getElementById("chatMessages");
  const suggestionsEl = document.getElementById("suggestions");
  const modeChips = document.querySelectorAll(".mode-chip");
  const chatStatus = document.getElementById("chatStatus");
  const clearChatBtn = document.getElementById("clearChat");

  if (!chatMessages || !askForm) return;


  let documentId = null;
  let isLoading = false;
  let answerMode = "mendalam";
  let suggestTimer = null;

  const MIN_CONTEXT = 30;

  function escapeHtml(str) {
    const d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
  }

  function scrollChat() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function setStatus(text, loading = false) {
    if (!chatStatus) return;
    chatStatus.textContent = text;
    chatStatus.classList.toggle("loading", loading);
  }

  function autoResizeTextarea() {
    questionInput.style.height = "auto";
    questionInput.style.height = Math.min(questionInput.scrollHeight, 120) + "px";
  }

  const WELCOME_HTML = `
    <div class="message bot welcome-msg">
      <div class="avatar bot-avatar" aria-hidden="true"></div>
      <div class="bubble">
        <p><strong>Selamat belajar!</strong></p>
        <p>Unggah PDF atau tempel konteks, lalu ajukan pertanyaan.</p>
      </div>
    </div>
  `;

  function resetChat() {
    chatMessages.innerHTML = WELCOME_HTML;
    setStatus("Siap membantu");
  }

  /** Fallback ringan jika API gagal — tetap dari cuplikan kalimat */
  function localSuggestions(text) {
    const sentences = text
      .split(/(?<=[.!?])\s+/)
      .map((s) => s.trim())
      .filter((s) => s.length > 40)
      .slice(0, 4);
    const qs = [];
    sentences.forEach((s) => {
      const subj = s.split(/\s+(?:adalah|merupakan|terjadi)/i)[0]?.trim().slice(0, 35);
      if (subj && subj.length > 5) {
        qs.push(`Apa yang dimaksud dengan ${subj} menurut materi?`);
      }
      if (/mitos|legenda/i.test(s)) qs.push("Apa mitos yang disebutkan dalam teks?");
      if (/jenis|macam|terdapat/i.test(s)) qs.push("Apa saja yang disebutkan dalam bagian ini?");
    });
    return [...new Set(qs)].slice(0, 6);
  }

  function renderSuggestions(list) {
    if (!list || list.length === 0) {
      suggestionsEl.innerHTML =
        '<p class="muted empty-hint">Tempel materi minimal 30 karakter untuk melihat saran.</p>';
      return;
    }
    suggestionsEl.innerHTML = list
      .map((q) => `<button type="button" class="suggestion-chip">${escapeHtml(q)}</button>`)
      .join("");

    suggestionsEl.querySelectorAll(".suggestion-chip").forEach((btn) => {
      btn.addEventListener("click", () => {
        questionInput.value = btn.textContent;
        autoResizeTextarea();
        askForm.requestSubmit();
      });
    });
  }

  async function fetchSuggestions() {
    const context = manualContext.value.trim();

    if (documentId) {
      try {
        const res = await fetch("/api/suggestions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ document_id: documentId }),
        });
        if (res.ok) {
          const data = await res.json();
          renderSuggestions(data.suggestions);
          return;
        }
      } catch {
        /* fallback below */
      }
    }

    if (context.length < MIN_CONTEXT) {
      renderSuggestions([]);
      return;
    }

    try {
      const res = await fetch("/api/suggestions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ context }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.suggestions?.length) {
          renderSuggestions(data.suggestions);
          return;
        }
      }
    } catch {
      /* use local fallback */
    }

    renderSuggestions(localSuggestions(context));
  }

  function scheduleSuggestions() {
    clearTimeout(suggestTimer);
    suggestTimer = setTimeout(fetchSuggestions, 400);
  }

  function onContextChange() {
    const len = manualContext.value.trim().length;
    if (len >= MIN_CONTEXT) {
      documentId = null;
      docInfo.classList.add("hidden");
      scheduleSuggestions();
    } else if (!documentId) {
      renderSuggestions([]);
    }
  }

  function formatAnswer(data) {
    const mode = data.mode || answerMode;
    const modeTag = `<span class="mode-tag">${escapeHtml(MODE_LABELS[mode] || mode)}</span>`;

    if (data.answer.startsWith("Maaf, materi")) {
      return modeTag + `<p>${escapeHtml(data.answer)}</p>`;
    }

    let body;
    if (mode === "langkah") {
      const lines = data.answer.split(/\n/).filter((l) => l.trim());
      const introLine = lines[0]?.endsWith(":") ? lines.shift() : null;
      const items = lines
        .map((line) => {
          const m = line.match(/^\d+\.\s*(.+)/);
          return `<li>${escapeHtml(m ? m[1] : line)}</li>`;
        })
        .join("");
      body = (introLine ? `<p>${escapeHtml(introLine)}</p>` : "") + `<ol class="steps-list">${items}</ol>`;
    } else {
      const parts = data.answer.split(/\n\n+/);
      body = parts.map((p) => `<p>${escapeHtml(p).replace(/\n/g, "<br>")}</p>`).join("");
    }

    let points = "";
    if (mode === "mendalam" && data.key_points?.length) {
      points =
        '<div class="answer-section"><div class="answer-section-title">Poin penting</div><ul class="key-points">' +
        data.key_points.map((p) => `<li>${escapeHtml(p)}</li>`).join("") +
        "</ul></div>";
    }

    return modeTag + body + points;
  }

  function appendUserMessage(text) {
    const div = document.createElement("div");
    div.className = "message user";
    div.innerHTML = `${ICONS.user}<div class="bubble"><p>${escapeHtml(text)}</p></div>`;
    chatMessages.appendChild(div);
    scrollChat();
  }

  function appendBotMessage(data) {
    const div = document.createElement("div");
    div.className = "message bot";
    div.innerHTML = `${ICONS.bot}<div class="bubble">${formatAnswer(data)}</div>`;
    chatMessages.appendChild(div);
    scrollChat();
  }

  function appendError(text) {
    const div = document.createElement("div");
    div.className = "message error";
    div.innerHTML = `${ICONS.bot}<div class="bubble"><p>${escapeHtml(text)}</p></div>`;
    chatMessages.appendChild(div);
    scrollChat();
  }

  function showTyping() {
    const div = document.createElement("div");
    div.className = "message bot typing";
    div.id = "typingIndicator";
    div.innerHTML = `${ICONS.bot}<div class="bubble">
      <span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>
    </div>`;
    chatMessages.appendChild(div);
    scrollChat();
  }

  function hideTyping() {
    document.getElementById("typingIndicator")?.remove();
  }

  modeChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      modeChips.forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      answerMode = chip.dataset.mode;
      const labels = { mendalam: "Mode mendalam aktif", ringkas: "Mode ringkas aktif", langkah: "Mode langkah aktif" };
      setStatus(labels[answerMode] || "Siap membantu");
    });
  });

  clearChatBtn?.addEventListener("click", resetChat);

  async function uploadFile(file) {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      appendError("Hanya file PDF yang didukung.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/api/upload", { method: "POST", body: formData });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Gagal mengunggah");

      documentId = data.document_id;
      docName.textContent = data.filename;
      docStats.textContent = `${data.char_count.toLocaleString("id-ID")} karakter`;
      docInfo.classList.remove("hidden");
      manualContext.value = "";

      renderSuggestions(data.suggestions?.length ? data.suggestions : []);
      if (!data.suggestions?.length) fetchSuggestions();
      setStatus("Materi siap — silakan bertanya");

      appendBotMessage({
        answer: `Materi "${data.filename}" siap. Pilih mode jawaban lalu ajukan pertanyaan.`,
        mode: "mendalam",
        key_points: [],
      });
    } catch (err) {
      appendError(err.message);
    }
  }

  uploadZone.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", (e) => {
    if (e.target.files[0]) uploadFile(e.target.files[0]);
  });
  uploadZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadZone.classList.add("dragover");
  });
  uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("dragover"));
  uploadZone.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadZone.classList.remove("dragover");
    if (e.dataTransfer.files[0]) uploadFile(e.dataTransfer.files[0]);
  });

  manualContext.addEventListener("input", onContextChange);
  manualContext.addEventListener("paste", () => setTimeout(onContextChange, 50));
  manualContext.addEventListener("blur", onContextChange);

  questionInput.addEventListener("input", autoResizeTextarea);
  questionInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      askForm.requestSubmit();
    }
  });

  askForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (isLoading) return;

    const question = questionInput.value.trim();
    if (!question) return;

    const context = manualContext.value.trim();
    if (!documentId && !context) {
      appendError("Unggah PDF atau tempel konteks teks terlebih dahulu.");
      return;
    }

    appendUserMessage(question);
    questionInput.value = "";
    autoResizeTextarea();
    isLoading = true;
    askBtn.disabled = true;
    setStatus("Menyusun jawaban...", true);
    showTyping();

    const payload = { question, mode: answerMode };
    if (documentId) payload.document_id = documentId;
    else payload.context = context;

    try {
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Gagal mendapatkan jawaban");

      hideTyping();
      data.mode = answerMode;
      appendBotMessage(data);
      setStatus("Siap membantu");
    } catch (err) {
      hideTyping();
      appendError(err.message);
      setStatus("Terjadi kesalahan");
    } finally {
      isLoading = false;
      askBtn.disabled = false;
      questionInput.focus();
    }
  });

  if (manualContext?.value.trim().length >= MIN_CONTEXT) {
    onContextChange();
  }
})();
