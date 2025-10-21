import streamlit as st
import pandas as pd
import httpx
import asyncio
import time
import json
import shlex
import re
from collections import Counter, defaultdict


# -----------------------------
# Helpers
# -----------------------------

def parse_curl(curl_text: str):
    """Parse a curl command into method, url, headers, data.

    Supports typical patterns like:
    curl -X POST "https://api.example.com/path" -H "Authorization: Bearer ..." -H "Content-Type: application/json" \
         --data '{"a":1, "b":"{{stb_id}}"}'
    """
    if not curl_text or "curl" not in curl_text:
        raise ValueError("유효한 curl 텍스트가 아닙니다.")

    # Normalize Windows/POSIX line continuations: remove trailing \\ or ^ at EOL
    text = curl_text.replace("\r\n", "\n")
    text = re.sub(r"\\\n", " ", text)  # POSIX \\ line continuation
    text = re.sub(r"\^\n", " ", text)   # Windows ^ line continuation
    text = re.sub(r"\^\s*$", "", text)  # Remove trailing ^ at end of lines

    # Tokenize while respecting quotes
    tokens = shlex.split(text)

    # Remove leading 'curl'
    if tokens and tokens[0] == "curl":
        tokens = tokens[1:]

    method = None
    url = None
    headers = {}
    data = None

    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in ("-X", "--request") and i + 1 < len(tokens):
            method = tokens[i + 1].upper()
            i += 2
            continue
        if t in ("-H", "--header") and i + 1 < len(tokens):
            hv = tokens[i + 1]
            if ":" in hv:
                k, v = hv.split(":", 1)
                headers[k.strip()] = v.strip()
            i += 2
            continue
        if t.startswith("http://") or t.startswith("https://"):
            url = t
            i += 1
            continue
        if t in ("--data", "--data-raw", "--data-binary", "-d") and i + 1 < len(tokens):
            data = tokens[i + 1]
            i += 2
            continue
        # Ignore other flags like --location, -L, etc.
        if t in ("--location", "-L"):
            i += 1
            continue
        # Ignore other flags
        i += 1

    if method is None:
        method = "GET" if (data is None) else "POST"
    if url is None:
        raise ValueError("curl에서 URL을 찾지 못했습니다.")

    return method, url, headers, data


# 점(.)을 포함한 키 지원 (예: stb_info.stb_id)
VAR_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_\.]+)\s*\}\}")


def apply_placeholders(text: str, variables: dict) -> str:
    if text is None:
        return None
    def _repl(m):
        key = m.group(1)
        return str(variables.get(key, m.group(0)))
    return VAR_PATTERN.sub(_repl, text)


def enforce_three_fields(body_text: str, variables: dict) -> str:
    """If the curl body lacks placeholders and contains literals, forcibly replace
    only the three target fields in-place by regex without altering other fields.
    Targets inside JSON-like text:
      - stb_info.stb_id
      - stb_info.mac_addr
      - stb_info.modl_nm
    """
    # 먼저 JSON으로 파싱 가능하면 안전하게 값을 교체한 뒤 문자열로 직렬화
    try:
        obj = json.loads(body_text)
        if isinstance(obj, dict) and isinstance(obj.get("stb_info"), dict):
            si = obj["stb_info"]
            if variables.get('stb_info.stb_id') is not None:
                si["stb_id"] = variables.get('stb_info.stb_id')
            if variables.get('stb_info.mac_addr') is not None:
                si["mac_addr"] = variables.get('stb_info.mac_addr')
            if variables.get('stb_info.modl_nm') is not None:
                si["modl_nm"] = variables.get('stb_info.modl_nm')
            return json.dumps(obj, ensure_ascii=False)
    except Exception:
        pass

    if not body_text:
        return body_text
    replacements = [
        (r'("stb_id"\s*:\s*")([^"]*)(")', variables.get('stb_info.stb_id', '')),
        (r'("mac_addr"\s*:\s*")([^"]*)(")', variables.get('stb_info.mac_addr', '')),
        (r'("modl_nm"\s*:\s*")([^"]*)(")', variables.get('stb_info.modl_nm', '')),
    ]
    new_text = body_text
    for pattern, value in replacements:
        if value is None:
            continue
        try:
            # 함수형 대체를 사용하여 백슬래시/특수문자 안전 처리
            new_text = re.sub(pattern, lambda m: m.group(1) + str(value) + m.group(3), new_text, count=1)
        except Exception:
            pass
    return new_text


async def send_request(client: httpx.AsyncClient, method: str, url: str, headers: dict, data: str, timeout_s: float, capture_preview: bool):
    start = time.perf_counter()
    try:
        sent_body_str = None
        if data is not None:
            # 원문 문자열 그대로 전송 (필드 순서/서식 보존)
            sent_body_str = data
            resp = await client.request(method, url, headers=headers, content=data.encode("utf-8"), timeout=timeout_s)
        else:
            resp = await client.request(method, url, headers=headers, timeout=timeout_s)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        result = {
            "ok": True,
            "status": resp.status_code,
            "elapsed_ms": elapsed_ms,
            # 요청 요약은 항상 포함
            "request": {
                "method": method,
                "url": url,
                "headers": headers or {},
                "body": sent_body_str
            }
        }
        # 전체 응답 본문 저장 (요청에 따라 프리뷰 대신 전체 제공)
        try:
            result["response_body"] = resp.text
        except Exception:
            result["response_body"] = None
        return result
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return {
            "ok": False, 
            "error": str(e), 
            "elapsed_ms": elapsed_ms,
            # 실패한 경우에도 요청 정보 포함
            "request": {
                "method": method,
                "url": url,
                "headers": headers or {},
                "body": data
            }
        }


async def run_load_test(method: str, url: str, headers: dict, data: str, rows: list, rps: int, duration_s: int, timeout_s: float, concurrency: int, capture_preview: bool):
    total_requests = rps * duration_s
    semaphore = asyncio.Semaphore(concurrency)
    results = []

    async with httpx.AsyncClient() as client:
        async def _one(idx: int):
            async with semaphore:
                row = rows[idx % len(rows)] if rows else {}
                # 치환 변수는 오직 세 가지 (점 포함 키명 유지)
                variables = {
                    "stb_info.stb_id": str(row.get("stb_id", "")),
                    "stb_info.mac_addr": str(row.get("mac_address", "")),
                    "stb_info.modl_nm": str(row.get("model_nm", "")),
                }
                u = apply_placeholders(url, variables)
                h = {k: apply_placeholders(v, variables) for k, v in (headers or {}).items()}
                d = apply_placeholders(data, variables)
                # 만약 템플릿에 플레이스홀더가 없고 예시처럼 리터럴이 온 경우, 세 필드만 강제치환
                if d and ('{{' not in d and '}}' not in d):
                    d = enforce_three_fields(d, variables)

                # 자동 바디 생성 제거: cURL 샘플 형식을 그대로 사용
                # Content-Type은 사용자 템플릿/헤더 결정에 따름
                
                # 디버깅: 첫 번째 요청만 로그 출력
                if idx == 0:
                    print(f"DEBUG - Request {idx}:")
                    print(f"  Method: {method}")
                    print(f"  URL: {u}")
                    print(f"  Headers: {h}")
                    print(f"  Data: {d[:100] if d else 'None'}...")
                
                return await send_request(client, method, u, h, d, timeout_s, capture_preview)

        # schedule respecting rate
        tasks = []
        start_time = time.perf_counter()
        for i in range(total_requests):
            # Schedule task
            tasks.append(asyncio.create_task(_one(i)))
            # Pace at RPS
            target_elapsed = (i + 1) / float(rps)
            while True:
                now = time.perf_counter() - start_time
                if now >= target_elapsed:
                    break
                await asyncio.sleep(min(0.001, target_elapsed - now))

        for t in asyncio.as_completed(tasks):
            res = await t
            results.append(res)

    return results


def summarize_results(results: list):
    total = len(results)
    success = sum(1 for r in results if r.get("ok"))
    codes = Counter([r.get("status") for r in results if r.get("ok")])
    latencies = [r.get("elapsed_ms", 0.0) for r in results]
    latencies_ok = [r.get("elapsed_ms", 0.0) for r in results if r.get("ok")]

    def pct(arr, p):
        if not arr:
            return None
        s = sorted(arr)
        k = max(0, min(len(s) - 1, int(round((p / 100.0) * (len(s) - 1)))))
        return s[k]

    summary = {
        "total": total,
        "success": success,
        "success_rate": (success / total * 100.0) if total else 0.0,
        "codes": dict(codes),
        "avg_ms": (sum(latencies) / total) if total else None,
        "p50_ms": pct(latencies_ok, 50) if latencies_ok else None,
        "p90_ms": pct(latencies_ok, 90) if latencies_ok else None,
        "p99_ms": pct(latencies_ok, 99) if latencies_ok else None,
    }
    return summary


# -----------------------------
# Streamlit UI
# -----------------------------

st.set_page_config(page_title="Stress Tester", page_icon="🚀", layout="wide")
st.title("🚀 Stress Tester")
st.caption("CSV 변수 치환 + cURL 템플릿 기반 REST 부하 테스트")

tabs = st.tabs(["⚙️ 설정", "▶️ 실행", "📊 통계"])


with tabs[0]:
    st.subheader("cURL 템플릿")
    default_curl = st.session_state.get("curl_template", """curl -X POST "http://1.255.145.229:8080/v1/edmp/api/update/stb" \\
-H "Content-Type: application/json;charset=utf-8" \\
-H "IF: IF-EDMP.UPDATE-003" \\
-H "response_format: json" \\
-H "ver: v1" \\
--data '{
    "if_no": "IF-EDMP.UPDATE.API-003",
    "response_format": "json",
    "ui_name": "NXNEWUI2Q",
    "ver": "v1",
    "stb_info": {
        "stb_id": "{A9CCC0C8-F569-11E9-819D-37B877ECC397}",
        "mac_addr": "80:8c:97:22:1c:80",
        "modl_nm": "BKO-UA500R",
        "stb_sw_ver": "16.522.47-0000",
        "stb_ip": "0.0.0.0",
        "stb_uptime": "20200409123923",
        "rcu_pairing": "0",
        "rcu_manufr_cd": "abcdabcdabcd",
        "rcu_firm_ver": "0x12",
        "hdmi_pow": "1",
        "trigger_cd": "01",
        "timestamp": "1584329976176"
    }
}' """)
    curl_template = st.text_area(
        "curl 샘플 입력",
        value=default_curl,
        height=180,
        placeholder="cURL 샘플을 입력하거나 기본값을 수정하세요. CSV의 stb_id, mac_address, model_nm 값이 stb_info 내부의 해당 필드로 치환됩니다."
    )

    st.markdown("---")
    st.subheader("CSV 업로드 및 컬럼 매핑")
    csv_file = st.file_uploader("CSV 파일 업로드", type=["csv"]) 
    df = None
    if csv_file is not None:
        try:
            df = pd.read_csv(csv_file)
            st.dataframe(df.head(10), use_container_width=True)
        except Exception as e:
            st.error(f"CSV 파일 읽기 오류: {e}")
            df = None

    st.markdown("---")
    col0, col1, col2, col3, col4 = st.columns(5)
    with col0:
        method_override = st.selectbox(
            "HTTP 메서드",
            options=["cURL에서 추출", "GET", "POST", "PUT", "PATCH", "DELETE"],
            index=2  # 기본 POST로 편의 제공
        )
    with col1:
        rps = st.slider("초당 호출 수 (RPS)", min_value=1, max_value=1000, value=10, step=1)
    with col2:
        duration_s = st.number_input("부하 지속 시간(초)", min_value=1, max_value=3600, value=10, step=1)
    with col3:
        timeout_s = st.number_input("요청 타임아웃(초)", min_value=1.0, max_value=60.0, value=10.0, step=0.5)
    with col4:
        concurrency = st.number_input("동시성(최대 동시 요청)", min_value=1, max_value=2000, value=100, step=1)

    st.markdown("---")
    capture_preview = st.checkbox("응답 본문 미리보기 수집(상위 200자)", value=False)

    if st.button("설정 저장"):
        st.session_state["curl_template"] = curl_template
        st.session_state["method_override"] = method_override
        st.session_state["rps"] = rps
        st.session_state["duration_s"] = duration_s
        st.session_state["timeout_s"] = timeout_s
        st.session_state["concurrency"] = concurrency
        st.session_state["capture_preview"] = capture_preview
        if df is not None:
            try:
                # pandas 버전 호환성을 위한 안전한 변환
                st.session_state["csv_rows"] = df.to_dict(orient="records")
            except Exception as e:
                # pandas 버전 호환성 문제 대비 대안 방법들
                try:
                    # 방법 1: iterrows 사용
                    st.session_state["csv_rows"] = [row.to_dict() for _, row in df.iterrows()]
                except Exception as e2:
                    # 방법 2: 수동 변환 (최후의 수단)
                    st.session_state["csv_rows"] = []
                    for i in range(len(df)):
                        row_dict = {}
                        for col in df.columns:
                            row_dict[col] = df.iloc[i][col]
                        st.session_state["csv_rows"].append(row_dict)
                    st.warning(f"pandas 호환성 문제로 수동 변환을 사용했습니다: {e2}")
        st.success("설정을 저장했습니다.")


with tabs[1]:
    st.subheader("부하 테스트 실행")
    curl_template = st.session_state.get("curl_template")
    method_override = st.session_state.get("method_override", "cURL에서 추출")
    csv_rows = st.session_state.get("csv_rows", [])
    rps = st.session_state.get("rps", 10)
    duration_s = st.session_state.get("duration_s", 10)
    timeout_s = st.session_state.get("timeout_s", 10.0)
    concurrency = st.session_state.get("concurrency", 100)
    capture_preview = st.session_state.get("capture_preview", False)

    if st.button("▶️ Start"):
        if not curl_template:
            st.error("cURL 템플릿을 입력/저장하세요.")
            st.stop()
        try:
            method, url, headers, data = parse_curl(curl_template)
        except Exception as e:
            st.error(f"cURL 파싱 실패: {e}")
            st.stop()

        # 사용자 선택이 있으면 메서드 덮어쓰기
        if method_override and method_override != "cURL에서 추출":
            method = method_override.upper()

        st.info(f"메서드: {method} | URL: {url}")
        with st.spinner("부하 테스트 실행 중..."):
            try:
                results = asyncio.run(
                    run_load_test(method, url, headers, data, csv_rows, rps, duration_s, timeout_s, concurrency, capture_preview)
                )
                st.session_state["results"] = results
            except Exception as e:
                st.error(f"실행 오류: {e}")
            else:
                st.success("테스트 완료")

    # 최근 결과 일부 미리보기 (요청/응답 분리 표시)
    results = st.session_state.get("results")
    if results:
        sample = results[:3]
        for i, r in enumerate(sample):
            st.markdown(f"**샘플 {i}**")
            col_req, col_resp = st.columns(2)
            with col_req:
                st.caption("Request")
                st.json({
                    "method": r.get("request", {}).get("method"),
                    "url": r.get("request", {}).get("url"),
                    "headers": r.get("request", {}).get("headers"),
                    "body": r.get("request", {}).get("body")
                })
            with col_resp:
                st.caption("Response")
                st.json({
                    "status": r.get("status"),
                    "elapsed_ms": r.get("elapsed_ms"),
                    "body": r.get("response_body")
                })
            st.markdown("---")


with tabs[2]:
    st.subheader("통계 요약")
    results = st.session_state.get("results")
    if not results: 
        st.info("아직 실행 결과가 없습니다.")
    else:
        summary = summarize_results(results)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("총 요청", f"{summary['total']}")
        c2.metric("성공(%)", f"{summary['success_rate']:.1f}%")
        c3.metric("평균 지연(ms)", f"{summary['avg_ms']:.1f}" if summary['avg_ms'] is not None else "-")
        c4.metric("P99(ms)", f"{summary['p99_ms']:.1f}" if summary['p99_ms'] is not None else "-")

        st.markdown("---")
        st.write("HTTP 상태 코드 분포")
        code_rows = sorted(summary["codes"].items()) if summary["codes"] else []
        st.table({"status_code": [k for k, _ in code_rows], "count": [v for _, v in code_rows]})

        st.markdown("---")
        st.write("지연시간 샘플(상위 50개)")
        st.write([r.get("elapsed_ms", 0.0) for r in results[:50]])


