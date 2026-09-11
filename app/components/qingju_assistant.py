"""Native Streamlit popover: available on every Qingju page, no iframe/server."""
from __future__ import annotations

import base64
from pathlib import Path

import pandas as pd
import streamlit as st

from assistant_service import LABELS, answer_question, load_context


def render_qingju_assistant(page: str) -> None:
    asset = Path(__file__).resolve().parents[2] / "assets/illustrations/qingju_assistant.svg"
    image = base64.b64encode(asset.read_bytes()).decode("ascii")
    st.markdown("""
    <style>
    .st-key-qingju_assistant {
      position:fixed!important; right:22px; bottom:20px; width:128px!important;
      z-index:10000; background:transparent; padding:0!important;
    }
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
    with st.container(key="qingju_assistant"):
        with st.popover("青聚小幫手", use_container_width=True):
            with st.container(key="qingju_assistant_content"):
                st.subheader("青聚小幫手")
                st.caption(f"陪你探索青聚新北 · 目前頁面：{page}。點擊外側或按 Esc 可收起。")
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
                            st.session_state.qingju_assistant_answer = answer_question(query, load_context(), page)
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
                        for note in result["limitations"]:
                            st.caption(note)
                else:
                    st.info("可以問職涯探索、行政區人口、職缺、租金與政策觀察；所有數字來自青聚網站既有資料。")
