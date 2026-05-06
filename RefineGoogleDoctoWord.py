import streamlit as st
import io
import re
import zipfile
from lxml import etree
from pythainlp.tokenize import word_tokenize

# --- 1. Streamlit UI Config ---
st.set_page_config(page_title="Thai Word Wrap & Font Fixer", page_icon="📝")

# --- 2. Configuration ---
THAI_FONT = "Sarabun"  
ZWSP = "\u200b"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"
THAI_RE = re.compile("[\u0e00-\u0e7f]")
MIXED_RE = re.compile("([\u0e00-\u0e7f]+)")

def q(tag): return f"{{{W_NS}}}{tag}"

# --- 3. Core Logic Functions ---
def fix_thai_text(text):
    if not THAI_RE.search(text):
        return text
    parts = MIXED_RE.split(text)
    out = []
    for part in parts:
        if part and all('\u0e00' <= ch <= '\u0e7f' for ch in part):
            tokens = word_tokenize(part, engine="newmm", keep_whitespace=False)
            out.append(ZWSP.join(t for t in tokens if t))
        else:
            out.append(part)
    return "".join(out)

def apply_thai_rpr(rpr):
    # ค้นหาหรือสร้างแท็ก rFonts
    rfonts = rpr.find(q('rFonts'))
    if rfonts is None:
        rfonts = etree.Element(q('rFonts'))
        rpr.insert(0, rfonts)
    
    # บังคับใช้ฟอนต์ Sarabun
    rfonts.set(q('ascii'), THAI_FONT)
    rfonts.set(q('hAnsi'), THAI_FONT)
    rfonts.set(q('eastAsia'), THAI_FONT)
    rfonts.set(q('cs'), THAI_FONT)

    # ปลดล็อค Theme
    for theme_attr in ['asciiTheme', 'hAnsiTheme', 'eastAsiaTheme', 'cstheme']:
        if q(theme_attr) in rfonts.attrib:
            del rfonts.attrib[q(theme_attr)]

    # ตั้งค่าภาษา
    lang = rpr.find(q('lang'))
    if lang is None:
        lang = etree.SubElement(rpr, q('lang'))
    lang.set(q('val'), 'th-TH')
    lang.set(q('eastAsia'), 'th-TH')
    lang.set(q('bidi'), 'th-TH')

def process_xml_bytes(xml_bytes):
    tree = etree.parse(io.BytesIO(xml_bytes))
    root = tree.getroot()
    
    # จัดการการขึ้นบรรทัดใหม่
    for br in root.findall(f".//{q('br')}"):
        if br.get(q('type'), 'textWrapping') == 'textWrapping':
            parent = br.getparent()
            idx = list(parent).index(br)
            t_space = etree.Element(q('t'))
            t_space.text = ' '
            t_space.set(f"{{{XML_NS}}}space", "preserve")
            parent.insert(idx, t_space)
            parent.remove(br)

    # วนลูปจัดการข้อความ (Run)
    for r_el in root.findall(f".//{q('r')}"):
        t_elements = r_el.findall(f".//{q('t')}")
        
        # แก้ไขจุดที่ทำให้เกิด Error: สร้าง rPr ให้ถูกวิธี
        rpr = r_el.find(q('rPr'))
        if rpr is None:
            rpr = etree.Element(q('rPr'))
            r_el.insert(0, rpr)
            
        apply_thai_rpr(rpr)
        
        for t in t_elements:
            orig = t.text or ""
            if THAI_RE.search(orig):
                t.text = fix_thai_text(orig)
                t.set(f"{{{XML_NS}}}space", "preserve")

    out = io.BytesIO()
    tree.write(out, xml_declaration=True, encoding="UTF-8", standalone=True)
    return out.getvalue()

def patch_styles_bytes(xml_bytes):
    tree = etree.parse(io.BytesIO(xml_bytes))
    root = tree.getroot()
    for rpr in root.findall(f".//{q('rPrDefault')}/{q('rPr')}"):
        apply_thai_rpr(rpr)
    for style in root.findall(f".//{q('style')}"):
        rpr = style.find(q('rPr'))
        if rpr is None:
            rpr = etree.SubElement(style, q('rPr'))
        apply_thai_rpr(rpr)
    out = io.BytesIO()
    tree.write(out, xml_declaration=True, encoding="UTF-8", standalone=True)
    return out.getvalue()

# --- 4. CSS: คืนค่าระบบ Highlight ดั้งเดิมเพื่อความชัดเจน ---
st.markdown("""
    <style>
    [data-testid="stFileUploadDropzone"] {
        padding: 80px !important;
        border: 2px dashed #4CAF50 !important;
        background-color: #f9f9f9 !important;
        border-radius: 15px !important;
    }
    [data-testid="stFileUploadDropzone"]:hover {
        border-color: #2196F3 !important;
        background-color: #e3f2fd !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 5. UI Main ---
st.title("📝 Thai Word Wrap & Font Fixer")
st.write("เครื่องมือช่วยแก้คำฉีกและเปลี่ยนฟอนต์เป็น Sarabun (รองรับไฟล์จาก Word และ Google Docs)")

uploaded_file = st.file_uploader("📥 ลากไฟล์ .docx มาวางที่นี่เพื่อเริ่มประมวลผล", type="docx")

if uploaded_file is not None:
    st.toast("✅ ได้รับไฟล์แล้ว! กำลังประมวลผล...", icon="🚀")
    
    with st.spinner(f"กำลังจัดการไฟล์: {uploaded_file.name}"):
        try:
            input_zip = zipfile.ZipFile(uploaded_file)
            names = input_zip.namelist()
            output_buffer = io.BytesIO()
            
            with zipfile.ZipFile(output_buffer, "w", zipfile.ZIP_DEFLATED) as output_zip:
                for name in names:
                    content = input_zip.read(name)
                    if re.match(r'word/(document|header\d*|footer\d*|endnotes|footnotes)\.xml$', name):
                        content = process_xml_bytes(content)
                    elif name == 'word/styles.xml':
                        content = patch_styles_bytes(content)
                    output_zip.writestr(name, content)
            
            st.success("🎉 ประมวลผลเสร็จเรียบร้อยแล้ว!")
            
            new_filename = uploaded_file.name.replace(".docx", "_fixed.docx")
            st.download_button(
                label="⬇️ ดาวน์โหลดไฟล์ที่แก้ไขแล้ว",
                data=output_buffer.getvalue(),
                file_name=new_filename,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                type="primary"
            )
            
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")

st.divider()
st.caption("พัฒนาเพื่อช่วยแก้ปัญหาการตัดคำและฟอนต์ภาษาไทย 🚀")