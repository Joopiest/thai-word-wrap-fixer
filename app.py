import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="True Real-time Translator", layout="wide")
st.title("⚡ True Real-time Translator")
st.markdown("ระบบแปลภาษาด่วนแบบ Real-time พัฒนาโดยใช้เทคโนโลยี Web Speech API และ JavaScript")

custom_html = """
<!DOCTYPE html>
<html>
<head>
<style>
  body { 
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
    color: #fff; 
    background-color: #0e1117; 
  }
  .container { padding: 10px; }
  
  .controls-container {
      display: flex;
      gap: 20px;
      margin-bottom: 25px;
  }
  .control-box {
      flex: 1;
      background: #1e2127;
      padding: 15px 20px;
      border-radius: 8px;
      border: 1px solid #333;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
  }
  .control-title {
      font-size: 14px;
      color: #a3a8b8;
      margin-bottom: 12px;
      font-weight: bold;
  }
  
  .lang-selector { display: flex; gap: 25px; }
  .lang-selector label { font-size: 16px; cursor: pointer; color: #e6eaf1; }
  
  .slider-container { display: flex; align-items: center; gap: 15px; width: 90%; }
  input[type=range] { flex: 1; accent-color: #ff4b4b; cursor: pointer; }
  .slider-val { font-size: 16px; color: #e6eaf1; min-width: 80px; }

  .btn-container { text-align: center; margin-bottom: 20px; }
  button { 
    padding: 12px 24px; font-size: 16px; font-weight: bold;
    border: none; border-radius: 8px; cursor: pointer; transition: 0.2s;
  }
  #startBtn { background-color: #ff4b4b; color: white; margin-right: 10px; }
  #stopBtn { background-color: #444; color: white; }

  .output-container { display: flex; gap: 20px; }
  
  /* --- ส่วนที่อัปเดต: ล็อกความสูงและใส่ Scrollbar --- */
  .box { 
    flex: 1; padding: 20px; border-radius: 8px; 
    background: #1e2127; border: 1px solid #333; 
    height: 300px;         /* ล็อกความสูงกล่องไว้ที่ 300px */
    overflow-y: auto;      /* ให้มี Scrollbar แนวตั้งเมื่อข้อความล้น */
  }
  
  /* ปรับแต่งหน้าตา Scrollbar ให้ดูโมเดิร์นเข้ากับเว็บ Dark Mode */
  .box::-webkit-scrollbar { width: 8px; }
  .box::-webkit-scrollbar-track { background: #1e2127; border-radius: 8px; }
  .box::-webkit-scrollbar-thumb { background: #555; border-radius: 8px; }
  .box::-webkit-scrollbar-thumb:hover { background: #777; }
  
  .title { font-weight: bold; color: #a3a8b8; margin-bottom: 15px; font-size: 16px; border-bottom: 1px solid #333; padding-bottom: 10px;}
  .text { font-size: 22px; color: #e6eaf1; line-height: 1.6; }
  .interim { color: #ff4b4b; } 
  .placeholder { color: #555; font-size: 18px; font-style: italic; }
</style>
</head>
<body>

<div class="container">
  
  <div class="controls-container">
    <div class="control-box">
        <div class="control-title">🌍 ทิศทางการแปล</div>
        <div class="lang-selector">
            <label><input type="radio" name="langMode" value="th2en" checked onchange="changeLang()"> 🇹🇭 ไทย ➡️ 🇬🇧 อังกฤษ</label>
            <label><input type="radio" name="langMode" value="en2th" onchange="changeLang()"> 🇬🇧 อังกฤษ ➡️ 🇹🇭 ไทย</label>
        </div>
    </div>
    
    <div class="control-box">
        <div class="control-title">⏱️ ถ้าเงียบเกินกี่วินาที ถึงจะล้างหน้าจอขึ้นพารากราฟใหม่?</div>
        <div class="slider-container">
            <input type="range" id="delaySlider" min="3" max="30" value="10" oninput="updateDelay()">
            <div class="slider-val"><span id="delayValue">10</span> วินาที</div>
        </div>
    </div>
  </div>

  <div class="btn-container">
      <button id="startBtn" onclick="startDictation()">🎤 กดเพื่อพูด (Live)</button>
      <button id="stopBtn" onclick="stopDictation()">⏹️ หยุด</button>
  </div>

  <div class="output-container">
    <!-- เพิ่ม ID ให้กล่อง เพื่อให้ JavaScript สั่งเลื่อน Scrollbar ได้ -->
    <div class="box" id="boxOrig">
      <div id="origTitle" class="title">🇹🇭 ต้นฉบับ (กำลังพูด):</div>
      <div id="original" class="text"><span class="placeholder">[รอรับเสียง...]</span></div>
    </div>
    <div class="box" id="boxTrans">
      <div id="transTitle" class="title">🇬🇧 คำแปล (Real-time):</div>
      <div id="translated" class="text"><span class="placeholder">[รอการแปล...]</span></div>
    </div>
  </div>
</div>

<script>
  let recognition;       
  let isRecognizing = false;
  let isManualStop = false; 
  let isAutoClearing = false; 
  let globalFinalTranscript = ''; 
  
  let clearDelayMs = 10000; 
  let clearTimer;           
  let inactivityTimer;      
  const IDLE_TIMEOUT_MS = 5 * 60 * 1000; 
  
  let sttLang = "th-TH";    
  let srcLang = "th";       
  let destLang = "en";      

  // ฟังก์ชันเลื่อน Scrollbar ลงล่างสุดอัตโนมัติ
  function scrollToBottom(elementId) {
      let box = document.getElementById(elementId);
      box.scrollTop = box.scrollHeight;
  }

  function updateDelay() {
      let val = document.getElementById('delaySlider').value;
      document.getElementById('delayValue').innerText = val;
      clearDelayMs = parseInt(val) * 1000;
  }

  function resetClearTimer() {
      clearTimeout(clearTimer);
      clearTimer = setTimeout(() => {
          globalFinalTranscript = ''; 
          document.getElementById('original').innerHTML = "<span class='placeholder'>[ขึ้นพารากราฟใหม่...]</span>";
          document.getElementById('translated').innerHTML = "<span class='placeholder'>[...]</span>";
          
          if (isRecognizing) {
              isAutoClearing = true;
              recognition.stop(); 
          }
      }, clearDelayMs);
  }

  function resetInactivityTimer() {
    clearTimeout(inactivityTimer); 
    if (isRecognizing) {
      inactivityTimer = setTimeout(() => {
        isManualStop = true; 
        recognition.stop();
        document.getElementById('original').innerHTML = "<span style='font-size:16px; color:#ff4b4b;'><i>ปิดไมค์อัตโนมัติ (ลืมปิดเกิน 5 นาที)</i></span>";
      }, IDLE_TIMEOUT_MS);
    }
  }

  if (window.hasOwnProperty('webkitSpeechRecognition')) {
    recognition = new webkitSpeechRecognition();
    recognition.continuous = true;       
    recognition.interimResults = true;   
    recognition.lang = sttLang;          

    recognition.onstart = function() {
      isRecognizing = true;
      globalFinalTranscript = ''; 
      document.getElementById('startBtn').innerText = "🟢 กำลังฟัง (พูดได้เลย)...";
      document.getElementById('startBtn').style.backgroundColor = "#00cc66";
      resetInactivityTimer(); 
    };

    recognition.onend = function() {
      isRecognizing = false;
      clearTimeout(inactivityTimer);
      clearTimeout(clearTimer);
      
      if (isAutoClearing) { 
          isAutoClearing = false;
          try { recognition.start(); } catch(e){}
          return;
      }

      if (!isManualStop) { 
          try { recognition.start(); return; } catch(e) {}
      }

      document.getElementById('startBtn').innerText = "🎤 กดเพื่อพูด (Live)";
      document.getElementById('startBtn').style.backgroundColor = "#ff4b4b";
    };

    recognition.onresult = function(event) {
      resetInactivityTimer(); 
      clearTimeout(clearTimer); 
      
      let interim_transcript = '';
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          globalFinalTranscript += event.results[i][0].transcript + ' ';
        } else {
          interim_transcript += event.results[i][0].transcript;
        }
      }

      let currentText = globalFinalTranscript + interim_transcript;
      document.getElementById('original').innerHTML = 
        globalFinalTranscript + '<span class="interim">' + interim_transcript + '</span>';

      // เลื่อนกล่องต้นฉบับลงล่างสุด
      scrollToBottom('boxOrig');

      if (currentText.trim() !== "") {
        translateText(currentText, srcLang, destLang);
        resetClearTimer(); 
      }
    };
  }

  function startDictation() {
    if (!isRecognizing) {
      isManualStop = false; 
      isAutoClearing = false;
      recognition.lang = sttLang;
      recognition.start();
    }
  }

  function stopDictation() {
    if (isRecognizing) {
      isManualStop = true; 
      recognition.stop();
    }
  }
  
  function changeLang() {
    let mode = document.querySelector('input[name="langMode"]:checked').value;
    if (mode === "th2en") {
        sttLang = "th-TH"; srcLang = "th"; destLang = "en";
        document.getElementById('origTitle').innerText = "🇹🇭 ต้นฉบับ (กำลังพูด):";
        document.getElementById('transTitle').innerText = "🇬🇧 คำแปล (Real-time):";
    } else {
        sttLang = "en-US"; srcLang = "en"; destLang = "th";
        document.getElementById('origTitle').innerText = "🇬🇧 ต้นฉบับ (กำลังพูด):";
        document.getElementById('transTitle').innerText = "🇹🇭 คำแปล (Real-time):";
    }
    
    if(isRecognizing) {
        isManualStop = true; 
        stopDictation();
    }
  }

  function translateText(text, src, dest) {
    let url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=${src}&tl=${dest}&dt=t&q=${encodeURI(text)}`;
    fetch(url)
      .then(response => response.json())
      .then(data => {
        let translated_text = '';
        for (let i = 0; i < data[0].length; i++) {
           translated_text += data[0][i][0];
        }
        document.getElementById('translated').innerHTML = translated_text;
        
        // เลื่อนกล่องคำแปลลงล่างสุดหลังจากแปลเสร็จ
        scrollToBottom('boxTrans');
      });
  }
</script>
</body>
</html>
"""

# เพิ่มความสูงของกล่อง Iframe เป็น 550 ให้มีพื้นที่รองรับ Scrollbar พอดี
components.html(custom_html, height=550)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #a3a8b8; font-size: 14px;'>Developed by <b>Joopiest Udomsaph</b></p>", unsafe_allow_html=True)