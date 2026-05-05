/**
 * ui.js — All DOM manipulation, rendering, and event handling.
 * Depends on api.js for data fetching.
 */

// --- State ---
let STATE = {
  privateKey: "",
  address: "",
  name: "",
  isAdmin: false,
  books: [],
  paused: false,
  adminAddr: ""
};

// --- Globals for Dynamic Forms ---
let addDurations = [];
let addPrices = [];
let editDurations = [];
let editPrices = [];
let currentBorrowBook = null;

// Track complex batch inputs
let batchState = {}; // Format: { 0: { durs: [], prices: [] }, 1: ... }

// Canvas drawing globals
let isDrawing = false;
let drawMode = false;
let pdfCtx = null;

// --- Utilities ---
function $(sel) { return document.querySelector(sel); }
function $$(sel) { return document.querySelectorAll(sel); }

function shortAddr(a) {
  return a ? a.slice(0, 6) + "..." + a.slice(-4) : "—";
}

function bookCoverUrl(title) {
  const query = encodeURIComponent(`book cover for ${title || "library book"}`);
  return `https://image.pollinations.ai/prompt/${query}?width=400&height=560&nologo=true`;
}

// --- NEW Helper: File Name Truncator ---
window.updateFileName = function(inputEl, spanId, defaultText) {
    const span = document.getElementById(spanId);
    if (!span) return;
    if (inputEl.files && inputEl.files.length > 0) {
        let name = inputEl.files[0].name;
        // Truncate long names to prevent layout breaking
        if (name.length > 22) {
            let ext = name.split('.').pop();
            let base = name.substring(0, 15);
            span.textContent = base + '... .' + ext;
        } else {
            span.textContent = name;
        }
    } else {
        span.textContent = defaultText;
    }
}

// --- Toast Notifications ---
function toast(msg, type = "i") {
  const wrap = $(".toast-w");
  if (!wrap) return;

  wrap.style.zIndex = "999999";

  const el = document.createElement("div");
  el.className = "toast " + type;
  const icons = { s: "fa-check-circle", e: "fa-times-circle", i: "fa-info-circle" };

  const msgText = msg instanceof Error ? msg.message : msg;

  el.innerHTML = `<i class="fas ${icons[type] || icons.i}"></i> ${msgText}`;
  wrap.appendChild(el);
  setTimeout(() => el.remove(), 3200);
}

// --- Loading State ---
function setLoading(btn, loading) {
  if (!btn) return;
  if (loading) {
    if (btn.getAttribute("data-loading") === "true") return;
    btn.setAttribute("data-loading", "true");
    btn.dataset.origHtml = btn.innerHTML;
    btn.innerHTML = '<span class="spinner"></span> Processing...';
    btn.disabled = true;
  } else {
    if (btn.dataset.origHtml) {
      btn.innerHTML = btn.dataset.origHtml;
    }
    btn.removeAttribute("data-loading");
    btn.disabled = false;
  }
}

// --- Navigation ---
function nav(pageId) {
  const adminPages = ["a-dash", "a-add", "a-batch", "a-ctrl", "a-xfer", "a-sec", "a-manage"];
  if (adminPages.includes(pageId) && !STATE.isAdmin) {
    toast("Access Denied: Admin privileges required.", "e");
    return;
  }

  $$(".ni").forEach(b => b.classList.remove("act"));
  const btn = $(`.ni[data-p="${pageId}"]`);
  if (btn) btn.classList.add("act");

  $$(".pg").forEach(p => p.classList.remove("act"));
  const pg = $(`#pg-${pageId}`);
  if (pg) pg.classList.add("act");

  const titles = {
    home: "Home", catalog: "Full Catalog", borrow: "My Borrowed Books",
    balances: "Balance Checker", history: "Activity History",
    "a-dash": "Dashboard", "a-add": "Add Book", "a-batch": "Batch Add", "a-ctrl": "System Controls",
    "a-xfer": "Transfer Ownership", "a-sec": "Security Test", "a-manage": "Manage Books"
  };
  const titleEl = $("#pgTitle");
  if (titleEl) titleEl.textContent = titles[pageId] || "Home";

  if (pageId === "home" || pageId === "a-dash") refreshHome();
  if (pageId === "catalog") refreshCatalog();
  if (pageId === "borrow") refreshBorrowReturn();
  if (pageId === "a-xfer") refreshAdminUsers();
  if (pageId === "a-manage") refreshManageBooks();
}

// --- Login & Logout Flow ---
async function doLogin(e) {
  if (e) e.preventDefault();
  const pk = $("#loginKey").value.trim();
  if (!pk) { toast("Enter your private key", "e"); return false; }

  const btn = $("#loginForm button[type='submit']");
  setLoading(btn, true);

  try {
    toast("Authenticating...", "i");

    const isAdminPage = window.location.pathname.toLowerCase().includes("admin") || document.title.includes("Admin");
    const userData = await Api.login(pk, isAdminPage);

    if (isAdminPage && !userData.is_admin) {
        throw new Error("Access denied. Admin privileges required.");
    }

    STATE.privateKey = pk;
    STATE.address = userData.address;
    STATE.name = userData.name;
    STATE.isAdmin = userData.is_admin;
    STATE.adminAddr = userData.admin_address;

    sessionStorage.setItem("library_pk", pk);

    $("#loginOverlay").style.display = "none";
    toast("Login successful!", "s");

    await initApp();

    if (!userData.registered && !(STATE.isAdmin && isAdminPage)) {
      await showRegistrationModal();
    }

  } catch (err) {
    const errorMsg = err instanceof Error ? err.message : "Authentication failed.";
    toast(errorMsg, "e");
    $("#loginOverlay").style.display = "flex";
    sessionStorage.removeItem("library_pk");
  } finally {
    setLoading(btn, false);
  }
  return false;
}

function doLogout() {
  STATE = { privateKey: "", address: "", name: "", isAdmin: false, books: [], paused: false, adminAddr: "" };

  const loginKey = $("#loginKey");
  if (loginKey) loginKey.value = "";

  sessionStorage.removeItem("library_pk");

  const overlay = $("#loginOverlay");
  if (overlay) overlay.style.display = "flex";

  $$(".admin-only").forEach(el => el.style.display = "none");

  nav('home');
  toast("Logged out successfully", "s");
}

async function initApp() {
  try {
    const status = await Api.getAdminStatus();
    STATE.paused = status.paused;
  } catch (e) {
    toast("Could not fetch system status", "e");
  }

  const roleEl = $(".sb-role");
  if (roleEl) {
    roleEl.className = "sb-role " + (STATE.isAdmin ? "is-admin" : "is-user");
    let dispName = STATE.name ? STATE.name : (STATE.isAdmin ? "Admin" : "User");
    roleEl.innerHTML = `<i class="fas ${STATE.isAdmin ? "fa-shield-halved" : "fa-user"}"></i> ${dispName} — Connected`;
  }

  const addrEl = $("#topAddr");
  if (addrEl) addrEl.textContent = shortAddr(STATE.address);

  $$(".admin-only").forEach(el => {
    if (STATE.isAdmin) {
        el.style.display = el.classList.contains("ni") ? "flex" : "block";
    } else {
        el.style.display = "none";
    }
  });

  if (STATE.isAdmin) {
      loadAdminUsers();
  }

  updatePauseUI();
  refreshHome();
}

function updatePauseUI() {
  const pill = $(".spill");
  const txt = $("#statusText");
  const btnP = $("#btnPause");
  const btnR = $("#btnResume");

  if (!pill) return;

  if (STATE.paused) {
    pill.className = "spill off";
    if (txt) txt.textContent = "Paused";
    if (btnP) btnP.disabled = true;
    if (btnR) btnR.disabled = false;
  } else {
    pill.className = "spill on";
    if (txt) txt.textContent = "Running";
    if (btnP) btnP.disabled = false;
    if (btnR) btnR.disabled = true;
  }
}

// --- Home Page ---
async function refreshHome() {
  try {
    const data = await Api.getStats(STATE.address);
    const hBooks = $("#hBooks"); if (hBooks) hBooks.textContent = data.total_books;
    const hAvail = $("#hAvail"); if (hAvail) hAvail.textContent = data.available;

    let lbcVal = data.total_minted;
    let lbcLbl = "LBC Minted";
    let txVal = data.total_transactions;
    let txLbl = "On-Chain Tx";

    if (!STATE.isAdmin && STATE.address) {
        try {
            const balData = await Api.getBalance(STATE.address);
            const histData = await Api.getHistory(STATE.address);
            lbcVal = balData.coin_readable;
            lbcLbl = "My LBC Balance";
            txVal = (histData.activities || []).length;
            txLbl = "My Transactions";
        } catch(e) {}
    }

    const hTx = $("#hTx"); if (hTx) hTx.textContent = txVal;

    const ds = $("#dashStats");
    if (ds) {
      ds.innerHTML = `
        <div class="stat-box"><div class="si" style="background:var(--pri3);color:var(--pri)"><i class="fas fa-book"></i></div><div><div class="sn">${data.total_books}</div><div class="sl">Total Books</div></div></div>
        <div class="stat-box"><div class="si" style="background:#E8F5E9;color:var(--success)"><i class="fas fa-check-circle"></i></div><div><div class="sn">${data.available}</div><div class="sl">Available</div></div></div>
        <div class="stat-box"><div class="si" style="background:#FFF3E0;color:var(--warn)"><i class="fas fa-coins"></i></div><div><div class="sn">${lbcVal}</div><div class="sl">${lbcLbl}</div></div></div>
        <div class="stat-box"><div class="si" style="background:#E8EAF6;color:#283593"><i class="fas fa-link"></i></div><div><div class="sn">${txVal}</div><div class="sl">${txLbl}</div></div></div>
      `;
    }

    const booksData = await Api.getBooks();
    STATE.books = booksData.books || [];

    let activeBooks = STATE.books;
    if(!STATE.isAdmin) activeBooks = STATE.books.filter(b => b.exists !== false);

    const feat = [...activeBooks].sort((a, b) => b.borrowCount - a.borrowCount).slice(0, 4);
    const fg = $("#featGrid");
    if (fg) fg.innerHTML = feat.length ? feat.map(b => renderBookCard(b)).join("") : '<p style="color:var(--fg2)">No books available yet.</p>';

    const sorted = [...activeBooks].sort((a, b) => b.borrowCount - a.borrowCount).slice(0, 5);
    const tb = $("#topBk");
    if (tb) {
      tb.innerHTML = sorted.length ? `<table><thead><tr><th>#</th><th>Title</th><th>Borrows</th><th>Status</th></tr></thead><tbody>${sorted.map((b, i) => `<tr><td>${i + 1}</td><td style="font-weight:600">${b.title}</td><td><strong>${b.borrowCount}</strong></td><td><span class="badge ${b.available ? "b-g" : "b-r"}">${b.available ? "Available" : "Borrowed"}</span></td></tr>`).join("")}</tbody></table>` : '<p style="color:var(--fg2);padding:14px">No data to display.</p>';
    }

    const tu = $("#topUs");
    if (tu) {
      const medals = ["#C8913A", "#9E9E9E", "#8D6E63"];
      tu.innerHTML = (data.top_users || []).map((u, i) => `
        <div style="display:flex;align-items:center;gap:11px;padding:11px 0;${i < (data.top_users || []).length - 1 ? "border-bottom:1px solid var(--border);" : ""}">
          <div style="width:30px;height:30px;border-radius:50%;background-color:${medals[i]}18;color:${medals[i]};display:flex;align-items:center;justify-content:center;font-weight:800;font-size:.8rem">${i + 1}</div>
          <div style="flex:1"><div style="font-weight:600;font-size:.88rem">${shortAddr(u.address)}</div><div style="font-size:.74rem;color:var(--fg2);font-family:monospace">${u.address}</div></div>
          <div style="font-weight:700;color:var(--pri)">${u.count} tx</div>
        </div>
      `).join("") || '<p style="color:var(--fg2)">No activity yet.</p>';
    }
  } catch (e) {
    console.error("Home refresh error:", e);
  }
}

function renderBookCard(b) {
  const imgSrc = `/api/books/image/${b.id}`;
  const fallbackSrc = bookCoverUrl(b.title);

  return `
    <div class="bk">
      <div class="bk-wrap">
        <img class="bk-cover" src="${imgSrc}" onerror="this.onerror=null; this.src='${fallbackSrc}';" alt="${b.title}" loading="lazy">
        ${b.borrowCount > 3 ? '<span class="bk-badge" style="background:var(--accent)">Popular</span>' : ""}
        ${!b.available ? '<span class="bk-badge" style="background:var(--danger)">Unavailable</span>' : ""}
      </div>
      <div class="bk-info">
        <div class="bk-title">${b.title}</div>
        <div class="bk-author">${b.author}</div>
        <div class="bk-foot">
          <span class="bk-status ${b.available ? "avail" : "out"}">${b.basePrice !== undefined ? b.basePrice + ' LBC' : (b.available ? "Available" : "Borrowed")}</span>
          <div class="bk-acts">
            <button class="bk-act" title="Borrow" onclick="quickBorrow(${b.id})"><i class="fas fa-hand-holding"></i></button>
          </div>
        </div>
      </div>
    </div>
  `;
}

function quickBorrow(id) {
  if (!STATE.privateKey) { toast("Login required", "e"); return; }

  const book = STATE.books.find(b => b.id === id);
  if(!book) return toast("Book not found", "e");
  if(!book.available) return toast("Book is currently unavailable", "e");

  currentBorrowBook = book;

  const imgSrc = `/api/books/image/${book.id}`;
  const fallbackSrc = bookCoverUrl(book.title);

  const modalImg = $("#bModalImg");
  if(modalImg) {
      modalImg.src = imgSrc;
      modalImg.onerror = function() { this.onerror = null; this.src = fallbackSrc; };
  }
  const modalTitle = $("#bModalTitle"); if(modalTitle) modalTitle.textContent = book.title;
  const modalAuthor = $("#bModalAuthor"); if(modalAuthor) modalAuthor.textContent = book.author;
  const modalBase = $("#bModalBasePrice"); if(modalBase) modalBase.textContent = book.basePrice + " LBC";
  const modalBookId = $("#bModalBookId"); if(modalBookId) modalBookId.value = book.id;

  const sel = $("#bModalDuration");
  if(sel) {
      const labels = { 86400: "1 Day", 604800: "1 Week", 2592000: "1 Month" };
      if(book.pricing && book.pricing.length > 0) {
          sel.innerHTML = book.pricing.map(p => `<option value="${p.duration}" data-price="${p.price}">${labels[p.duration] || (p.duration/86400)+' Days'} (+${p.price} LBC)</option>`).join("");
      } else {
          sel.innerHTML = '<option disabled value="0">No pricing available</option>';
      }
  }

  updateBorrowPrice();
  const bm = $("#borrowModal");
  if(bm) bm.style.display = "flex";
}

function updateBorrowPrice() {
  if(!currentBorrowBook) return;
  const sel = $("#bModalDuration");
  if(!sel) return;
  const opt = sel.options[sel.selectedIndex];
  if(!opt) return;

  const durPrice = parseFloat(opt.getAttribute("data-price") || 0);
  const total = currentBorrowBook.basePrice + durPrice;

  const feeEl = $("#bModalFee"); if(feeEl) feeEl.textContent = durPrice + " LBC";
  const totalEl = $("#bModalTotal"); if(totalEl) totalEl.textContent = total + " LBC";
}

async function executeBorrow() {
  const btn = $("#btnConfirmBorrow");
  const bookId = parseInt($("#bModalBookId")?.value);
  const duration = parseInt($("#bModalDuration")?.value);

  if(!bookId || !duration) return toast("Invalid selection. Please choose a duration.", "e");

  setLoading(btn, true);
  try {
      await Api.borrowBook(STATE.privateKey, bookId, duration);
      toast("Book borrowed successfully!", "s");
      const bm = $("#borrowModal");
      if(bm) bm.style.display = "none";
      refreshHome();
      if ($("#pg-catalog") && $("#pg-catalog").classList.contains("act")) refreshCatalog();
  } catch(e) {
      toast(e, "e");
  } finally {
      setLoading(btn, false);
  }
}

// --- Catalog Page ---
async function refreshCatalog() {
  try {
    const data = await Api.getBooks();
    STATE.books = data.books || [];
    const grid = $("#catGrid");
    if (grid) {
      const activeBooks = STATE.isAdmin ? STATE.books : STATE.books.filter(b => b.exists !== false);
      grid.innerHTML = activeBooks.length
        ? activeBooks.map(b => renderBookCard(b)).join("")
        : '<p style="color:var(--fg2);grid-column:1/-1;text-align:center;padding:40px">No books in the catalog.</p>';
    }
  } catch (e) {
    console.error("Catalog error:", e);
  }
}

// --- Borrow / Return Page ---
async function refreshBorrowReturn() {
  try {
    const data = await Api.getBooks();
    const books = data.books || [];
    STATE.books = books;
    const avail = books.filter(b => b.available && b.exists !== false);
    const brSel = $("#brSel");
    if (brSel) {
      brSel.innerHTML = avail.length
        ? avail.map(b => `<option value="${b.id}">${b.title} (${b.id})</option>`).join("")
        : '<option disabled>No available books</option>';
    }

    if (STATE.address) {
      try {
        const borrowed = await Api.getMyBorrowed(STATE.address);
        const rtSel = $("#rtSel");
        const listContainer = $("#activeLoansContainer");

        if (rtSel) {
          rtSel.innerHTML = borrowed.books.length
            ? borrowed.books.map(b => `<option value="${b.id}">${b.title} (${b.id})</option>`).join("")
            : '<option disabled>No borrowed books</option>';
        }

        if (listContainer) {
            if (borrowed.books.length > 0) {
                listContainer.innerHTML = borrowed.books.map(b => `
                    <div style="display:flex; justify-content:space-between; align-items:center; padding: 12px; background: var(--bg); border: 1px solid var(--border); border-radius: 8px; margin-bottom: 8px;">
                        <div style="font-weight:600; font-size:.95rem;">${b.title}</div>
                        <div style="display:flex; gap:8px;">
                            <button class="btn btn-p btn-sm" onclick="openPdfViewer(${b.id})"><i class="fas fa-book-reader"></i> Read PDF</button>
                        </div>
                    </div>
                `).join("");
            } else {
                listContainer.innerHTML = '<p style="color:var(--fg2); font-size: .9rem; padding: 15px; text-align: center; border: 1px dashed var(--border); border-radius: 8px;">You have no active loans.</p>';
            }
        }
      } catch (e) {
        if ($("#rtSel")) $("#rtSel").innerHTML = '<option disabled>Could not fetch</option>';
        if ($("#activeLoansContainer")) $("#activeLoansContainer").innerHTML = '<p style="color:var(--danger);">Error loading loans.</p>';
      }
    }
  } catch (e) {
    console.error("Borrow/Return error:", e);
  }
}

async function doBorrow() {
  const bookId = parseInt($("#brSel")?.value);
  if (!bookId) { toast("Select a book", "e"); return; }
  quickBorrow(bookId);
}

async function doReturn() {
  const btn = $("#btnReturn");
  if (!btn) return;
  const bookId = parseInt($("#rtSel")?.value);
  if (!bookId) { toast("Select a book", "e"); return; }
  setLoading(btn, true);
  try {
    await Api.returnBook(STATE.privateKey, bookId);
    toast("Done", "s");
    refreshBorrowReturn();
  } catch (e) { toast(e, "e"); }
  finally { setLoading(btn, false); }
}

// --- Secure PDF Viewer Controllers & Canvas Tools ---
function initPdfCanvas() {
    const canvas = document.getElementById("pdfCanvas");
    if(!canvas) return;

    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;
    pdfCtx = canvas.getContext("2d");

    canvas.addEventListener("mousedown", (e) => {
        if(!drawMode) return;
        isDrawing = true;
        const rect = canvas.getBoundingClientRect();
        pdfCtx.beginPath();
        pdfCtx.moveTo(e.clientX - rect.left, e.clientY - rect.top);
    });

    canvas.addEventListener("mousemove", (e) => {
        if(!isDrawing || !drawMode) return;
        const rect = canvas.getBoundingClientRect();
        pdfCtx.strokeStyle = document.getElementById("penColor").value;
        pdfCtx.lineWidth = 3;
        pdfCtx.lineCap = "round";
        pdfCtx.lineJoin = "round";
        pdfCtx.lineTo(e.clientX - rect.left, e.clientY - rect.top);
        pdfCtx.stroke();
    });

    canvas.addEventListener("mouseup", () => isDrawing = false);
    canvas.addEventListener("mouseleave", () => isDrawing = false);
}

window.toggleDrawMode = function() {
    drawMode = !drawMode;
    const canvas = document.getElementById("pdfCanvas");
    const btn = document.getElementById("btnDrawMode");
    if(!canvas || !btn) return;

    if(drawMode) {
        canvas.style.pointerEvents = "auto";
        btn.style.background = "var(--accent)";
        btn.style.borderColor = "var(--accent)";
        toast("Draw Mode ON: Scroll is locked while drawing.", "i");
    } else {
        canvas.style.pointerEvents = "none";
        btn.style.background = "transparent";
        btn.style.borderColor = "#555";
        toast("Draw Mode OFF: Scroll unlocked.", "i");
    }
}

window.clearCanvas = function() {
    if(pdfCtx) {
        pdfCtx.clearRect(0, 0, pdfCtx.canvas.width, pdfCtx.canvas.height);
    }
}

window.openPdfViewer = function(bookId) {
    if(!STATE.privateKey) return toast("Authentication required", "e");
    const book = STATE.books.find(b => b.id === bookId);
    if(book) {
        const titleEl = $("#pdfViewerTitle");
        if(titleEl) titleEl.textContent = `Reading: ${book.title}`;
    }

    const url = `/api/books/read/${bookId}?pk=${STATE.privateKey}#toolbar=0&navpanes=0`;
    const frame = $("#pdfIframe");
    if(frame) frame.src = url;

    const overlay = $("#pdfOverlay");
    if(overlay) {
        overlay.style.display = "flex";
        setTimeout(initPdfCanvas, 100);
    }
}

window.closePdfViewer = function() {
    const overlay = $("#pdfOverlay");
    if(overlay) overlay.style.display = "none";
    const frame = $("#pdfIframe");
    if(frame) frame.src = "";
    clearCanvas();
    if(drawMode) toggleDrawMode();
}

// --- Balance Checker ---
async function checkBalance() {
  const addr = $("#balAddr")?.value?.trim() || STATE.address;
  if (!addr) { toast("Enter an address", "e"); return; }

  const btn = $("#btnCheckBal");
  setLoading(btn, true);
  try {
    const data = await Api.getBalance(addr);
    const res = $("#balRes");
    if (res) {
      res.style.display = "block";
      res.innerHTML = `
        <div style="font-size:.82rem;color:var(--fg2);margin-bottom:8px">${shortAddr(addr)} <span style="font-family:monospace">(${addr})</span></div>
        <div class="coin-row">
          <div class="coin-box"><div class="coin-lbl"><i class="fas fa-coins" style="color:var(--accent)"></i> Library Coin</div><div class="coin-val" style="color:var(--accent)">${data.coin_readable}</div></div>
          <div class="coin-box"><div class="coin-lbl"><i class="fab fa-ethereum" style="color:#627EEA"></i> Ethereum</div><div class="coin-val" style="color:#627EEA">${data.eth_readable}</div></div>
        </div>
      `;
    }
  } catch (e) { toast(e, "e"); }
  finally { setLoading(btn, false); }
}

// --- Activity History ---
async function showHistory() {
  const addr = $("#histAddr")?.value?.trim() || STATE.address;
  if (!addr) { toast("Enter an address", "e"); return; }

  const btn = $("#btnShowHist");
  setLoading(btn, true);
  try {
    const data = await Api.getHistory(addr);
    const res = $("#histRes");
    if (res) {
      const acts = data.activities || [];
      res.innerHTML = acts.length
        ? `<div class="tw"><table><thead><tr><th>Block</th><th>Action</th><th>Detail</th></tr></thead><tbody>${acts.map(a => `<tr><td style="font-family:monospace;font-size:.8rem">#${a.block}</td><td><span class="at at-${a.type.toLowerCase()}">${a.type}</span></td><td>${a.detail}</td></tr>`).join("")}</tbody></table></div>`
        : '<p style="color:var(--fg2)">No activity found for this address.</p>';
    }
  } catch (e) { toast(e, "e"); }
  finally { setLoading(btn, false); }
}

function addDuration() {
    const durSel = $("#durSelect");
    const priceInp = $("#durPrice");
    if(!durSel || !priceInp) return;

    const dur = parseInt(durSel.value);
    const price = parseFloat(priceInp.value);

    if(isNaN(price) || price < 0) return toast("Enter a valid positive price", "e");
    if(addDurations.includes(dur)) return toast("Duration already added", "e");

    addDurations.push(dur);
    addPrices.push(price);
    priceInp.value = "";
    renderAddDurations();
}

function renderAddDurations() {
    const list = $("#durList");
    if(!list) return;
    const labels = { 86400: "1 Day", 604800: "1 Week", 2592000: "1 Month" };
    list.innerHTML = addDurations.map((d, i) => `
        <div class="chip">
            ${labels[d] || (d/86400 + ' Days')} (+${addPrices[i]} LBC)
            <i class="fas fa-times" style="margin-left:5px;cursor:pointer;color:var(--danger)" onclick="removeAddDuration(${i})"></i>
        </div>
    `).join("");
}

window.removeAddDuration = function(index) {
    addDurations.splice(index, 1);
    addPrices.splice(index, 1);
    renderAddDurations();
}

// --- Admin: Add Book ---
async function adminAddBook() {
  if (!STATE.isAdmin) return toast("Access Denied", "e");

  const btn = $("#btnAddBook");
  if (!btn) return;
  const title = $("#aTitle")?.value?.trim();
  const author = $("#aAuthor")?.value?.trim();
  const basePrice = $("#aBasePrice")?.value || 0;

  const imgFile = $("#aImage")?.files[0];
  const pdfFile = $("#aPdf")?.files[0];

  if (!title || !author) return toast("Title and author required", "e");
  if (!imgFile || !pdfFile) return toast("Both Image and PDF files are required", "e");
  if (addDurations.length === 0) return toast("Add at least one duration pricing", "e");

  setLoading(btn, true);
  try {
    await Api.adminAddBook(STATE.privateKey, title, author, basePrice, imgFile, pdfFile, addDurations, addPrices);
    toast("Book published successfully", "s");

    ["#aTitle", "#aAuthor"].forEach(s => { const el = $(s); if (el) el.value = ""; });
    const bpEl = $("#aBasePrice"); if(bpEl) bpEl.value = "0";

    const imgEl = $("#aImage"); if(imgEl) imgEl.value = "";
    const imgNameEl = $("#imgName"); if(imgNameEl) imgNameEl.textContent = "Choose Image";

    const pdfEl = $("#aPdf"); if(pdfEl) pdfEl.value = "";
    const pdfNameEl = $("#pdfName"); if(pdfNameEl) pdfNameEl.textContent = "Choose PDF";

    addDurations = []; addPrices = [];
    renderAddDurations();
  } catch (e) { toast(e, "e"); }
  finally { setLoading(btn, false); }
}

// --- Admin: Manage Books ---
async function refreshManageBooks() {
    try {
        const data = await Api.getBooks();
        STATE.books = data.books || [];
        const grid = $("#adminBookGrid");
        if (!grid) return;

        grid.innerHTML = STATE.books.length ? STATE.books.map(b => {
            const imgSrc = `/api/books/image/${b.id}`;
            const fallbackSrc = bookCoverUrl(b.title);
            return `
            <div class="bk">
              <div class="bk-wrap" style="opacity: ${b.exists ? '1' : '0.6'}">
                <img class="bk-cover" src="${imgSrc}" onerror="this.onerror=null; this.src='${fallbackSrc}';" alt="${b.title}">
                <span class="bk-badge" style="background:${b.available ? 'var(--success)' : 'var(--danger)'}">${b.available ? 'Avail' : 'Out'}</span>
                <span class="bk-badge" style="top:auto;bottom:8px;background:${b.exists ? 'var(--pri)' : 'var(--fg2)'}">${b.exists ? 'Active' : 'Hidden'}</span>
              </div>
              <div class="bk-info">
                <div class="bk-title">${b.title}</div>
                <div class="bk-author" style="margin-bottom:5px; color:var(--accent); font-weight:600;">Base: ${b.basePrice} LBC</div>
                <div class="bk-foot" style="margin-top:10px;">
                  <button class="btn btn-o btn-sm" style="flex:1;justify-content:center" onclick="openEditBookModal(${b.id})"><i class="fas fa-edit"></i> Manage</button>
                </div>
              </div>
            </div>
            `;
        }).join("") : '<p style="color:var(--fg2);grid-column:1/-1;text-align:center;padding:20px;">No books found in catalog.</p>';
    } catch (e) { toast(e, "e"); }
}

window.openEditBookModal = function(id) {
    const book = STATE.books.find(b => b.id === id);
    if(!book) return;

    $("#editBookId").value = book.id;
    $("#editTitle").value = book.title;
    $("#editAuthor").value = book.author;
    $("#editBasePrice").value = book.basePrice;
    $("#editExistingImageHash").value = book.imageHash;
    $("#editExistingPdfHash").value = book.pdfHash;

    const iFile = $("#editImageFile"); if(iFile) iFile.value = "";
    const pFile = $("#editPdfFile"); if(pFile) pFile.value = "";
    const iName = $("#editImgName"); if(iName) iName.textContent = "Choose New Image (Optional)";
    const pName = $("#editPdfName"); if(pName) pName.textContent = "Choose New PDF (Optional)";

    editDurations = []; editPrices = [];
    if(book.pricing) {
        book.pricing.forEach(p => {
            editDurations.push(p.duration);
            editPrices.push(p.price);
        });
    }
    renderEditDurations();

    const toggleBtn = $("#btnToggleStatus");
    if(toggleBtn) {
        toggleBtn.innerHTML = book.exists ? '<i class="fas fa-trash"></i> Delete Book' : '<i class="fas fa-undo"></i> Restore Book';
        toggleBtn.className = book.exists ? 'btn btn-d' : 'btn btn-a';
        if(!book.exists) {
            toggleBtn.style.backgroundColor = 'var(--success)';
            toggleBtn.style.borderColor = 'var(--success)';
            toggleBtn.style.color = '#fff';
        } else {
            toggleBtn.style.backgroundColor = '';
            toggleBtn.style.borderColor = '';
            toggleBtn.style.color = '';
        }
    }

    $("#manageBookModal").style.display = "flex";
}

window.addEditDuration = function() {
    const durSel = $("#editDurSelect");
    const priceInp = $("#editDurPrice");
    if(!durSel || !priceInp) return;

    const dur = parseInt(durSel.value);
    const price = parseFloat(priceInp.value);

    if(isNaN(price) || price < 0) return toast("Enter a valid positive price", "e");
    if(editDurations.includes(dur)) return toast("Duration already added", "e");

    editDurations.push(dur);
    editPrices.push(price);
    priceInp.value = "";
    renderEditDurations();
}

function renderEditDurations() {
    const list = $("#editDurList");
    if(!list) return;
    const labels = { 86400: "1 Day", 604800: "1 Week", 2592000: "1 Month" };
    list.innerHTML = editDurations.map((d, i) => `
        <div class="chip">
            ${labels[d] || (d/86400 + ' Days')} (+${editPrices[i]} LBC)
            <i class="fas fa-times" style="margin-left:5px;cursor:pointer;color:var(--danger)" onclick="removeEditDuration(${i})"></i>
        </div>
    `).join("");
}

window.removeEditDuration = function(index) {
    editDurations.splice(index, 1);
    editPrices.splice(index, 1);
    renderEditDurations();
}

window.updateBookDetails = async function() {
    const btn = $("#btnUpdateBook");
    const id = parseInt($("#editBookId").value);
    const title = $("#editTitle").value.trim();
    const author = $("#editAuthor").value.trim();
    const basePrice = $("#editBasePrice").value || 0;
    const imgHash = $("#editExistingImageHash").value;
    const pdfHash = $("#editExistingPdfHash").value;
    const imgFile = $("#editImageFile")?.files[0];
    const pdfFile = $("#editPdfFile")?.files[0];

    if(!title || !author) return toast("Title and author required", "e");
    if(editDurations.length === 0) return toast("At least one duration required", "e");

    setLoading(btn, true);
    try {
        await Api.adminUpdateBook(STATE.privateKey, id, title, author, basePrice, imgFile, pdfFile, imgHash, pdfHash, editDurations, editPrices);
        toast("Book updated successfully", "s");
        $("#manageBookModal").style.display = "none";
        refreshManageBooks();
    } catch(e) { toast(e, "e"); }
    finally { setLoading(btn, false); }
}

window.toggleBookStatus = async function() {
    const id = parseInt($("#editBookId").value);
    const book = STATE.books.find(b => b.id === id);
    const action = book.exists ? "delete (hide)" : "restore";

    if(!confirm(`Are you sure you want to ${action} this book?`)) return;

    const btn = $("#btnToggleStatus");
    setLoading(btn, true);
    try {
        await Api.adminToggleBook(STATE.privateKey, id);
        toast(`Book ${action}d successfully`, "s");
        $("#manageBookModal").style.display = "none";
        refreshManageBooks();
    } catch(e) { toast(e, "e"); }
    finally { setLoading(btn, false); }
}

// --- Dynamic Batch Add UI Generation ---
window.renderBatchInputs = function() {
    const countInput = $("#batchCount");
    const container = $("#batchInputsContainer");
    if (!countInput || !container) return;

    let count = parseInt(countInput.value) || 1;
    if (count < 1) count = 1;
    if (count > 20) count = 20;

    let html = "";
    for (let i = 0; i < count; i++) {
        if(!batchState[i]) batchState[i] = { durs: [], prices: [] };

        html += `
        <div class="card" style="margin-bottom:15px; padding:20px; border-left: 4px solid var(--pri);">
            <h4 style="margin-bottom:15px; font-weight:700;">Book #${i+1}</h4>
            <div class="grid2">
                <div class="fg"><label class="fl">Title</label><input class="fi batch-title" id="bTitle_${i}" placeholder="Book title"></div>
                <div class="fg"><label class="fl">Author</label><input class="fi batch-author" id="bAuthor_${i}" placeholder="Author name"></div>
            </div>
            
            <div class="grid2">
                <div class="fg">
                  <label class="fl">Base Price (LBC)</label>
                  <input class="fi batch-price" id="bPrice_${i}" type="number" step="0.01" value="0">
                </div>
                <div style="display:flex; gap:10px;">
                    <div class="fg" style="flex:1;">
                      <label class="fl">Image</label>
                      <div class="file-input-wrapper">
                        <input type="file" id="bImg_${i}" class="batch-img" accept="image/*" onchange="updateFileName(this, 'bImgName_${i}', 'Img')">
                        <div class="file-input-display" style="padding: 9px;"><i class="fas fa-image"></i><span id="bImgName_${i}" class="file-name-text">Img</span></div>
                      </div>
                    </div>
                    <div class="fg" style="flex:1;">
                      <label class="fl">PDF</label>
                      <div class="file-input-wrapper">
                        <input type="file" id="bPdf_${i}" class="batch-pdf" accept="application/pdf" onchange="updateFileName(this, 'bPdfName_${i}', 'PDF')">
                        <div class="file-input-display" style="padding: 9px;"><i class="fas fa-file-pdf"></i><span id="bPdfName_${i}" class="file-name-text">PDF</span></div>
                      </div>
                    </div>
                </div>
            </div>

            <div class="fg" style="background:var(--bg); padding:15px; border-radius:10px; border:1px dashed var(--border);">
                <label class="fl">Durations & Prices</label>
                <div style="display:flex;gap:10px;margin-bottom:10px;">
                    <select class="fs" id="bDurSel_${i}">
                        <option value="86400">1 Day</option>
                        <option value="604800">1 Week</option>
                        <option value="2592000">1 Month</option>
                    </select>
                    <input class="fi" id="bDurPrice_${i}" type="number" step="0.01" placeholder="Add. Cost">
                    <button type="button" class="btn btn-a btn-sm" onclick="addBatchDuration(${i})"><i class="fas fa-plus"></i></button>
                </div>
                <div class="chips" id="bDurList_${i}">${renderBatchDurationsHtml(i)}</div>
            </div>
        </div>`;
    }
    container.innerHTML = html;
}

window.addBatchDuration = function(index) {
    const durSel = $(`#bDurSel_${index}`);
    const priceInp = $(`#bDurPrice_${index}`);
    if(!durSel || !priceInp) return;

    const dur = parseInt(durSel.value);
    const price = parseFloat(priceInp.value);

    if(isNaN(price) || price < 0) return toast("Enter a valid positive price", "e");
    if(batchState[index].durs.includes(dur)) return toast("Duration already added for this book", "e");

    batchState[index].durs.push(dur);
    batchState[index].prices.push(price);
    priceInp.value = "";

    const list = $(`#bDurList_${index}`);
    if(list) list.innerHTML = renderBatchDurationsHtml(index);
}

window.removeBatchDuration = function(bookIndex, durIndex) {
    batchState[bookIndex].durs.splice(durIndex, 1);
    batchState[bookIndex].prices.splice(durIndex, 1);
    const list = $(`#bDurList_${bookIndex}`);
    if(list) list.innerHTML = renderBatchDurationsHtml(bookIndex);
}

function renderBatchDurationsHtml(index) {
    const state = batchState[index];
    if(!state || state.durs.length === 0) return '<span style="font-size:0.8rem; color:var(--fg2);">No durations added yet.</span>';
    const labels = { 86400: "1 Day", 604800: "1 Week", 2592000: "1 Month" };
    return state.durs.map((d, i) => `
        <div class="chip">
            ${labels[d] || (d/86400 + ' Days')} (+${state.prices[i]} LBC)
            <i class="fas fa-times" style="margin-left:5px;cursor:pointer;color:var(--danger)" onclick="removeBatchDuration(${index}, ${i})"></i>
        </div>
    `).join("");
}

// --- Admin: Batch Add Submit ---
async function adminBatchAdd() {
  if (!STATE.isAdmin) return toast("Access Denied", "e");

  const btn = $("#btnBatch");
  const countInput = $("#batchCount");
  if (!btn || !countInput) return;

  const count = parseInt(countInput.value) || 0;
  const batchData = [];

  for (let i = 0; i < count; i++) {
      const t = $(`#bTitle_${i}`)?.value.trim();
      const a = $(`#bAuthor_${i}`)?.value.trim();
      const bp = $(`#bPrice_${i}`)?.value || 0;
      const imgFile = $(`#bImg_${i}`)?.files[0];
      const pdfFile = $(`#bPdf_${i}`)?.files[0];

      const durs = batchState[i]?.durs || [];
      const prs = batchState[i]?.prices || [];

      if (!t || !a || !imgFile || !pdfFile || durs.length === 0) {
          toast(`Book #${i+1} is missing required fields, files, or durations.`, "e");
          return;
      }

      batchData.push({
          title: t, author: a, basePrice: bp,
          imageFile: imgFile, pdfFile: pdfFile,
          durations: durs, prices: prs
      });
  }

  setLoading(btn, true);
  try {
    await Api.adminBatchAdd(STATE.privateKey, batchData);
    toast(`Successfully published ${batchData.length} books!`, "s");
    batchState = {};
    renderBatchInputs();
  } catch (e) { toast(e, "e"); }
  finally { setLoading(btn, false); }
}

// --- Admin: Mint ---
async function adminMint() {
  if (!STATE.isAdmin) return toast("Access Denied", "e");

  const btn = $("#btnMint");
  if (!btn) return;

  const dropdownVal = $("#mintSelect")?.value;
  const manualVal = $("#mintAddr")?.value?.trim();

  let to = manualVal;
  if (!to && dropdownVal) {
      to = dropdownVal;
  }

  const amount = parseFloat($("#mintAmt")?.value);
  if (!to || !amount) { toast("Address and amount required", "e"); return; }

  setLoading(btn, true);
  try {
    await Api.adminMint(STATE.privateKey, to, amount);
    toast("Done", "s");
    if ($("#mintAddr")) $("#mintAddr").value = "";
    if ($("#mintSelect")) $("#mintSelect").value = "";
  } catch (e) { toast(e, "e"); }
  finally { setLoading(btn, false); }
}

// --- Admin: Pause / Resume ---
async function adminPause() {
  if (!STATE.isAdmin) return toast("Access Denied", "e");

  const btn = $("#btnPause"); if (!btn) return;
  setLoading(btn, true);
  try {
    await Api.adminPause(STATE.privateKey);
    STATE.paused = true;
    toast("Done", "s");
    updatePauseUI();
  } catch (e) { toast(e, "e"); }
  finally { setLoading(btn, false); }
}

async function adminResume() {
  if (!STATE.isAdmin) return toast("Access Denied", "e");

  const btn = $("#btnResume"); if (!btn) return;
  setLoading(btn, true);
  try {
    await Api.adminResume(STATE.privateKey);
    STATE.paused = false;
    toast("Done", "s");
    updatePauseUI();
  } catch (e) { toast(e, "e"); }
  finally { setLoading(btn, false); }
}

// --- Admin: Users Dropdown ---
async function loadAdminUsers() {
    if(!STATE.isAdmin) return;
    const sel = $("#xferSelect");
    const mintSel = $("#mintSelect");

    try {
        const data = await Api.adminGetUsers(STATE.privateKey);
        if(data.error) throw new Error(data.error);

        const users = data.users || [];

        let htmlXfer = '<option value="" disabled selected>No other users found</option>';
        let htmlMint = '<option value="" disabled selected>No users found</option>';

        if (users.length > 0) {
            htmlXfer = '<option value="" disabled selected>-- Select a User --</option>';
            htmlMint = '<option value="" disabled selected>-- Select a User --</option>';
            users.forEach(u => {
                htmlXfer += `<option value="${u.address}">${u.display}</option>`;
                htmlMint += `<option value="${u.address}">${u.display}</option>`;
            });
        }

        if(sel) sel.innerHTML = htmlXfer;
        if(mintSel) mintSel.innerHTML = htmlMint;
    } catch(e) {
        console.error("Error loading users for transfer:", e);
        if(sel) sel.innerHTML = '<option value="">Failed to load users</option>';
        if(mintSel) mintSel.innerHTML = '<option value="">Failed to load users</option>';
    }
}

async function refreshAdminUsers() {
   await loadAdminUsers();
}

// --- Admin: Transfer Ownership ---
async function prepareAdminTransfer() {
  if (!STATE.isAdmin) return toast("Access Denied", "e");

  let newAdmin = "";
  const dropdownVal = $("#xferSelect")?.value;
  const manualVal = $("#newAdm")?.value?.trim();

  if (manualVal) {
      newAdmin = manualVal;
  } else if (dropdownVal) {
      newAdmin = dropdownVal;
  }

  if (!newAdmin) {
      toast("Enter or select a new admin address", "e");
      return;
  }

  const confirmDisplay = $("#confirmAddrDisplay");
  const overlay = $("#confirmOverlay");
  if(confirmDisplay && overlay) {
      confirmDisplay.textContent = newAdmin;
      overlay.style.display = "flex";
  }
}

async function executeAdminTransfer() {
  const overlay = $("#confirmOverlay");
  if(overlay) overlay.style.display = "none";

  const newAdmin = $("#confirmAddrDisplay")?.textContent;
  if(!newAdmin) return;

  const confirmBtn = $("#btnConfirmXfer");
  setLoading(confirmBtn, true);

  try {
    await Api.adminTransferOwnership(STATE.privateKey, newAdmin);
    toast("Ownership transferred successfully.", "s");

    if ($("#newAdm")) $("#newAdm").value = "";
    if ($("#xferSelect")) $("#xferSelect").value = "";

    const res = $("#xferRes");
    if (res) {
      res.innerHTML = `
        <div class="test-item pass"><i class="fas fa-check-circle"></i><div>Ownership transferred to ${shortAddr(newAdmin)}</div></div>
        <div class="albar w" style="margin-top:12px"><i class="fas fa-triangle-exclamation"></i><span>You are no longer the admin. Please log out.</span></div>
      `;
    }

    setTimeout(() => {
        doLogout();
    }, 1500);
  } catch (e) {
    toast(e, "e");
  } finally {
    setLoading(confirmBtn, false);
  }
}

// --- Admin: Export CSV ---
async function adminExportCSV() {
  if (!STATE.isAdmin) return toast("Access Denied", "e");

  const btn = $("#btnExportCsv");
  if (!btn) return;
  setLoading(btn, true);
  try {
    const res = await Api.adminExportCSV(STATE.privateKey);
    toast(res.message || "Export successful", "s");

    const link = document.createElement('a');
    link.href = '/data/snapshot.csv?t=' + Date.now();
    link.download = 'snapshot.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  } catch (e) {
    toast(e, "e");
  } finally {
    setLoading(btn, false);
  }
}

// --- Admin: Security Test ---
async function runSecurityTest() {
  if (!STATE.isAdmin) return toast("Access Denied", "e");

  const res = $("#secRes");
  const btn = $("#btnSec");
  if (!res || !btn) return;

  setLoading(btn, true);
  res.innerHTML = '<div style="padding:15px;color:var(--fg2);text-align:center"><span class="spinner"></span> Running tests against the blockchain...</div>';

  const tests = [
    { name: "Non-admin blocked from addBook", fn: () => Api.adminAddBook("0x" + "0".repeat(64), "Hacked", "Hacker", 0, null, null, [], []) },
    { name: "Non-admin blocked from mint", fn: () => Api.adminMint("0x" + "0".repeat(64), STATE.address, 100) },
    { name: "Non-admin blocked from pause", fn: () => Api.adminPause("0x" + "0".repeat(64)) },
    { name: "Non-admin blocked from transfer", fn: () => Api.adminTransferOwnership("0x" + "0".repeat(64), STATE.address) },
  ];

  let html = "";
  for (const test of tests) {
    try {
      await test.fn();
      html += `<div class="test-item fail"><i class="fas fa-times-circle"></i><div>${test.name}<div class="detail">Call unexpectedly succeeded</div></div></div>`;
    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : String(e);
      html += `<div class="test-item pass"><i class="fas fa-check-circle"></i><div>${test.name}<div class="detail">Correctly rejected: ${errorMsg.slice(0, 80)}</div></div></div>`;
    }
  }

  html += `<div style="margin-top:12px;padding:10px 14px;border-radius:10px;background:var(--pri3);color:var(--pri);font-weight:700;font-size:.9rem"><i class="fas fa-clipboard-check" style="margin-right:6px"></i>All ${tests.length} tests completed</div>`;
  res.innerHTML = html;
  setLoading(btn, false);
}

// --- Registration Modal ---
function showRegistrationModal() {
  return new Promise((resolve) => {
    if (document.getElementById("regOverlay")) return resolve();

    const wrap = document.createElement("div");
    wrap.className = "login-overlay";
    wrap.id = "regOverlay";
    wrap.innerHTML = `
      <div class="login-card">
        <div class="login-icon" style="background:var(--success)"><i class="fas fa-user-plus"></i></div>
        <h2 style="font-size:1.5rem;font-weight:900;margin-bottom:5px">Complete Profile</h2>
        <p style="color:var(--fg2);font-size:.92rem;margin-bottom:22px">Register your display name on the blockchain.</p>
        <div class="fg">
          <label class="fl" style="text-align:left">Your Name</label>
          <input class="fi" id="regName" type="text" placeholder="e.g. Youssef" required>
        </div>
        <button class="btn btn-p" id="btnDoReg" style="width:100%;justify-content:center;padding:11px">Register Profile</button>
      </div>
    `;
    document.body.appendChild(wrap);

    $("#btnDoReg").addEventListener("click", async () => {
      const n = $("#regName").value.trim();
      if (!n) return toast("Name required", "e");

      const btn = $("#btnDoReg");
      setLoading(btn, true);
      try {
        await Api.register(STATE.privateKey, n);
        toast("Account created successfully", "s");
        STATE.name = n;

        const roleEl = $(".sb-role");
        if (roleEl) roleEl.innerHTML = `<i class="fas ${STATE.isAdmin ? "fa-shield-halved" : "fa-user"}"></i> ${STATE.name} — Connected`;

        wrap.remove();
        resolve();
      } catch(e) {
        toast(e, "e");
        setLoading(btn, false);
      }
    });
  });
}

function navigateToLibraryAsAdmin() {
    window.location.href = "/";
}

// --- Init on DOM Ready ---
document.addEventListener("DOMContentLoaded", () => {
  $$(".admin-only").forEach(el => el.style.display = "none");

  $$(".ni[data-p]").forEach(btn => {
    btn.addEventListener("click", () => nav(btn.dataset.p));
  });

  const btnLogout = $("#btnLogout");
  if (btnLogout) btnLogout.addEventListener("click", doLogout);

  const ham = $("#ham");
  const sidebar = $(".sidebar");
  const mainArea = $(".main");
  if (ham) ham.addEventListener("click", () => sidebar?.classList.toggle("open"));
  if (mainArea) mainArea.addEventListener("click", () => sidebar?.classList.remove("open"));

  const savedPk = sessionStorage.getItem("library_pk");
  if (savedPk && !STATE.privateKey) {
      const pkInput = $("#loginKey");
      if (pkInput) pkInput.value = savedPk;
      doLogin(null);
  }

  const batchCountInput = $("#batchCount");
  if (batchCountInput) {
      renderBatchInputs();
      batchCountInput.addEventListener("input", renderBatchInputs);
      batchCountInput.addEventListener("change", renderBatchInputs);
  }

  const selAdmin = $("#xferSelect");
  const manualAdmin = $("#newAdm");
  if (selAdmin && manualAdmin) {
      selAdmin.addEventListener("change", () => { if (selAdmin.value) manualAdmin.value = ""; });
      manualAdmin.addEventListener("input", () => { if (manualAdmin.value) selAdmin.value = ""; });
  }

  const selMint = $("#mintSelect");
  const manualMint = $("#mintAddr");
  if (selMint && manualMint) {
      selMint.addEventListener("change", () => { if (selMint.value) manualMint.value = ""; });
      manualMint.addEventListener("input", () => { if (manualMint.value) selMint.value = ""; });
  }

  const loginForm = $("#loginForm");
  if (loginForm) loginForm.addEventListener("submit", doLogin);

  const btnBorrow = $("#btnBorrow");
  if (btnBorrow) btnBorrow.addEventListener("click", doBorrow);
  const btnReturn = $("#btnReturn");
  if (btnReturn) btnReturn.addEventListener("click", doReturn);
  const btnCheckBal = $("#btnCheckBal");
  if (btnCheckBal) btnCheckBal.addEventListener("click", checkBalance);
  const btnShowHist = $("#btnShowHist");
  if (btnShowHist) btnShowHist.addEventListener("click", showHistory);

  const btnAddBook = $("#btnAddBook");
  if (btnAddBook) btnAddBook.addEventListener("click", adminAddBook);
  const btnBatch = $("#btnBatch");
  if (btnBatch) btnBatch.addEventListener("click", adminBatchAdd);
  const btnMint = $("#btnMint");
  if (btnMint) btnMint.addEventListener("click", adminMint);
  const btnPause = $("#btnPause");
  if (btnPause) btnPause.addEventListener("click", adminPause);
  const btnResume = $("#btnResume");
  if (btnResume) btnResume.addEventListener("click", adminResume);

  const btnXfer = $("#btnXfer");
  if (btnXfer) btnXfer.addEventListener("click", prepareAdminTransfer);
  const btnConfirmXfer = $("#btnConfirmXfer");
  if (btnConfirmXfer) btnConfirmXfer.addEventListener("click", executeAdminTransfer);

  const btnExportCsv = $("#btnExportCsv");
  if (btnExportCsv) btnExportCsv.addEventListener("click", adminExportCSV);
  const btnSec = $("#btnSec");
  if (btnSec) btnSec.addEventListener("click", runSecurityTest);
});