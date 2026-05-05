/**
 * api.js — All backend API communication for the Campus Library DApp.
 * Every function returns a Promise. Errors are handled by ui.js toast system.
 */

const API_BASE = window.location.origin;

const Api = {

  async _handleRes(res) {
    let data;
    try {
      data = await res.json();
    } catch (e) {
      throw new Error("Server returned invalid JSON.");
    }
    if (!res.ok) {
      throw new Error(data.error || "An unknown error occurred.");
    }
    return data;
  },

  async login(privateKey, isAdminLogin = false) {
    const res = await fetch(`${API_BASE}/api/auth`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ private_key: privateKey, is_admin_login: isAdminLogin })
    });
    return this._handleRes(res);
  },

  async getUserInfo(address) {
    const res = await fetch(`${API_BASE}/api/user/${address}`);
    return this._handleRes(res);
  },

  async register(privateKey, name) {
    const res = await fetch(`${API_BASE}/api/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ private_key: privateKey, name })
    });
    return this._handleRes(res);
  },

  async getBooks() {
    const res = await fetch(`${API_BASE}/api/books`);
    return this._handleRes(res);
  },

  async borrowBook(privateKey, bookId, duration) {
    const res = await fetch(`${API_BASE}/api/books/borrow`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ private_key: privateKey, book_id: bookId, duration: duration })
    });
    return this._handleRes(res);
  },

  async returnBook(privateKey, bookId) {
    const res = await fetch(`${API_BASE}/api/books/return`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ private_key: privateKey, book_id: bookId })
    });
    return this._handleRes(res);
  },

  async getMyBorrowed(address) {
    const res = await fetch(`${API_BASE}/api/books/my-borrowed`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ address })
    });
    return this._handleRes(res);
  },

  async getBalance(address) {
    const res = await fetch(`${API_BASE}/api/balance/${address}`);
    return this._handleRes(res);
  },

  async getHistory(address) {
    const res = await fetch(`${API_BASE}/api/history/${address}`);
    return this._handleRes(res);
  },

  async getStats(address = "") {
    const res = await fetch(`${API_BASE}/api/stats?address=${address}`);
    return this._handleRes(res);
  },

  async getAdminStatus() {
    const res = await fetch(`${API_BASE}/api/admin/status`);
    return this._handleRes(res);
  },

  async adminGetUsers(privateKey) {
    const res = await fetch(`${API_BASE}/api/admin/users`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ private_key: privateKey })
    });
    return this._handleRes(res);
  },

  async adminAddBook(privateKey, title, author, basePrice, imageFile, pdfFile, durations, prices) {
    const formData = new FormData();
    formData.append("private_key", privateKey);
    formData.append("title", title);
    formData.append("author", author);
    formData.append("basePrice", basePrice);

    if (imageFile) formData.append("image", imageFile);
    if (pdfFile) formData.append("pdf", pdfFile);

    formData.append("durations", JSON.stringify(durations));
    formData.append("prices", JSON.stringify(prices));

    const res = await fetch(`${API_BASE}/api/admin/add-book`, {
      method: "POST",
      body: formData
    });
    return this._handleRes(res);
  },

  async adminUpdateBook(privateKey, bookId, title, author, basePrice, imageFile, pdfFile, existingImageHash, existingPdfHash, durations, prices) {
    const formData = new FormData();
    formData.append("private_key", privateKey);
    formData.append("bookId", bookId);
    formData.append("title", title);
    formData.append("author", author);
    formData.append("basePrice", basePrice);
    formData.append("existingImageHash", existingImageHash || "");
    formData.append("existingPdfHash", existingPdfHash || "");

    if (imageFile) formData.append("image", imageFile);
    if (pdfFile) formData.append("pdf", pdfFile);

    formData.append("durations", JSON.stringify(durations));
    formData.append("prices", JSON.stringify(prices));

    const res = await fetch(`${API_BASE}/api/admin/update-book`, {
      method: "POST",
      body: formData
    });
    return this._handleRes(res);
  },

  async adminToggleBook(privateKey, bookId) {
    const res = await fetch(`${API_BASE}/api/admin/toggle-book`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ private_key: privateKey, bookId: bookId })
    });
    return this._handleRes(res);
  },

  async adminBatchAdd(privateKey, batchData) {
    const formData = new FormData();
    formData.append("private_key", privateKey);
    formData.append("count", batchData.length);

    batchData.forEach((item, i) => {
        formData.append(`title_${i}`, item.title);
        formData.append(`author_${i}`, item.author);
        formData.append(`basePrice_${i}`, item.basePrice);
        if (item.imageFile) formData.append(`image_${i}`, item.imageFile);
        if (item.pdfFile) formData.append(`pdf_${i}`, item.pdfFile);
        formData.append(`durations_${i}`, JSON.stringify(item.durations));
        formData.append(`prices_${i}`, JSON.stringify(item.prices));
    });

    const res = await fetch(`${API_BASE}/api/admin/batch-add`, {
      method: "POST",
      body: formData
    });
    return this._handleRes(res);
  },

  async adminMint(privateKey, to, amount) {
    const res = await fetch(`${API_BASE}/api/admin/mint`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ private_key: privateKey, to, amount })
    });
    return this._handleRes(res);
  },

  async adminPause(privateKey) {
    const res = await fetch(`${API_BASE}/api/admin/pause`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ private_key: privateKey })
    });
    return this._handleRes(res);
  },

  async adminResume(privateKey) {
    const res = await fetch(`${API_BASE}/api/admin/resume`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ private_key: privateKey })
    });
    return this._handleRes(res);
  },

  async adminTransferOwnership(privateKey, newAdmin) {
    const res = await fetch(`${API_BASE}/api/admin/transfer-ownership`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ private_key: privateKey, new_admin: newAdmin })
    });
    return this._handleRes(res);
  },

  async adminExportCSV(privateKey) {
    const res = await fetch(`${API_BASE}/api/admin/export-csv`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ private_key: privateKey })
    });
    return this._handleRes(res);
  }
};