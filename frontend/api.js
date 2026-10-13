// MeetingNote Pro 화면 공통 - 토큰 보관 · API 호출 · 세션 만료 · 소속 팀 확인
// 색과 클래스는 theme.js 와 각 화면의 퍼블리싱 마크업을 그대로 쓴다. 여기서는 새 클래스를 만들지 않는다
(function () {
  const KEY = "token";

  const store = {
    get() { try { return localStorage.getItem(KEY); } catch (e) { return null; } },
    set(t) { try { localStorage.setItem(KEY, t); } catch (e) {} },
    clear() { try { localStorage.removeItem(KEY); } catch (e) {} }
  };

  class ApiError extends Error {
    constructor(status, code, msg) { super(msg || "요청을 처리하지 못했습니다"); this.status = status; this.code = code; }
  }

  // 토큰이 없거나 만료 · 위조면 서버는 401 TOKEN_EXPIRED. 토큰을 지우고 로그인 화면으로 보낸다
  function expire() {
    store.clear();
    location.href = "/login.html?expired=1";
    return new Promise(() => {});  // 이동하는 동안 뒤 코드가 돌지 않게 멈춘다
  }

  async function call(method, path, body) {
    const opt = { method, headers: {} };
    const t = store.get();
    if (t) opt.headers.Authorization = "Bearer " + t;
    if (body instanceof FormData) opt.body = body;
    else if (body !== undefined) { opt.headers["Content-Type"] = "application/json"; opt.body = JSON.stringify(body); }
    let r;
    try { r = await fetch(path, opt); }
    catch (e) { throw new ApiError(0, "NETWORK", "서버에 연결하지 못했습니다"); }
    if (r.status === 204) return null;
    const data = await r.json().catch(() => ({}));
    const isAuthForm = path === "/api/auth/login" || path === "/api/auth/signup";
    if (r.status === 401 && data.code === "TOKEN_EXPIRED" && !isAuthForm) return expire();
    if (!r.ok) throw new ApiError(r.status, data.code, data.msg);
    return data;
  }

  // 업로드는 진행률을 받으려고 XHR 로 보낸다
  function upload(file, onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", "/api/upload");
      const t = store.get();
      if (t) xhr.setRequestHeader("Authorization", "Bearer " + t);
      xhr.upload.onprogress = (e) => { if (e.lengthComputable) onProgress(e.loaded / e.total); };
      xhr.upload.onload = () => onProgress(1);
      xhr.onload = () => {
        let data = {};
        try { data = JSON.parse(xhr.responseText); } catch (e) {}
        if (xhr.status === 401 && data.code === "TOKEN_EXPIRED") return expire();
        if (xhr.status >= 200 && xhr.status < 300) resolve(data);
        else reject(new ApiError(xhr.status, data.code, data.msg));
      };
      xhr.onerror = () => reject(new ApiError(0, "NETWORK", "서버에 연결하지 못했습니다"));
      const fd = new FormData();
      fd.append("file", file);
      xhr.send(fd);
    });
  }

  // 화면 진입. 토큰이 없으면 로그인, 소속 팀이 없으면 팀 설정의 팀 만들기 · 합류로 보낸다
  async function boot(opts) {
    const needTeam = !opts || opts.needTeam !== false;
    if (!store.get()) { location.href = "/login.html"; return new Promise(() => {}); }
    const [me, teams] = await Promise.all([call("GET", "/api/auth/me"), call("GET", "/api/teams")]);
    const team = teams[0] || null;
    if (needTeam && !team) { location.href = "/team.html"; return new Promise(() => {}); }
    return { me, team };
  }

  // 로그인 · 가입 직후 이동할 곳 - 소속 팀이 없으면 팀 설정
  async function landing() {
    const teams = await call("GET", "/api/teams");
    return teams.length ? "/meetings.html" : "/team.html";
  }

  async function logout() {
    try { await call("POST", "/api/auth/logout"); } catch (e) {}
    store.clear();
    location.href = "/login.html";
  }

  const esc = (s) => String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");

  const pad = (n) => String(n).padStart(2, "0");
  // 저장은 UTC, 화면 표시는 현지 시간
  function fmt(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }
  // datetime-local 입력값(현지) <-> ISO UTC
  const toLocalInput = (iso) => { const d = new Date(iso); return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`; };
  const fromLocalInput = (v) => new Date(v).toISOString();

  // 상대 표기 - 오늘 14:12 · 어제 17:40 · 9월 18일
  function when(iso) {
    const d = new Date(iso), now = new Date();
    const day = (x) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
    const diff = Math.round((day(now) - day(d)) / 86400000);
    const hm = `${pad(d.getHours())}:${pad(d.getMinutes())}`;
    if (diff === 0) return "오늘 " + hm;
    if (diff === 1) return "어제 " + hm;
    return `${d.getMonth() + 1}월 ${d.getDate()}일`;
  }

  // 활동 띠 색은 kind 로 고른다 (프로그램정의서 7-2)
  const ACT_COLOR = { meeting_add: "blue", todo_assign: "orange", todo_done: "green", comment_add: "purple", member_join: "purple" };
  // 회의록 카드 띠는 목록 순서대로 돌려 쓴다
  const CARD_COLORS = ["blue", "green", "orange", "purple", "red"];
  const STATUS = {
    OPEN:  { label: "대기", color: "orange" },
    DOING: { label: "진행", color: "blue" },
    DONE:  { label: "완료", color: "green" }
  };

  // 기한 지남 - 서버는 판정하지 않는다. 완료한 것은 제외
  const LATE_WORDS = ["어제", "지난 주", "지난주", "지난 달", "지난달"];
  function isLate(t) {
    if (t.status === "DONE" || !t.due_text) return false;
    const s = t.due_text.trim();
    if (LATE_WORDS.some((w) => s.startsWith(w))) return true;
    const today = new Date(); today.setHours(0, 0, 0, 0);
    let m = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
    if (m) return new Date(+m[1], +m[2] - 1, +m[3]) < today;
    m = s.match(/^(\d{1,2})월\s*(\d{1,2})일$/);
    if (m) return new Date(today.getFullYear(), +m[1] - 1, +m[2]) < today;
    return false;
  }

  window.API = { token: store, call, upload, boot, landing, logout, esc, fmt, when, toLocalInput, fromLocalInput,
                 ACT_COLOR, CARD_COLORS, STATUS, isLate, ApiError };
})();
