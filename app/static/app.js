(function () {
  const tabs = document.querySelectorAll(".tab");
  const panels = {
    cvd: document.getElementById("panel-cvd"),
    colorize: document.getElementById("panel-colorize"),
    restore: document.getElementById("panel-restore"),
    upscale: document.getElementById("panel-upscale"),
    advupscale: document.getElementById("panel-advupscale"),
  };
  const loading = document.getElementById("loading");
  const loadingText = loading?.querySelector(".loading-text");
  const errBox = document.getElementById("error");
  const resultWrap = document.getElementById("result-wrap");
  const resultImg = document.getElementById("result-img");
  const resultMeta = document.getElementById("result-meta");
  const resultQuality = document.getElementById("result-quality");
  const pipelineWrap = document.getElementById("pipeline-wrap");
  const pipelineStepsEl = document.getElementById("pipeline-steps");
  const downloadLink = document.getElementById("download-link");
  const histWrap = document.getElementById("hist-wrap");
  const histInputCanvas = document.getElementById("hist-input");
  const histOutputCanvas = document.getElementById("hist-output");
  const histR = document.getElementById("hist-r");
  const histG = document.getElementById("hist-g");
  const histB = document.getElementById("hist-b");
  const histView = document.getElementById("hist-view");

  const compareWrap = document.getElementById("compare-wrap");
  const compareRange = document.getElementById("compare-range");
  const compareClip = document.getElementById("after-clip");
  const compareDivider = document.getElementById("compare-divider");
  const beforeImg = document.getElementById("before-img");
  const afterImg = document.getElementById("after-img");
  const cvdInsightsWrap = document.getElementById("cvd-insights");
  const cvdGridWrap = document.getElementById("cvd-grid-wrap");
  const cvdGridImg = document.getElementById("cvd-grid-img");
  const cvdGridDownload = document.getElementById("cvd-grid-download");
  const paletteWrap = document.getElementById("palette-wrap");
  const paletteSummary = document.getElementById("palette-summary");
  const paletteColors = document.getElementById("palette-colors");
  const paletteTableBody = document.querySelector("#palette-table tbody");
  const btnCvdGrid = document.getElementById("btn-cvd-grid");
  const btnPaletteSafety = document.getElementById("btn-palette-safety");

  const sev = document.getElementById("severity");
  const str = document.getElementById("strength");
  const sevVal = document.getElementById("sev-val");
  const strVal = document.getElementById("str-val");

  let activeTool = "cvd";
  const toolStates = {
    cvd: null,
    colorize: null,
    restore: null,
    upscale: null,
    advupscale: null,
  };
  const toolBusy = {
    cvd: false,
    colorize: false,
    restore: false,
    upscale: false,
    advupscale: false,
  };
  const toolLabels = {
    cvd: "Color blind",
    colorize: "Colorize Pro",
    restore: "Restore",
    upscale: "Upscale",
    advupscale: "Advanced Upscale",
  };

  if (sev && sevVal) {
    sev.addEventListener("input", () => {
      sevVal.textContent = sev.value;
    });
  }
  if (str && strVal) {
    str.addEventListener("input", () => {
      strVal.textContent = str.value;
    });
  }

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const name = tab.getAttribute("data-tab") || "cvd";
      activeTool = name;

      tabs.forEach((t) => {
        const on = t === tab;
        t.classList.toggle("active", on);
        t.setAttribute("aria-selected", on ? "true" : "false");
      });
      Object.entries(panels).forEach(([key, el]) => {
        if (!el) return;
        const on = key === name;
        el.classList.toggle("active", on);
        el.hidden = !on;
      });

      clearError();
      renderToolState(activeTool);
      updateLoadingUi();
    });
  });

  setupDropZones();
  [histR, histG, histB, histView].forEach((el) =>
    el?.addEventListener("change", () => {
      if (activeTool === "cvd") renderToolState(activeTool);
    })
  );

  compareRange?.addEventListener("input", () => {
    updateCompareSlider(Number(compareRange.value));
    const state = toolStates[activeTool];
    if (state) state.compareValue = Number(compareRange.value);
  });

  document.getElementById("form-cvd")?.addEventListener("submit", (e) => {
    e.preventDefault();
    submitForm(e.target, { json: "/colorblind/process-json", binary: "/colorblind/process" }, "colorblind", "cvd");
  });
  document.getElementById("form-colorize")?.addEventListener("submit", (e) => {
    e.preventDefault();
    submitForm(e.target, { json: "/colorize/process-json", binary: "/colorize/process" }, "colorize", "colorize");
  });
  document.getElementById("form-restore")?.addEventListener("submit", (e) => {
    e.preventDefault();
    submitForm(e.target, { json: "/restore/process-json", binary: "/restore/process" }, "restore", "restore");
  });
  document.getElementById("form-upscale")?.addEventListener("submit", (e) => {
    e.preventDefault();
    submitForm(e.target, { json: "/upscale/process-json", binary: "/upscale/process" }, "upscale", "upscale");
  });
  document.getElementById("form-adv-upscale")?.addEventListener("submit", (e) => {
    e.preventDefault();
    submitForm(
      e.target,
      { json: "/advanced-upscale/process-json", binary: "/advanced-upscale/process" },
      "advanced-upscale",
      "advupscale"
    );
  });
  btnCvdGrid?.addEventListener("click", async () => {
    await runCvdGrid();
  });
  btnPaletteSafety?.addEventListener("click", async () => {
    await runPaletteSafety();
  });

  function showError(msg) {
    errBox.textContent = msg;
    errBox.classList.remove("hidden");
  }

  function clearError() {
    errBox.textContent = "";
    errBox.classList.add("hidden");
  }

  function setBusy(toolKey, busy, form) {
    toolBusy[toolKey] = busy;
    if (form) {
      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn) submitBtn.disabled = busy;
    }
    updateLoadingUi();
  }

  function updateLoadingUi() {
    const busy = !!toolBusy[activeTool];
    loading.classList.toggle("hidden", !busy);
    if (loadingText) {
      loadingText.textContent = busy
        ? `Processing ${toolLabels[activeTool] || "image"}...`
        : "Processing...";
    }
  }

  function clearResultUiVisual() {
    resultWrap.classList.add("hidden");
    downloadLink.classList.add("hidden");
    downloadLink.removeAttribute("href");
    resultMeta.textContent = "";
    resultQuality.textContent = "";
    resultQuality.classList.add("hidden");
    pipelineWrap.classList.add("hidden");
    pipelineStepsEl.innerHTML = "";
    histWrap.classList.add("hidden");
    compareWrap.classList.add("hidden");
    resultImg.classList.add("hidden");
    beforeImg.src = "";
    afterImg.src = "";
    resultImg.src = "";
    cvdInsightsWrap.classList.add("hidden");
    cvdGridWrap.classList.add("hidden");
    cvdGridImg.src = "";
    cvdGridDownload.classList.add("hidden");
    cvdGridDownload.removeAttribute("href");
    paletteWrap.classList.add("hidden");
    paletteSummary.textContent = "";
    paletteColors.innerHTML = "";
    paletteTableBody.innerHTML = "";
  }

  function revokeStateUrls(state) {
    if (!state) return;
    if (state.resultObjectUrl) URL.revokeObjectURL(state.resultObjectUrl);
    if (state.originalObjectUrl) URL.revokeObjectURL(state.originalObjectUrl);
    if (state.gridObjectUrl) URL.revokeObjectURL(state.gridObjectUrl);
  }

  function clearToolState(toolKey) {
    revokeStateUrls(toolStates[toolKey]);
    toolStates[toolKey] = null;
  }

  function setToolState(toolKey, state) {
    clearToolState(toolKey);
    toolStates[toolKey] = state;
  }

  function renderToolState(toolKey) {
    clearResultUiVisual();
    const state = toolStates[toolKey];
    if (!state) return;

    resultMeta.textContent = state.metaText || "";
    if (state.qualityText) {
      resultQuality.textContent = state.qualityText;
      resultQuality.classList.remove("hidden");
    }
    if (Array.isArray(state.pipelineSteps) && state.pipelineSteps.length > 0) {
      pipelineWrap.classList.remove("hidden");
      pipelineStepsEl.innerHTML = "";
      state.pipelineSteps.forEach((s) => {
        const li = document.createElement("li");
        li.textContent = s;
        pipelineStepsEl.appendChild(li);
      });
    }

    if (state.useCompare) {
      beforeImg.src = state.originalObjectUrl;
      afterImg.src = state.resultObjectUrl;
      compareRange.value = String(state.compareValue ?? 50);
      updateCompareSlider(Number(compareRange.value));
      compareWrap.classList.remove("hidden");
    } else {
      resultImg.src = state.resultObjectUrl;
      resultImg.classList.remove("hidden");
    }

    downloadLink.href = state.resultObjectUrl;
    downloadLink.download = state.downloadName || "processed.png";
    downloadLink.classList.remove("hidden");
    resultWrap.classList.remove("hidden");

    if (state.histData) {
      renderHistogramFromState(state.histData);
      histWrap.classList.remove("hidden");
    }
    if (toolKey === "cvd") {
      renderCvdInsights(state);
    }
  }

  async function submitForm(form, endpoints, toolName, toolKey) {
    clearError();

    const fileInput = form.querySelector('input[name="file"]');
    const srcFile = fileInput?.files?.[0] ?? null;
    const inputFileBytes = srcFile ? srcFile.size : 0;
    setBusy(toolKey, true, form);
    try {
      const fdJson = new FormData(form);
      const jsonRes = await fetch(endpoints.json, { method: "POST", body: fdJson });
      if (!jsonRes.ok) throw new Error(await extractError(jsonRes));

      const payload = await jsonRes.json();
      const blob = base64ToBlob(payload.image, "image/png");
      const resultObjectUrl = URL.createObjectURL(blob);
      const meta = payload.meta || {};
      const inputMeta = meta.input || {};
      const outputMeta = meta.output || {};

      const inBytes = inputMeta.byte_size || inputFileBytes;
      const outBytes = outputMeta.byte_size || blob.size;
      const inW = inputMeta.width || "?";
      const inH = inputMeta.height || "?";
      const outW = outputMeta.width || "?";
      const outH = outputMeta.height || "?";
      const inFmt = inputMeta.format || "?";
      const outFmt = outputMeta.format || "PNG";
      const metaText =
        `Size: ${formatBytes(inBytes)} -> ${formatBytes(outBytes)} | ` +
        `Resolution: ${inW}x${inH} -> ${outW}x${outH} | ` +
        `Format: ${inFmt} -> ${outFmt}`;

      let qualityText = "";
      if (meta.quality && Number.isFinite(meta.quality.ssim) && Number.isFinite(meta.quality.psnr)) {
        qualityText =
          `Quality (vs input reference): SSIM ${meta.quality.ssim.toFixed(4)}, ` +
          `PSNR ${meta.quality.psnr.toFixed(2)} dB`;
      }

      let histData = null;
      if (toolName === "colorblind") {
        histData = await loadHistogram(form);
      }

      const originalObjectUrl = srcFile instanceof File ? URL.createObjectURL(srcFile) : null;
      setToolState(toolKey, {
        resultObjectUrl,
        originalObjectUrl,
        metaText,
        qualityText,
        pipelineSteps: meta.pipeline?.steps || [],
        histData,
        useCompare: srcFile instanceof File,
        compareValue: 50,
        downloadName: `${toolName}-result.png`,
      });
      renderToolState(activeTool);
    } catch (jsonError) {
      try {
        const fdBinary = new FormData(form);
        const binaryRes = await fetch(endpoints.binary, { method: "POST", body: fdBinary });
        if (!binaryRes.ok) throw new Error(await extractError(binaryRes));

        const blob = await binaryRes.blob();
        const resultObjectUrl = URL.createObjectURL(blob);
        const outDims = await imageDimensions(resultObjectUrl);
        const metaText =
          `Output: ${outDims.width}x${outDims.height} | ${formatBytes(blob.size)} ` +
          `(legacy response mode)`;

        const originalObjectUrl = srcFile instanceof File ? URL.createObjectURL(srcFile) : null;
        setToolState(toolKey, {
          resultObjectUrl,
          originalObjectUrl,
          metaText,
          qualityText: "",
          pipelineSteps: [],
          histData: null,
          useCompare: srcFile instanceof File,
          compareValue: 50,
          downloadName: `${toolName}-result.png`,
        });
        renderToolState(activeTool);
      } catch (binaryError) {
        showError(binaryError.message || jsonError.message || "Request failed");
        renderToolState(activeTool);
      }
    } finally {
      setBusy(toolKey, false, form);
    }
  }

  async function runCvdGrid() {
    const form = document.getElementById("form-cvd");
    const fileInput = document.getElementById("cvd-file");
    if (!fileInput?.files?.[0]) {
      showError("Choose an image in Color blind tab first.");
      return;
    }
    clearError();
    setBusy("cvd", true, form);
    try {
      const fd = new FormData(form);
      const res = await fetch("/colorblind/grid", { method: "POST", body: fd });
      if (!res.ok) throw new Error(await extractError(res));
      const payload = await res.json();
      const blob = base64ToBlob(payload.image, "image/png");
      const objectUrl = URL.createObjectURL(blob);
      const current = toolStates.cvd || {};
      if (current.gridObjectUrl) URL.revokeObjectURL(current.gridObjectUrl);
      toolStates.cvd = {
        ...current,
        gridObjectUrl: objectUrl,
        gridDescription: payload.meta?.description || "Original + 8 simulations",
      };
      if (activeTool === "cvd") renderToolState("cvd");
    } catch (e) {
      showError(e.message || "Failed to generate CVD grid");
    } finally {
      setBusy("cvd", false, form);
    }
  }

  async function runPaletteSafety() {
    const form = document.getElementById("form-cvd");
    const fileInput = document.getElementById("cvd-file");
    if (!fileInput?.files?.[0]) {
      showError("Choose an image in Color blind tab first.");
      return;
    }
    clearError();
    setBusy("cvd", true, form);
    try {
      const fd = new FormData(form);
      const res = await fetch("/colorblind/palette-safety", { method: "POST", body: fd });
      if (!res.ok) throw new Error(await extractError(res));
      const payload = await res.json();
      const current = toolStates.cvd || {};
      toolStates.cvd = {
        ...current,
        paletteData: payload,
      };
      if (activeTool === "cvd") renderToolState("cvd");
    } catch (e) {
      showError(e.message || "Failed to analyze palette safety");
    } finally {
      setBusy("cvd", false, form);
    }
  }

  function renderCvdInsights(state) {
    const hasGrid = !!state.gridObjectUrl;
    const hasPalette = !!state.paletteData;
    if (!hasGrid && !hasPalette) return;
    cvdInsightsWrap.classList.remove("hidden");
    if (hasGrid) {
      cvdGridWrap.classList.remove("hidden");
      cvdGridImg.src = state.gridObjectUrl;
      cvdGridDownload.href = state.gridObjectUrl;
      cvdGridDownload.classList.remove("hidden");
    }
    if (hasPalette) {
      paletteWrap.classList.remove("hidden");
      const data = state.paletteData;
      paletteSummary.textContent =
        `Risky pairs: ${data.summary?.risky_pair_count ?? 0}, ` +
        `Warning pairs: ${data.summary?.warning_pair_count ?? 0}, ` +
        `Total pairs: ${data.summary?.total_pairs ?? 0}.`;
      paletteColors.innerHTML = "";
      (data.palette || []).forEach((c) => {
        const el = document.createElement("div");
        el.className = "swatch";
        el.title = `${c.hex} (${c.rgb.join(", ")})`;
        el.style.background = c.hex;
        paletteColors.appendChild(el);
      });
      paletteTableBody.innerHTML = "";
      (data.pairs || []).forEach((p) => {
        const tr = document.createElement("tr");
        const protanopia = p.per_cvd?.protanopia;
        const deuteranopia = p.per_cvd?.deuteranopia;
        const tritanopia = p.per_cvd?.tritanopia;
        const protanomaly = p.per_cvd?.protanomaly;
        const deuteranomaly = p.per_cvd?.deuteranomaly;
        const tritanomaly = p.per_cvd?.tritanomaly;
        const metric = p.base_deltae ?? p.base_distance ?? "-";
        const className = p.risky_any ? "risk-bad" : p.warning_any ? "risk-warn" : "risk-good";
        const status = p.risky_any ? "Risky" : p.warning_any ? "Warning" : "Safe";
        tr.innerHTML = `
          <td>${p.pair?.[0]} - ${p.pair?.[1]}</td>
          <td>${metric}</td>
          <td>${formatRiskCell(protanopia)}</td>
          <td>${formatRiskCell(deuteranopia)}</td>
          <td>${formatRiskCell(tritanopia)}</td>
          <td>${formatRiskCell(protanomaly)}</td>
          <td>${formatRiskCell(deuteranomaly)}</td>
          <td>${formatRiskCell(tritanomaly)}</td>
          <td class="${className}">${status}</td>
        `;
        paletteTableBody.appendChild(tr);
      });
    }
  }

  function formatRiskCell(item) {
    if (!item) return "-";
    const val = item.deltae ?? item.simulated_distance ?? "-";
    const cls = item.risk_class || (item.risky ? "risky" : "safe");
    const marker = cls === "risky" ? "!" : cls === "warning" ? "~" : "";
    return `${val}${marker ? " " + marker : ""}`;
  }

  function updateCompareSlider(percent) {
    const bounded = Math.max(0, Math.min(100, percent));
    compareClip.style.clipPath = `inset(0 ${100 - bounded}% 0 0)`;
    compareDivider.style.left = `${bounded}%`;
  }

  function setupDropZones() {
    const zones = document.querySelectorAll(".drop-zone");
    zones.forEach((zone) => {
      const inputId = zone.getAttribute("data-file-input");
      const input = inputId ? document.getElementById(inputId) : null;
      const fileNameEl = inputId ? document.getElementById(`${inputId}-name`) : null;
      const pickBtn = zone.querySelector(".pick-btn");
      if (!input || !fileNameEl) return;

      pickBtn?.addEventListener("click", () => input.click());
      input.addEventListener("change", () => {
        const file = input.files && input.files[0];
        fileNameEl.textContent = file ? `${file.name} (${formatBytes(file.size)})` : "No file selected";
        const key = inferToolKeyFromInputId(inputId);
        if (file && key) {
          clearToolState(key);
          if (key === activeTool) renderToolState(activeTool);
        }
      });

      ["dragenter", "dragover"].forEach((evt) =>
        zone.addEventListener(evt, (e) => {
          e.preventDefault();
          zone.classList.add("dragover");
        })
      );
      ["dragleave", "drop"].forEach((evt) =>
        zone.addEventListener(evt, (e) => {
          e.preventDefault();
          zone.classList.remove("dragover");
        })
      );
      zone.addEventListener("drop", (e) => {
        const files = e.dataTransfer?.files;
        if (!files || files.length === 0) return;
        const dt = new DataTransfer();
        dt.items.add(files[0]);
        input.files = dt.files;
        input.dispatchEvent(new Event("change"));
      });
    });
  }

  function inferToolKeyFromInputId(inputId) {
    if (inputId === "cvd-file") return "cvd";
    if (inputId === "colorize-file") return "colorize";
    if (inputId === "restore-file") return "restore";
    if (inputId === "upscale-file") return "upscale";
    if (inputId === "adv-upscale-file") return "advupscale";
    return null;
  }

  async function loadHistogram(form) {
    const fd = new FormData(form);
    const res = await fetch("/colorblind/histogram", { method: "POST", body: fd });
    if (!res.ok) throw new Error(await extractError(res));
    return await res.json();
  }

  function renderHistogramFromState(histData) {
    const channelEnabled = {
      r: histR?.checked ?? true,
      g: histG?.checked ?? true,
      b: histB?.checked ?? true,
    };
    if ((histView?.value || "inout") === "diff") {
      drawHistogram(histInputCanvas, histData.input_histogram, channelEnabled, false);
      drawHistogram(histOutputCanvas, histData.difference_histogram, channelEnabled, true);
      return;
    }
    drawHistogram(histInputCanvas, histData.input_histogram, channelEnabled, false);
    drawHistogram(histOutputCanvas, histData.output_histogram, channelEnabled, false);
  }

  function drawHistogram(canvas, histogram, enabled, isDiff) {
    if (!canvas || !histogram) return;
    const ctx = canvas.getContext("2d");
    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = "#121a25";
    ctx.fillRect(0, 0, width, height);
    ctx.strokeStyle = "#2a3544";
    ctx.lineWidth = 1;
    for (let i = 1; i <= 4; i++) {
      const y = (height / 5) * i;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    const values = [enabled.r ? histogram.r : [0], enabled.g ? histogram.g : [0], enabled.b ? histogram.b : [0]];
    const absMax = Math.max(
      1,
      ...values[0].map((v) => Math.abs(v)),
      ...values[1].map((v) => Math.abs(v)),
      ...values[2].map((v) => Math.abs(v))
    );
    if (enabled.r) renderChannel(ctx, histogram.r, absMax, "rgba(255, 107, 107, 0.9)", width, height, isDiff);
    if (enabled.g) renderChannel(ctx, histogram.g, absMax, "rgba(95, 211, 122, 0.9)", width, height, isDiff);
    if (enabled.b) renderChannel(ctx, histogram.b, absMax, "rgba(111, 166, 255, 0.9)", width, height, isDiff);
  }

  function renderChannel(ctx, values, maxVal, color, width, height, isDiff) {
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    values.forEach((v, i) => {
      const x = (i / 255) * width;
      const ratio = isDiff ? (v / maxVal + 1) / 2 : v / maxVal;
      const y = height - ratio * (height - 4) - 2;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  }

  function base64ToBlob(base64, mimeType) {
    const byteChars = atob(base64);
    const bytes = new Uint8Array(byteChars.length);
    for (let i = 0; i < byteChars.length; i++) bytes[i] = byteChars.charCodeAt(i);
    return new Blob([bytes], { type: mimeType });
  }

  function formatBytes(bytes) {
    if (!bytes || bytes <= 0) return "0 B";
    const units = ["B", "KB", "MB", "GB"];
    const idx = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
    const value = bytes / Math.pow(1024, idx);
    return `${value.toFixed(value >= 10 || idx === 0 ? 0 : 1)} ${units[idx]}`;
  }

  async function extractError(response) {
    let detail = response.statusText;
    try {
      const j = await response.json();
      if (j.detail) {
        if (Array.isArray(j.detail)) {
          detail = j.detail.map((d) => (typeof d === "object" && d.msg ? d.msg : String(d))).join("; ");
        } else {
          detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
        }
      }
    } catch (_) {
      // ignore parse errors
    }
    return detail;
  }

  function imageDimensions(src) {
    return new Promise((resolve, reject) => {
      const im = new Image();
      im.onload = () => resolve({ width: im.naturalWidth, height: im.naturalHeight });
      im.onerror = () => reject(new Error("Could not read output image dimensions"));
      im.src = src;
    });
  }

  window.addEventListener("beforeunload", () => {
    Object.values(toolStates).forEach((s) => revokeStateUrls(s));
  });

  renderToolState(activeTool);
})();
