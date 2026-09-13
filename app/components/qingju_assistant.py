"""Native Streamlit popover: available on every Qingju page, no iframe/server."""
from __future__ import annotations

import base64
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from assistant_service import LABELS, answer_question, load_context
from policy_agent.contracts import SessionContext
from policy_agent.orchestrator import PolicyAgentOrchestrator

_DRAG_STORAGE_KEY = "qingjuAssistantPos"
_ASSISTANT_SELECTOR = ".st-key-qingju_assistant"


_DRAG_SCRIPT = """
<script>
(function() {
    const doc = window.parent.document;
    const win = window.parent;
    const STORAGE_KEY = "__STORAGE_KEY__";
    const SELECTOR = "__SELECTOR__";
    const MARGIN_WIDE = {x: 22, y: 20};
    const MARGIN_NARROW = {x: 12, y: 12};
    const THRESHOLD = 4;

    // Streamlit destroys this component's iframe on every rerun, which kills the
    // closures below while leaving them registered on the parent document. Each
    // instance claims a generation so stale handlers detach themselves.
    const generation = (win.__qjPinGeneration || 0) + 1;
    win.__qjPinGeneration = generation;

    function current() {
        return win.__qjPinGeneration === generation;
    }

    function on(target, type, handler, options) {
        function wrapped(ev) {
            if (!current()) {
                target.removeEventListener(type, wrapped, options);
                return;
            }
            handler(ev);
        }
        target.addEventListener(type, wrapped, options);
    }

    function clamp(value, min, max) {
        return Math.min(Math.max(value, min), max);
    }

    function viewport() {
        return {w: doc.documentElement.clientWidth, h: doc.documentElement.clientHeight};
    }

    function init() {
        const el = doc.querySelector(SELECTOR);
        // Wait for layout: the anchor is derived from the rendered size.
        if (!el || !el.offsetWidth || !el.offsetHeight) { return false; }
        el.style.touchAction = "none";

        // Desired position in viewport coordinates. `anchored` keeps the default
        // bottom-right placement responsive until the user drags the assistant.
        const state = {left: 0, top: 0, anchored: true};

        try {
            const saved = JSON.parse(win.localStorage.getItem(STORAGE_KEY) || "null");
            if (saved && typeof saved.left === "number" && typeof saved.top === "number") {
                state.left = saved.left;
                state.top = saved.top;
                state.anchored = false;
            }
        } catch (err) { /* ignore unreadable or malformed storage */ }

        function resolveAnchor() {
            const vp = viewport();
            const margin = vp.w <= 600 ? MARGIN_NARROW : MARGIN_WIDE;
            state.left = vp.w - el.offsetWidth - margin.x;
            state.top = vp.h - el.offsetHeight - margin.y;
        }

        function clampState() {
            const vp = viewport();
            state.left = clamp(state.left, 0, Math.max(0, vp.w - el.offsetWidth));
            state.top = clamp(state.top, 0, Math.max(0, vp.h - el.offsetHeight));
        }

        // `position: fixed` is only viewport-relative when no ancestor creates a
        // containing block (transform, filter, backdrop-filter, contain...).
        // Streamlit's DOM does create such ancestors, which makes the element
        // scroll away with the content. Measuring the rendered rect and
        // correcting the offset keeps it pinned whatever the containing block is.
        function pin() {
            const rect = el.getBoundingClientRect();
            const dx = state.left - rect.left;
            const dy = state.top - rect.top;
            if (Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5) { return; }
            const currentLeft = parseFloat(el.style.left) || 0;
            const currentTop = parseFloat(el.style.top) || 0;
            el.style.left = (currentLeft + dx) + "px";
            el.style.top = (currentTop + dy) + "px";
        }

        el.style.right = "auto";
        el.style.bottom = "auto";
        if (state.anchored) { resolveAnchor(); } else { clampState(); }
        el.style.left = state.left + "px";
        el.style.top = state.top + "px";
        pin();

        let queued = false;
        function schedulePin() {
            if (queued) { return; }
            queued = true;
            win.requestAnimationFrame(function() {
                queued = false;
                pin();
            });
        }

        // Capture phase catches scrolling of any Streamlit container, not just
        // the window, so the assistant follows every scrollable ancestor.
        on(win, "scroll", schedulePin, true);
        on(win, "wheel", schedulePin, {passive: true, capture: true});
        on(win, "resize", function() {
            if (state.anchored) { resolveAnchor(); } else { clampState(); }
            schedulePin();
        });
        if (win.visualViewport) {
            on(win.visualViewport, "resize", schedulePin);
            on(win.visualViewport, "scroll", schedulePin);
        }
        // Reruns and popover open/close reflow the layout without a scroll event.
        if (win.__qjPinObserver) {
            try { win.__qjPinObserver.disconnect(); } catch (err) { /* already gone */ }
        }
        const observer = new win.MutationObserver(function() {
            if (!current()) {
                observer.disconnect();
                return;
            }
            schedulePin();
        });
        observer.observe(doc.body, {childList: true, subtree: true});
        win.__qjPinObserver = observer;

        let dragging = false;
        let moved = false;
        let startX = 0, startY = 0, startLeft = 0, startTop = 0;

        on(el, "mousedown", function(ev) {
            if (ev.button !== 0) { return; }
            const rect = el.getBoundingClientRect();
            dragging = true;
            moved = false;
            startX = ev.clientX;
            startY = ev.clientY;
            startLeft = rect.left;
            startTop = rect.top;
        });

        on(doc, "mousemove", function(ev) {
            if (!dragging) { return; }
            const dx = ev.clientX - startX;
            const dy = ev.clientY - startY;
            if (!moved && (Math.abs(dx) > THRESHOLD || Math.abs(dy) > THRESHOLD)) {
                moved = true;
                state.anchored = false;
                el.style.cursor = "grabbing";
                doc.body.style.userSelect = "none";
            }
            if (moved) {
                ev.preventDefault();
                state.left = startLeft + dx;
                state.top = startTop + dy;
                clampState();
                pin();
            }
        });

        on(doc, "mouseup", function() {
            if (!dragging) { return; }
            dragging = false;
            el.style.cursor = "";
            doc.body.style.userSelect = "";
            if (!moved) { return; }
            try {
                win.localStorage.setItem(
                    STORAGE_KEY, JSON.stringify({left: state.left, top: state.top})
                );
            } catch (err) { /* storage unavailable */ }
            // Swallow only the click that ends a real drag, so a plain click
            // still opens the popover.
            el.dataset.qjSuppressClick = "1";
            win.setTimeout(function() { el.dataset.qjSuppressClick = "0"; }, 0);
        });

        on(el, "click", function(ev) {
            if (el.dataset.qjSuppressClick === "1") {
                ev.preventDefault();
                ev.stopPropagation();
            }
        }, true);

        return true;
    }

    if (win.__qjPinRetry) { win.clearInterval(win.__qjPinRetry); }
    if (!init()) {
        win.__qjPinRetry = win.setInterval(function() {
            if (!current() || init()) { win.clearInterval(win.__qjPinRetry); }
        }, 150);
        win.setTimeout(function() { win.clearInterval(win.__qjPinRetry); }, 10000);
    }
})();
</script>
"""


def _render_drag_script() -> None:
    """Keep the assistant pinned to the viewport and make it mouse-draggable.

    Streamlit reruns the whole script on every interaction, so the dragged
    position is persisted client-side (parent window localStorage) and
    re-applied on each rerun.
    """
    script = _DRAG_SCRIPT.replace("__STORAGE_KEY__", _DRAG_STORAGE_KEY).replace(
        "__SELECTOR__", _ASSISTANT_SELECTOR
    )
    components.html(script, height=0, width=0)


def render_qingju_assistant(page: str) -> None:
    asset = Path(__file__).resolve().parents[2] / "assets/illustrations/qingju_assistant.svg"
    image = base64.b64encode(asset.read_bytes()).decode("ascii")
    st.markdown("""
    <style>
    .st-key-qingju_assistant {
      position:fixed!important; right:22px; bottom:20px; width:128px!important;
      z-index:10000; background:transparent; padding:0!important; cursor:grab;
    }
    .st-key-qingju_assistant:active { cursor:grabbing; }
    .st-key-qingju_assistant [data-testid="stPopoverButton"] {
      position:relative; margin-top:92px; min-height:38px; width:128px;
      border-radius:24px; border:1px solid #acd5bd; background:#edf8ef; color:#24523b;
      box-shadow:0 4px 18px #163b3020; font-size:13px;
    }
    .st-key-qingju_assistant [data-testid="stPopoverButton"]::before {
      content:""; position:absolute; bottom:36px; left:19px; width:90px; height:100px;
      background:center/contain no-repeat url("data:image/svg+xml;base64,IMAGE");
      animation:qj-assistant-bob 3.5s ease-in-out infinite;
    }
    .st-key-qingju_assistant [data-testid="stPopoverButton"] svg { display:none; }
    [data-testid="stPopoverBody"]:has(.st-key-qingju_assistant_content) {
      width:min(500px,calc(100vw - 24px))!important; max-height:70dvh;
      overflow-y:auto; overscroll-behavior:contain; border-radius:20px;
      background:#fffdf8; border:1px solid #bfdcc8; padding:18px;
    }
    .st-key-qingju_assistant_content [data-testid="stFormSubmitButton"] { margin-top:0; }
    @keyframes qj-assistant-bob { 50% { transform:translateY(-4px) rotate(2deg); } }
    @media(max-width:600px) {
      .st-key-qingju_assistant { right:12px; bottom:max(12px,env(safe-area-inset-bottom)); }
      [data-testid="stPopoverBody"]:has(.st-key-qingju_assistant_content) { max-height:65dvh; }
    }
    @media(prefers-reduced-motion:reduce) {
      .st-key-qingju_assistant button::before { animation:none!important; }
    }
    </style>
    """.replace("IMAGE", image), unsafe_allow_html=True)
    _render_drag_script()
    with st.container(key="qingju_assistant"):
        with st.popover("青聚小幫手", use_container_width=True):
            with st.container(key="qingju_assistant_content"):
                st.subheader("青聚小幫手")
                st.caption(f"陪你探索青聚新北 · 目前頁面：{page}。僅使用青聚既有的新北資料；AI 政策分析為獨立服務。")
                examples = ["自行輸入", "職涯探索可以看什麼？", "護理轉職科技有哪些方向？",
                            "板橋目前青年人口有多少？", "比較板橋與淡水", "板橋租金是多少？",
                            "哪些行政區值得進一步觀察？", "每千名青年求才人數是什麼？"]
                with st.form("qingju_assistant_form"):
                    example = st.selectbox("推薦問題", examples, key="qingju_assistant_example")
                    question = st.text_input("想問青聚什麼？", max_chars=500, key="qingju_assistant_question",
                                             placeholder="輸入問題，或選一個推薦問題")
                    submitted = st.form_submit_button("詢問小幫手", use_container_width=True)
                if submitted:
                    query = question.strip() or (example if example != "自行輸入" else "")
                    if not query:
                        st.info("請輸入問題或選擇推薦問題。")
                    else:
                        try:
                            session = SessionContext(**st.session_state.get("qingju_agent_context", {}))
                            result = PolicyAgentOrchestrator().run(query, session)
                            # Retain existing site/career explanations not in the policy tool scope.
                            if not result["tool_results"]:
                                legacy = answer_question(query, load_context(), page)
                                if legacy["intent"] in {"site_guide", "career_evidence", "metric_explain"}:
                                    result = {**legacy, "tool_results": [], "session_context": result["session_context"]}
                            st.session_state.qingju_agent_context = result["session_context"]
                            st.session_state.qingju_assistant_answer = result
                        except (OSError, ValueError, KeyError, RuntimeError):
                            st.session_state.qingju_assistant_answer = None
                            st.error("目前資料不足以回答這個問題。青聚資料暫時無法讀取，請稍後再試。")
                result = st.session_state.get("qingju_assistant_answer")
                if result:
                    st.markdown("#### 回答")
                    st.write(result["answer"])
                    if result["evidence"]:
                        st.markdown("#### 數據依據")
                        st.dataframe(pd.DataFrame(result["evidence"]).rename(columns=LABELS), hide_index=True, use_container_width=True)
                    with st.expander("資料來源、期間與限制"):
                        if result["data_period"]:
                            st.json(result["data_period"])
                        for item in result["sources"]:
                            st.write(item["file"])
                            st.caption(f"來源：{item['source']} · 期間：{item['data_period'] or '未確認'}")
                            if item.get("url", "") and item["url"].startswith("https://"):
                                st.link_button("原始來源", item["url"])
                            st.code(item["sha256"], language=None)
                        for warning in result["reliability"]:
                            st.caption(f"{warning['district']} · 刊登樣本 {warning['job_postings']}：{warning['warning']}")
                        for tool_result in result.get("tool_results", []):
                            if tool_result["data"].get("factors"):
                                st.json(tool_result["data"]["factors"])
                        for note in result["limitations"]:
                            st.caption(note)
                else:
                    st.info("可以問職涯探索、行政區人口、職缺、租金與政策觀察；所有數字僅來自青聚網站既有的新北資料。")
