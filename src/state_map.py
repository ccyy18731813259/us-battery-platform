# -*- coding: utf-8 -*-
"""州份额地图 · 浏览器端逐年播放组件

为什么不用 st.plotly_chart：Plotly 原生动画必须由用户点击播放按钮触发，
无法满足「进入页签即自动播放」。这里把图交给 iframe 内的 plotly.js，
由脚本按年份逐帧 restyle：自动开播、播到末帧即停（不循环）、
Streamlit 重跑时 iframe 重建等价于「立即停止并跳到新日期」。
"""
import json

import numpy as np
import streamlit as st

try:
    import streamlit.components.v1 as components
except Exception:      # pragma: no cover - 旧版本兜底
    components = None


_STATE_MAP_TPL = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  html, body { margin:0; padding:0; background:#ffffff;
               font-family:'Noto Sans SC','PingFang SC','Microsoft YaHei',sans-serif; }
  #swrap { position:relative; width:100%; height:__H__px; }
  #shdr  { height:32px; display:flex; align-items:baseline; gap:9px; padding:0 2px; }
  #syear { font-size:21px; font-weight:700; color:#12355B; letter-spacing:.5px;
           font-variant-numeric:tabular-nums; }
  #ssub  { font-size:12.5px; color:#8A8A86; }
  #shint { margin-left:auto; font-size:11.5px; color:#B4B2AA; }
  #smap  { width:100%; height:__H2__px; }
  #sreplay { position:absolute; right:0; bottom:-3px; font-size:11.5px; color:#C6C4BC;
             background:none; border:none; cursor:pointer; padding:2px 4px; }
  #sreplay:hover { color:#2E86AB; }
</style></head>
<body>
<div id="swrap">
  <div id="shdr">
    <span id="syear">—</span><span id="ssub"></span>
    <span id="shint">颜色越深 = 该州占全美进口份额越高　·　悬停查看金额</span>
  </div>
  <div id="smap"></div>
  <button id="sreplay" title="重新播放">↻ 重播</button>
</div>
<script>
(function () {
  var CFG = __CFG__;
  var gd = document.getElementById("smap");
  var elY = document.getElementById("syear");
  var elS = document.getElementById("ssub");
  var CDN = ["https://cdn.plot.ly/plotly-2.35.2.min.js",
             "https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js",
             "https://unpkg.com/plotly.js-dist-min@2.35.2/plotly.min.js"];

  function loadLib(i) {
    if (window.Plotly) return Promise.resolve(true);
    if (i >= CDN.length) return Promise.resolve(false);
    return new Promise(function (res) {
      var s = document.createElement("script");
      s.src = CDN[i];
      s.onload = function () { res(!!window.Plotly); };
      s.onerror = function () { res(loadLib(i + 1)); };
      document.head.appendChild(s);
    });
  }

  function layout() {
    return {
      height: __H2__, margin: { l: 0, r: 0, t: 0, b: 0 },
      paper_bgcolor: "#ffffff",
      font: { family: "'Noto Sans SC',sans-serif", size: 12.5, color: "#3A3A38" },
      geo: { scope: "usa", projection: { type: "albers usa" }, domain: { x: [0, 0.94], y: [0, 1] },
             bgcolor: "rgba(0,0,0,0)", lakecolor: "#FFFFFF", showlakes: true,
             showsubunits: true, subunitcolor: "#8A8A86", subunitwidth: 0.5,
             showcoastlines: false, showland: false }
    };
  }

  function trace(f) {
    return {
      type: "choropleth", locationmode: "USA-states", locations: f.codes,
      z: f.z, customdata: f.cd,
      /* plotly 内置 "Blues" 是低值深、高值浅，与「颜色越深 = 份额越高」相反；
         这里改用标准 ColorBrewer Blues（低值浅、高值深） */
      colorscale: [[0, "#f7fbff"], [0.125, "#deebf7"], [0.25, "#c6dbef"],
                   [0.375, "#9ecae1"], [0.5, "#6baed6"], [0.625, "#4292c6"],
                   [0.75, "#2171b5"], [0.875, "#08519c"], [1, "#08306b"]],
      zmin: 0, zmax: CFG.zmax,
      marker: { line: { color: "#8A8A86", width: 0.7 } },
      colorbar: { title: { text: "占全美份额（%）", side: "top", font: { size: 11 } },
                  thickness: 13, len: 0.68, x: 0.955, xpad: 0, outlinewidth: 0,
                  tickfont: { size: 11 }, ticksuffix: "%" },
      hovertemplate: "<b>%{customdata[0]}</b><br>进口额：%{customdata[1]} 亿美元" +
                     "<br>占全美份额：%{customdata[2]}%<extra></extra>"
    };
  }

  var playing = false, tid = null;

  function show(i) {
    var f = CFG.frames[i];
    Plotly.restyle(gd, { "z": [f.z], "customdata": [f.cd] }, [0]);
    elY.textContent = f.label;
    elS.textContent = f.sub;
  }

  function stop() {
    playing = false;
    if (tid) { clearTimeout(tid); tid = null; }
  }

  function play() {
    stop();
    playing = true;
    var i = 0;
    show(0);
    function tick() {
      if (!playing) return;
      i += 1;
      if (i >= CFG.frames.length) { playing = false; return; }   /* 停在终点帧，不循环 */
      show(i);
      if (i < CFG.frames.length - 1) { tid = setTimeout(tick, 760); }
      else { playing = false; }
    }
    tid = setTimeout(tick, 800);
  }

  function whenVisible(fn) {
    var done = false;
    function go() { if (done) return; done = true; fn(); }
    function vis() {
      var r = gd.getBoundingClientRect();
      return r.width > 12 && r.height > 12;
    }
    if (vis()) return go();
    if (window.IntersectionObserver) {
      var io = new IntersectionObserver(function (es) {
        for (var k = 0; k < es.length; k++) {
          if (es[k].isIntersecting) { io.disconnect(); go(); return; }
        }
      }, { threshold: 0.01 });
      io.observe(gd);
    }
    var n = 0;
    var iv = setInterval(function () {          /* 页签隐藏时等待，进入可见区域后开播 */
      n += 1;
      if (vis()) { clearInterval(iv); go(); }
      else if (n > 120) { clearInterval(iv); go(); }
    }, 250);
  }

  document.getElementById("sreplay").addEventListener("click", function () {
    if (window.Plotly) play();
  });

  loadLib(0).then(function (ok) {
    if (!ok) { elY.textContent = ""; elS.textContent = "图表库加载失败，请检查网络后刷新页面"; return; }
    var last = CFG.frames.length - 1;
    Plotly.newPlot(gd, [trace(CFG.frames[CFG.play ? 0 : last])], layout(),
                   { responsive: true, displayModeBar: false }).then(function () {
      if (CFG.play) { whenVisible(play); }
      else { show(last); }
    });
  });
})();
</script>
</body></html>"""


def show_iframe_html(html: str, height: int):
    """渲染可执行脚本的 iframe（新版用 st.iframe，旧版回退 components.html）"""
    if hasattr(st, "iframe"):
        st.iframe(html, height=height)
    else:
        components.html(html, height=height, scrolling=False)


def state_share_map(frames, play=True, height=480):
    """州份额地图：浏览器端逐年播放，播到终点帧后停止（不循环）。
    页签不可见时等待，进入可见区域才开播；重跑（如修改日期）会重建 iframe，从而立即中断播放。"""
    _mx = max([max(f["z"]) for f in frames] + [1.0])
    _zmax = float(np.ceil(_mx / 2.0) * 2)          # 色标上限取整到 2pp，各帧可比
    payload = json.dumps({"frames": frames, "zmax": _zmax, "play": bool(play)},
                         ensure_ascii=False)
    return (_STATE_MAP_TPL
            .replace("__CFG__", payload)
            .replace("__H2__", str(height - 32))
            .replace("__H__", str(height)))
