import json
import math
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import database

from config import WEB_HOST, WEB_PORT

state = {
    "online": False,
    "raw": "",
    "updated": "-",
    "v": {}
}

state_lock = threading.Lock()


def set_state(online, raw, updated, values):
    with state_lock:
        state["online"] = online
        state["raw"] = raw
        state["updated"] = updated
        state["v"] = dict(values or {})


def get_state():
    with state_lock:
        return {
            "online": state["online"],
            "raw": state["raw"],
            "updated": state["updated"],
            "v": dict(state["v"])
        }


def json_value(v, key):
    x = v.get(key)
    if isinstance(x, (int, float)):
        return x
    return x


def fmt_number(x, digits=1, suffix=""):
    if x is None:
        return "—"
    if isinstance(x, (int, float)):
        return f"{x:.{digits}f}{suffix}"
    return str(x) + suffix


HTML_HOME = r"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>STARK Monitor</title>
<style>
*{box-sizing:border-box}
body{
    margin:0;
    background:#f3f4f6;
    color:#111827;
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif
}
.header{
    background:#111827;
    color:white;
    padding:18px 16px 20px
}
.header-title{font-size:22px;font-weight:700}
.header-sub{margin-top:7px;font-size:14px;color:#d1d5db}
.status{
    display:inline-flex;
    align-items:center;
    gap:7px;
    margin-top:10px;
    font-size:14px
}
.dot{
    width:9px;height:9px;border-radius:50%;
    background:#9ca3af
}
.dot.online{background:#22c55e}
.container{max-width:900px;margin:auto;padding:14px}
.graph-button{
    display:block;
    width:100%;
    border:0;
    border-radius:14px;
    padding:16px;
    margin-bottom:14px;
    background:#2563eb;
    color:white;
    font-size:17px;
    font-weight:700;
    text-decoration:none;
    text-align:center
}
.grid{
    display:grid;
    grid-template-columns:repeat(2,minmax(0,1fr));
    gap:12px
}
.card{
    background:white;
    border-radius:15px;
    padding:16px;
    box-shadow:0 2px 8px rgba(0,0,0,.06)
}
.card-main{min-height:125px}
.card-title{font-size:14px;color:#6b7280;margin-bottom:9px}
.card-value{font-size:29px;line-height:1.1;font-weight:750}
.card-sub{margin-top:8px;color:#6b7280;font-size:13px}
.section{margin-top:18px}
.section-title{font-size:18px;font-weight:700;margin:0 0 10px}
.param{
    display:flex;
    justify-content:space-between;
    gap:12px;
    padding:10px 0;
    border-bottom:1px solid #e5e7eb
}
.param:last-child{border-bottom:0}
.param-name{color:#4b5563}
.param-value{font-weight:650;text-align:right}
@media(max-width:500px){
    .card-value{font-size:25px}
    .card-main{min-height:115px}
}
</style>
</head>
<body>

<div class="header">
    <div class="header-title">STARK COUNTRY 2000 INV MAX</div>
    <div class="header-sub">Мониторинг инвертора</div>
    <div class="status">
        <span id="dot" class="dot"></span>
        <span id="status">Проверка связи…</span>
        <span>·</span>
        <span id="updated">—</span>
    </div>
</div>

<div class="container">

<a class="graph-button" href="/graphs">📈 ГРАФИКИ</a>

<div class="grid">

<div class="card card-main">
<div class="card-title">☀️ СОЛНЦЕ</div>
<div class="card-value" id="pv_power">—</div>
<div class="card-sub" id="pv_detail">PV</div>
</div>

<div class="card card-main">
<div class="card-title">⚡ ПОТРЕБЛЕНИЕ</div>
<div class="card-value" id="load_w">—</div>
<div class="card-sub" id="load_detail">Нагрузка</div>
</div>

<div class="card card-main">
<div class="card-title">🔋 АКБ</div>
<div class="card-value" id="battery_voltage">—</div>
<div class="card-sub" id="battery_detail">—</div>
</div>

<div class="card card-main">
<div class="card-title">🌐 СЕТЬ</div>
<div class="card-value" id="grid_voltage">—</div>
<div class="card-sub" id="grid_detail">—</div>
</div>

</div>

<div class="section">
<div class="section-title">☀️ Солнечные панели</div>
<div class="card">
<div class="param"><span class="param-name">PV мощность</span><span class="param-value" id="p_pv_power">—</span></div>
<div class="param"><span class="param-name">PV напряжение</span><span class="param-value" id="p_pv_voltage">—</span></div>
<div class="param"><span class="param-name">PV ток</span><span class="param-value" id="p_pv_current">—</span></div>
<div class="param"><span class="param-name">Ток заряда от PV</span><span class="param-value" id="p_pv_charge_current">—</span></div>
<div class="param"><span class="param-name">Расчётная мощность PV</span><span class="param-value" id="p_pv_calc">—</span></div>
</div>
</div>

<div class="section">
<div class="section-title">⚡ Нагрузка / выход</div>
<div class="card">
<div class="param"><span class="param-name">Мощность</span><span class="param-value" id="p_load_w">—</span></div>
<div class="param"><span class="param-name">Полная мощность</span><span class="param-value" id="p_load_va">—</span></div>
<div class="param"><span class="param-name">Нагрузка</span><span class="param-value" id="p_load_percent">—</span></div>
<div class="param"><span class="param-name">Напряжение выхода</span><span class="param-value" id="p_output_voltage">—</span></div>
<div class="param"><span class="param-name">Частота выхода</span><span class="param-value" id="p_output_frequency">—</span></div>
</div>
</div>

<div class="section">
<div class="section-title">🔋 Аккумулятор</div>
<div class="card">
<div class="param"><span class="param-name">Напряжение</span><span class="param-value" id="p_battery_voltage">—</span></div>
<div class="param"><span class="param-name">Заряд</span><span class="param-value" id="p_battery_capacity">—</span></div>
<div class="param"><span class="param-name">Ток заряда</span><span class="param-value" id="p_battery_charge_current">—</span></div>
<div class="param"><span class="param-name">Мощность заряда</span><span class="param-value" id="p_battery_charge_power">—</span></div>
<div class="param"><span class="param-name">Шина DC</span><span class="param-value" id="p_bus_voltage">—</span></div>
</div>
</div>

<div class="section">
<div class="section-title">🌐 Сеть</div>
<div class="card">
<div class="param"><span class="param-name">Напряжение сети</span><span class="param-value" id="p_grid_voltage">—</span></div>
<div class="param"><span class="param-name">Частота сети</span><span class="param-value" id="p_grid_frequency">—</span></div>
</div>
</div>

<div class="section">
<div class="section-title">🌡 Инвертор</div>
<div class="card">
<div class="param"><span class="param-name">Температура</span><span class="param-value" id="p_temperature">—</span></div>
<div class="param"><span class="param-name">Status</span><span class="param-value" id="p_status">—</span></div>
<div class="param"><span class="param-name">Field 15</span><span class="param-value" id="p_field15">—</span></div>
<div class="param"><span class="param-name">Field 17</span><span class="param-value" id="p_field17">—</span></div>
<div class="param"><span class="param-name">Field 18</span><span class="param-value" id="p_field18">—</span></div>
<div class="param"><span class="param-name">Device status</span><span class="param-value" id="p_device_status">—</span></div>
</div>
</div>

    <div class="section">
        <div class="section-title">🛠 Служебные данные</div>
        <div class="card">
            <div class="param">
                <span class="param-name">Последний ответ</span>
                <span class="param-value" id="raw_updated">—</span>
            </div>
            <div style="margin-top:12px">
                <div class="param-name" style="margin-bottom:7px">Сырой QPIGS</div>
                <pre id="raw_qpigs" style="
                    margin:0;
                    padding:12px;
                    background:#f3f4f6;
                    border-radius:10px;
                    white-space:pre-wrap;
                    word-break:break-all;
                    font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;
                    color:#374151;
                ">—</pre>
            </div>
        </div>
    </div>

</div>

<script>
function fmt(x,unit="",digits=1){
    if(x===null||x===undefined)return "—";
    if(typeof x==="number")return x.toFixed(digits)+unit;
    return String(x)+unit;
}

function setv(id,x,unit="",digits=1){
    const e=document.getElementById(id);
    if(e)e.textContent=fmt(x,unit,digits);
}

async function update(){
    try{
        const r=await fetch("/api/state",{cache:"no-store"});
        const d=await r.json();
        const v=d.v||{};

        document.getElementById("dot").classList.toggle("online",!!d.online);
        document.getElementById("status").textContent=d.online?"Связь есть":"Нет связи";
        document.getElementById("updated").textContent=d.updated||"—";
          document.getElementById("raw_updated").textContent=d.updated||"—";
          document.getElementById("raw_qpigs").textContent=d.raw||"—";

        setv("pv_power",v.pv_power," W",0);
        setv("pv_detail",v.pv_voltage," V");
        setv("load_w",v.load_w," W",0);
        setv("load_detail",v.load_percent," %",0);
        setv("battery_voltage",v.battery_voltage," V",2);
        setv("battery_detail",v.battery_capacity," %",0);
        setv("grid_voltage",v.grid_voltage," V");
        setv("grid_detail",v.grid_frequency," Hz");

        setv("p_pv_power",v.pv_power," W",0);
        setv("p_pv_voltage",v.pv_voltage," V");
        setv("p_pv_current",v.pv_current," A");
        setv("p_pv_charge_current",v.pv_charge_current," A");
        setv("p_pv_calc",v.pv_calculated_power," W",0);

        setv("p_load_w",v.load_w," W",0);
        setv("p_load_va",v.load_va," VA",0);
        setv("p_load_percent",v.load_percent," %",0);
        setv("p_output_voltage",v.output_voltage," V");
        setv("p_output_frequency",v.output_frequency," Hz");

        setv("p_battery_voltage",v.battery_voltage," V",2);
        setv("p_battery_capacity",v.battery_capacity," %",0);
        setv("p_battery_charge_current",v.battery_charge_current," A",1);
        setv("p_battery_charge_power",v.battery_charge_power," W",1);
        setv("p_bus_voltage",v.bus_voltage," V",0);

        setv("p_grid_voltage",v.grid_voltage," V");
        setv("p_grid_frequency",v.grid_frequency," Hz");

        setv("p_temperature",v.temperature," °C",1);
        setv("p_status",v.status);
        setv("p_field15",v.field15);
        setv("p_field17",v.field17);
        setv("p_field18",v.field18);
        setv("p_device_status",v.device_status);

    }catch(e){
        document.getElementById("dot").classList.remove("online");
        document.getElementById("status").textContent="Ошибка связи";
    }
}

update();
setInterval(update,2000);
</script>
</body>
</html>
"""


HTML_GRAPHS = r"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>STARK — Графики</title>
<style>
*{box-sizing:border-box}
body{
    margin:0;
    background:#f3f4f6;
    color:#111827;
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif
}
.header{
    background:#111827;
    color:white;
    padding:18px 16px
}
.header-title{font-size:22px;font-weight:700}
.header-sub{margin-top:6px;color:#d1d5db;font-size:14px}
.container{max-width:1000px;margin:auto;padding:14px}
.back{
    display:block;
    text-decoration:none;
    color:#2563eb;
    font-weight:700;
    margin-bottom:12px
}
.controls{
    background:white;
    border-radius:15px;
    padding:14px;
    box-shadow:0 2px 8px rgba(0,0,0,.06);
    margin-bottom:14px
}
.periods{
    display:grid;
    grid-template-columns:repeat(5,1fr);
    gap:8px;
    margin-bottom:14px
}
button{
    border:0;
    border-radius:10px;
    padding:11px 8px;
    background:#e5e7eb;
    color:#111827;
    font-weight:650;
    cursor:pointer
}
button.active{
    background:#2563eb;
    color:white
}
.metrics{
    display:grid;
    grid-template-columns:repeat(2,1fr);
    gap:8px
}
.metric{
    display:flex;
    align-items:center;
    gap:8px;
    font-size:14px
}
.chart-card{
    background:white;
    border-radius:15px;
    padding:12px;
    margin-bottom:14px;
    box-shadow:0 2px 8px rgba(0,0,0,.06)
}
.chart-title{
    font-size:17px;
    font-weight:700;
    margin:4px 4px 10px
}
canvas{
    width:100%;
    height:260px;
    display:block
}
.info{
    color:#6b7280;
    font-size:13px;
    margin-top:8px
}
@media(max-width:600px){
    .periods{grid-template-columns:repeat(3,1fr)}
    .metrics{grid-template-columns:1fr}
    canvas{height:230px}
}
</style>
</head>
<body>

<div class="header">
<div class="header-title">📈 Графики</div>
<div class="header-sub">STARK COUNTRY 2000 INV MAX</div>
</div>

<div class="container">

<a class="back" href="/">← На главную</a>

<div class="controls">

<div class="periods">
<button data-hours="1">1 час</button>
<button data-hours="6">6 часов</button>
<button data-hours="24" class="active">24 часа</button>
<button data-hours="168">7 дней</button>
<button data-hours="720">30 дней</button>
</div>

<div class="metrics">
<label class="metric"><input type="checkbox" value="pv_power" checked> ☀️ Солнце</label>
<label class="metric"><input type="checkbox" value="load_w" checked> ⚡ Потребление</label>
<label class="metric"><input type="checkbox" value="battery_capacity" checked> 🔋 Заряд АКБ</label>
<label class="metric"><input type="checkbox" value="battery_voltage"> 🔋 Напряжение АКБ</label>
<label class="metric"><input type="checkbox" value="grid_voltage"> 🌐 Напряжение сети</label>
<label class="metric"><input type="checkbox" value="grid_frequency"> 🌐 Частота сети</label>
<label class="metric"><input type="checkbox" value="pv_voltage"> ☀️ Напряжение PV</label>
<label class="metric"><input type="checkbox" value="pv_current"> ☀️ Ток PV</label>
</div>

<div class="info" id="info">Загрузка…</div>

</div>

<div id="charts"></div>

</div>

<script>
const names={
    pv_power:["☀️ Мощность солнца","W"],
    load_w:["⚡ Потребление","W"],
    battery_capacity:["🔋 Заряд АКБ","%"],
    battery_voltage:["🔋 Напряжение АКБ","V"],
    grid_voltage:["🌐 Напряжение сети","V"],
    grid_frequency:["🌐 Частота сети","Hz"],
    pv_voltage:["☀️ Напряжение PV","V"],
    pv_current:["☀️ Ток PV","A"]
};

let hours=24;

function selected(){
    return [...document.querySelectorAll(".metric input:checked")].map(x=>x.value);
}

function nice(v){
    if(v>=1000)return (v/1000).toFixed(1)+"k";
    if(v>=100)return v.toFixed(0);
    if(v>=10)return v.toFixed(1);
    return v.toFixed(2);
}

function draw(canvas,rows,metric){
    const ctx=canvas.getContext("2d");
    const rect=canvas.getBoundingClientRect();
    const dpr=window.devicePixelRatio||1;
    canvas.width=rect.width*dpr;
    canvas.height=rect.height*dpr;
    ctx.scale(dpr,dpr);

    const W=rect.width,H=rect.height;
    const pad={l:48,r:12,t:18,b:30};

    ctx.clearRect(0,0,W,H);

    const values=rows
        .map(x=>Number(x[metric]))
        .filter(Number.isFinite);

    if(!values.length){
        ctx.fillStyle="#6b7280";
        ctx.font="14px sans-serif";
        ctx.fillText("Нет данных",pad.l,50);
        return;
    }

    let min=Math.min(...values);
    let max=Math.max(...values);

    if(min===max){
        min-=1;
        max+=1;
    }else{
        const margin=(max-min)*0.08;
        min-=margin;
        max+=margin;
    }

    const cw=W-pad.l-pad.r;
    const ch=H-pad.t-pad.b;

    ctx.strokeStyle="#e5e7eb";
    ctx.lineWidth=1;
    ctx.fillStyle="#6b7280";
    ctx.font="11px sans-serif";

    for(let i=0;i<=4;i++){
        const y=pad.t+ch*i/4;
        ctx.beginPath();
        ctx.moveTo(pad.l,y);
        ctx.lineTo(W-pad.r,y);
        ctx.stroke();

        const val=max-(max-min)*i/4;
        ctx.fillText(nice(val),4,y+4);
    }

    const first=rows[0].ts;
    const last=rows[rows.length-1].ts;
    const span=Math.max(1,last-first);

    ctx.beginPath();
    let started=false;

    rows.forEach(row=>{
        const v=Number(row[metric]);
        if(!Number.isFinite(v))return;

        const x=pad.l+((row.ts-first)/span)*cw;
        const y=pad.t+(max-v)/(max-min)*ch;

        if(!started){
            ctx.moveTo(x,y);
            started=true;
        }else{
            ctx.lineTo(x,y);
        }
    });

    ctx.strokeStyle="#2563eb";
    ctx.lineWidth=2;
    ctx.stroke();

    ctx.fillStyle="#6b7280";

    const labels=4;
    for(let i=0;i<=labels;i++){
        const ts=first+span*i/labels;
        const x=pad.l+cw*i/labels;
        const date=new Date(ts*1000);
        let text;

        if(hours<=24){
            text=date.toLocaleTimeString("ru-RU",{hour:"2-digit",minute:"2-digit"});
        }else{
            text=date.toLocaleDateString("ru-RU",{day:"2-digit",month:"2-digit"});
        }

        ctx.fillText(text,Math.max(0,x-18),H-8);
    }
}

function render(rows,metrics){
    const root=document.getElementById("charts");
    root.innerHTML="";

    metrics.forEach(metric=>{
        const card=document.createElement("div");
        card.className="chart-card";

        const title=document.createElement("div");
        title.className="chart-title";
        title.textContent=names[metric][0];

        const canvas=document.createElement("canvas");

        card.appendChild(title);
        card.appendChild(canvas);
        root.appendChild(card);

        draw(canvas,rows,metric);
    });
}

let graphRows = [];
let graphMetrics = [];

async function load(){
    const metrics=selected();

    if(!metrics.length){
        graphRows=[];
        graphMetrics=[];
        document.getElementById("charts").innerHTML="";
        document.getElementById("info").textContent="Выберите хотя бы один параметр";
        return;
    }

    const qs=new URLSearchParams();
    qs.set("hours",hours);
    qs.set("metrics",metrics.join(","));

    try{
        const r=await fetch("/api/history?"+qs.toString(),{cache:"no-store"});
        const d=await r.json();

        if(!d.ok){
            throw new Error(d.error||"API error");
        }

        graphRows=d.rows;
        graphMetrics=metrics;

        render(graphRows,graphMetrics);

        document.getElementById("info").textContent=
            `Период: ${d.period} · точек: ${d.rows.length} · шаг: ${d.step} сек`;
    }catch(e){
        document.getElementById("info").textContent="Ошибка загрузки графика: "+e;
    }
}

document.querySelectorAll("[data-hours]").forEach(button=>{
    button.addEventListener("click",()=>{
        document.querySelectorAll("[data-hours]").forEach(x=>x.classList.remove("active"));
        button.classList.add("active");
        hours=Number(button.dataset.hours);
        load();
    });
});

document.querySelectorAll(".metric input").forEach(x=>{
    x.addEventListener("change",load);
});

let resizeTimer = null;

window.addEventListener("resize",()=>{
    clearTimeout(resizeTimer);

    resizeTimer=setTimeout(()=>{
        if(graphRows.length && graphMetrics.length){
            render(graphRows,graphMetrics);
        }
    },150);
});

load();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        return

    def send_text(self, text, content_type="text/html; charset=utf-8", status=200):
        data=text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type",content_type)
        self.send_header("Content-Length",str(len(data)))
        self.send_header("Cache-Control","no-store")
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, obj, status=200):
        data=json.dumps(obj,ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(data)))
        self.send_header("Cache-Control","no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed=urlparse(self.path)
        path=parsed.path
        qs=parse_qs(parsed.query)

        if path=="/":
            self.send_text(HTML_HOME)
            return

        if path=="/graphs":
            self.send_text(HTML_GRAPHS)
            return

        if path=="/api/state":
            self.send_json(get_state())
            return

        if path=="/api/history":
            self.api_history(qs)
            return

        self.send_text("404",status=404)

    def api_history(self,qs):
        try:
            hours=float(qs.get("hours",["24"])[0])

            if hours<=0:
                raise ValueError("hours must be > 0")

            hours=min(hours,720)

            metrics_text=qs.get("metrics",[""])[0]
            metrics=[x.strip() for x in metrics_text.split(",") if x.strip()]

            allowed={
                "grid_voltage",
                "grid_frequency",
                "output_voltage",
                "output_frequency",
                "load_w",
                "load_percent",
                "battery_voltage",
                "battery_capacity",
                "battery_charge_current",
                "pv_current",
                "pv_voltage",
                "pv_power",
                "temperature"
            }

            metrics=[x for x in metrics if x in allowed]

            if not metrics:
                self.send_json({
                    "ok":False,
                    "error":"no valid metrics"
                },400)
                return

            end_ts=int(time.time())
            start_ts=int(end_ts-hours*3600)

            # Цель — не тащить в браузер тысячи/десятки тысяч точек.
            # До ~600 точек на график вполне достаточно для плавного отображения.
            target_points=600
            duration=max(1,end_ts-start_ts)
            step=max(1,int(math.ceil(duration/target_points)))

            rows=database.history(
                start_ts,
                end_ts,
                metrics,
                step=step
            )

            self.send_json({
                "ok":True,
                "period":f"{hours:g} ч",
                "start_ts":start_ts,
                "end_ts":end_ts,
                "step":step,
                "metrics":metrics,
                "rows":rows
            })

        except Exception as e:
            self.send_json({
                "ok":False,
                "error":repr(e)
            },500)


def start_server():
    server=ThreadingHTTPServer((WEB_HOST,WEB_PORT),Handler)
    print(f"STARK WEB: http://0.0.0.0:{WEB_PORT}",flush=True)
    server.serve_forever()
