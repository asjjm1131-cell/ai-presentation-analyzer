import streamlit as st
import fitz
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


st.set_page_config(
    page_title="AI 발표 코칭 시스템",
    page_icon="🎤",
    layout="wide"
)

st.markdown("""
<style>
.title-box {
    padding: 28px;
    border-radius: 20px;
    background: linear-gradient(135deg, #eef2ff, #f8fafc);
    border: 1px solid #e5e7eb;
    margin-bottom: 25px;
}
.big-title {
    font-size: 42px;
    font-weight: 800;
    color: #1f2937;
}
.sub-title {
    font-size: 18px;
    color: #4b5563;
    margin-top: 10px;
}
.card {
    padding: 22px;
    border-radius: 16px;
    background-color: white;
    border: 1px solid #e5e7eb;
    box-shadow: 0px 4px 12px rgba(0,0,0,0.05);
    margin-bottom: 18px;
}
.score {
    font-size: 38px;
    font-weight: 800;
    color: #2563eb;
}
.good {
    color: #16a34a;
    font-weight: 800;
}
.warn {
    color: #d97706;
    font-weight: 800;
}
.danger {
    color: #dc2626;
    font-weight: 800;
}
</style>
""", unsafe_allow_html=True)


st.markdown("""
<div class="title-box">
    <div class="big-title">🎤 AI 발표자료 + 발표자 분석 시스템</div>
    <div class="sub-title">
    PDF 발표자료와 발표자의 웹캠 이미지를 분석하여 발표 완성도를 평가합니다.
    </div>
</div>
""", unsafe_allow_html=True)


def calculate_ppt_score(text_count, image_count, title_exists=True):
    score = 90
    reasons = []

    if text_count > 1200:
        score -= 45
        reasons.append("텍스트 매우 많음")
    elif text_count > 800:
        score -= 35
        reasons.append("텍스트 많음")
    elif text_count > 500:
        score -= 25
        reasons.append("텍스트 다소 많음")
    elif text_count > 300:
        score -= 12
        reasons.append("텍스트 보통 이상")
    elif text_count < 50:
        score -= 12
        reasons.append("내용이 너무 적음")
    else:
        reasons.append("텍스트 양 적절")

    if image_count == 0:
        score -= 20
        reasons.append("이미지 없음")
    elif image_count > 5:
        score -= 12
        reasons.append("이미지가 너무 많음")
    elif 1 <= image_count <= 3:
        score += 5
        reasons.append("이미지 사용 적절")
    else:
        reasons.append("이미지 개수 보통")

    if title_exists:
        reasons.append("제목 존재")
    else:
        score -= 10
        reasons.append("제목 부족")

    return max(0, min(100, score)), reasons


def analyze_presenter(image_file):
    if not CV2_AVAILABLE:
        return None, "OpenCV가 설치되지 않았습니다."

    image = Image.open(image_file)
    img_array = np.array(image)
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    eye_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_eye.xml"
    )
    smile_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_smile.xml"
    )

    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    score = 40
    feedback = []

    if len(faces) == 0:
        feedback.append("얼굴이 감지되지 않았습니다. 카메라를 정면으로 바라보세요.")
        return {"score": 30, "feedback": feedback}, None

    x, y, w, h = faces[0]
    score += 20
    feedback.append("얼굴이 정상적으로 감지되었습니다.")

    img_h, img_w = gray.shape
    face_center_x = x + w / 2
    screen_center_x = img_w / 2

    centered = abs(face_center_x - screen_center_x) < img_w * 0.18

    if centered:
        score += 15
        feedback.append("발표자가 화면 중앙에 위치해 있습니다.")
    else:
        feedback.append("발표자가 화면 중앙에서 벗어나 있습니다.")

    roi_gray = gray[y:y+h, x:x+w]

    eyes = eye_cascade.detectMultiScale(roi_gray)
    if len(eyes) >= 1:
        score += 15
        feedback.append("눈이 감지되어 시선 처리가 양호한 것으로 판단됩니다.")
    else:
        feedback.append("눈 감지가 약합니다. 카메라를 정면으로 바라보는 것이 좋습니다.")

    smiles = smile_cascade.detectMultiScale(roi_gray, 1.7, 20)
    if len(smiles) > 0:
        score += 10
        feedback.append("웃는 표정이 감지되었습니다. 발표 인상이 긍정적입니다.")
    else:
        feedback.append("표정 변화가 적습니다. 자연스러운 표정을 유지하면 좋습니다.")

    return {"score": max(0, min(100, score)), "feedback": feedback}, None


ppt_score = None
presenter_score = None

col_left, col_right = st.columns(2)

with col_left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📄 발표자료 분석")
    uploaded_file = st.file_uploader("PDF 발표자료를 업로드하세요", type=["pdf"])
    st.markdown('</div>', unsafe_allow_html=True)

with col_right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📷 발표자 분석")
    camera_image = st.camera_input("발표자 사진을 촬영하세요")
    st.markdown('</div>', unsafe_allow_html=True)


if uploaded_file is not None:
    pdf = fitz.open(stream=uploaded_file.read(), filetype="pdf")

    slide_scores = []
    slide_data = []

    for page_num in range(len(pdf)):
        page = pdf[page_num]

        text = page.get_text()
        text_count = len(text)
        image_count = len(page.get_images(full=True))

        lines = [line.strip() for line in text.split("\n") if line.strip()]
        title_exists = len(lines) > 0 and len(lines[0]) >= 3

        score, reasons = calculate_ppt_score(text_count, image_count, title_exists)

        if score >= 75:
            danger_text = "양호"
            danger_class = "good"
        elif score >= 50:
            danger_text = "주의"
            danger_class = "warn"
        else:
            danger_text = "위험"
            danger_class = "danger"

        estimated_time = text_count / 450

        slide_scores.append(score)
        slide_data.append({
            "page": page_num + 1,
            "text_count": text_count,
            "image_count": image_count,
            "score": score,
            "danger_text": danger_text,
            "danger_class": danger_class,
            "reasons": reasons,
            "estimated_time": estimated_time
        })

    worst_slide = slide_scores.index(min(slide_scores)) + 1
    total_text_count = sum(item["text_count"] for item in slide_data)
    total_estimated_time = total_text_count / 450

    base_score = int(np.mean(slide_scores))
    score_std = np.std(slide_scores)
    avg_text_per_slide = total_text_count / len(slide_data)

    text_only_count = sum(1 for item in slide_data if item["image_count"] == 0)
    text_only_ratio = text_only_count / len(slide_data)

    ppt_score = base_score
    final_reasons = []

    if score_std > 20:
        ppt_score -= 10
        final_reasons.append("슬라이드별 품질 편차가 큼")
    elif score_std > 12:
        ppt_score -= 5
        final_reasons.append("슬라이드별 품질 편차가 있음")

    if avg_text_per_slide > 700:
        ppt_score -= 15
        final_reasons.append("슬라이드당 평균 글자 수가 많음")
    elif avg_text_per_slide > 450:
        ppt_score -= 8
        final_reasons.append("슬라이드당 평균 글자 수가 다소 많음")

    if text_only_ratio > 0.5:
        ppt_score -= 15
        final_reasons.append("텍스트 위주 슬라이드 비율이 높음")
    elif text_only_ratio > 0.3:
        ppt_score -= 8
        final_reasons.append("텍스트 위주 슬라이드가 다소 많음")

    if total_estimated_time > 15:
        ppt_score -= 12
        final_reasons.append("예상 발표 시간이 너무 김")
    elif total_estimated_time > 10:
        ppt_score -= 6
        final_reasons.append("예상 발표 시간이 다소 김")

    if len(final_reasons) == 0:
        final_reasons.append("전체 구성이 안정적임")

    ppt_score = max(0, min(100, int(ppt_score)))

    st.subheader("📊 슬라이드별 분석 결과")

    for item in slide_data:
        reason_text = ", ".join(item["reasons"])

        st.markdown(f"""
        <div class="card">
            <h3>슬라이드 {item["page"]}</h3>
            <p>글자 수: {item["text_count"]}</p>
            <p>이미지 개수: {item["image_count"]}</p>
            <p>예상 발표 시간: <b>{item["estimated_time"]:.1f}분</b></p>
            <p>생존 가능성: <b>{item["score"]}%</b></p>
            <p>위험도: <span class="{item["danger_class"]}">{item["danger_text"]}</span></p>
            <p>분석 이유: <b>{reason_text}</b></p>
        </div>
        """, unsafe_allow_html=True)

    st.subheader("📈 슬라이드별 생존 가능성 그래프")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(range(1, len(slide_scores) + 1), slide_scores, marker="o")
    ax.axhline(y=75, linestyle="--", label="Good 기준")
    ax.axhline(y=50, linestyle="--", label="Warning 기준")
    ax.set_xlabel("Slide Number")
    ax.set_ylabel("Survival Score")
    ax.set_ylim(0, 100)
    ax.grid(True)
    ax.legend()
    st.pyplot(fig)

    final_reason_text = ", ".join(final_reasons)

    st.markdown(f"""
    <div class="card">
        <h3>발표자료 최종 결과</h3>
        <p>기본 평균 점수: <b>{base_score}%</b></p>
        <p>최종 발표자료 점수</p>
        <div class="score">{ppt_score}%</div>
        <p>가장 위험한 슬라이드: <b>{worst_slide}페이지</b></p>
        <p>총 예상 발표 시간: <b>{total_estimated_time:.1f}분</b></p>
        <p>슬라이드당 평균 글자 수: <b>{avg_text_per_slide:.0f}자</b></p>
        <p>텍스트 위주 슬라이드 비율: <b>{text_only_ratio * 100:.1f}%</b></p>
        <p>최종 감점/판단 이유: <b>{final_reason_text}</b></p>
    </div>
    """, unsafe_allow_html=True)


if camera_image is not None:
    result, error = analyze_presenter(camera_image)

    st.subheader("🧑 발표자 분석 결과")

    if error:
        st.error(error)
    else:
        presenter_score = result["score"]

        st.markdown(f"""
        <div class="card">
            <h3>발표자 점수</h3>
            <div class="score">{presenter_score}%</div>
        </div>
        """, unsafe_allow_html=True)

        for fb in result["feedback"]:
            st.write("• " + fb)


if ppt_score is not None and presenter_score is not None:
    final_score = int(ppt_score * 0.6 + presenter_score * 0.4)

    st.header("🏁 종합 발표 평가")

    st.markdown(f"""
    <div class="card">
        <p>발표자료 점수: <b>{ppt_score}%</b></p>
        <p>발표자 점수: <b>{presenter_score}%</b></p>
        <p>최종 발표 완성도</p>
        <div class="score">{final_score}%</div>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("💡 종합 피드백")

    if final_score >= 80:
        st.success("발표자료와 발표자 상태가 모두 우수합니다.")
    elif final_score >= 60:
        st.warning("전체적으로 양호하지만 일부 슬라이드 구성 또는 발표 자세 개선이 필요합니다.")
    else:
        st.error("발표자료와 발표자 상태 모두 개선이 필요합니다.")
else:
    st.info("PDF 발표자료와 발표자 사진을 모두 입력하면 종합 평가가 출력됩니다.")
