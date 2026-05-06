import streamlit as st
import io
import re
import zipfile
from lxml import etree
from pythainlp.tokenize import word_tokenize

# --- 1. Streamlit UI Config ---
st.set_page_config(
    page_title="Thai Word Wrap & Font Fixer | by Joopiest", 
    page_icon="📝",
    layout="centered"
)

# --- 2. Configuration & Analytics ---
THAI_FONT = "Sarabun"  
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"
THAI_RE = re.compile("[\u0e00-\u0e7f]")
MIXED_RE = re.compile("([\u0e00-\u0e7f]+)")

# สำหรับระบบ Logbook (Hits Counter Badge)
# แทนที่ 'joopiest/thai-word-wrap-fixer' ด้วยชื่อ repository จริงของคุณจู๊ป
HITS_BADGE_URL = f"https://hits.dwyl.com/joopiest/thai-word-wrap-fixer.svg"

def q(tag): return f"{{{W_NS}}}{tag}"

# --- 3. Core Logic Functions ---
def fix_thai_text(text):
    if not THAI_RE.search(text): return text
    parts = MIXED_RE.split(text)
    out = []
    for part in parts:
        if part and all('\u0e00' <= ch <= '\u0e7f' for ch in part):
            tokens = word_tokenize(part, engine="newmm", keep_whitespace=False)
            out.append("\u200b".join(t for t in tokens if t))
        else:
            out.append(part)
    return "".join(out)

def apply_thai_rpr(rpr):
    rfonts = rpr.find(q('rFonts'))
    if rfonts is None:
        rfonts = etree.Element(q('rFonts'))
        rpr.insert(0, rfonts)
    rfonts.set(q('ascii'), THAI_FONT)
    rfonts.set(q('hAnsi'), THAI_FONT)
    rfonts.set(q('eastAsia'), THAI_FONT)
    rfonts.set(q('cs'), THAI_FONT)
    for t_attr in ['asciiTheme', 'hAnsiTheme', 'eastAsiaTheme', 'cstheme']:
        if q(t_attr) in rfonts.attrib: del rfonts.attrib[q(t_attr)]
    lang = rpr.find(q('lang')) or etree.SubElement(rpr, q('lang'))
    lang.set(q('val'), 'th-TH')
    lang.set(q('eastAsia'), 'th-TH')
    lang.set(q('bidi'), 'th-TH')

def process_xml_bytes(xml_bytes):
    tree = etree.parse(io.BytesIO(xml_bytes))
    root = tree.getroot()
    for br in root.findall(f".//{q('br')}"):
        if br.get(q('type'), 'textWrapping') == 'textWrapping':
            p = br.getparent()
            t_s = etree.Element(q('t')); t_s.text = ' '; t_s.set(f"{{{XML_NS}}}space", "preserve")
            p.insert(list(p).index(br), t_s); p.remove(br)
    for r_el in root.findall(f".//{q('r')}"):
        rpr = r_el.find(q('rPr'))
        if rpr is None:
            rpr = etree.Element(q('rPr')); r_el.insert(0, rpr)
        apply_thai_rpr(rpr)
        for t in r_el.findall(f".//{q('t')}"):
            if THAI_RE.search(t.text or ""):
                t.text = fix_thai_text(t.text)
                t.set(f"{{{XML_NS}}}space", "preserve")
    out = io.BytesIO()
    tree.write(out, xml_declaration=True, encoding="UTF-8", standalone=True)
    return out.getvalue()

def patch_styles_bytes(xml_bytes):
    tree = etree.parse(io.BytesIO(xml_bytes))
    root = tree.getroot()
    for rpr in root.findall(f".//{q('rPrDefault')}/{q('rPr')}"): apply_thai_rpr(rpr)
    for style in root.findall(f".//{q('style')}"):
        rpr = style.find(q('rPr')) or etree.SubElement(style, q('rPr'))
        apply_thai_rpr(rpr)
    out = io.BytesIO()
    tree.write(out, xml_declaration=True, encoding="UTF-8", standalone=True)
    return out.getvalue()

# --- 4. CSS Design ---
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stFileUploadDropzone { border: 2px dashed #4CAF50 !important; border-radius: 15px !important; }
    .footer { font-size: 14px; color: #64748b; text-align: center; margin-top: 50px; }
    .credit { font-weight: bold; color: #2e7d32; }
    </style>
""", unsafe_allow_html=True)

# --- 5. UI Layout ---

# Header Section with Credit
st.title("📝 Thai Word Wrap & Font Fixer")
st.markdown(f"พัฒนาโดย: **<span class='credit'>Joopiest Udomsaph</span>**", unsafe_allow_html=True)

# Logbook / Analytics Badge (แสดงจำนวนคนเข้าใช้)
st.markdown(f"[![Visitors]({HITS_BADGE_URL})](https://hits.dwyl.com)")

st.write("เครื่องมือช่วยแก้ปัญหาภาษาไทยตัดคำผิดและฟอนต์ไม่มาตรฐานจาก Google Docs")

# ส่วนรับไฟล์
uploaded_file = st.file_uploader("📥 ลากไฟล์ .docx มาวางตรงนี้เพื่อเริ่มประมวลผล", type="docx")

if uploaded_file is not None:
    with st.spinner('กำลังประมวลผล...'):
        try:
            input_zip = zipfile.ZipFile(uploaded_file)
            output_buffer = io.BytesIO()
            with zipfile.ZipFile(output_buffer, "w", zipfile.ZIP_DEFLATED) as output_zip:
                for name in input_zip.namelist():
                    content = input_zip.read(name)
                    if re.match(r'word/(document|header\d*|footer\d*|endnotes|footnotes)\.xml$', name):
                        content = process_xml_bytes(content)
                    elif name == 'word/styles.xml':
                        content = patch_styles_bytes(content)
                    output_zip.writestr(name, content)
            
            st.success("🎉 ประมวลผลเสร็จเรียบร้อย!")
            st.download_button(
                label="⬇️ ดาวน์โหลดไฟล์ที่แก้ไขแล้ว",
                data=output_buffer.getvalue(),
                file_name=uploaded_file.name.replace(".docx", "_fixed.docx"),
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                type="primary"
            )
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")

# Disclaimer Section
st.divider()
st.info("⚠️ **Disclaimer:** เครื่องมือนี้ให้บริการฟรีเพื่อสาธารณประโยชน์ ผู้พัฒนา (Joopiest Udomsaph) ไม่รับผิดชอบต่อความเสียหาย สูญหาย หรือความผิดพลาดของข้อมูลใดๆ ที่อาจเกิดขึ้นจากการใช้งานซอฟต์แวร์นี้ในทุกกรณี")

# Footer
st.markdown("<div class='footer'>© 2024 Thai Word Wrap Fixer | พัฒนาด้วย ❤️ เพื่อชุมชนคนทำงาน</div>", unsafe_allow_html=True)


### วิธีการดูสถิติแบบละเอียด (Daily, Monthly, Yearly):
# นอกเหนือจากตัวเลขบนหน้าเว็บ คุณจู๊ปสามารถเข้าไปดูสถิติเชิงลึกได้ที่หน้าจัดการของ Streamlit ครับ:
# 1. ไปที่ [share.streamlit.io](https://share.streamlit.io/)
# 2. คลิกที่จุดสามจุด **(...)** ข้างๆ ชื่อแอปของคุณจู๊ป
# 3. เลือกเมนู **"Analytics"**
# 4. คุณจู๊ปจะเห็นกราฟแสดงจำนวนคนเข้าชม รายวัน รายสัปดาห์ และรายเดือน อย่างละเอียดและแม่นยำที่สุดครับ

# เครื่องมือนี้อัปเกรดเรียบร้อยแล้ว! ลองนำไปใช้และแบ่งปันให้เพื่อนๆ ได้เลยครับ หากมีตรงไหนอยากให้ปรับเพิ่มบอกผมได้ทันทีครับ